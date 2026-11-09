export interface Company {
  id: string;
  name: string;
  country?: string;
  status?: string;
  primary_ticker?: string;
  aliases?: string[];
  tickers?: string[];
}

export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  type: string;
  description?: string;
  status?: string;
  direction?: string;
  direction_review_status?: string;
  evidence_grade?: string;
  known_from?: string;
  source_ids: string[];
}

export interface GraphData {
  root: string;
  nodes: Company[];
  edges: Relationship[];
  total_nodes: number;
  total_edges: number;
}

export interface Snapshot {
  revision: number;
  date: string;
  companies: Company[];
  relationships: Relationship[];
  sources: Record<string, { title: string; url: string }>;
}
