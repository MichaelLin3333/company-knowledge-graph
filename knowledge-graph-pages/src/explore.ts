import type { Company, GraphData, Snapshot } from './api';
import { groupConnections } from './graphConnections';

export const startingCompanies = [
  { id: 'AAPL', label: 'Apple' },
  { id: 'MSFT', label: 'Microsoft' },
  { id: 'AMZN', label: 'Amazon' },
  { id: 'NVDA', label: 'NVIDIA' },
  { id: 'TSMC', label: 'TSMC' },
  { id: 'CRM', label: 'Salesforce' },
  { id: 'KO', label: 'Coca-Cola (KO)' },
];

export function makeSearch(companies: Company[]) {
  const index = companies.map(company => ({
    company,
    name: company.name.toLowerCase(),
    symbols: [company.id, ...company.tickers ?? []].map(value => value.toLowerCase()),
    text: [company.name, company.id, ...company.tickers ?? [], ...company.aliases ?? []]
      .join(' ').toLowerCase(),
  }));
  return (input: string) => {
    const query = input.trim().toLowerCase();
    if (!query) return [];
    const words = query.split(/\s+/);
    const rank = (item: typeof index[number]) =>
      item.symbols.includes(query) ? 0 : item.name.startsWith(query) ? 1 : 2;
    return index.filter(item => words.every(word => item.text.includes(word)))
      .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name))
      .slice(0, 12)
      .map(item => item.company);
  };
}

export function neighborhood(snapshot: Snapshot, companies: Map<string, Company>, root: string) {
  const neighbors = new Set([root]);
  for (const edge of snapshot.relationships) {
    if (edge.source_id === root) neighbors.add(edge.target_id);
    if (edge.target_id === root) neighbors.add(edge.source_id);
  }
  const otherCompanies = [...neighbors].filter(id => id !== root)
    .map(id => companies.get(id)!)
    .sort((a, b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
  const records = snapshot.relationships.filter(
    edge => neighbors.has(edge.source_id) && neighbors.has(edge.target_id),
  );
  const nodeLimit = root === 'AAPL' ? 300 : 100;
  const edgeLimit = root === 'AAPL' ? 600 : 300;
  const nodes = [companies.get(root)!, ...otherCompanies.slice(0, nodeLimit - 1)];
  const visible = new Set(nodes.map(company => company.id));
  const edges = records.filter(edge => visible.has(edge.source_id) && visible.has(edge.target_id))
    .slice(0, edgeLimit);
  const graph: GraphData = { root, nodes, edges, total_nodes: neighbors.size, total_edges: records.length };
  const connections = groupConnections(records).sort((a, b) => {
    const aDirect = a.companyIds.includes(root);
    const bDirect = b.companyIds.includes(root);
    return Number(bDirect) - Number(aDirect) || connectionName(a.companyIds, companies, root)
      .localeCompare(connectionName(b.companyIds, companies, root));
  });
  return { graph, connections };
}

export function connectionName(ids: string[], companies: Map<string, Company>, root: string) {
  return ids.filter(id => id !== root).map(id => companies.get(id)!.name).join(' / ')
    || companies.get(root)!.name;
}
