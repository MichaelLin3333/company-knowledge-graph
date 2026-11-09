import type { Relationship } from './api';

export type PresentationDirection = 'directed' | 'bidirectional' | 'undirected';
export interface EdgePresentation {
 source:string; target:string; direction:PresentationDirection;
 label:string; category:string; directionBasis:string; roleLabel:string;
}

// Colors identify relationship roles in the current view, not company sectors,
// investment importance, evidence quality or the expected direction of a price.
export const palette:Record<string,{label:string;line:string;fill:string;border:string}> = {
 supply:{label:'Supply & manufacturing',line:'#5eead4',fill:'#163f43',border:'#5eead4'},
 customers:{label:'Customers & distribution',line:'#60a5fa',fill:'#1b3355',border:'#60a5fa'},
 ownership:{label:'Ownership & investment',line:'#fbbf24',fill:'#42391f',border:'#fbbf24'},
 collaboration:{label:'Collaboration & integration',line:'#c084fc',fill:'#38284e',border:'#c084fc'},
 infrastructure:{label:'Infrastructure & finance',line:'#38bdf8',fill:'#15394e',border:'#38bdf8'},
 competition:{label:'Competition',line:'#fb7185',fill:'#4a293b',border:'#fb7185'},
 unknown:{label:'Other / unclassified',line:'#94a3b8',fill:'#28354b',border:'#94a3b8'},
};

export function categoryFor(type:string):string {
 if (/compet|substitut/i.test(type)) return 'competition';
 if (/invest|ownership|stake|subsidiary|equity|joint_venture|acquisit|parent|asset_purchase|asset_transfer|business_disposal/i.test(type)) return 'ownership';
 if (/power|infrastructure|financ|lease|energy|project|loan|debt|guarantee|capacity_reservation/i.test(type)) return 'infrastructure';
 if (/supplier|supply|upstream|manufactur|assembly|packag|fabricat|equipment|material|component_presence|component_exposure/i.test(type)) return 'supply';
 if (/customer|downstream|channel|distribut|resell/i.test(type)) return 'customers';
 if (/complement|collaborat|partner|integrat|licens|dependenc|joint_develop|service_adoption/i.test(type)) return 'collaboration';
 return 'unknown';
}

const defaultLabels:Record<string,string> = {
 upstream_supplier:'Supplies',downstream_customer:'Serves',channel_partner:'Channel partner',
 strategic_equity:'Invests in',joint_venture:'Joint venture',infrastructure:'Infrastructure partner',
 financing:'Financial relationship',competitor:'Competes with',complement:'Collaborates with',
};

function currentLabel(edge:Relationship, label:string):string {
 if (edge.status==='planned' && !/proposed|planned/i.test(label)) return `${label} · planned`;
 if (edge.status==='historical') return `${label} · historical`;
 return label;
}


export function edgePresentation(edge:Relationship):EdgePresentation {
 const category=categoryFor(edge.type??'');
 const label=defaultLabels[edge.type]??String(edge.type||'Related').replace(/_/g,' ');
 const result:EdgePresentation={source:edge.source_id,target:edge.target_id,direction:'undirected',category,label:currentLabel(edge,label),roleLabel:label,directionBasis:'No verified one-way role is available for this displayed record. The line indicates a relationship only.'};

 // Newly researched, reviewed directions are authoritative. Never infer them
 // from the order of a discovery path, the root company, or an issuer ticker.
 if (edge.direction_review_status==='reviewed' && ['directed','bidirectional'].includes(edge.direction??'')) {
  result.direction=edge.direction as PresentationDirection;
  result.directionBasis='The research record marks the direction as reviewed.';
 }
 return result;
}

export function nodeCategory(id:string, edges:Relationship[], root:string):string {
 const scores:Record<string,number>={};
 for (const edge of edges) {
  if (edge.source_id!==id && edge.target_id!==id) continue;
  const category=edgePresentation(edge).category;
  // Direct relationships to the selected company take precedence over a
  // counterparty's wider ecosystem. Ties have a deterministic palette order.
  const weight=id!==root && (edge.source_id===root||edge.target_id===root)?4:1;
  scores[category]=(scores[category]??0)+weight;
 }
 return Object.keys(palette).reduce((best,key)=>(scores[key]??0)>(scores[best]??0)?key:best,'unknown');
}
