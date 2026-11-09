# Company Fieldnotes for GitHub Pages

This is a read-only, browser-based edition of the knowledge graph. Search covers the exported company register by name, ticker, alias, or graph ID. The seven starting companies are Apple, Microsoft, Amazon, NVIDIA, TSMC, Salesforce, and Coca-Cola. Each company can be linked directly with a query such as `?company=KO`.

## Review and publish

1. Review `dist/data/graph.json` for public release. The site exposes the exported company identities, documented relationship summaries, and source links to visitors.
2. Place the **contents** of `dist/` at the root of a dedicated publishing branch, or in `docs/` on your chosen branch. Include the empty `.nojekyll` file.
3. Under **Settings → Pages → Build and deployment**, choose **Deploy from a branch**. Select the branch and folder you used in step 2.
4. Open the URL in the Pages settings. Test the **Coca-Cola (KO)** shortcut and a direct link ending in `?company=KO`.

A private repository can still have a public Pages site. Review the audience before enabling Pages. [GitHub publishing settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## Preview or rebuild

Use `npm ci` and `npm run build` from this directory to recreate `dist/`. The included snapshot is revision 89. To use a newer published graph revision, run `python export_snapshot.py PATH_TO_GRAPH_SQLITE3`, then rebuild. The export reads the source database in read-only mode and copies a selected set of graph fields into `public/data/graph.json`.

Serve the built folder over HTTP to preview it. For example, run `python -m http.server 4173 --bind 127.0.0.1 --directory dist` and open `http://127.0.0.1:4173/`. The site loads its snapshot over HTTP.

The package includes company identities, explicitly documented relationships, and linked source titles and URLs. It omits drafts, research queue entries, price data, original source files, and private browser settings. Research publishing, revision restoration, and quote refresh are part of the local app. The Pages version uses the published snapshot until a replacement is exported and deployed.
