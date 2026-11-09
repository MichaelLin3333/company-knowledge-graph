# Connection clarity and free dragging — version 1.2.0

The canvas shows one straight line for each unordered company pair in the
currently filtered graph. It has no arrowheads or relationship labels.
Reciprocal roles and parallel contracts are grouped visually; their research
records, claims, directions, dates and evidence remain separate.

Clicking a line opens a company-connection drawer. Every matching relationship
has its own role, status, date range, supporting claims and sources. Its full
relationship record remains individually accessible. A line with several
relationship categories uses neutral slate; a single-category line retains
that category's color. The accessible table continues to enumerate individual
records. Counts distinguish visual connections from research records.

Manual dragging stops the global Cola arrangement. The grabbed node follows
the pointer, and only overlapping neighbors and their collision chain move.
There are no springs, automatic centering or whole-network reheating during a
drag. Pulling a company into empty space leaves other companies in place, and
its released position is saved. Pins remain fixed obstacles. The pause control
temporarily disables collision assistance; Arrange explicitly runs the global
collision-aware layout. Initial neighborhoods also use Cola, while valid saved
layouts are restored without a fresh simulation.

The existing direction presentation helper is used only in evidence details
and the accessible table. Graph grouping does not certify legacy directions,
manufacture reciprocal contracts, combine different dates or modify the data.

## Verification

`tools/graph_interaction_qa.cjs` checks zero arrowheads, one straight unlabeled
line per pair, retained relationship counts, grouped evidence, stable drawer
selection, stacked-coordinate repair, stable saved layouts, actual pointer
dragging into empty space and a local obstacle, pins, the collision toggle,
mobile framing and unchanged research snapshots. The scale suite checks six
root neighborhoods and the 100-company / 300-edge response fixture. Neither
suite publishes research or requests prices.

Results are written to `verification/graph_ui_checks.json` and
`verification/graph_scale_checks.json`; screenshots are in `previews/ui3-*`.

Cola remains the established engine for initial/explicit arrangement:
[Cytoscape-Cola](https://github.com/cytoscape/cytoscape.js-cola).
