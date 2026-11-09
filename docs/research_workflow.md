# Running the next research batch

This application stores a graph and research history. Codex performs the research when requested. There is no background autonomous search or new company batch in the initial delivery.

## Start

1. Inspect the current revision, company/project details and research queue.
2. Choose a root or existing frontier item, facets, mode and cutoff. Use the reusable request below.
3. Read the playbook, taxonomy, source registry and query checklist. Resolve identity and declare source review slots.
4. Research within the local two-hop budget. Company mode investigates up to 25 companies; project mode up to five projects. Extract all entries in disclosed relevant lists even when more than 25 names appear.
5. Produce a batch JSON, process-coverage report, exclusions/access gaps and resumable next frontier.
6. Validate, inspect the diff, correct errors, and publish the authorized local batch. Export the revision and verify it matches the proposed change.

## Ready-to-copy company request

> Continue the company knowledge graph from company ID **[ID]** or frontier item **[ID]**, using the current graph revision and a public-information cutoff of **[YYYY-MM-DD]**. Investigate **[selected facets]** in company mode. Apply the playbook: enumerate all names in relevant dated official lists, investigate at most 25 distinct companies, and add no more than two company hops from this batch's root. Read the root's latest three annual reports and two available interim/earnings updates and each deeply investigated counterparty's latest annual report plus relationship disclosures. Preserve explicit primary/attributed evidence, unknown quantities, dates, conflicts and private entities. Produce and validate the versioned batch, publish valid changes within this authorized local task, report coverage and unresolved leads, and save the next frontier. Do not run statistical or trading experiments.

## Ready-to-copy project request

> Continue the company knowledge graph from project ID **[ID]**, or identify projects explicitly described for company ID **[ID]**, with cutoff **[YYYY-MM-DD]**. Use project mode, investigate at most five projects, and enumerate all named participants and their evidenced roles. Inspect project/SPV, sponsor, lender, utility, planning and award documents. Distinguish equity, debt, leases, offtake, guarantees, grants, arrangements and advisory work. No inferred participant clique and no deeper participant-company ecosystem investigation in this batch. Produce, validate and publish the authorized local batch, report source coverage and gaps, and queue participant-company investigations separately.

## Pause and resume

Finish a batch when its investigation budget, two-hop frontier or declared source checklist is exhausted. Keep blocked and pending tasks; do not equate a stopped search with no relationship. Future batches can begin at those tasks and extend the accumulated graph.

When evidence is inaccessible, save the official URL, query, attempted route, date, relevant lead and specific missing passage. Do not use a search snippet as if the full document was read. When documents disagree, retain both and explain the different periods, scopes or unresolved contradiction.

For a stale base revision, inspect the intervening update and regenerate the proposal against the active revision. Do not overwrite IDs. A revision restore creates another revision rather than deleting the intervening work.

## What to report after publication

Give the new revision and batch ID; counts of added/changed companies, relationships, claims, projects and frontier items; source/document coverage; list extraction and identity-resolution counts; evidence gaps; and the next useful frontier. Explain whether any relationship is only planned, attributed, ambiguous, or unquantified. Do not imply that graph size measures completeness or signal quality.
