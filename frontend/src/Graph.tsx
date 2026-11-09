import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import cytoscape, { Core, EdgeSingular, ElementDefinition, Layouts } from 'cytoscape';
import cola from 'cytoscape-cola';
import { Focus, Minus, Pause, Play, Plus, RotateCcw, Route } from 'lucide-react';
import type { GraphData } from './api';
import { categoryFor, nodeCategory, palette } from './graphPresentation';
import { groupConnections, type ConnectionGroup } from './graphConnections';
import { companyNodeLabel } from './companyLabels';
import './graph.css';
import { reducedMotion, selectionPulse } from './graphEffects';
import { createDragPhysics, type DragPhysics } from './dragPhysics';
import { appleUSListings, excludedFill, screenLabels, unassessedBorder, type AppleScreen } from './investmentScreen';

cytoscape.use(cola);
type Point = { x:number; y:number };
type ColaLayout = Layouts;
type Motion = 'running'|'dragging'|'settled'|'paused';
const LABEL_VERSION = 'fieldnotes.layoutVersion.';
const LAYOUT_VERSION = 'midnight-circles-5';

function validPoint(value:unknown):value is Point {
 const point=value as Point;return !!point&&Number.isFinite(point.x)&&Number.isFinite(point.y)&&Math.abs(point.x)<1e6&&Math.abs(point.y)<1e6;
}

// Repair old saved layouts before the first frame. Label dimensions stay fixed
// in model space, so zoom cannot silently invalidate collision constraints.
function repairPositions(nodes:ElementDefinition[]) {
 const placed:{x:number;y:number;w:number;h:number}[]=[];
 for(const element of nodes){
  const original=element.position||{x:0,y:0},w=element.data?.root?130:112,h=element.data?.root?130:112;
  let point={...original};
  const overlaps=(p:Point)=>placed.some(other=>Math.abs(p.x-other.x)<(w+other.w)/2+18&&Math.abs(p.y-other.y)<(h+other.h)/2+18);
  for(let step=0;overlaps(point)&&step<1200;step++){
   const angle=step*2.3999632297,distance=40*Math.sqrt(step+1);
   point={x:original.x+Math.cos(angle)*distance,y:original.y+Math.sin(angle)*distance};
  }
  element.position=point;placed.push({...point,w,h});
 }
}

