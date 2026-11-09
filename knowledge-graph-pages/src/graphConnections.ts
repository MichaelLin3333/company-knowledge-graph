import type { Relationship } from './api';
import { edgePresentation, palette } from './graphPresentation';

export interface ConnectionGroup {
 id:string;
 companyIds:[string,string];
 relationshipIds:string[];
 categories:string[];
 color:string;
}

// Group for display only. Reciprocal directions, dates, evidence and distinct
// economic roles remain independent research records and are never merged.
export function groupConnections(edges:Relationship[]):ConnectionGroup[] {
 const groups=new Map<string,ConnectionGroup>();
 for(const edge of edges){
  const companyIds=[edge.source_id,edge.target_id].sort() as [string,string];
  const id='connection:'+companyIds.map(encodeURIComponent).join(':');
  let group=groups.get(id);
  if(!group){group={id,companyIds,relationshipIds:[],categories:[],color:'#78889a'};groups.set(id,group);}
  group.relationshipIds.push(edge.id);
  const category=edgePresentation(edge).category;
  if(!group.categories.includes(category))group.categories.push(category);
 }
 for(const group of groups.values()){
  group.relationshipIds.sort();group.categories.sort();
  if(group.categories.length===1)group.color=palette[group.categories[0]]?.line||'#78889a';
 }
 return [...groups.values()];
}

export type DetailSelection = {kind:'company'|'relationship'|'project';id:string} |
 {kind:'connection';id:string;companyIds:[string,string];relationshipIds:string[]};
