// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import React,{useLayoutEffect,useMemo,useRef,useState} from 'react';
/** One transfer to one opaque frame. No credentials or Host callbacks cross;
 * changed bytes/mode/authority retire the browsing context and its scripts. */
export function InteractiveHtmlFrame({html,frameName,title,className,statusClassName,failed,signal}){
 const [unavailable,setUnavailable]=useState(false),frame=useRef(null),channel=useMemo(()=>crypto.randomUUID(),[html]);
 useLayoutEffect(()=>{
  setUnavailable(false);let sent=false;const timer=setTimeout(()=>{window.removeEventListener('message',receive);if(!signal.aborted)setUnavailable(true);},5000),receive=event=>{
   if(sent||signal.aborted||event.source!==frame.current?.contentWindow||event.origin!=='null'||event.data?.type!=='augmentor-html-ready'||event.data?.channel!==channel)return;
   sent=true;clearTimeout(timer);window.removeEventListener('message',receive);
   frame.current.contentWindow.postMessage({type:'augmentor-html-document',channel,html},'*');
  };
  window.addEventListener('message',receive);const retire=()=>{clearTimeout(timer);window.removeEventListener('message',receive);};signal.addEventListener('abort',retire,{once:true});
  return()=>{retire();signal.removeEventListener('abort',retire);};
 },[html,channel,signal]);
 if(unavailable)return <p className={statusClassName} role="alert">{failed}</p>;
 return <iframe key={channel} ref={frame} name={frameName} className={className} src={'/dsh-html-frame.html#channel='+channel} sandbox="allow-scripts" referrerPolicy="no-referrer" title={title} data-html-preview/>;
}
