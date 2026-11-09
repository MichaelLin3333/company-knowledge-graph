# Research batch format and publication

The machine-readable contract is `schemas/batch_v1.schema.json`. It validates structure. The application additionally checks existing IDs, explicit evidence, public dates, product attribution, two-hop reachability and revision consistency.

## Files and lifecycle

- `templates/batch_v1.empty.json` is valid JSON/schema and contains no research. Fill a real root, current `base_revision`, cutoff and stable batch ID before validating for publication. Empty roots intentionally cannot publish.
- `templates/batch_v1.fictional_example.json` demonstrates two explicit adjacent supply relationships and a project, without creating a transitive supplier shortcut or project clique.
- `templates/batch_v1.fictional_correction.json` demonstrates claim supersession and explicit object/status updates after that example has been published into an isolated database.
- Both example batches are **fictional fixtures** with reserved `.invalid` URLs. They are not evidence and must not be published into the research database.

Prepare a batch against the active revision. Validation stages a durable proposal and returns errors, warnings, an additions/updates diff, coverage and bounded graph preview. It does not change active research. Publication rechecks the base revision and commits the complete proposal atomically.

A validated local batch can be published by Codex within the user's authorized research task. The application's review buttons are available to the user; they are not a requirement for another approval question on every reversible local update.

Identical batch ID and content is idempotent. A reused ID with different content conflicts. If another update changed the base revision, inspect its diff and prepare an updated proposal with a new batch identity as needed. Do not silently rebase a factual conflict.

## Top-level fields

| Field | Meaning |
|---|---|
| `schema_version` | `"1.0"` |
| `batch_id`, `name` | Stable machine ID and readable description. Never reuse an ID for different content. |
| `base_revision` | Active revision the research proposal was prepared against. |
| `cutoff` | ISO day; public knowledge after this date is excluded from the batch. |
| `mode` | `company` or `project`. |
| `root_company_ids`, `root_project_ids` | Existing or proposed resolved roots. Company mode needs a company root; project mode needs a project root. |
| `max_additional_hops` | `2` in v1. This is local to this batch, not the total accumulated graph depth. |
| `investigated_company_ids` | Distinct companies deeply investigated; at most 25 in company mode and none in project mode. Identity/list enumeration is separate. |
| `investigated_project_ids` | Projects investigated; at most five in project mode. |
| Object arrays | `companies`, `instruments`, `sources`, `relationships`, `claims`, `projects`, `participations`, `frontier`, `coverage`. All objects have stable `id`. |
| `supersedes_claim_ids` | Existing claim IDs replaced by new claims with corresponding `supersedes_id`; history is retained. |
| `record_updates` | Explicit changes to existing object fields with reason and claim support. Optional; defaults to an empty array. |
| `research_log` | Searches, section reviews, list extraction, blocked access, exclusions and next actions. |

The framework preserves additional fields. That allows original-language passages, original names, exact financial instruments, document IDs, and coverage details to survive export. Unknown additional fields do not bypass admission checks.

## Object meanings

**Company:** legal/economic identity, country, status, parent, aliases, notes and review date. Legal parentage, issuer equivalence and broader affiliation remain separate fields. Parent IDs must resolve and cannot create cycles.

**Instrument:** ticker, exchange, currency and primary flag, attached to a company ID. A second share class or ADR does not create a second company. Quotes are independent cached observations, outside research revisions.

**Source:** title, publisher, public URL, publication date/precision, retrieval time and locator. Preserve source-specific original document identifiers where syndicated copies repeat the same announcement. A fiscal year is not a publication date.

**Relationship:** resolved `source_id` and `target_id` are **company IDs**, not citation IDs. Store type, description, status, evidence grade, direction/review status, scope, product/project, dates, batch and supporting claim IDs. A directed edge needs reviewed, explicit direction. If two parties have distinct roles, keep parallel relationships.

**Claim:** one supported assertion. Bilateral claims use `entity_kind: "relationship"` (or omit it for compatibility), a relationship ID, matching subject/object company IDs, predicate, text, evidence grade, source IDs, locator, supporting text, public date/precision and optional terms. New accepted claims permit primary or attributed explicit evidence only.

