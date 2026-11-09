import type { Core } from 'cytoscape';

export const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** A short selection cue, independent of relationship direction or price data. */
export function selectionPulse(graph: Core, ids: string[]) {
 if (reducedMotion() || document.hidden || graph.destroyed()) return () => {};
 const host = graph.container();
 if (!host) return () => {};
 const canvas = document.createElement('canvas');
 canvas.className = 'graph-selection-pulse';
 canvas.setAttribute('aria-hidden', 'true');
 Object.assign(canvas.style, {position:'absolute', inset:'0', pointerEvents:'none', zIndex:'2'});
 host.appendChild(canvas);
 const context = canvas.getContext('2d');
 if (!context) { canvas.remove(); return () => {}; }
 let frame = 0;
 const started = performance.now();
 const cleanup = () => { cancelAnimationFrame(frame); canvas.remove(); };
 const draw = (now:number) => {
  if (graph.destroyed() || document.hidden || reducedMotion()) { cleanup(); return; }
  const progress = (now - started) / 850;
  if (progress >= 1) { cleanup(); return; }
  const ratio = window.devicePixelRatio || 1;
  canvas.width = host.clientWidth * ratio; canvas.height = host.clientHeight * ratio;
  canvas.style.width = host.clientWidth + 'px'; canvas.style.height = host.clientHeight + 'px';
  context.scale(ratio, ratio);
  for (const id of ids) {
   const node = graph.getElementById(id); if (!node.length || !node.isNode()) continue;
   const point = node.renderedPosition();
   const radius = Math.max(8, node.renderedWidth()/2) + 5 + progress*26;
   context.beginPath(); context.arc(point.x,point.y,radius,0,Math.PI*2);
   context.strokeStyle = `rgba(94,234,212,${.75*(1-progress)})`;
   context.lineWidth = 2; context.shadowColor = '#5eead4'; context.shadowBlur = 10;
   context.stroke();
  }
  frame = requestAnimationFrame(draw);
 };
 frame = requestAnimationFrame(draw);
 return cleanup;
}
