"""Prepare a reviewable Pages snapshot from the local graph database."""

import argparse
from collections import defaultdict
import ipaddress
import json
from pathlib import Path
import sqlite3
from urllib.parse import parse_qsl, urlsplit


STARTERS = {"AAPL", "MSFT", "AMZN", "NVDA", "TSMC", "CRM", "KO"}
COMPANY_FIELDS = ("id", "name", "country", "status", "aliases")
RELATIONSHIP_FIELDS = (
    "id", "source_id", "target_id", "type", "description", "status",
    "direction", "direction_review_status", "evidence_grade", "known_from",
)


def select_fields(record, fields):
    return {key: record[key] for key in fields if record.get(key) is not None}


def public_url(url):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            return False
        if "." not in host or host.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass
        sensitive = {"access_token", "api_key", "apikey", "auth", "key", "password", "signature", "sig", "token"}
        return not any(key.lower() in sensitive or key.lower().startswith("x-amz-")
                       for key, _ in parse_qsl(parsed.query))
    except ValueError:
        return False


def export(database, destination):
    database = database.resolve(strict=True)
    wal = database.with_name(database.name + "-wal")
    query = "SELECT revision, created_at, snapshot FROM revisions ORDER BY revision DESC LIMIT 1"
    uri = database.as_uri() + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            revision, created_at, raw = connection.execute(query).fetchone()
    except sqlite3.OperationalError:
        if wal.exists():
            raise
        before = database.stat()
        with sqlite3.connect(uri + "&immutable=1", uri=True) as connection:
            revision, created_at, raw = connection.execute(query).fetchone()
        after = database.stat()
        if wal.exists() or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("The database changed while exporting. Retry after it is idle.")
    snapshot = json.loads(raw)
    instruments = defaultdict(list)
    for row in snapshot["instruments"]:
        if row.get("ticker"):
            instruments[row["company_id"]].append(row)

    companies = []
    for row in snapshot["companies"]:
        company = select_fields(row, COMPANY_FIELDS)
        listings = instruments[row["id"]]
        if listings:
            primary = next((item for item in listings if item.get("is_primary")), listings[0])
            company["primary_ticker"] = primary["ticker"]
            company["tickers"] = sorted({item["ticker"] for item in listings})
        companies.append(company)

    company_ids = {row["id"] for row in companies}
    if missing := STARTERS - company_ids:
        raise ValueError(f"Missing starting companies: {', '.join(sorted(missing))}")

    superseded = {row.get("supersedes_id") for row in snapshot["claims"]}
    source_ids_by_edge = defaultdict(set)
    for row in snapshot["claims"]:
        if row.get("relationship_id") and row["id"] not in superseded:
            source_ids_by_edge[row["relationship_id"]].update(row.get("source_ids") or [])
    sources = {
        row["id"]: {"title": row.get("title") or "Source document", "url": row["url"]}
        for row in snapshot["sources"] if public_url(row.get("url") or "")
    }

    relationships = []
    for row in snapshot["relationships"]:
        if row.get("legacy_retention") == "excluded" or row.get("evidence_grade") not in {
            "primary_explicit", "attributed_explicit",
        }:
            continue
        if not {row["source_id"], row["target_id"]} <= company_ids:
            continue
        edge = select_fields(row, RELATIONSHIP_FIELDS)
        ids = source_ids_by_edge[row["id"]] or set(row.get("source_ids") or [])
        edge["source_ids"] = sorted(ids & sources.keys())
        relationships.append(edge)

    used_sources = {identifier for row in relationships for identifier in row["source_ids"]}
    payload = {
        "revision": revision,
        "date": created_at[:10],
        "companies": companies,
        "relationships": relationships,
        "sources": {key: sources[key] for key in sorted(used_sources)},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Revision {revision}: {len(companies):,} companies, {len(relationships):,} relationships, "
          f"{len(used_sources):,} linked sources")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "public/data/graph.json")
    args = parser.parse_args()
    export(args.database, args.output)
