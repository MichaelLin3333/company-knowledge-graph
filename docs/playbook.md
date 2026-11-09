# Company relationship research playbook

A reusable method for extending the graph from any technology company, across industries, countries and public/private ownership. Research produces dated, explicit connections and a resumable frontier. It does not infer stock-price transmission, rank stocks or run a signal experiment.

The application starts from the frozen earlier atlas. Subsequent company research is published in separate dated batches; the research reports, queue and revision history record their actual coverage and limits.

## 1. Choose a bounded investigation

Record the active graph revision, an information cutoff, starting company or frontier item, selected research branches and batch mode before searching.

| Mode | Deeper investigation limit | Enumeration | Expansion limit |
|---|---:|---|---:|
| Company | 25 distinct companies, including the root if deeply investigated | Extract every relevant name from a dated disclosed list | Two additional company hops from the declared batch roots |
| Project | Five distinct projects; no deeper company investigations in this batch | Extract all explicitly named project participants | Two additional company hops; participant ecosystem research becomes a company batch |

A company is **investigated** when its own reports and relationship disclosures are reviewed beyond identity/list-entry resolution. Resolving 200 names in an official supplier list does not turn them into 200 deeper investigations. Log the distinction. Do not truncate a list to fit the investigation limit.

Two hops is a local search budget. A later batch can start at an existing frontier and continue farther through the accumulated network. The application checks actual adjacency rather than trusting a declared depth number.

Prioritize an uncovered branch, a named dependency, a specific contract or a project with identifiable participants. Do not prioritize by stock returns. Keep a separate queue item for each entity and branch: reviewing a supplier role does not complete investment research for the same company.

## 2. Resolve identity before joining records

For each root and newly resolved company, record the legal name, local-language name, former names, verified official domains, country and available filing identifiers. Add brands as aliases unless a separately incorporated entity is evidenced. Distinguish a project name from its corporate SPV.

Company IDs remain stable when a ticker changes. Instruments attach to companies; ADRs, local ordinary shares and share classes are not new economic issuers. A parent relationship, issuer-equivalence group and broader affiliation are three separate concepts.

For ambiguous list entries, keep the original spelling, list/page locator and unresolved-name lead. Do not guess a listed parent from a similar name or assign an instrument before resolving the issuer.

Record public, private, subsidiary or unknown status with its evidence date. A private company may have a listed parent or investors, but it does not inherit their stock prices. A project SPV can be a company node when its corporate identity is established; the physical factory or campus is a project record.

## 3. Review a repeatable source set

For each research root, locate the latest three annual reports and latest two interim or earnings updates available by the cutoff. Review the relevant sections rather than claiming the full report was read. If fewer reports exist, record the reason and the available documents.

For a deeply investigated counterparty, review its latest annual report and the specific relationship disclosures. Extend backwards to establish a first supported public date, contract amendments or ownership changes. First found is not necessarily first published.

| Source sections | Questions and explicit signals |
|---|---|
| Business, products and geography | Which legal entities, products and facilities are named? |
| Sourcing, manufacturing and concentration | Who fabricates, assembles, tests, supplies materials or is identified as a major customer? |
| Commitments, leases and contingencies | Which contracts, counterparties, capacity commitments or guarantees are disclosed? |
| Investments, related parties and consolidation | Who owns what, with what voting/control rights, and on which date? |
| Subsidiary and contract exhibits | Which legal entities and agreements can be followed into original documents? |
| Transactions, subsequent events and outlook | Is a transaction signed, conditional, closed, cancelled or only forecast? |
| Supplier responsibility, partner and investment lists | What exactly does membership establish, and what does it leave unspecified? |

Search both counterparties' official sites. A named supplier in one party's filing may have a useful customer concentration or product disclosure in the other party's report. Anonymous major customers remain anonymous unless a source explicitly resolves them.

Use primary original documents wherever possible. Public institutional reports, technical specialists and credible reporting can establish an **attributed explicit** connection when they name the parties and state the relationship. Keep estimates and forecasts attributed; do not upgrade them to company confirmation.

### Global source routing

