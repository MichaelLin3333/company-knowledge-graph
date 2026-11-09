import { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, ChevronRight, Network, Search, X } from 'lucide-react';
import type { Company, Snapshot } from './api';
import Graph from './Graph';
import type { ConnectionGroup } from './graphConnections';
import { edgePresentation } from './graphPresentation';
import { connectionName, makeSearch, neighborhood, startingCompanies } from './explore';
import './styles.css';

function CompanySearch({ search, onOpen }: { search: ReturnType<typeof makeSearch>; onOpen: (id: string) => void }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const results = useMemo(() => search(query), [search, query]);
  const expanded = open && Boolean(query.trim());

  function choose(company: Company) {
    setQuery('');
    setOpen(false);
    onOpen(company.id);
  }

  return <div className="search" onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
  }}>
    <Search size={18} aria-hidden="true" />
    <input
      ref={input}
      role="combobox"
      aria-label="Search companies"
      aria-autocomplete="list"
      aria-expanded={expanded}
      aria-controls="company-matches"
      aria-activedescendant={expanded && results[active] ? 'company-match-' + active : undefined}
      placeholder="Search companies or tickers"
      value={query}
      onChange={event => { setQuery(event.target.value); setActive(0); setOpen(true); }}
      onFocus={() => setOpen(true)}
      onKeyDown={event => {
        if (event.key === 'Escape') { setOpen(false); return; }
        if (!results.length) return;
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault();
          setOpen(true);
          const delta = event.key === 'ArrowDown' ? 1 : -1;
          setActive(value => (value + delta + results.length) % results.length);
        }
        if (event.key === 'Enter' && expanded && results[active]) choose(results[active]);
      }}
    />
    {query && <button className="icon" aria-label="Clear company search" onClick={() => {
      setQuery(''); setActive(0); input.current?.focus();
    }}><X size={16} /></button>}
    <div id="company-matches" role="listbox" aria-label="Company matches" hidden={!expanded}>
      {results.map((company, index) => <button
        key={company.id}
        id={'company-match-' + index}
        type="button"
        tabIndex={-1}
        role="option"
        aria-selected={index === active}
        onMouseDown={event => event.preventDefault()}
        onClick={() => choose(company)}
      >
        <span>{company.name}<small>{company.primary_ticker ?? company.id}{company.country ? ' · ' + company.country : ''}</small></span>
        <ChevronRight size={16} />
      </button>)}
      {!results.length && <p role="status">No companies match “{query}”.</p>}
    </div>
  </div>;
}

const companyHref = (id: string) => '?company=' + encodeURIComponent(id);
const label = (value?: string) => (value ?? '').replaceAll('_', ' ');