export default function Graph({data,root,pins,onCompany,onConnection,onPositions,onPin,selected,investmentScreen}: {
 data:GraphData|null;root:string;pins:string[];onCompany:(id:string)=>void;onConnection:(group:ConnectionGroup)=>void;onPositions:(positions:Record<string,Point>)=>void;onPin:(id:string)=>void;selected?:string;
 investmentScreen?:AppleScreen;
}) {
 const legend=useRef<HTMLDivElement>(null),host=useRef<HTMLDivElement>(null),cy=useRef<Core|null>(null),lastRoot=useRef('');
 const callbacks=useRef({onCompany,onConnection,onPositions,onPin}),pinIds=useRef(pins),physicsEnabled=useRef(true);
 const layout=useRef<ColaLayout|null>(null),settleTimer=useRef<ReturnType<typeof setInterval>|null>(null),dragged=useRef<string|null>(null),dragPhysics=useRef<DragPhysics|null>(null);
 const restart=useRef<(fit?:boolean)=>void>(()=>{}),stop=useRef<(save?:boolean)=>void>(()=>{});
 const [motion,setMotion]=useState<Motion>('settled'),[live,setLive]=useState(true);
 const [pathMode,setPathMode]=useState(false),[pathMissing,setPathMissing]=useState(false);
 const [tooltip,setTooltip]=useState<{text:string;x:number;y:number}|null>(null);
 callbacks.current={onCompany,onConnection,onPositions,onPin};pinIds.current=pins;

 const savePositions=()=>{
  const graph=cy.current;if(!graph)return;
  const positions:Record<string,Point>={};graph.nodes().forEach(node=>{positions[node.id()]={...node.position()};});
  callbacks.current.onPositions(positions);
 };
 const fitNetwork=(graph:Core)=>{
  if(!graph.nodes().length)return;
  const box=graph.nodes().boundingBox({includeLabels:true,includeOverlays:false}),padding=host.current&&host.current.clientWidth<500?32:48;
  const width=graph.width(),height=graph.height();
  const zoom=Math.max(.14,Math.min(1.55,(width-padding*2)/Math.max(1,box.w),(height-padding*2)/Math.max(1,box.h)));
  graph.viewport({zoom,pan:{x:width/2-(box.x1+box.w/2)*zoom,y:height/2-(box.y1+box.h/2)*zoom}});
 };

 useEffect(()=>{
  if(!host.current)return;
  const graph=cytoscape({container:host.current,elements:[],wheelSensitivity:.4,minZoom:.14,maxZoom:3.5,style:[
   {selector:'node',style:{'shape':'ellipse','width':96,'height':96,'background-color':'data(fill)','border-color':'data(border)','border-width':2.5,'label':'data(short)','color':'#e2e8f0','font-family':'Inter, Segoe UI, sans-serif','font-size':12,'font-weight':600,'text-valign':'center','text-halign':'center','text-wrap':'wrap','text-max-width':'86px','overlay-opacity':0,'min-zoomed-font-size':7}},
   {selector:'node[root]',style:{'width':112,'height':112,'background-color':'#5eead4','border-color':'#d7fff8','border-width':3,'color':'#062b27','font-size':14,'font-weight':700,'text-max-width':'100px','min-zoomed-font-size':0}},
   {selector:'node[private]',style:{'border-style':'dashed'}},
   {selector:'node.screen-excluded',style:{'background-color':excludedFill,'border-color':'#a3a7ae','color':'#f4f4f5'}},
   {selector:'node.screen-unassessed',style:{'border-color':unassessedBorder,'border-style':'dashed'}},
   {selector:'node[pinned]',style:{'border-width':4,'border-style':'double','underlay-color':'#e3aa35','underlay-padding':5,'underlay-opacity':.2}},
   {selector:'edge',style:{'width':(edge:EdgeSingular)=>Math.max(2.6,1.8/edge.cy().zoom()),'line-color':'data(color)','curve-style':'straight','opacity':.55,'target-arrow-shape':'none','source-arrow-shape':'none','label':'','overlay-opacity':0,'z-index':1}},
   {selector:'node.active',style:{'border-color':'#facc15','border-width':4,'underlay-shape':'ellipse','underlay-color':'#5eead4','underlay-padding':7,'underlay-opacity':.19,'z-index':10,'min-zoomed-font-size':0}},
   {selector:'edge.active',style:{'width':(edge:EdgeSingular)=>Math.max(4.6,3.4/edge.cy().zoom()),'opacity':1,'underlay-shape':'ellipse','underlay-color':'#5eead4','underlay-padding':4,'underlay-opacity':.15,'z-index':9}},
   {selector:'.dim',style:{'opacity':.16}}
  ]});
  cy.current=graph;
  const interaction=createDragPhysics(graph,{enabled:()=>physicsEnabled.current,reduced:reducedMotion,onState:running=>setMotion(running?(dragged.current?'dragging':'running'):physicsEnabled.current?'settled':'paused'),onSave:savePositions});
  dragPhysics.current=interaction;
  const stopPhysics=(save=true)=>{
   if(settleTimer.current)clearInterval(settleTimer.current);settleTimer.current=null;
   layout.current?.stop();layout.current=null;
   interaction.stop(false);
   if(!graph.destroyed()) {if(save)savePositions();setMotion(physicsEnabled.current?'settled':'paused');}
  };
  stop.current=stopPhysics;
  const startPhysics=(fit=false)=>{
   stopPhysics(false);interaction.reset();if(!graph.nodes().length)return;
   graph.nodes().forEach(node=>{pinIds.current.includes(node.id())?node.lock():node.unlock();});
   setMotion('running');
   const running=graph.layout({name:'cola',animate:!reducedMotion(),infinite:!reducedMotion(),refresh:1,fit:false,randomize:false,avoidOverlap:true,handleDisconnected:true,nodeDimensionsIncludeLabels:true,nodeSpacing:22,edgeLength:220,centerGraph:false,ungrabifyWhileSimulating:false,unconstrIter:0,userConstIter:0,allConstIter:12,convergenceThreshold:.015} as any) as ColaLayout;
   layout.current=running;running.run();
   let elapsed=0,stable=0,prior:Record<string,Point>={};
   settleTimer.current=setInterval(()=>{
    elapsed+=120;let change=0;
    graph.nodes().forEach(node=>{const point=node.position(),old=prior[node.id()];if(old)change=Math.max(change,Math.hypot(point.x-old.x,point.y-old.y));prior[node.id()]={...point};});
    if(dragged.current){elapsed=0;stable=0;return;}
    stable=change<.25?stable+1:0;
    if((elapsed>=1080&&stable>=4)||elapsed>=3600){stopPhysics();if(fit)fitNetwork(graph);}
   },120);
  };
  restart.current=startPhysics;
  graph.on('tap','node',event=>callbacks.current.onCompany(event.target.id()));
  graph.on('tap','edge',event=>callbacks.current.onConnection(event.target.data('connection')));
  graph.on('cxttap','node',event=>callbacks.current.onPin(event.target.id()));
  graph.on('grab','node',event=>{
   // Stop only the automatic layout; the drag simulation starts immediately.
   stopPhysics(false);dragged.current=event.target.id();setTooltip(null);
   interaction.begin(event.target.id());
  });
  graph.on('free','node',event=>{
   dragged.current=null;interaction.release(event.target.id());
  });
  graph.on('mouseover','node',event=>{
   if(dragged.current)return;
   const point=event.target.renderedPosition();
   const screenLabel=event.target.data('screenLabel');
   setTooltip({text:event.target.data('name')+(event.target.locked()?' · pinned':'')+(screenLabel?` · ${screenLabel}`:''),x:point.x,y:point.y});
  });
  graph.on('mouseover','edge',event=>{
   if(dragged.current)return;const point=event.renderedPosition||{x:graph.width()/2,y:70};
   setTooltip({text:'Open company connection details',x:point.x,y:point.y});
  });
  graph.on('mouseout','node,edge',()=>setTooltip(null));
  graph.on('pan zoom',()=>{setTooltip(null);if(lastRoot.current)localStorage.setItem('fieldnotes.viewport.'+lastRoot.current,JSON.stringify({zoom:graph.zoom(),pan:graph.pan()}));});
  graph.on('zoom',()=>graph.style().update());
  let priorSize={width:host.current.clientWidth,height:host.current.clientHeight};
  let resizeTimer:ReturnType<typeof setTimeout>;
  const observer=new ResizeObserver(()=>{
   const width=host.current?.clientWidth||0,height=host.current?.clientHeight||0;
   const resized=Math.abs(width-priorSize.width)>1||Math.abs(height-priorSize.height)>1;
   const zoom=graph.zoom(),pan=graph.pan();
   const center={x:(priorSize.width/2-pan.x)/zoom,y:(priorSize.height/2-pan.y)/zoom};
   priorSize={width,height};graph.resize();
   // Opening a drawer or widening the workspace preserves the user's scale.
   if(resized&&width&&height){clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(!graph.destroyed()&&!dragged.current)graph.pan({x:width/2-center.x*graph.zoom(),y:height/2-center.y*graph.zoom()});},100);}
  });observer.observe(host.current);
  const legendObserver=new ResizeObserver(()=>{if(host.current&&legend.current){host.current.style.bottom=legend.current.getBoundingClientRect().height+'px';graph.resize();}});
  if(legend.current)legendObserver.observe(legend.current);
  const pauseWhenHidden=()=>{if(document.hidden)stopPhysics();};
  document.addEventListener('visibilitychange',pauseWhenHidden);
  return()=>{
   interaction.dispose();dragPhysics.current=null;clearTimeout(resizeTimer);if(settleTimer.current)clearInterval(settleTimer.current);layout.current?.stop();layout.current=null;
   document.removeEventListener('visibilitychange',pauseWhenHidden);observer.disconnect();legendObserver.disconnect();graph.destroy();cy.current=null;
  };
 },[]);

 useLayoutEffect(()=>{
  // A new neighborhood can move the canvas without changing its dimensions.
  cy.current?.resize();
 },[data,root]);

 useEffect(()=>{
  const graph=cy.current;if(!graph||!data||(data.root&&data.root!==root))return;
  stop.current(false);dragPhysics.current?.reset();const rootChanged=lastRoot.current!==root;lastRoot.current=root;
  let stored:Record<string,Point>={};
  try{stored=JSON.parse(localStorage.getItem('fieldnotes.positions.'+root)||'{}');}catch{/* Invalid legacy view state gets a clean layout. */}
  const currentPositions:Record<string,Point>={};graph.nodes().forEach(node=>{currentPositions[node.id()]={...node.position()};});
  const previousIds=new Set(graph.nodes().map(node=>node.id()));
  const categories=Object.keys(palette);
  const ordered=[...data.nodes].sort((a,b)=>a.id===root?-1:b.id===root?1:a.id.localeCompare(b.id));
  const nodeElements:ElementDefinition[]=ordered.map((node,index)=>{
   const category=nodeCategory(node.id,data.edges,root),colors=palette[category]||palette[categoryFor('')];
   const group=Math.max(0,categories.indexOf(category)),angle=(index/Math.max(1,ordered.length-1))*Math.PI*2+group*.11;
   const radius=node.id===root?0:Math.max(190,Math.sqrt(ordered.length)*53)+(index%3)*40;
   const old=(!rootChanged&&currentPositions[node.id])||stored[node.id];
   const position=validPoint(old)?old:{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius};
    const short=companyNodeLabel(node,node.id===root);
   return {data:{id:node.id,name:node.name,short,category,fill:colors.fill,border:colors.border||colors.line,...(node.id===root?{root:true}:{}),...(/private/i.test(node.status||'')?{private:true}:{}),...(pins.includes(node.id)?{pinned:true}:{})},position};
  });
  repairPositions(nodeElements);
  const edgeElements:ElementDefinition[]=groupConnections(data.edges).map(connection=>({data:{id:connection.id,source:connection.companyIds[0],target:connection.companyIds[1],color:connection.color,connection,relationshipIds:connection.relationshipIds}}));
  graph.startBatch();graph.elements().remove();graph.add([...nodeElements,...edgeElements]);graph.endBatch();
  graph.nodes().forEach(node=>{pins.includes(node.id())?node.lock():node.unlock();});
  const layoutVersion=root==='AAPL'?`${LAYOUT_VERSION}-full-roster`:LAYOUT_VERSION;
  const layoutUpdated=localStorage.getItem(LABEL_VERSION+root)!==layoutVersion;
  let restored=false;
  if(rootChanged&&!layoutUpdated){
   try{const view=JSON.parse(localStorage.getItem('fieldnotes.viewport.'+root)||'null');if(view&&Number.isFinite(view.zoom)&&validPoint(view.pan)){graph.viewport(view);restored=true;}}catch{/* Fit an invalid saved viewport. */}
  }
  const added=data.nodes.some(node=>!previousIds.has(node.id));
  if((rootChanged&&!restored)||!previousIds.size||layoutUpdated)fitNetwork(graph);
  localStorage.setItem(LABEL_VERSION+root,layoutVersion);
  // Selecting a record does not enter this effect, so it cannot rearrange nodes.
  const completeSavedLayout=data.nodes.every(node=>validPoint(stored[node.id]));
  if(physicsEnabled.current&&(layoutUpdated||(rootChanged&&!completeSavedLayout)||(!rootChanged&&added)))restart.current((rootChanged&&!restored)||layoutUpdated);
  else {savePositions();setMotion(physicsEnabled.current?'settled':'paused');}
  if(!rootChanged&&added)graph.resize();
 },[data,root]);

 useEffect(()=>{
  const graph=cy.current;if(!graph)return;
  graph.nodes().forEach(node=>{if(pins.includes(node.id())){node.data('pinned',true);node.lock();}else{node.removeData('pinned');node.unlock();}});
  dragPhysics.current?.syncPins();
 },[pins]);
 useEffect(()=>{setPathMode(false);setPathMissing(false);},[selected,root]);
 useEffect(()=>{const graph=cy.current;if(graph&&selected)return selectionPulse(graph,[selected]);},[selected]);
 useEffect(()=>{
  const graph=cy.current;if(!graph)return;graph.elements().removeClass('active dim');
  if(!selected)return;let element=graph.getElementById(selected);if(!element.length)element=graph.edges().filter(edge=>edge.data('relationshipIds')?.includes(selected));if(!element.length)return;
  if(pathMode&&element.nodes().length&&graph.getElementById(root).length){
   const path=graph.elements().aStar({root:graph.getElementById(root),goal:element,directed:false});
   if(path.found){path.path.addClass('active');graph.elements().difference(path.path).addClass('dim');setPathMissing(false);return;}setPathMissing(true);
  }
  element.addClass('active');const connected=element.nodes().length?element.closedNeighborhood():element.union(element.connectedNodes());graph.elements().difference(connected).addClass('dim');
 },[selected,data,pathMode,root]);

 useEffect(()=>{
  const graph=cy.current;
  if(!graph||lastRoot.current!==root)return;
  graph.batch(()=>graph.nodes().forEach(node=>{
   const entry=investmentScreen?.companies[node.id()];
   node.toggleClass('screen-excluded',entry?.status==='excluded');
   node.toggleClass('screen-unassessed',!!entry&&['insufficient','unlisted','unmapped'].includes(entry.status));
   if(entry)node.data('screenLabel',screenLabels[entry.status]);else node.removeData('screenLabel');
  }));
 },[data,root,investmentScreen]);

 const toggleLive=()=>{
  physicsEnabled.current=!physicsEnabled.current;setLive(physicsEnabled.current);
  if(physicsEnabled.current)setMotion('settled');else{stop.current();setMotion('paused');}
 };
 return <div className="graph-stage graph-stage-v2" data-layout-state={motion}>
  <div ref={host} className="graph-canvas" aria-label="Company relationship graph. Drag a company to reshape the network. Connected companies respond continuously while dragging. Placed companies retain flexible anchors. Each line opens every relationship between that company pair. Use the relationship table for keyboard navigation." role="img"/>
  {tooltip&&<div className="node-tooltip" style={{left:Math.max(12,Math.min(tooltip.x-100,(host.current?.clientWidth||300)-255)),top:Math.max(12,tooltip.y-62)}}>{tooltip.text}</div>}
  <div className={'layout-status '+(motion==='running'||motion==='dragging'?'is-settling':'')} role="status"><span/>{motion==='dragging'?'Dragging · live springs':motion==='running'?'Settling network':motion==='paused'?'Motion paused':'Spring motion · drag to reshape'}</div>
   {selected&&data?.nodes.some(node=>node.id===selected)&&<div className="path-control"><button className="button" onClick={()=>{const graph=cy.current,node=graph?.getElementById(selected);if(graph&&node?.length){stop.current();const point=node.position(),zoom=Math.max(1,graph.zoom());graph.viewport({zoom,pan:{x:graph.width()/2-point.x*zoom,y:graph.height()/2-point.y*zoom}});}}}><Focus size={13}/>Zoom to selected company</button>{selected!==root&&<button className={'button '+(pathMode?'active':'')} onClick={()=>setPathMode(!pathMode)}><Route size={13}/>{pathMode?'Clear highlighted path':'Highlight path from root'}</button>}{pathMode&&<small>{pathMissing?'No path connects these companies in this view.':'Documented adjacency only; no implied transitive relationship.'}</small>}</div>}
  {!data?.nodes.length&&<div className="canvas-empty"><span className="orb"/>{data?"No companies match this view. Widen the filters to continue.":"Preparing your company network…"}</div>}
  <div className="graph-controls" aria-label="Graph controls">
   <button title="Zoom in" aria-label="Zoom in" onClick={()=>{const graph=cy.current;if(graph)graph.zoom({level:graph.zoom()*1.2,renderedPosition:{x:graph.width()/2,y:graph.height()/2}});}}><Plus size={18}/></button>
   <button title="Zoom out" aria-label="Zoom out" onClick={()=>{const graph=cy.current;if(graph)graph.zoom({level:graph.zoom()/1.2,renderedPosition:{x:graph.width()/2,y:graph.height()/2}});}}><Minus size={18}/></button>
   <button title="Fit network" aria-label="Fit network" onClick={()=>cy.current&&fitNetwork(cy.current)}><Focus size={18}/></button>
   <button title="Arrange unpinned companies" aria-label="Arrange unpinned companies" onClick={()=>restart.current(true)}><RotateCcw size={17}/></button>
   <button className={live?'physics-active':''} title={live?'Pause graph motion':'Resume graph motion'} aria-label={live?'Pause graph motion':'Resume graph motion'} aria-pressed={live} onClick={toggleLive}>{live?<Pause size={16}/>:<Play size={16}/>}</button>
  </div>
  <div ref={legend} className="graph-legend" aria-label="Relationship colors and investment screen">
   {Object.entries(palette).filter(([key])=>key!=='unknown').map(([key,value])=><span key={key}><i className="legend-swatch" style={{background:value.line}}/>{value.label}</span>)}
   <span><i className="legend-swatch" style={{background:'#78889a'}}/>Multiple categories</span>
   {investmentScreen&&<>
    <span><i className="legend-swatch" style={{background:excludedFill,height:9}}/>Gray nodes · price-risk exclusion ({investmentScreen.counts.excluded})</span>
    <span><i className="legend-swatch" style={{border:`1px dashed ${unassessedBorder}`,height:9}}/>Dashed gold outline · no screen decision</span>
    <span className="legend-note">Apple price-risk screen through {investmentScreen.as_of} · {investmentScreen.counts.retained} peers retained for research. Open a company for its result.</span>
    <span className="legend-note">U.S. exchange listings as of {appleUSListings.as_of} · {appleUSListings.count} companies · {appleUSListings.retained} in the screened basket, including Apple.</span>
   </>}
   <span className="legend-note">One line per company pair. Click to inspect all roles, directions and evidence.</span>
  </div>
 </div>;
}
