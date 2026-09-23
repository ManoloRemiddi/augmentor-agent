// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

class VoiceCapture extends AudioWorkletProcessor {
  constructor(){super();this.active=false;this.samples=[];this.phase=0;
    this.port.onmessage=({data})=>{if(data==='start'){this.samples=[];this.phase=0;this.active=true;}else if(data==='stop'){this.active=false;this.flush();this.port.postMessage({type:'ended'});}};
  }
  flush(){if(this.samples.length){const pcm=new Int16Array(this.samples);this.samples=[];this.port.postMessage(pcm.buffer,[pcm.buffer]);}}
  process(inputs){
    const input=inputs[0]?.[0];if(!this.active||!input)return true;
    // Context requests 16 kHz; reject rather than silently resample incorrectly.
    if(sampleRate!==16000){this.port.postMessage({type:'error',message:'16 kHz capture is unavailable in this browser.'});this.active=false;return true;}
    for(const sample of input){this.samples.push(Math.round(Math.max(-1,Math.min(1,sample))*32767));if(this.samples.length===320)this.flush();}
    return true;
  }
}
registerProcessor('resonant-capture',VoiceCapture);
