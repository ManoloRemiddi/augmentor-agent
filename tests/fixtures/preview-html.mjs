// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Independently authored documents; no private or upstream test material. */
export function previewHtml(label='AUTHORED_HTML',probeOrigin='https://external.invalid'){
 return `<!doctype html><html><head><meta charset="utf-8"><title>Authored HTML fixture</title><link rel="stylesheet" href="theme.css?fixture=1"><link rel="stylesheet" href="${probeOrigin}/never.css"><link rel="dns-prefetch" href="${probeOrigin}"><style>body{margin:0;padding:12px;font-family:sans-serif}#counter{padding:10px}#tick{display:block}</style></head><body><h1 id="marker">${label}</h1><div id="asset-result">LOCAL_ASSET_PENDING</div><button id="counter">Count 0</button><output id="tick">0</output><img src="${probeOrigin}/never.png"><iframe src="${probeOrigin}/never-frame"></iframe><script src="large.js?fixture=1"></script><script src="${probeOrigin}/never.js"></script><script>
 let count=0;document.getElementById('counter').onclick=()=>document.getElementById('counter').textContent='Count '+(++count);
 let tick=0;setInterval(()=>document.getElementById('tick').textContent=String(++tick),30);
 const proof=document.body.dataset;proof.executed='yes';
 try{parent.document.body.dataset.childEscaped='yes';proof.parentBlocked='no';}catch{proof.parentBlocked='yes';}
 try{localStorage.setItem('never','fixture');proof.storageBlocked='no';}catch{proof.storageBlocked='yes';}
 proof.rtcBlocked=String(typeof RTCPeerConnection==='undefined'&&typeof webkitRTCPeerConnection==='undefined');
 const child=document.createElement('iframe');document.body.append(child);try{proof.nestedRtcBlocked=typeof child.contentWindow.RTCPeerConnection==='undefined'?'yes':'no';}catch{proof.nestedRtcBlocked='yes';}finally{child.remove();}
 proof.repeatedPayloads='0';window.addEventListener('message',e=>{if(e.data?.type==='augmentor-html-document')proof.repeatedPayloads=String(Number(proof.repeatedPayloads)+1);});parent.postMessage({type:'augmentor-html-ready',channel:new URLSearchParams(location.hash.slice(1)).get('channel')},'*');
 fetch('${probeOrigin}/never-fetch').catch(()=>{});try{const socket=new WebSocket('${probeOrigin.replace(/^http/,'ws')}/never-socket');socket.onerror=()=>{};}catch{}
 try{proof.workerBlocked='pending';const worker=new Worker('data:text/javascript,postMessage(1)');worker.onmessage=()=>{proof.workerBlocked='no';worker.terminate();};worker.onerror=()=>{proof.workerBlocked='yes';worker.terminate();};}catch{proof.workerBlocked='yes';}
 </script></body></html>`;
}
export function previewHtmlScript(label='AUTHORED_LARGE_SCRIPT'){
 return '/*'+ ' '.repeat(300*1024)+'*/\ndocument.getElementById("asset-result").textContent='+JSON.stringify(label)+';';
}
