export type RecordData = Record<string, any>;
export interface Company extends RecordData { id:string; name:string; country?:string; status?:string; primary_ticker?:string; }
export interface Relationship extends RecordData { id:string; source_id:string; target_id:string; type:string; description?:string; evidence_grade?:string; status?:string; direction?:string; }
export interface GraphData { revision:number; root:string; nodes:Company[]; edges:Relationship[]; hidden_nodes:number; hidden_edges:number; total_nodes:number; total_edges:number; limits:{nodes:number;edges:number}; filter_note?:string; }
export interface Filters { types:string; evidence:string; statuses:string; country:string; product:string; project_id:string; batch_id:string; as_of:string; }
export const emptyFilters:Filters = { types:'',evidence:'',statuses:'',country:'',product:'',project_id:'',batch_id:'',as_of:'' };
export async function api<T=RecordData>(path:string, init?:RequestInit):Promise<T> {
 const response = await fetch('/api'+path, { ...init, headers:{'Content-Type':'application/json',...init?.headers} });
 const isJson = response.headers.get('content-type')?.includes('application/json');
 const data = isJson ? await response.json() : await response.text();
 if(!response.ok) throw new Error(typeof data==='string' ? data : (typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data.errors||data)));
 return data;
}
export const post = <T=RecordData>(path:string, body:unknown) => api<T>(path,{method:'POST',body:JSON.stringify(body)});
export function label(value:unknown):string { return String(value ?? 'Unknown').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()); }
export function display(value:unknown):string { return value===null||value===undefined||value===''?'Not disclosed':typeof value==='object'?JSON.stringify(value):String(value); }
export function download(value:unknown,name:string) { const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})); const anchor=document.createElement('a'); anchor.href=url;anchor.download=name;anchor.click();URL.revokeObjectURL(url); }