A product-specific relationship needs a claim's `product` or `product_scope` to match it. This records the explicit assignment; it cannot be assembled from a product catalogue and generic supplier list.

Company/project factual claims can instead use `entity_kind: "company"` with `company_id`, or `entity_kind: "project"` with `project_id`; `relationship_id` is null. The object endpoint can be null. These claims support company status or project updates without inventing a bilateral relationship.

**Term:** value, unit, fiscal/contract period, scope/denominator, its own evidence date and source IDs. Leave `terms: []` when no quantity is disclosed. An explicitly recorded quantity requires units; unknown value/date/period remains null rather than a fabricated value. Do not inherit a current number's date from an older relationship.

**Project:** physical facility/program context, location, stage, description, sources, milestones and terms. An established corporate SPV has its own company node and may be referenced by `spv_company_id`.

**Participation:** project ID, company ID, exact role, sources and supporting claim IDs. It needs an atomic project claim with `predicate: "project_role"`, the same `company_id`, `project_id` and `role`. A generic project-plan claim cannot establish an unrelated company or financing role. It creates no pairwise company edge. A lender/borrower, lessor/lessee or supplier/customer edge requires separate explicit bilateral evidence.

**Frontier:** company **or** project ID, facet, status, local depth, root, parent item, reason, sources and next action. Use exactly one resolved company/project. For an ambiguous list entry, attach an `unresolved_name` lead to the originating resolved company's item and retain the list locator in notes/reason. Never invent an unresolved company node solely to satisfy an endpoint.

**Coverage:** source review slots, list extraction or branch states. Use `kind` to distinguish `document_review`, `list_enumeration`, `branch`, `access_gap` or other recorded process metrics. Store actual counts and gaps without claiming a true-network completeness percentage.

## Dates and historical views

Accepted precisions are `time`, `day`, `month`, `year` and `unknown`. Unknown date means JSON `null`. Time uses an ISO timestamp with offset or `Z`. Use `YYYY-MM-DD` for day, `YYYY-MM` for month and `YYYY` for year. Month/year values preserve their precision. The backend uses the end of a month/year conservatively for day-cutoff eligibility; it does not invent an earlier public day.

The source's public date and claim's knowledge date cannot exceed the cutoff. A future effective date or opening milestone can be retained as a planned fact if disclosed before cutoff. Unknown-dated claims stay out of historical graph views.

An `as_of` view is a filter over recorded dated assertions, not a claim that the historical network is complete. Revision restoration gives the research state saved at that revision. It is different from filtering today's evidence by an historical public date. A current quote keeps its current timestamp in either case.

## Corrections and conflicts

New arrays add objects; they do not silently overwrite an existing ID. Use new claims with `supersedes_id` for corrected assertions. Reference conflicting existing claims using `conflict_with_ids`, keeping both visible. A supersession must refer to the same relationship or factual entity.

Explicit object changes have this shape:

```json
{
  "kind": "relationships",
  "id": "existing_relationship_id",
  "changes": {"status": "cancelled"},
  "claim_ids": ["new_sourced_cancellation_claim"],
  "reason": "The new cited disclosure explicitly cancels the agreement."
}
```

Allowed kinds are companies, instruments, relationships, projects, participations, frontier and coverage. IDs and relationship endpoints remain immutable. Factual changes need claims tied to the affected company, project or relationship. Administrative frontier/coverage status changes need a reason and may have empty claim IDs. Prior snapshots remain unchanged.

## Validation checklist

Before publishing, check references, exact endpoints, issuer duplicates, source passage/locator, direction, claim/source public dates, own dates and units on numbers, status, product assignment, project roles, investigation budget and actual two-hop adjacency. Invalid proposals publish nothing. Claims do not become stronger because several copied announcements cite them.

The JSON schema cannot prove a passage is truthful, independent or correctly translated. Codex must read and record the underlying evidence. Automated admission checks protect structure and semantics; they do not replace research judgment.
