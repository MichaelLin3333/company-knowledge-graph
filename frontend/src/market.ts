import type { GraphData, RecordData } from './api';

export type PriceMode = 'daily' | 'relative' | 'market';
export type PricePanel = 'apple' | 'controls';
export const modeLabel:Record<PriceMode,string>={daily:'Daily move',relative:'Relative to Apple',market:'Relative to SPY + XLK'};
export const modeUnit=(mode:PriceMode)=>mode==='daily'?'%':' pp';
export type PriceBasis = 'close' | 'adjusted';
export interface TimelineRow {day:string; close:number; change_pct:number|null; adjusted_change_pct:number|null}
export interface CacheStatus {job:RecordData|null; instruments:number; with_history:number; failed:number; retrieved_at:string|null}
export interface PriceNetwork extends GraphData {panel:PricePanel;title:string;apple_node_count:number;control_company_count:number;control_policy?:RecordData|null;instruments:Record<string,RecordData>;cache:CacheStatus;benchmark_cache:CacheStatus;timeline:TimelineRow[];scope_note:string}
export interface DailyPrice {
 company_id:string;instrument_id:string|null;ticker:string|null;currency:string|null;exchange:string|null;
 timezone:string|null;date:string;close:number|null;adjusted_close:number|null;previous_date:string|null;
 previous_close:number|null;previous_adjusted_close:number|null;change_pct:number|null;vs_apple_pp:number|null;
 aligned_with_apple:boolean;relative_note:string|null;availability:string;missing_reason:string|null;
 retrieved_at:string|null;refresh_error:string|null;history_last_date:string|null;provider:string;
 market_adjusted_pp:number|null;market_expected_pct:number|null;market_fit_observations:number;
 market_fit_start:string|null;market_fit_end:string|null;market_reason:string|null;
 market_beta_spy?:number|null;market_beta_xlk?:number|null;market_alpha_pct?:number|null;
}
export interface PriceDay {date:string;root:string;panel:PricePanel;basis:PriceBasis;prices:DailyPrice[];apple_change_pct:number|null;apple_previous_date:string|null;counts:Record<string,number>;method:string;market_model:{window_sessions:number;minimum_aligned_observations:number;method:string;benchmarks:Record<string,{ticker:string;date:string;change_pct:number|null;previous_date:string|null}>}}
export const signed = (value:number|null|undefined, unit='%') => value==null?'—':`${value>0?'+':''}${value.toFixed(2)}${unit}`;
export const priceValue = (row:DailyPrice|undefined,mode:PriceMode) => row ? (mode==='market'?row.market_adjusted_pp:mode==='relative'?row.vs_apple_pp:row.change_pct) : null;
export const missingReason=(row:DailyPrice|undefined,mode:PriceMode)=>row?.missing_reason||(mode==='market'?row?.market_reason:mode==='relative'?row?.relative_note:null);
export const pricePositionKey=(network:PriceNetwork)=>'fieldnotes.price-map.positions.midnight-v2.'+(network.panel==='controls'?'controls.':'')+network.root;

export function priceColor(value:number|null|undefined,limit=5) {
 if(value==null||!Number.isFinite(value))return {fill:'#28354b',text:'#cbd5e1',border:'#64748b'};
 if(Math.abs(value)<1e-10)return {fill:'#18223b',text:'#e2e8f0',border:'#52627d'};
 const amount=Math.min(Math.abs(value)/Math.max(.01,limit),1);
 const start=[24,34,59],end=value>0?[16,110,80]:[161,40,65];
 const fill='#'+start.map((v,i)=>Math.round(v+(end[i]-v)*amount).toString(16).padStart(2,'0')).join('');
 return {fill,text:'#f1f5f9',border:value>0?'#34d399':'#fb7185'};
}

export function graphPositions(ids:string[],root:string):Record<string,{x:number;y:number}> {
 const others=ids.filter(id=>id!==root),cols=Math.max(7,Math.ceil(Math.sqrt(ids.length*1.25)));
 const rows=Math.ceil((ids.length+9)/cols),cx=Math.floor(cols/2),cy=Math.floor(rows/2);
 const slots:{x:number;y:number}[]=[];
 for(let y=0;y<rows;y++)for(let x=0;x<cols;x++)if(Math.abs(x-cx)>1||Math.abs(y-cy)>1)slots.push({x:x*116,y:y*90});
 while(slots.length<others.length){const y=rows+Math.floor((slots.length-others.length)/cols)+1;for(let x=0;x<cols;x++)slots.push({x:x*116,y:y*90});}
 const positions:Record<string,{x:number;y:number}>={[root]:{x:cx*116,y:cy*90}};
 others.forEach((id,index)=>positions[id]=slots[index]);
 return positions;
}
