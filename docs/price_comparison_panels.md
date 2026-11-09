# Cross-industry controls and SPY + XLK adjustment

The Daily price map now has two panels and three color modes. The date, price measure and color scale carry across panel switches, so the same session can be compared directly.

## Panels

**Apple network** retains every node and documented relationship in the current Apple neighborhood. At delivery this is 201 companies, including Apple, and 276 underlying relationship records.

**Cross-industry controls** contains 30 US-listed companies plus Apple as a visual reference. Its nodes are drawn in the same style, but it has no invented edges. The roster is separate from the research graph and creates no company, relationship, claim or revision in that graph.

| Business group | Companies |
|---|---|
| Packaged food | General Mills (GIS), Hormel (HRL), J. M. Smucker (SJM) |
| Restaurants | Darden (DRI), Texas Roadhouse (TXRH), Brinker (EAT) |
| Water utilities | American Water (AWK), California Water Service (CWT), American States Water (AWR) |
| Homebuilding | D.R. Horton (DHI), Lennar (LEN), PulteGroup (PHM) |
| Residential property | UDR (UDR), Essex (ESS), Mid-America Apartment Communities (MAA) |
| Property/casualty insurance | Allstate (ALL), Progressive (PGR), Cincinnati Financial (CINF) |
| Hospitals/care | HCA (HCA), Universal Health Services (UHS), Tenet (THC) |
| Apparel | PVH (PVH), Ralph Lauren (RL), VF (VFC) |
| Waste services | Waste Management (WM), Republic Services (RSG), Waste Connections (WCN) |
| Agriculture/protein | Archer-Daniels-Midland (ADM), Tyson (TSN), Pilgrim's Pride (PPC) |

The roster was chosen by business category before inspecting downloaded returns. Its primary tickers are absent from the installed Apple neighborhood at revision 16. Each selection has an official corporate/IR link in `backend/control_companies.json` and the company inspector. Business categories are based on those disclosures; absence from this graph does not prove absence of all direct or indirect business ties.

The companies are **not established as statistically unrelated**. They share broad markets, interest rates and other macroeconomic exposures; three companies per business group also share industry shocks. They were not selected by minimizing historical correlations, and no randomization, correlation screen or formal placebo test was run. This retrospective, currently listed basket is not matched to the global Apple network on size, country, liquidity or volatility. Node counts differ (31 including Apple versus 201), so compare color proportions and patterns, not the absolute count of colored tiles.

American Water/Essential Utilities and the redirected AvalonBay/Vivmark example were avoided as paired control choices after public source checks revealed corporate developments. CWT and UDR were used instead. This was source/identity screening before examining price outcomes, not performance-based selection.

## Three color modes

1. **Daily move:** the original local-session close-to-close percentage change.
2. **Relative to Apple:** the original company move minus Apple's move, in percentage points. Return-window dates must match.
3. **Relative to SPY + XLK:** the company's observed move minus its fitted two-factor market/technology move, in percentage points. Apple's own node shows Apple's residual rather than zero.

For the new third mode, the displayed value is:

`company return[t] - (alpha + beta_SPY * SPY return[t] + beta_XLK * XLK return[t])`.

Green means the company moved above that fitted value, and red means below it. It can be green while its absolute price fell. All three modes use the selected fixed color limit; the scale is not reset each day or fitted separately to force a visual pattern. Gray is unavailable, not zero or no correlation. The close/adjusted-close selector applies consistently to the company and both ETFs.

## Fitting, overlap and timing

For each company/date, take the **252 strictly older SPY sessions**, then retain observations whose company, SPY and XLK return start/end calendar dates agree. Require **120 aligned observations**. Include an intercept. Neither the selected day's return nor any later return enters coefficient fitting. Initial history is fetched from December 2013 to warm up the displayed period starting in 2015; newly listed instruments can still lack sufficient history.

SPY and XLK overlap and are correlated. The implementation first regresses XLK on SPY within that exact prior fitting sample, then uses standardized SPY and the orthogonal XLK component with an intercept. This is algebraically the same joint ordinary-least-squares fit as using SPY and XLK together. It is **not** subtraction of both ETF returns, an equal-weight ETF basket, or two separate regressions. The resulting joint coefficients and the fitted return are available in exported data. Singular or effectively collinear factors produce an unavailable result rather than unstable colors.

The benchmark strip shows the selected day's actual SPY and XLK moves. The inspector shows observed, fitted and residual return, the number of fitting observations and their dates. Model-ready counts, positive/negative counts, directory colors, node colors, tooltips and exports all use the active color mode. Node positions do not change when changing the color mode or date; panel-specific layout storage prevents the 31-node basket from disturbing the Apple layout.

This is an **ex-post descriptive adjustment**. Asian, European and US closes on one date are not simultaneous. Returns remain in each instrument's own currency, without FX conversion. The ETFs contain Apple and other network companies, so adjustment can remove genuine shared company/technology movement as well as broad-market movement. Residuals do not prove causal transmission, independent shocks, absence of common factors, or an exploitable signal.

## Prices, source register and preservation

The 30 company histories and the two ETFs were downloaded through yfinance on 27 October 2026. All 176 requested instrument histories (144 existing mapped companies, 30 controls and two ETFs) succeeded in the acquisition run. Some dates can still be missing, and success does not certify every provider bar. Prices use the existing isolated daily cache; there is no broker connection or paid-data subscription.

The full dated roster and official source URLs are in `backend/control_companies.json`. The ETFs are benchmark instruments off the canvas, not extra company nodes. Provider references: [SPY sponsor page](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy), [XLK sponsor page](https://www.ssga.com/us/en/individual/etfs/state-street-technology-select-sector-spdr-etf-xlk), [yfinance documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html).

Examples of primary business descriptions: [General Mills](https://www.generalmills.com/), [Darden](https://www.darden.com/), [California Water Service](https://www.calwatergroup.com/), [D.R. Horton](https://investor.drhorton.com/), [UDR](https://www.udr.com/), [Allstate](https://www.allstate.com/), [HCA](https://investor.hcahealthcare.com/overview/default.aspx), [Ralph Lauren](https://corporate.ralphlauren.com/), [Waste Connections](https://www.wasteconnections.com/), [Tyson](https://www.tysonfoods.com/). These establish business activities, not absence of relationships with Apple.

The update includes 63 passing isolated backend checks, the frontend build/type check, numerical comparison against a direct joint regression, recovery of a known residual, selected-day/future-data exclusion, insufficient-history and singular-factor cases, matching return windows, and a check that the control view creates no graph records. Live-view evidence and installation fingerprints are in `verification/comparison_panels_*`. Research records remain at the existing revision; earlier statistical studies are untouched.
