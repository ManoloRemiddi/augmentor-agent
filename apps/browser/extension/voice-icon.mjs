// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Same 97-point contour and state marks as native VoiceButton.paintEvent.
export function attachVoiceIcon(button){
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','-14 -14 28 28');svg.setAttribute('aria-hidden','true');svg.classList.add('voice-drawing')
 const make=(name,attrs,parent=svg)=>{const node=document.createElementNS(ns,name);for(const[k,v]of Object.entries(attrs))node.setAttribute(k,String(v));parent.append(node);return node}
 const defs=make('defs',{}),gradient=make('radialGradient',{id:'voice-glow',cx:'.43',cy:'.43',r:'.5'},defs)
 make('stop',{offset:0,'stop-color':'currentColor','stop-opacity':.22},gradient);make('stop',{offset:1,'stop-color':'currentColor','stop-opacity':0},gradient)
 make('circle',{r:14,fill:'url(#voice-glow)'})
 const contour=make('path',{fill:'currentColor','fill-opacity':.094,stroke:'currentColor','stroke-width':1.3}),marks=make('g',{fill:'currentColor',stroke:'currentColor','stroke-width':1,'stroke-linecap':'round'})
 button.replaceChildren(svg)
 let phase=0,timer=null,levels=[],hover=false
 const draw=()=>{
  const state=button.dataset.state;const radius=8.8+(phase?.5*Math.sin(phase*2):0)
  const points=Array.from({length:97},(_,i)=>{const a=i*Math.PI*2/96,r=radius*(1+.065*Math.sin(3*a+phase*.85)+.035*Math.cos(2*a-phase));return `${i?'L':'M'}${(Math.cos(a)*r).toFixed(3)},${(Math.sin(a)*r).toFixed(3)}`})
  contour.setAttribute('d',points.join(' ')+'Z');contour.setAttribute('fill-opacity',state==='listening'?'.294':'.094');marks.replaceChildren()
  if(state==='listening'){
   Array.from({length:11},(_,i)=>{const h=Math.max(.25,Math.min(1,levels[i]||0)*5.5);make('line',{x1:(i-5)*1.15,x2:(i-5)*1.15,y1:-h,y2:h},marks)})
   if(button.dataset.mode==='locked'){make('rect',{x:6,y:6,width:5,height:4,rx:1},marks);make('path',{d:'M7 6V5a1.5 1.5 0 0 1 3 0v1',fill:'none'},marks)}
  }else if(state==='speaking')make('rect',{x:-2.5,y:-2.5,width:5,height:5,rx:1},marks)
  else if(['connecting','recognizing','thinking'].includes(state))for(const x of [-3.5,0,3.5])make('circle',{cx:x,cy:0,r:.9,stroke:'none'},marks)
  else if(['error','disconnected'].includes(state)){make('rect',{x:-.7,y:-4,width:1.4,height:5,rx:.5},marks);make('circle',{cx:0,cy:3,r:.9},marks)}
  if(button.dataset.mode==='hands-free')make('circle',{r:11,fill:'none','stroke-dasharray':'21 13.55','stroke-width':1.2,transform:'rotate(-20)'},marks)
 }
 const sync=()=>{const active=(hover||['listening','speaking','connecting','recognizing','thinking'].includes(button.dataset.state))&&document.documentElement.dataset.animation!=='false'&&!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if(active&&!timer)timer=setInterval(()=>{phase+=.033;draw()},33)
  else if(!active&&timer){clearInterval(timer);timer=null;phase=0}draw()}
 button.addEventListener('pointerenter',()=>{hover=true;sync()});button.addEventListener('pointerleave',()=>{hover=false;sync()})
 const observer=new MutationObserver(sync);observer.observe(button,{attributes:true,attributeFilter:['data-state','data-mode']})
 window.addEventListener('pagehide',()=>{clearInterval(timer);observer.disconnect()},{once:true});draw()
 return {levels(value){levels=value;draw()}}
}
