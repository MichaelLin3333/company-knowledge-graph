import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import cytoscape, { type Core, type ElementDefinition, type Layouts } from 'cytoscape';
import { Focus, Minus, Plus, RotateCcw, Pause, Play } from 'lucide-react';
import cola from 'cytoscape-cola';
import { reducedMotion, selectionPulse } from './graphEffects';
import { createDragPhysics, type DragPhysics } from './dragPhysics';
import { groupConnections, type ConnectionGroup } from './graphConnections';
import { graphPositions, priceColor, priceValue, pricePositionKey, modeLabel, modeUnit, missingReason, signed, type PriceDay, type PriceMode, type PriceNetwork } from './market';

cytoscape.use(cola);

export interface PriceCanvasHandle {fit:()=>void;focus:(id:string)=>void;exportPNG:()=>Promise<void>}
interface Props {network:PriceNetwork;day:PriceDay|null;mode:PriceMode;limit:number;selected:string|null;connections:boolean;onCompany:(id:string)=>void;onConnection:(group:ConnectionGroup)=>void}

export default forwardRef<PriceCanvasHandle,Props>(function PriceCanvas({network,day,mode,limit,selected,connections,onCompany,onConnection},ref){
 const host=useRef<HTMLDivElement>(null),cy=useRef<Core|null>(null);
 const callbacks=useRef({onCompany,onConnection});callbacks.current={onCompany,onConnection};
 const latest=useRef({network,day,mode,limit});latest.current={network,day,mode,limit};
 const [tooltip,setTooltip]=useState<{x:number;y:number;id:string}|null>(null);
 const layout=useRef<Layouts|null>(null),physics=useRef(true),dragPhysics=useRef<DragPhysics|null>(null);
 const [live,setLive]=useState(true),[arranging,setArranging]=useState(false),[dragging,setDragging]=useState(false);
 const stopLayout=()=>{const current=layout.current;layout.current=null;if(current){current.stop();cy.current?.nodes().stop(true,false);}};
 const savePositions=()=>{const g=cy.current;if(g&&!g.destroyed())localStorage.setItem(pricePositionKey(latest.current.network),JSON.stringify(Object.fromEntries(g.nodes().map(n=>[n.id(),n.position()]))));};
 const arrange=(fitAfter=false)=>{
  const g=cy.current;if(!g||!g.edges().length)return;stopLayout();dragPhysics.current?.reset();setArranging(true);
  g.nodes().unlock();
  const running=g.layout({name:'cola',animate:!reducedMotion(),infinite:false,fit:false,randomize:false,avoidOverlap:true,nodeDimensionsIncludeLabels:true,nodeSpacing:16,edgeLength:150,maxSimulationTime:2200,stop:()=>{if(g.destroyed()||layout.current!==running)return;layout.current=null;setArranging(false);savePositions();if(fitAfter)fit();}} as any);
  layout.current=running;running.run();
 };
 const fit=()=>{const graph=cy.current;if(graph){graph.resize();graph.fit(graph.elements(),26);}};
 const focus=(id:string)=>{const graph=cy.current,node=graph?.getElementById(id);if(graph&&node?.length){const p=node.position(),zoom=Math.max(.95,graph.zoom());graph.viewport({zoom,pan:{x:graph.width()/2-p.x*zoom,y:graph.height()/2-p.y*zoom}});}};
 useImperativeHandle(ref,()=>({fit,focus,exportPNG:async()=>{
  const graph=cy.current,current=latest.current;if(!graph||!current.day)return;
  const uri=graph.png({full:true,scale:1.5,bg:'#0b1020'});
  const img=new Image();img.src=uri;await img.decode();
  const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height+150;
  const context=canvas.getContext('2d');if(!context)return;
  context.fillStyle='#0b1020';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(img,0,150);
  context.fillStyle='#e2e8f0';context.font='bold 28px sans-serif';
  context.fillText(`${current.network.title} | ${current.day.date} | ${modeLabel[current.mode]}`,28,40);
  context.font='18px sans-serif';context.fillText(`${network.nodes.length} companies | ${current.day.basis==='close'?'Close price':'Adjusted close'} | fixed color limit +/-${current.limit}${modeUnit(current.mode)} | Gray: unavailable`,28,72);
  [-1,-.5,0,.5,1].forEach((v,i)=>{context.fillStyle=priceColor(v*current.limit,current.limit).fill;context.fillRect(28+i*150,90,140,22);context.fillStyle='#e2e8f0';context.font='15px sans-serif';context.fillText(signed(v*current.limit,modeUnit(current.mode)),30+i*150,133);});
  const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(new Error('Map image could not be created.'))));
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${current.network.panel}-price-map-${current.day.date}-${current.mode}.png`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000);
 }}));

 useEffect(()=>{
  if(!host.current)return;
  const graph=cytoscape({container:host.current,elements:[],layout:{name:'preset'},minZoom:.08,maxZoom:3.5,wheelSensitivity:.4,style:[
   {selector:'node',style:{'shape':'ellipse','width':72,'height':72,'label':'data(caption)','background-color':'data(fill)','border-color':'data(border)','border-width':1.3,'color':'data(text)','font-size':13,'font-weight':600,'font-family':'Segoe UI, sans-serif','text-valign':'center','text-halign':'center','text-wrap':'wrap','text-max-width':'66px','overlay-opacity':0,'min-zoomed-font-size':7,'transition-property':'background-color, border-color, color','transition-duration':reducedMotion()?0:220}},
   {selector:'node[root]',style:{'width':112,'height':112,'font-size':18,'border-width':4,'border-color':'#5eead4','underlay-shape':'ellipse','underlay-color':'#5eead4','underlay-padding':10,'underlay-opacity':.18,'text-max-width':'102px','min-zoomed-font-size':0,'z-index':5}},
   {selector:'node[missing]',style:{'border-style':'dashed'}},
   {selector:'edge',style:{'width':.8,'line-color':'#536d94','opacity':.25,'curve-style':'straight','target-arrow-shape':'none','source-arrow-shape':'none','overlay-opacity':0}},
   {selector:'edge.highlight',style:{'width':2.6,'opacity':.85,'line-color':'#5eead4','z-index':4}},
   {selector:'node.chosen',style:{'border-width':4,'border-color':'#facc15','underlay-shape':'ellipse','underlay-color':'#5eead4','underlay-padding':5,'underlay-opacity':.3,'z-index':7}},
   {selector:'node[root].chosen',style:{'border-color':'#5eead4','border-width':5,'underlay-shape':'ellipse','underlay-color':'#5eead4','underlay-padding':10,'underlay-opacity':.2}},
  ]});cy.current=graph;
  graph.on('tap','node',event=>callbacks.current.onCompany(event.target.id()));
  graph.on('tap','edge',event=>callbacks.current.onConnection(event.target.data('connection')));
  graph.on('mouseover','node',event=>{const point=event.target.renderedPosition();setTooltip({id:event.target.id(),x:point.x,y:point.y});graph.edges().removeClass('highlight');event.target.connectedEdges().addClass('highlight');});
  graph.on('mouseout','node',()=>{setTooltip(null);graph.edges().removeClass('highlight');});
  graph.on('pan zoom grab',()=>setTooltip(null));
  const interaction=createDragPhysics(graph,{enabled:()=>physics.current,reduced:reducedMotion,onState:setArranging,onSave:savePositions});
  dragPhysics.current=interaction;
  graph.on('grab','node',event=>{stopLayout();setDragging(true);interaction.begin(event.target.id());});
  graph.on('free','node',event=>{setDragging(false);interaction.release(event.target.id());});
  const observer=new ResizeObserver(()=>graph.resize());observer.observe(host.current);
  const onHidden=()=>{if(document.hidden){stopLayout();interaction.stop();}};document.addEventListener('visibilitychange',onHidden);
  return()=>{interaction.dispose();dragPhysics.current=null;document.removeEventListener('visibilitychange',onHidden);stopLayout();observer.disconnect();graph.destroy();cy.current=null;};
 },[]);

 useEffect(()=>{
  const graph=cy.current;if(!graph)return;
  stopLayout();dragPhysics.current?.reset();
  const ordered=[...network.nodes].sort((a,b)=>a.id===network.root?-1:b.id===network.root?1:(a.country||'').localeCompare(b.country||'')||a.name.localeCompare(b.name));
  let saved:Record<string,{x:number;y:number}>={};try{saved=JSON.parse(localStorage.getItem(pricePositionKey(latest.current.network))||'{}');}catch{/* fresh view */}
  const positions=graphPositions(ordered.map(n=>n.id),network.root);
  const elements:ElementDefinition[]=ordered.map(node=>({data:{id:node.id,name:node.name,caption:node.primary_ticker||node.id,fill:'#28354b',text:'#cbd5e1',border:'#64748b',...(node.id===network.root?{root:true}:{})},position:saved[node.id]&&Number.isFinite(saved[node.id].x)&&Number.isFinite(saved[node.id].y)?saved[node.id]:positions[node.id]}));
  const edges=groupConnections(network.edges).map(connection=>({data:{id:connection.id,source:connection.companyIds[0],target:connection.companyIds[1],connection}}));
  graph.batch(()=>{graph.elements().remove();graph.add([...elements,...edges]);});
  requestAnimationFrame(fit);
 },[network.nodes,network.edges,network.root]);

 useEffect(()=>{
  const graph=cy.current;if(!graph)return;const rows=new Map(day?.prices.map(row=>[row.company_id,row])||[]);
  graph.batch(()=>graph.nodes().forEach(node=>{
   const row=rows.get(node.id()),value=priceValue(row,mode),colors=priceColor(value,limit);
   const symbol=row?.ticker||network.nodes.find(n=>n.id===node.id())?.primary_ticker||node.id();
   node.data({...colors,caption:`${node.id()===network.root?'APPLE · ':''}${symbol.length>14?symbol.slice(0,13)+'…':symbol}\n${signed(value,modeUnit(mode))}`});
   if(value==null)node.data('missing',true);else node.removeData('missing');
  }));
 },[day,mode,limit,network]);
 useEffect(()=>{const graph=cy.current;if(!graph)return;graph.nodes().removeClass('chosen');if(selected){graph.getElementById(selected).addClass('chosen');return selectionPulse(graph,[selected]);}},[selected,network.nodes]);
 useEffect(()=>{cy.current?.edges().style('display',connections?'element':'none');},[connections,network]);
 const hoverCompany=network.nodes.find(n=>n.id===tooltip?.id),hoverPrice=day?.prices.find(p=>p.company_id===tooltip?.id);
 return <div className="price-canvas-wrap">
  <div ref={host} className="price-canvas" role="img" aria-label={`${network.panel==='controls'?'Cross-industry reference':'Complete Apple'} price graph: ${network.nodes.length} companies. ${day?.date||'Loading date'}. Use the company list for keyboard access.`}/>
  <div className="price-canvas-controls"><button aria-label="Zoom price graph in" title="Zoom in" onClick={()=>{const g=cy.current;if(g)g.zoom({level:g.zoom()*1.3,renderedPosition:{x:g.width()/2,y:g.height()/2}});}}><Plus size={17}/></button><button aria-label="Zoom price graph out" title="Zoom out" onClick={()=>{const g=cy.current;if(g)g.zoom({level:g.zoom()/1.3,renderedPosition:{x:g.width()/2,y:g.height()/2}});}}><Minus size={17}/></button><button aria-label="Fit entire Apple graph" title="Fit every company" onClick={fit}><Focus size={17}/></button><button aria-label="Arrange as connected network" title={network.edges.length?"Arrange as connected network":"No relationship edges asserted in this reference panel"} disabled={!network.edges.length} onClick={()=>arrange(true)}><ActivityIcon/></button><button aria-label="Reset price graph layout" title="Compact atlas layout" onClick={()=>{const g=cy.current;if(g){stopLayout();dragPhysics.current?.reset();g.nodes().unlock();const ordered=[...network.nodes].sort((a,b)=>a.id===network.root?-1:b.id===network.root?1:(a.country||'').localeCompare(b.country||'')||a.name.localeCompare(b.name));const positions=graphPositions(ordered.map(n=>n.id),network.root);const resetting=g.layout({name:'preset',positions,animate:!reducedMotion(),animationDuration:450,fit:true,padding:26});layout.current=resetting;resetting.run();localStorage.removeItem(pricePositionKey(latest.current.network));fit();}}}><RotateCcw size={17}/></button><button aria-label={live?'Pause price graph motion':'Resume price graph motion'} title={live?'Pause spring motion':'Resume spring motion'} aria-pressed={live} disabled={!network.edges.length} className={live?'active':''} onClick={()=>{physics.current=!physics.current;setLive(physics.current);if(!physics.current){stopLayout();dragPhysics.current?.stop();setArranging(false);}}}>{live?<Pause size={16}/>:<Play size={16}/>}</button></div>
  <div className="price-motion-status" role="status"><i/>{arranging?(dragging?'Dragging · live springs':'Settling network'):!network.edges.length?'Independent reference companies':live?'Spring motion · drag to reshape':'Motion paused'}</div>
  {tooltip&&hoverCompany&&<div className="price-node-tooltip" style={{left:Math.min(Math.max(tooltip.x-110,8),(host.current?.clientWidth||400)-244),top:Math.max(tooltip.y-100,8)}}><strong>{hoverCompany.name}</strong><span>{hoverPrice?.ticker||'No own listing'} · {hoverCompany.country||'Country unknown'}</span><b>{signed(hoverPrice?.change_pct)} daily · {signed(hoverPrice?.vs_apple_pp,' pp')} vs Apple</b>{mode==='market'&&<small>After SPY + XLK: {signed(hoverPrice?.market_adjusted_pp,' pp')}</small>}{missingReason(hoverPrice,mode)&&<small>{missingReason(hoverPrice,mode)}</small>}</div>}
 </div>;
});
function ActivityIcon(){return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="4" r="2"/><circle cx="20" cy="5" r="2"/><circle cx="5" cy="20" r="2"/><circle cx="20" cy="20" r="2"/><path d="m5 5 5 5m4 0 5-4M6 19l4-5m4 0 5 5"/></svg>}
