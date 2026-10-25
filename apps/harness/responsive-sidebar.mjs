// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export function sidebarPresentation({width,orientation}){
 return width>=960&&!orientation?.startsWith('portrait')?'expanded':'collapsed';
}
/** Only geometry/session boundaries change the default. Keyboard height and
 * ordinary renders cannot undo the user's manual sidebar toggle. */
export function bindResponsiveSidebar(controller,previews,view){
 let last;
 const update=()=>{
  const sid=controller.state.sessionId;if(!sid||controller.state.phase!=='ready')return;
  const mode=sidebarPresentation({width:view.innerWidth,orientation:view.screen?.orientation?.type});
  const key=sid+':'+mode;if(key===last)return;last=key;
  previews.sidebar.actions.setExpanded(sid,mode==='expanded');
 };
 const unsubscribe=controller.subscribe(update);
 view.addEventListener('resize',update);view.screen?.orientation?.addEventListener('change',update);
 update();return()=>{unsubscribe();view.removeEventListener('resize',update);view.screen?.orientation?.removeEventListener('change',update);};
}
