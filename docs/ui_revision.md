# Graph interface revision — historical version 1.1

Superseded interaction details: version 1.2 removes canvas arrows, groups each company pair into one line, and uses local collision spacing during manual dragging. See [the current interaction notes](ui_interaction_update.md). The notes below document the earlier layout-engine decision.

This revision improves exploration of the existing company atlas. It does not add company research, change accepted research claims, or run return or trading experiments.

## Layout decision

The app retains Cytoscape.js for evidence drawers, parallel edges, paths and accessible table integration. The earlier one-time concentric layout and saved coordinates did not maintain separation during dragging. The revised graph uses Cytoscape-Cola, an established continuous layout extension with overlap constraints. Fixed label geometry prevents zoom-dependent dimensions from invalidating collision spacing. Physics runs during arrangement and dragging, then settles rather than continually consuming resources.

References reviewed:

- [Cytoscape layout guide](https://blog.js.cytoscape.org/2020/05/11/layouts/) explains continuous layouts and layout extensions.
- [Cytoscape-Cola](https://github.com/cytoscape/cytoscape.js-cola) provides the simulation and overlap handling used here.
- [Force Graph](https://github.com/vasturiano/force-graph) was reviewed as an alternative with force-directed interaction and directional link styling. Keeping Cytoscape preserves the application’s existing interaction model while adding the needed layout engine.

## Visual meaning

Colors separate relationship categories, rather than asserting company sectors or financial materiality. A company may have several roles. Edges retain separate relationship records, evidence grades and source links. Arrowheads represent the specified economic role, never predicted stock movement or a flow inferred from graph distance. Unresolved relationships remain undirected.

The economic direction layer is presentation only. Original research records and migration review flags remain available. The detailed direction rules and exceptions are documented alongside the presentation code.

## Verification

UI acceptance checks exercise initial layout, saved coincident positions, refresh, real pointer dragging, pinned nodes, company directory, responsive layout and evidence drawers. Browser checks use a separate browser context and do not publish research. Screenshots and machine-readable verification results are stored in previews/ and verification/.

All six original company neighborhoods were checked for tile/label overlaps. A synthetic 100-company/300-edge response exercises the display limit without entering the research database. The final build passed real pointer dragging, pin locking, reload, saved stacked-position repair, all-company enumeration, private-company navigation and mobile framing. Browser checks recorded no JavaScript errors or external runtime requests.

See `verification/graph_ui_checks.json`, `verification/graph_scale_checks.json` and `verification/frontend_audit.json` for dated results. The direction layer has 14 focused tests over all 180 original relationship records. Prior backend, quotation and publication checks remain in the original verification record; this interface update does not change those services.
