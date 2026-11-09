# Apple daily price map

Open **Daily price map** in the left navigation, or open `http://127.0.0.1:8765/?view=prices` while this local app is running. The usual START.cmd launcher still applies.

The view renders the complete current Apple direct neighborhood: **201 companies including Apple**, **276 underlying relationship records**, grouped into **226 visible company-pair connections**. It includes documented links between the counterparties. It does not recursively traverse every company reachable from Apple into an unrelated global network. The normal network explorer retains its existing display cap; this dedicated view shows every Apple node.

## Reading the colors

- **Daily move:** green for a positive close-to-close change, red for a negative change. The deeper the color, the larger the magnitude.
- **Relative to Apple:** company percentage change minus Apple's percentage change, in percentage points. Green means outperforming Apple, even when both returns are negative. Apple's own relative value is zero.
- **Gray:** no usable return for the selected date or selected comparison. A private/unmapped company never borrows a parent's price. Missing dates never become zero returns.
- Color limits are fixed at +/-2, 5 or 10 percent (or percentage points), unchanged as dates advance. Values beyond the limit retain their actual labels and saturate at the darkest color. Node text contrast is checked at 4.5:1 or greater.
- Apple is larger and outlined in gold. Selecting a node preserves its price color. Connections have no arrows and group reciprocal/parallel records; clicking opens their individual directions, terms and evidence.

## Navigating days

Choose a date, step backward/forward through Apple's sessions, choose a year, scrub its timeline or press Play. Playback starts at the year's beginning when launched from its last available session and stops at its end. The date picker also permits holidays; those can legitimately show unavailable companies. Node positions and zoom remain stable as the date or color mode changes.

Expand the workspace for a larger map. Fit includes every company. Zoom, drag, locate a company, choose the connected-network arrangement or restore the compact atlas layout. Search and sorting affect the directory, not graph membership. The accessible table and CSV include all companies and missing-data reasons. Save map exports the entire graph, not only the current viewport, with its date, measure, color limit and legend.

## Prices and timing

Initial history was fetched explicitly on **27 October 2026**, using **yfinance only**. All **144 companies with a mapped primary instrument** returned some daily history; the other **57 companies** remain represented without their own mapped price. History is available from 2015 where the instrument has observations. Availability varies by date, listing, exchange calendar, suspension and provider coverage. A successful history download does not imply that every requested date is present.

Close price change uses Yahoo's `Close` series with `auto_adjust=False`:

`100 * (close on the selected local session / previous available local-session close - 1)`.

Adjusted close change instead uses Yahoo's `Adj Close` series, including its corporate-action and dividend adjustments. Raw and adjusted series are never silently mixed. The chosen instrument, currency, exchange, prior date and retrieval timestamp remain available. A bar dated today in its exchange timezone is excluded conservatively because it might still be changing. Zero-volume rows are not treated as traded daily observations.

Relative comparison is shown only when both companies have an observation on the selected local date and the same prior-session date. A holiday that changes the return window therefore makes the relative value unavailable. Same-date closes in Asia, Europe and the US are not simultaneous, and returns are measured in each listing's currency without FX conversion. This map does not estimate correlation, direction of causation or market latency.

The graph is today's documented network over historical prices. It does not assert that all displayed relationships existed on the historical price date. Research timestamps and quotation timestamps remain separate.

## Refresh, storage and preservation

Browsing dates reads the local cache without requesting market data. Refresh history explicitly updates the mapped instruments, with two concurrent fetches and a 15-minute request cache. Failures retain prior successful observations and expose the refresh error. Unknown symbols are not guessed, and alternative share classes/ADRs do not become duplicate company nodes.

Daily bars live in `data/daily_prices.sqlite3`, separately from `graph.sqlite3` and `quotes.sqlite3`. Adding or refreshing daily prices creates no research revision. Original studies, atlas, research batches and claims are untouched. A dated source/bundle backup is kept in `data/ui_backups/` for this update.

## Verification

The delivery includes 57 passing isolated backend checks, including daily-return calculations, percentage-point comparison, adjusted prices, missing/closed dates, IPO history, no parent-price substitution, zero-volume handling, failure preservation, request deduplication and the dedicated full-network route. Existing backend/quote tests also pass. Frontend type checking/build passes. Helper checks cover monotonic color intensity, saturation, missing-versus-zero colors, label contrast and nonoverlapping initial layouts for 201 and 1,000 companies.

Browser checks cover the full 201-node view, historical date selection, daily/relative modes, closed weekends, a pre-IPO company, directory search without node removal, playback and pause, and both layout choices. Checkpoint screenshots, real cached-data checks and research-preservation fingerprints are in `verification/daily_price_*`.

Sources for provider/library behavior: [yfinance download reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html), [Cytoscape.js API](https://js.cytoscape.org/). Data are provider observations and may contain errors or gaps; no replacement data are fabricated.


## Comparison-panel extension

The current interface adds cross-industry controls and a third SPY + XLK color mode. See [the comparison guide](price_comparison_panels.md). Existing raw/Apple-relative formulas and missing-date rules remain available.
