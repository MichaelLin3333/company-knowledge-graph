import type { Core } from 'cytoscape';

export interface Point { x:number; y:number }
export interface BodyInput extends Point { id:string; radius:number; pinned:boolean }
export interface LinkInput { source:string; target:string }
interface Body extends BodyInput {
 vx:number; vy:number; ax:number; ay:number; manual:boolean; degree:number;
}
interface Spring { a:Body; b:Body; length:number; dx:number; dy:number }
const limit = (value:number, maximum:number) => Math.max(-maximum, Math.min(maximum, value));

/** Drag-only springs. An explicit Arrange action uses the global layout instead.
 * Rest lengths come from the current layout, never a discarded solver snapshot.
 * User placements are soft anchors, while explicit pins remain immovable.
 */
export class DragSimulation {
 readonly bodies = new Map<string, Body>();
 private placements = new Map<string, Point>();
 private springs:Spring[] = [];
 private grabbed:string|null = null;

 begin(nodes:BodyInput[], links:LinkInput[], id:string) {
  const previous = new Map(this.bodies);
  this.bodies.clear();
  for (const node of nodes) {
   const anchor = this.placements.get(node.id) || node;
   const old = previous.get(node.id);
   this.bodies.set(node.id, {...node, vx:old?.vx||0, vy:old?.vy||0,
    ax:anchor.x, ay:anchor.y, manual:this.placements.has(node.id), degree:0});
  }
  this.springs = [];
  for (const link of links) {
   const a=this.bodies.get(link.source), b=this.bodies.get(link.target);
   if (!a || !b || a===b) continue;
   a.degree++; b.degree++;
   this.springs.push({a,b,dx:b.x-a.x,dy:b.y-a.y,length:Math.max(a.radius+b.radius+18,Math.hypot(b.x-a.x,b.y-a.y))});
  }
  this.grabbed=id;
  const held=this.bodies.get(id); if(held){held.vx=0;held.vy=0;}
 }

 move(id:string, point:Point) {
  const body=this.bodies.get(id);
  if(body){body.x=point.x;body.y=point.y;body.vx=0;body.vy=0;}
 }

 release(id:string, point:Point) {
  this.move(id,point);
  this.placements.set(id,{...point});
  const body=this.bodies.get(id);
  if(body){body.ax=point.x;body.ay=point.y;body.manual=true;}
  this.grabbed=null;
 }

 reset() { this.bodies.clear();this.springs=[];this.placements.clear();this.grabbed=null; }

 step(dt=1) {
  dt=Math.max(.25,Math.min(dt,1.5));
  const bodies=[...this.bodies.values()];
  const forces=new Map(bodies.map(body=>[body.id,{x:0,y:0}]));
  const fixed=(body:Body)=>body.pinned||body.id===this.grabbed;
  for(const spring of this.springs){
   const {a,b}=spring,dx=b.x-a.x,dy=b.y-a.y,distance=Math.max(.01,Math.hypot(dx,dy));
   const driven=a.id===this.grabbed||b.id===this.grabbed;
   const force=limit(distance-spring.length,driven?350:120)*(driven?.065:.045);
   // A small shear spring transmits sideways drags, not only edge stretching.
   const shear=driven?.018:.004;
   const x=dx/distance*force+limit(dx-spring.dx,350)*shear;
   const y=dy/distance*force+limit(dy-spring.dy,350)*shear;
   const af=forces.get(a.id)!,bf=forces.get(b.id)!;
   // A hub's many incident edges must not multiply its acceleration.
   // A held leaf must visibly tug a large hub. Its input is not divided by the
   // hub's degree; existing manual placements still resist that input gently.
   const aw=b.id===this.grabbed?(a.manual?.18:1):1/Math.sqrt(Math.max(1,a.degree));
   const bw=a.id===this.grabbed?(b.manual?.18:1):1/Math.sqrt(Math.max(1,b.degree));
   af.x+=x*aw;af.y+=y*aw;bf.x-=x*bw;bf.y-=y*bw;
  }
  for(let i=0;i<bodies.length;i++)for(let j=i+1;j<bodies.length;j++){
   const a=bodies[i],b=bodies[j],dx=b.x-a.x,dy=b.y-a.y;
   const distance=Math.hypot(dx,dy),overlap=a.radius+b.radius+14-distance;
   if(overlap<=0||fixed(a)&&fixed(b))continue;
   // Stable separation direction for perfectly coincident nodes.
   const nx=distance>.001?dx/distance:1,ny=distance>.001?dy/distance:0;
   const force=Math.min(18,overlap*.22);
   const aw=fixed(a)?0:fixed(b)?1:a.manual&&!b.manual?.18:!a.manual&&b.manual?.82:.5;
   const bw=1-aw,af=forces.get(a.id)!,bf=forces.get(b.id)!;
   af.x-=nx*force*aw;af.y-=ny*force*aw;bf.x+=nx*force*bw;bf.y+=ny*force*bw;
  }
  let maximumSpeed=0,maximumForce=0;
  for(const body of bodies){
   if(fixed(body)){body.vx=0;body.vy=0;continue;}
   const force=forces.get(body.id)!;
   const dx=body.ax-body.x,dy=body.ay-body.y,distance=Math.hypot(dx,dy);
   // Placements resist later gestures, but yield gradually under collisions.
   const strength=body.manual?.24:body.degree?.014:0;
   const resistance=body.manual&&distance>20?1+(distance-20)*.08:1;
   force.x+=dx*strength*resistance;force.y+=dy*strength*resistance;
   const damping=Math.pow(.76,dt);
   body.vx=(body.vx+force.x*dt)*damping;body.vy=(body.vy+force.y*dt)*damping;
   const speed=Math.hypot(body.vx,body.vy),maximum=body.manual?4:9;
   if(speed>maximum){body.vx*=maximum/speed;body.vy*=maximum/speed;}
   body.x+=body.vx*dt;body.y+=body.vy*dt;
   maximumSpeed=Math.max(maximumSpeed,Math.hypot(body.vx,body.vy));
   maximumForce=Math.max(maximumForce,Math.hypot(force.x,force.y));
  }
  return maximumSpeed<.06&&maximumForce<.08;
 }
}

