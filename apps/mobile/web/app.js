// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import RFB from '@novnc/novnc/core/rfb.js';
import {bindKeyboard} from './keyboard.js';
const $=id=>document.getElementById(id);
let rfb=null,clipboard='',resizeTimer,serial=Promise.resolve(),connected=false;
const status=message=>$('status').textContent=message;
async function api(action,body={}){
  const response=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
  const value=await response.json();if(!response.ok){const error=Error(value.error??'Connection unavailable');error.status=response.status;throw error;}return value;
}
async function fit(){
  if(!connected)return;
  const rect=$('screen').getBoundingClientRect();const width=Math.max(340,Math.min(1600,Math.floor(rect.width))),height=Math.max(300,Math.min(1400,Math.floor(rect.height)));
  await api('resize',{width,height});
}
async function connect(){
  $('reconnect').hidden=true;status('Connecting…');
  const ticket=await api('connect');if(ticket.protocol!=='augmentor-desktop/1')throw Error('Incompatible desktop connection.');
  $('pair').hidden=true;$('screen').hidden=false;$('remote').hidden=false;
  rfb=new RFB($('screen'),`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/desktop`,{credentials:{password:ticket.password}});
  rfb.scaleViewport=false;rfb.resizeSession=false;rfb.background='#101819';rfb.qualityLevel=8;rfb.compressionLevel=2;
  rfb.addEventListener('connect',()=>{connected=true;status('');fit().catch(error=>status(error.message));});
  rfb.addEventListener('disconnect',()=>{connected=false;$('keyboard-input').value='';$('keyboard-tools').hidden=true;$('reconnect').hidden=false;status('Disconnected. Your agent continues on the computer.');});
  rfb.addEventListener('securityfailure',()=>status('Desktop connection refused. Restart the remote service.'));
  rfb.addEventListener('clipboard',event=>{clipboard=event.detail.text;$('clipboard').disabled=!clipboard;});
}
function connectionError(error){status(error.message);$('reconnect').hidden=error.status===401;if(error.status===401){$('pair').hidden=false;$('remote').hidden=true;$('screen').hidden=true;}}
$('reconnect').onclick=()=>connect().catch(connectionError);
$('pair').onsubmit=async event=>{event.preventDefault();try{await api('pair',{key:$('key').value});$('key').value='';await connect();}catch(error){connectionError(error);}};
$('show').onclick=()=>api('show').catch(error=>status(error.message));
$('disconnect').onclick=async()=>{try{await api('logout');rfb?.disconnect();connected=false;$('keyboard-tools').hidden=true;$('keyboard-input').value='';$('pair').hidden=false;$('remote').hidden=true;$('screen').hidden=true;status('Disconnected');}catch(error){status(error.message);}};
$('clipboard').disabled=true;
$('clipboard').onclick=async()=>{try{await navigator.clipboard.writeText(clipboard);status('Copied');setTimeout(()=>status(''),1500);}catch{status('Allow clipboard access to copy from Desktop.');}};
$('keyboard').onclick=()=>{$('keyboard-tools').hidden=false;$('keyboard-input').focus();};
$('select-all').onclick=()=>{rfb?.sendKey(0xffe3,'ControlLeft',true);rfb?.sendKey(97,'KeyA');rfb?.sendKey(0xffe3,'ControlLeft',false);$('keyboard-input').focus();};
$('backspace').onclick=()=>{rfb?.sendKey(0xff08);$('keyboard-input').focus();};
$('enter').onclick=()=>rfb?.sendKey(0xff0d);
$('hide-keyboard').onclick=()=>{$('keyboard-tools').hidden=true;$('keyboard-input').blur();rfb?.focus();};
bindKeyboard($('keyboard-input'),key=>rfb?.sendKey(key),()=>connected);
new ResizeObserver(()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{serial=serial.catch(()=>{}).then(fit).catch(error=>status(error.message));},250);}).observe($('screen'));
window.addEventListener('pagehide',()=>rfb?.disconnect());
// Keep transport controls above the on-screen keyboard on engines that resize
// only the visual viewport. Native content then receives the smaller dimensions.
function visibleHeight(){document.body.style.height=Math.floor(window.visualViewport?.height??window.innerHeight)+'px';}
window.visualViewport?.addEventListener('resize',visibleHeight);window.addEventListener('resize',visibleHeight);visibleHeight();
connect().catch(connectionError);
