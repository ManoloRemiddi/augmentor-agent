// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Fixed opaque-frame bootstrap. Accept exactly one document from its embedding
// app origin/window; no message requests files, actions, credentials or models.
(()=>{
 if(window.parent===window)return;
 // WebRTC ICE is outside connect-src enforcement; no peer-connection capability
 // is offered by this local document viewer. Nested frames/workers are also denied.
 for(const name of ['RTCPeerConnection','webkitRTCPeerConnection'])Object.defineProperty(window,name,{value:undefined,writable:false,configurable:false});
 const channel=new URLSearchParams(location.hash.slice(1)).get('channel'),origin=new URL(location.href).origin;
 if(!channel||! /^[a-f0-9-]{36}$/.test(channel))return;
 const receive=event=>{
  if(event.source!==window.parent||event.origin!==origin||event.data?.type!=='augmentor-html-document'||event.data?.channel!==channel||typeof event.data.html!=='string')return;
  window.removeEventListener('message',receive);const html=event.data.html;document.open();document.write(html);document.close();
 };
 window.addEventListener('message',receive);
 window.parent.postMessage({type:'augmentor-html-ready',channel},origin);
})();
