// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Reuse the product picker/editor; the existing service owns all prompt records.
import {attachPromptLibrary} from './shared-prompts/prompt-library.mjs';

export function attachHarnessPrompts({input,button,rpc,ready,context,changed}){
  return attachPromptLibrary({input,settingsButton:button,context,changed,
    editorOptions:{improvementLabel:'Improvement instructions',improvementDescription:'Shared instructions for Improve prompt. Pi makes one tool-free request with the selected model; only the editable draft is replaced. These instructions are separate from saved /prompts.'},
    send:async(type,{request})=>{
      if(type!=='prompts'||!['list','save','delete','improvement.save'].includes(request?.action))return {ok:false,error:'Unsupported prompt operation.'};
      if(!ready())return {ok:false,error:'Wait for the private Harness connection to be ready.'};
      const {action,...params}=request;
      try{return {ok:true,library:await rpc(action==='improvement.save'?'prompts.improvementSave':'prompts.'+action,params)};}
      catch(error){return {ok:false,error:error.message};}
    },
  });
}
