# Company Knowledge Graph

Explore documented relationships between companies, trace claims to source records, and manage evidence-led research batches in a local browser app.

This repository includes the application and a portable copy of [published graph revision 89](snapshots/revision-89.json). The graph contains 2,822 company and entity records, 3,936 relationships, 4,745 claims, and 2,920 source records.

## Run on Windows

Clone this repository or download and extract it from GitHub. In PowerShell, open the repository folder and run the following with Python 3.13 installed.

```powershell
python -m pip install -r requirements.txt
Expand-Archive -LiteralPath .\snapshots\revision-89.zip -DestinationPath .\data
python launch.py
```

Extract the snapshot once in a fresh checkout. If the app already has a graph database in `data`, use a separate checkout to explore this snapshot. After the first launch, use `START.cmd` and `STOP.cmd` to open and stop the app.

Use the company search to open a neighborhood. Select a connection to see the underlying relationships, claims, and source links. The app can export the graph as JSON through the Revisions view.

## Snapshot scope

The archive contains the active published graph, including the research queue, source records, and published batch identifiers. Earlier database revisions, draft proposals, quote and market data caches, raw source downloads, and local browser settings are outside this snapshot. The local revision history starts at revision 89. The [manifest](snapshots/revision-89.json) records the graph and archive checksums.

## Development

The prebuilt browser app is in `frontend/dist`. To rebuild after frontend changes, run `npm ci` and `npm run build` from `frontend`. Run `python -m pytest tests -q` from the repository root to check the backend. See the [research playbook](docs/playbook.md), [API contract](CONTRACT.md), and [third-party notices](THIRD_PARTY_NOTICES.md).