| Jurisdiction or context | Starting routes | Important limit |
|---|---|---|
| United States | [SEC EDGAR](https://www.sec.gov/search-filings), [public data APIs](https://data.sec.gov/), [Item 601 exhibits](https://www.ecfr.gov/current/title-17/chapter-II/part-229/subpart-229.600/section-229.601) | Narrative relationships need original filing sections; public XBRL is not a supply-chain database. |
| Japan | [EDINET](https://disclosure2.edinet-fsa.go.jp/), [TDnet](https://www.release.tdnet.info/inbs/I_main_00.html) | Use local-language filings when translations are missing. Statutory and timely disclosures differ. |
| South Korea | [DART](https://dart.fss.or.kr/), [English DART](https://englishdart.fss.or.kr/) | English coverage does not reproduce every Korean filing. [FSS guidance](https://dart.fss.or.kr/guide/main.jsp?menu=300) describes that limitation. |
| Taiwan | [MOPS](https://mops.twse.com.tw/), [English MOPS](https://emops.twse.com.tw/) | Interfaces have changed. Follow current navigation if legacy links fail. [TWSE route](https://www.twse.com.tw/en/about/company/service.html). |
| Hong Kong | [HKEXnews](https://www.hkexnews.hk/) | Separate issuer announcements, interests disclosures and custody records. |
| Mainland China | [CNINFO](https://www.cninfo.com.cn/) and issuer/exchange filings | Search the original Chinese legal name and code; distinguish formal filings from interactive answers. |
| United Kingdom | [Companies House](https://find-and-update.company-information.service.gov.uk/), [FCA storage mechanism](https://www.fca.org.uk/markets/primary-markets/regulatory-disclosures/national-storage-mechanism) | Corporate identity records and regulated announcements answer different questions. |
| European countries | Home-state official storage mechanism; [Germany](https://www.unternehmensregister.de/), [France AMF BDIF](https://bdif.amf-france.org/), [Netherlands AFM](https://www.afm.nl/en/sector/registers) | Use the issuer's jurisdiction. The [European Commission route](https://finance.ec.europa.eu/financial-markets/company-reporting-and-auditing/company-reporting/transparency-requirements-listed-companies_en) explains national storage. |
| Factories, data centers and energy | Planning authority, utility commission, grid operator, SPV, project sponsor, lender and award documents; [FERC](https://www.ferc.gov/ferc-online/elibrary) where applicable | Application, permit, financing close, construction and operation are distinct stages. |
| Public procurement and support | [SAM.gov](https://sam.gov/), [EU TED](https://ted.europa.eu/), applicable national/local award registries | Opportunity, award ceiling, obligation and actual payment are distinct. |

The machine-readable source registry records verified routes, access limitations and their check date. A portal is a place to look, not evidence of a company relationship. Recheck at research time. Missing English text, blocked access or no search results do not establish that a connection is absent.

## 4. Run six explicit branches

### Supply and manufacturing

Start with dated supplier lists, supplier awards, sourcing notes, manufacturing announcements and supplier/customer reports. Enumerate all relevant names. Then investigate specific products and stages using explicit disclosures or attributed technical analysis.

Use the following hardware checklist to avoid a chip-only network:

- Displays, panels, cover glass, backlights and touch interfaces.
- Optics, image sensors, lenses, camera modules and stabilization.
- Microphones, speakers, audio codecs, haptics and actuators.
- Cells, packs, charging, power management and adapters.
- Processors, accelerators, memory and storage.
- Connectivity, RF, antennas and other sensors.
- Boards, substrates, connectors, cables and passive components.
- Mechanical parts, enclosures, metals, polymers, chemicals, adhesives and coatings.
- Production equipment, inspection, precision tooling and robotics.
- Subassembly, final assembly, testing, packaging and logistics.

For each product/stage, record known company-to-company links, the named model/facility/geography, status and gaps. A stage can have multiple suppliers, and one supplier can serve multiple stages. Do not impose a single linear assembly line where the documents support a network.

**Product-assignment rule:** supplier-list membership plus a supplier product catalogue cannot establish that the supplier provides that component to the root. Keep a generic supplier relationship and an unresolved product-assignment lead unless a source explicitly connects the product and parties. A teardown is attributed evidence for its identified model/variant and date; do not extrapolate it to every product generation.

When following `A buys from B` and `B buys from C`, preserve those adjacent assertions. Do not create an `A buys from C` edge or claim that C's deliveries serve A's order. Supplier tier is relative to the starting path, not a permanent attribute of a company.

### Customers and distribution

Inspect named customer disclosures, deployments, procurement awards, resellers, marketplaces, licensing and implementation partners. Distinguish an ordinary user from a commercial customer, a customer from a reseller, and a marketplace listing from a realized material sales channel.

Disclosed exposure needs its denominator and fiscal period. A contract ceiling is not recognized revenue. A customer logo or case study can establish a narrow described use, but not a revenue share or current contract duration.

### Corporate ecosystem

Follow consolidation notes, subsidiary exhibits, acquisition documents, ownership registers and governance disclosures. Separate legal parentage, a minority investment, a joint venture, voting control and operational influence. A collaboration agreement does not establish supervision or control.

Record acquisitions through announced, signed, conditional and completed states. A proposed acquisition does not convert the target into a completed subsidiary. Retain brand, operating subsidiary and listed parent context without counting the same issuer as independent confirmation.

### Collaboration and dependencies

Inspect joint releases, partner directories, integration documentation, API/model/cloud agreements, licensing and joint-development disclosures. Record the specific commercial and technical scope, geography, product generation and duration where given.

For software companies, cover hosting/compute/storage; models and data; APIs, identity and security; platform distribution and marketplaces; payments; implementation, consulting and managed services.

A partner badge establishes directory membership only unless the linked material describes more. Reciprocal product adoption, distribution and hosting are separate claims even when announced in one release. Competitor, customer and supplier roles can coexist.

### Strategic investment

Search both investors and investees, round announcements, portfolio disclosures, ownership filings, warrants, convertibles and transaction documents. Follow named private investees as companies, even without instruments.

Record ownership percentage separately from dollar investment, valuation and committed capital. Capture whether a stake is direct, through a fund, diluted/undiluted or accompanied by governance rights where stated. Common passive ownership alone stays outside the core operating-dependency graph; an explicit investment claim can be retained with its narrow meaning.

Do not convert an investor's portfolio membership into a commercial partnership. Do not add a company's other portfolio firms as economic counterparties without explicit evidence.

### Projects and financing

Start with the project, then branch into its explicitly named participants. Inspect project/SPV accounts, development announcements, permitting, utility dockets, leases, financing notices, lender/sponsor disclosures, grant awards and contract exhibits.

Record location, corporate SPV if established, stage, dates, milestones, financing instruments and each party's role. Distinguish developer, owner, operator, tenant, offtaker, contractor, equipment supplier, lender, equity provider, guarantor, arranger, advisor, lessor and grant provider.

Keep equity, debt, leases, offtake, guarantees, subsidies and advisory mandates separate. A financing arranger is not automatically a lender. A campus investment headline is not necessarily finance committed to the SPV. A guarantee has a beneficiary/obligor and limit; it is not a deployed equity investment.

**No project clique:** two companies participating in the same facility do not automatically have a bilateral contract. Store project participation with a separate atomic role claim identifying the company, project and exact role. A generic project-plan claim cannot establish another company's financing role. Add a company-to-company financing, supply or lease edge only when a source explicitly identifies those counterparties. Government agencies can be cited in project context; only corporate legal entities become graph company nodes.

## 5. Record searches and inspect the actual passage

Use verified names and aliases in these query patterns. Add local-language equivalents and official-domain searches. The query checklist is reusable; actual executions belong in the batch research log.

```text
"{company}" ("supplier" OR "manufactures for" OR "major customer")
"{company}" ("supply agreement" OR "licensing agreement" OR "joint development")
"{company}" ("subsidiary" OR "joint venture" OR "acquisition" OR "control")
"{company}" ("invested in" OR "investment from" OR "funding round" OR "warrant")
"{company}" ("factory" OR "fab" OR "data center" OR "capacity expansion")
"{project}" ("loan" OR "equity" OR "lease" OR "guarantee" OR "financial close")
"{project}" ("owner" OR "developer" OR "contractor" OR "offtake")
"{supplier}" ("suppliers" OR "materials" OR "subcontractor" OR "manufacturing partner")
"{company}" "{counterparty}" ("renewed" OR "terminated" OR "cancelled" OR "completed")
site:{official_domain} "{counterparty_alias}"
```

Log the exact query, date/time, engine or portal, aliases/language, reviewed results, outcome and next action. Search snippets suggest leads; the claim must come from the underlying document. If the passage cannot be accessed, preserve the access gap and lead rather than claiming it was read.

Use ordinary public access. This workflow does not contact companies, send messages, register accounts, buy research, or submit regulatory filings.

## 6. Admit atomic claims, not plausible narratives

### Two accepted evidence grades

| Grade | Admission | Display |
|---|---|---|
| Primary explicit | A company, regulator, exchange, court or official project document explicitly identifies the relationship and parties. | Primary explicit, with source and locator. |
| Attributed explicit | A named institution, specialist publication or credible report explicitly states the relationship. | Attributed explicit, retaining the original attribution and uncertainty. |
| Unresolved lead | Inference, anonymous counterparty, unresolved identity, inaccessible passage or insufficiently specific claim. | Research queue; no new accepted economic edge. |

Evidence grade describes provenance, not financial materiality or predicted return. A primary announcement may describe a planned or conditional relationship. Repeated copies of one announcement are not independent corroboration; identify the original document and reused passage where possible.

Each accepted claim records company endpoints, predicate, text, evidence grade, source IDs, URL/publisher/title, section/page locator, a concise supporting passage or faithful paraphrase, dates and status. Split an announcement's different assertions into separate claims so they can change independently.

A directed edge also requires a reviewed economic direction. Store `supplier → customer`, `investor → investee`, or another explicitly defined role pair. Search traversal, disclosure order and hypothesized information flow are not economic direction. If direction is unresolved in legacy evidence, retain an undirected documentary connection and label the uncertainty.

New product-specific claims need explicit product scope in the claim itself. Shared industry, correlated stock prices, adjacent diagram positions, shared passive investors and co-participation in a project cannot create an accepted commercial connection.

### Dates and quantities

Keep these meanings separate:

- Publication/public-availability date: when the cited assertion became public.
- Retrieval/review date: when the researcher accessed it.
- Valid/effective interval: when the relationship operated or is expected to operate.
- Quantity's evidence date and fiscal period: when a number was disclosed and what it measures.
- Price observation/retrieval time: independent market-data timestamps.

Use `null` for unknown dates and `date_precision: "unknown"`; do not invent January 1, period end or midnight. A month- or year-only date keeps its actual precision. Unknown-dated claims stay out of historical information-cutoff views until their timing is established. Planned future operation is permitted when the announcement itself was public before the research cutoff.

Store every number with value, unit, denominator/scope, fiscal period, own source IDs and `known_from`. Examples of different quantities include company revenue percentage, project MW, contract ceiling, investment dollars, shares and voting rights. They are not interchangeable. Unknown exposure is not zero, and physical capacity is not revenue sensitivity.

A current ownership percentage must not enter an older historical view just because the relationship existed earlier. Where the earliest disclosure has not been established, label the date as the earliest supporting evidence reviewed, not the universal first public date.

### Contradictions and revisions

Keep competing explicit claims and their sources visible. Mark conflict references instead of averaging percentages or selecting the most convenient report. Inspect whether apparent conflicts reflect different dates, legal entities, denominators, products or planned versus completed status.

Corrections use new claim IDs and `supersedes_id`, with sources and explanation. Never silently overwrite a published claim or reuse an ID for new content. Company/project facts can use their own entity claims. Existing object changes use explicit `record_updates` with a reason and claim support; frontier or coverage status changes need an administrative reason. Earlier revisions remain exportable. An information-cutoff view is a view of dated recorded evidence, not proof that all historical knowledge has been reconstructed.

## 7. Traverse without losing the frontier

Use breadth-first enumeration followed by selective depth-first investigation:

1. Resolve the root and record requested facets and source slots.
2. Enumerate all named entries in relevant supplier, subsidiary, partner and investment lists.
3. Resolve identities or keep explicit unresolved entries; attach list-level evidence only for what membership establishes.
4. Select the next investigations using uncovered facets and explicit dependency/project leads.
5. Review counterparties and follow supported adjacent relationships within the local two-hop budget.
6. Record investigated, pending, blocked, excluded and no-explicit-evidence outcomes for each entity/facet.
7. Validate a proposed batch, inspect its diff and publish it atomically.
8. Resume from unfinished frontier items in a later batch.

The queue stores a stable item ID, company or project, facet, root, parent item, local depth, status, reason, source IDs and next action. If a name is unresolved, retain it in the queue with the source locator, attached to the originating resolved company/project and an `unresolved_name` field; do not invent an unresolved company node. Visiting one entity does not complete all its facets.

Do not manufacture shortcuts to make an extra-hop company fit the budget. If the path is beyond the permitted expansion or an intermediate relationship is unsupported, queue the next investigation and explain the gap.

## 8. Report coverage of the declared search

At the end of every batch, report:

| Metric | Denominator and interpretation |
|---|---|
| Required source slots | Root's three annual and two latest interim/earnings documents, or explicit not-applicable reason. List reviewed sections, blocked and pending slots. |
| List extraction | Entries disclosed in each specific dated list versus entries actually extracted. Keep lists separate across periods. |
| Identity resolution | Resolved and ambiguous entries from those extracted lists. A duplicate entry is not a new issuer. |
| Investigation frontier | Investigated, pending, blocked and excluded known entity/facet tasks. |
| Accepted-claim traceability | Accepted claims with sources, locator, supporting text and date precision. |
| Branch coverage | Findings, no explicit evidence found, not researched, blocked or not applicable for each of the six branches. |
| Budget | Distinct investigated companies/projects and maximum additional adjacency distance. |

A reviewed branch with no explicit evidence is not proof of no relationship. The graph's true completeness is unknown. Do not report a percentage of the entire supply chain or ecosystem. A manufacturing trajectory contains documented stages, links and visible gaps, not a reconstructed confidential bill of materials.

List extraction can be complete for a named document while broader industry coverage remains incomplete. Explain both facts together.

## 9. Prepare, validate and publish a research batch

Use the versioned batch template. It carries the base revision, cutoff, roots, limits, entities, instruments, sources, relationships, atomic claims, projects and roles, frontier, coverage, supersessions and research log. Examples in the templates folder are fictional and must not be imported into the production graph as research.

For a new connection, resolve both company IDs, add its source record, write its atomic supporting claim, and reference the claim from the relationship. In a relationship `source_id` and `target_id` mean company IDs. In a claim `source_ids` means citation IDs.

Keep unrelated economic roles as parallel relationships rather than compressing a supply contract, investment and collaboration into one edge. Project participation is its own record and never produces an automatic clique.

The local application performs a staged validation and diff before publication. Codex can publish a validated batch within an authorized research request; the review controls do not impose another permission request for each reversible local update. Invalid proposals do not change the active graph. Publication checks the base revision again and commits the entire batch or nothing. Re-importing identical content under the same batch ID is a no-op; changing content under that ID conflicts. If the base revision changed, inspect current data and prepare a corrected batch against the new revision.

Restoring an old revision creates a new revision with the old research state; it does not delete history. Quotes and local graph positions are not research evidence and are excluded from research snapshot hashes.

## 10. Explore the application without confusing display with evidence

Start with a one-hop company neighborhood. Open a company for status, legal parent, listings, prices, relationships, projects, claims and gaps. Open an edge for role/direction, scope, terms and source passages. Use the table when graph geometry is inconvenient.

The display is bounded to 100 companies and 300 edges, with at most 25 additional companies per expansion. Hidden counts describe undisplayed results. They do not imply missing research. Opening a drawer does not expand or rearrange the graph. Node size and edge thickness do not encode unknown financial importance.

Use the supply, ownership, project and batch lenses to organize documented roles. A path highlights adjacent claims; it never becomes a new shortcut relationship. The project view explains shared participation without inventing bilateral contracts.

Prices come only from yfinance, on manual refresh of the selected instrument, cached for 15 minutes. The drawer shows observation type/time, currency and retrieval time. A latest daily close is labelled as a close. Retrieval failure retains the old observation with stale/error flags. Private companies have no substituted own-share quote.

Historical graph evidence and current prices use separate timestamps. Applying an evidence cutoff does not turn the selected company's current quotation into a historical price. No price refresh is a research confirmation or evidence of delayed market reaction.

## 11. Request the next research batch

Copy the research-request template and fill the root or frontier IDs, facets and cutoff. Codex reads the current graph, performs the bounded research and produces a traceable batch proposal plus coverage and next-frontier report. The application does not run an autonomous researcher or need an additional AI-service credential.

The framework can be applied to any technology company; no additional anchor is researched automatically. A new research request controls what is investigated next. Company relationship research remains separate from any later statistical protocol.