export interface DragPhysicsOptions {
 enabled:()=>boolean;
 reduced:()=>boolean;
 onState:(running:boolean)=>void;
 onSave:()=>void;
}

/** One animation loop stays alive from pointer down through release/settling. */
export function createDragPhysics(graph:Core,options:DragPhysicsOptions){
 const simulation=new DragSimulation();
 let frame=0,last=0,releasedAt=0,stable=0,held:string|null=null,disposed=false;
 const stop=(save=true)=>{
  cancelAnimationFrame(frame);frame=0;last=0;
  if(!disposed){options.onState(false);if(save)options.onSave();}
 };
 const tick=(now:number)=>{
  frame=0;
  if(disposed||graph.destroyed()||document.hidden||!options.enabled()||options.reduced()){stop();return;}
  if(held){const node=graph.getElementById(held);if(node.length)simulation.move(held,node.position());}
  const settled=simulation.step(last?(now-last)/(1000/60):1);last=now;
  graph.batch(()=>{
   for(const body of simulation.bodies.values()){
    const node=graph.getElementById(body.id);
    if(node.length&&body.id!==held&&!node.locked()&&!node.grabbed()){
     const current=node.position();
     if(Math.abs(current.x-body.x)>.0001||Math.abs(current.y-body.y)>.0001)node.position({x:body.x,y:body.y});
    }
   }
  });
  stable=settled?stable+1:0;
  // Never cool while the pointer is held, even if the cursor temporarily rests.
  if(!held&&(stable>=15||now-releasedAt>4500)){stop();return;}
  frame=requestAnimationFrame(tick);
 };
 const wake=()=>{
  if(!disposed&&!graph.destroyed()&&!document.hidden&&options.enabled()&&!options.reduced()){
   options.onState(true);
   if(!frame){last=0;frame=requestAnimationFrame(tick);}
  }
 };
 return {
  begin(id:string){
   // Cancel just the frame, not the current positions or placement memory.
   cancelAnimationFrame(frame);frame=0;held=id;stable=0;
   simulation.begin(graph.nodes().map(node=>({id:node.id(),...node.position(),radius:Math.max(node.outerWidth(),node.outerHeight())/2,pinned:node.locked()})),
    graph.edges().map(edge=>({source:edge.source().id(),target:edge.target().id()})),id);
   wake();
  },
  release(id:string){
   const node=graph.getElementById(id);if(node.length)simulation.release(id,node.position());
   held=null;releasedAt=performance.now();stable=0;options.onSave();wake();
  },
  syncPins(){for(const body of simulation.bodies.values()){const node=graph.getElementById(body.id);if(node.length){body.pinned=node.locked();if(body.pinned)simulation.move(body.id,node.position());}}},
  stop,
  reset(){stop(false);held=null;simulation.reset();},
  dispose(){disposed=true;cancelAnimationFrame(frame);frame=0;simulation.reset();}
 };
}

export type DragPhysics = ReturnType<typeof createDragPhysics>;