function Explorer({ snapshot }: { snapshot: Snapshot }) {
  const companies = useMemo(() => new Map(snapshot.companies.map(company => [company.id, company])), [snapshot]);
  const records = useMemo(() => new Map(snapshot.relationships.map(edge => [edge.id, edge])), [snapshot]);
  const search = useMemo(() => makeSearch(snapshot.companies), [snapshot]);
  function fromLocation() {
    const id = new URLSearchParams(window.location.search).get('company') ?? 'AAPL';
    return companies.has(id) ? id : 'AAPL';
  }
  const [root, setRoot] = useState(fromLocation);
  const [selected, setSelected] = useState<string>();
  const [connection, setConnection] = useState<ConnectionGroup>();
  const [pins, setPins] = useState<string[]>([]);
  const [filter, setFilter] = useState('');
  const { graph, connections } = useMemo(() => neighborhood(snapshot, companies, root), [snapshot, companies, root]);
  const company = companies.get(root)!;
  const visibleConnections = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return connections;
    return connections.filter(group => group.companyIds.some(id => id !== root &&
      [companies.get(id)?.name, companies.get(id)?.primary_ticker, id].join(' ').toLowerCase().includes(query)));
  }, [companies, connections, filter, root]);

  function reset(next: string) {
    setRoot(next);
    setSelected(undefined);
    setConnection(undefined);
    setFilter('');
  }
  function open(id: string) {
    if (id !== root) window.history.pushState(null, '', companyHref(id));
    reset(id);
  }
  useEffect(() => {
    const pop = () => reset(fromLocation());
    window.addEventListener('popstate', pop);
    return () => window.removeEventListener('popstate', pop);
  }, [companies]);

  const selectedCompany = selected && !connection ? companies.get(selected) : undefined;
  const shownCompany = selectedCompany ?? company;
  const detail = useRef<HTMLDivElement>(null);
  function showConnection(group: ConnectionGroup) {
    setSelected(group.id);
    setConnection(group);
    if (window.matchMedia('(max-width: 920px)').matches) {
      detail.current?.scrollIntoView({ block: 'nearest' });
    }
  }

  return <div className="shell">
    <header className="top">
      <div className="brand">
        <span className="mark"><Network size={22} aria-hidden="true" /></span>
        <div><strong>Company Fieldnotes</strong><span>Knowledge graph</span></div>
      </div>
      <CompanySearch search={search} onOpen={open} />
      <span className="edition">Read-only snapshot</span>
    </header>
    <main>
      <nav className="starters" aria-label="Starting companies">
        <span>Starting companies</span>
        <div>
          {startingCompanies.map(item => <a key={item.id} href={companyHref(item.id)}
            aria-current={root === item.id ? 'page' : undefined}
            onClick={event => {
              if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
              event.preventDefault();
              open(item.id);
            }}>{item.label}</a>)}
        </div>
      </nav>
      <section className="heading" aria-label="Current company">
        <div>
          <p className="eyebrow">Company network</p>
          <h1>{company.name}</h1>
          <p className="subheading">{[company.primary_ticker, company.country, label(company.status)].filter(Boolean).join(' · ')}</p>
        </div>
        <div className="revision">Revision {snapshot.revision}<span>{snapshot.date}</span></div>
      </section>
      <div className="workspace">
        <section className="canvas-card" aria-label="Interactive network">
          <header>
            <h2>Relationship map</h2>
            <span>{graph.nodes.length.toLocaleString()} of {graph.total_nodes.toLocaleString()} entities on canvas</span>
          </header>
          <Graph data={graph} root={root} pins={pins} selected={selected}
            onCompany={id => { setSelected(id); setConnection(undefined); }}
            onConnection={showConnection}
            onPin={id => setPins(current => current.includes(id) ? current.filter(pin => pin !== id) : [...current, id])}
            onPositions={positions => localStorage.setItem('fieldnotes.positions.' + root, JSON.stringify(positions))}
          />
        </section>
        <aside className="inspect" aria-label="Network details">
          <div className="record" ref={detail}>
            {connection ? <>
              <header><p className="eyebrow">Relationship records</p><button className="icon" aria-label="Close relationship details" onClick={() => {
                setConnection(undefined); setSelected(undefined);
              }}><X size={16} /></button></header>
              <h2>{connectionName(connection.companyIds, companies, root)}</h2>
              {connection.companyIds.filter(id => id !== root).map(id => <button key={id} className="outline" onClick={() => open(id)}>Explore {companies.get(id)?.name}<ArrowUpRight size={14} /></button>)}
              <div className="evidence">
                {connection.relationshipIds.map(id => {
                  const edge = records.get(id)!;
                  const view = edgePresentation(edge);
                  const arrow = view.direction === 'directed' ? ' → ' : view.direction === 'bidirectional' ? ' ↔ ' : ' · ';
                  return <article key={id}>
                    <h3>{view.label}</h3>
                    <p>{companies.get(view.source)?.name}{arrow}{companies.get(view.target)?.name}</p>
                    {edge.description && <p>{edge.description}</p>}
                    <small>{[label(edge.evidence_grade), edge.known_from, label(edge.status)].filter(Boolean).join(' · ')}</small>
                    {edge.source_ids.length > 0 && <ul>{edge.source_ids.map(sourceId => {
                      const source = snapshot.sources[sourceId];
                      return <li key={sourceId}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}<ArrowUpRight size={13} /></a></li>;
                    })}</ul>}
                  </article>;
                })}
              </div>
            </> : <>
              <header><p className="eyebrow">Company record</p>{selectedCompany && <button className="icon" aria-label="Clear selected company" onClick={() => setSelected(undefined)}><X size={16} /></button>}</header>
              <h2>{shownCompany.name}</h2>
              <p>{[shownCompany.primary_ticker, shownCompany.country, label(shownCompany.status)].filter(Boolean).join(' · ')}</p>
              {selectedCompany && selectedCompany.id !== root && <button className="outline" onClick={() => open(selectedCompany.id)}>Open company graph<ArrowUpRight size={14} /></button>}
            </>}
          </div>
          <section className="connections" aria-labelledby="connection-heading">
            <header><h2 id="connection-heading">Connections</h2><span>{connections.length}</span></header>
            <input type="search" aria-label="Filter connections" placeholder="Filter connections" value={filter}
              onChange={event => setFilter(event.target.value)} />
            <ul>
              {visibleConnections.map(group => <li key={group.id}>
                <button aria-pressed={connection?.id === group.id} onClick={() => showConnection(group)}>
                  <span className="dot" style={{ backgroundColor: group.color }} />
                  <span>{connectionName(group.companyIds, companies, root)}<small>{group.relationshipIds.length} {group.relationshipIds.length === 1 ? 'record' : 'records'}</small></span>
                  <ChevronRight size={15} />
                </button>
              </li>)}
            </ul>
            {!visibleConnections.length && <p>{filter ? 'No connections match this filter.' : 'No documented connections in this snapshot.'}</p>}
          </section>
        </aside>
      </div>
      <footer>{snapshot.companies.length.toLocaleString()} entities · {snapshot.relationships.length.toLocaleString()} documented relationships · Revision {snapshot.revision}</footer>
    </main>
  </div>;
}

const app = createRoot(document.getElementById('root')!);
app.render(<main className="message" role="status">Loading the knowledge graph…</main>);
fetch(new URL('./data/graph.json', document.baseURI))
  .then(response => {
    if (!response.ok) throw new Error('Snapshot request failed');
    return response.json() as Promise<Snapshot>;
  })
  .then(snapshot => app.render(<Explorer snapshot={snapshot} />))
  .catch(() => app.render(<main className="message" role="alert">The graph snapshot could not load. <button className="outline" onClick={() => window.location.reload()}>Retry</button></main>));
