# Graph colors and relationship directions

The current canvas has no arrows and shows one straight line per company pair. Direction rules below apply in the connection and relationship detail windows and the accessible table. Several categories in one pair use neutral slate. Individual research records and evidence remain separate.

Colors distinguish six relationship roles: supply and manufacturing (teal),
customers and distribution (blue), ownership and investment (amber),
collaboration and integration (violet), infrastructure and financing (cyan),
and competition (coral). Gray indicates an unclassified relationship.

A company's color is the dominant relationship role in the visible network.
Direct relationships with the selected root take precedence over relationships
in the surrounding ecosystem. This is not an industry, importance, risk,
financial-exposure or predicted-return classification. Private-company and pin
styling remain independent from the role color.

An arrow follows the economic role named in the evidence: supplier to buyer,
service provider to user, investor to investee, or adviser to client. Distribution
arrows follow the product toward its named distribution partner. A co-founder
arrow identifies the founder and venture; it does not imply sole ownership.
Planned and historical relationships retain those labels.

Two arrow heads appear only for the two legacy records whose explicit roles say
the cloud/model/channel partnership is reciprocal. This denotes a reciprocal
partnership, not two independently verified supply contracts. Competition,
co-investors in a third company, and financial partnerships without a named
bilateral funding flow have no directional arrow. The absence of an arrow means
that the display does not assign a single direction.

The imported atlas originally preserved every direction as unreviewed because
discovery-path indexing was inconsistent. The display-only review in
`frontend/src/legacyDirectionReview.ts` reads the existing explicit roles and
descriptions; it does not change the SQLite research records, evidence grades,
historical eligibility or graph revisions. All 180 original records retain
their original endpoints and research flags. The graph's existing admission
rules continue to exclude the two consolidated-subsidiary records and the
unresolved competitor inference.

The presentation review requires exact original parties, type, description,
scope and status, the original batch and direction flag, unchanged legacy
metadata, and the original sole active claim. A superseding or conflicting claim,
changed record or unfamiliar identifier falls back to an undirected display.
Explicitly reviewed directions from a later published research batch take
precedence. The rebuild tool verifies the original atlas's SHA-256 before
recreating this index; a changed seed cannot acquire arrows automatically.

Clicking a relationship shows its display-direction explanation and source
evidence. A display arrow never asserts that a stock price moves first, that a
customer pays a supplier directly, or that a supplier's entire product catalogue
serves the selected company. Paths do not create shortcut relationships.

Verification: `node tools/test_graph_presentation.cjs` runs 14 checks covering
all 180 legacy records, suppliers and second-tier paths, investor and customer
roles, planned/historical labels, reciprocal and symmetric relationships,
correction safeguards and non-mutation of evidence.
