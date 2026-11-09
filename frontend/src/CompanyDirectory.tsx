import { useEffect, useMemo, useState } from 'react';
import { Building2, Check, ChevronRight, Globe2, LoaderCircle, Network, PanelLeftClose, PanelLeftOpen, RefreshCw, Search, X } from 'lucide-react';
import { api, label, type Company } from './api';
import './directory.css';

type Props = {
  open: boolean;
  revision: number;
  root: string;
  visibleIds: string[];
  selectedId?: string | null;
  onToggle: () => void;
  onCompany: (id: string) => void;
  onRoot: (id: string) => void;
};

/** The directory indexes the complete company register, never just graph results. */
export default function CompanyDirectory({ open, revision, root, visibleIds, selectedId, onToggle, onCompany, onRoot }: Props) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [query, setQuery] = useState('');
  const [country, setCountry] = useState('');
  const [status, setStatus] = useState('');
  const [inViewOnly, setInViewOnly] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadDirectory() {
      setLoading(true);
      setError('');
      try {
        const indexed: Company[] = [];
        let expected = 0;
        do {
          const response = await api<{ items: Company[]; total: number }>('/companies?limit=500&offset=' + indexed.length);
          if (cancelled) return;
          expected = response.total;
          indexed.push(...response.items);
          setTotal(expected);
          if (!response.items.length && indexed.length < expected) throw new Error('The company register returned an incomplete page. Please retry.');
        } while (indexed.length < expected);
        if (!cancelled) setCompanies(indexed);
      } catch (cause) {
        if (!cancelled) setError((cause as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadDirectory();
    return () => { cancelled = true; };
  }, [revision, retry]);

  const visible = useMemo(() => new Set(visibleIds), [visibleIds]);
  const countries = useMemo(() => [...new Set(companies.map(company => company.country).filter(Boolean))].sort() as string[], [companies]);
  const statuses = useMemo(() => [...new Set(companies.map(company => company.status).filter(Boolean))].sort() as string[], [companies]);
  const filtered = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return companies.filter(company => {
      const searchable = [company.name, company.id, company.primary_ticker, ...(company.aliases || [])].join(' ').toLocaleLowerCase();
      return (!term || searchable.includes(term)) && (!country || company.country === country) && (!status || company.status === status) && (!inViewOnly || visible.has(company.id));
    });
  }, [companies, query, country, status, inViewOnly, visible]);
  const hasFilters = Boolean(query || country || status || inViewOnly);
  function resetFilters() { setQuery(''); setCountry(''); setStatus(''); setInViewOnly(false); }
  function completeAction(action: () => void) {
    action();
    if (window.matchMedia('(max-width: 1100px)').matches) onToggle();
  }

  return <>
    {open && <button className="directory-backdrop" aria-label="Close company directory" onClick={onToggle} />}
    <aside className={'company-directory ' + (open ? 'is-open' : 'is-collapsed')} aria-label="All companies" data-testid="company-directory">
      {!open ? <button className="directory-rail" onClick={onToggle} aria-label="Open all-company directory" title="Open all-company directory"><PanelLeftOpen size={18} /><span>All companies</span><strong>{total || companies.length || '—'}</strong></button> : <>
        <div className="directory-heading"><div><span className="directory-eyebrow">Complete register</span><h2>All companies <span data-testid="directory-total">{total || companies.length}</span></h2></div><button className="icon-button" aria-label="Collapse company directory" title="Collapse company directory" onClick={onToggle}><PanelLeftClose size={18} /></button></div>
        <div className="directory-tools">
          <label className="directory-search"><Search size={16} /><span className="sr-only">Search all companies</span><input type="search" value={query} placeholder="Name or stock symbol" onChange={event => setQuery(event.target.value)} /><kbd>{companies.length}</kbd></label>
          <div className="directory-filter-row"><label><span className="sr-only">Directory country</span><select aria-label="Directory country" value={country} onChange={event => setCountry(event.target.value)}><option value="">All countries</option>{countries.map(value => <option key={value} value={value}>{value}</option>)}</select></label><label><span className="sr-only">Directory company status</span><select aria-label="Directory company status" value={status} onChange={event => setStatus(event.target.value)}><option value="">All statuses</option>{statuses.map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label></div>
          <div className="directory-view-options"><button className={inViewOnly ? 'active' : ''} onClick={() => setInViewOnly(!inViewOnly)} aria-pressed={inViewOnly}><span className="directory-view-dot" />In this view <span>{visibleIds.length}</span>{inViewOnly && <Check size={12} />}</button>{hasFilters && <button className="directory-clear" onClick={resetFilters}>Clear <X size={12} /></button>}</div>
        </div>
        <div className="directory-result-caption" aria-live="polite"><span>{loading ? 'Loading complete register…' : `${filtered.length} ${filtered.length === 1 ? 'company' : 'companies'}${hasFilters ? ' match' : ' in register'}`}</span><span>NAME A–Z</span></div>
        {error && <div className="directory-error" role="alert"><p>{error}</p><button onClick={() => setRetry(value => value + 1)}><RefreshCw size={13} />Retry loading</button></div>}
        <div className="directory-company-list" role="list" aria-label="Company register">
          {loading && !companies.length ? <div className="directory-empty"><LoaderCircle size={21} className="spin" /><p>Loading all companies</p></div> : filtered.map(company => {
            const isRoot = company.id === root;
            const isVisible = visible.has(company.id);
            return <div role="listitem" key={company.id} className={'directory-company ' + (isRoot ? 'is-root ' : '') + (selectedId === company.id ? 'is-selected' : '')} data-company-id={company.id}>
              <button className="directory-company-record" onClick={() => completeAction(() => onCompany(company.id))} aria-label={`Open ${company.name} company record`} title={`Open ${company.name} company record`}><span className={'directory-avatar ' + (company.status === 'private' ? 'is-private' : '')}>{company.primary_ticker ? company.name.slice(0, 1) : <Building2 size={15} />}</span><span className="directory-company-copy"><strong>{company.name}</strong><span className="directory-company-meta"><span>{company.primary_ticker || label(company.status)}</span><span className="directory-meta-divider">·</span><span>{company.country || 'Country unknown'}</span></span><span className="directory-company-context">{isRoot ? <span className="directory-current"><Network size={10} />Starting company</span> : isVisible ? <span className="directory-in-view"><span className="directory-view-dot" />In view</span> : <span className="directory-outside">Outside current view</span>}<span>{company.relationship_count ?? 0} links</span></span></span></button>
              <button className="directory-explore" title={`Explore ${company.name} network`} aria-label={`Explore ${company.name} network`} onClick={() => completeAction(() => onRoot(company.id))}><ChevronRight size={16} /></button>
            </div>;
          })}
          {!loading && !error && !filtered.length && <div className="directory-empty"><Search size={23} /><h3>No companies match</h3><p>Try another name, symbol or filter.</p><button onClick={resetFilters}>Clear directory filters</button></div>}
        </div>
        <div className="directory-footer"><Globe2 size={14} /><p>Every company in the research register. Graph filters and display limits do not remove entries.</p></div>
      </>}
    </aside>
  </>;
}
