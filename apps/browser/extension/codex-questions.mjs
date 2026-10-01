// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

/** A cancellable form; no answer is preselected or sent until the user submits. */
export function codexQuestions(doc,questions,signal){
  if(signal?.aborted)return Promise.resolve(null)
  return new Promise(resolve=>{
    const make=(tag,text)=>{const node=doc.createElement(tag);if(text)node.textContent=text;return node}
    const dialog=make('dialog');dialog.className='shared-prompt-editor memory-dialog codex-questions'
    dialog.append(make('h3','Augmentor · questions'))
    const fields=questions.map(question=>{
      const field=make('fieldset');field.append(make('legend',question.header),make('p',question.question))
      const select=make('select');select.setAttribute('aria-label',question.header+' choices')
      const none=make('option','Choose an option or write an answer');none.value='';select.append(none)
      for(const option of question.options??[]){const item=make('option',option.label+(option.description?' — '+option.description:''));item.value=option.label;select.append(item)}
      if(question.options?.length)field.append(select)
      const custom=make('textarea');custom.maxLength=16000;custom.setAttribute('aria-label',question.header+' answer');custom.placeholder='Write an answer…';field.append(custom);dialog.append(field)
      return {question,select,custom}
    })
    const actions=make('div'),cancel=make('button','Cancel'),submit=make('button','Send answers');cancel.type=submit.type='button';actions.append(cancel,submit);dialog.append(actions)
    let finished=false
    const finish=answers=>{if(finished)return;finished=true;signal?.removeEventListener('abort',abort);for(const field of fields)field.custom.value='';dialog.close();dialog.remove();resolve(answers)}
    const abort=()=>finish(null)
    const validate=()=>{submit.disabled=fields.some(({select,custom})=>(!select.value&&!custom.value.trim())||custom.value.length>16000)}
    for(const {select,custom} of fields){select.onchange=validate;custom.oninput=validate}
    cancel.onclick=abort;dialog.addEventListener('cancel',event=>{event.preventDefault();abort()})
    submit.onclick=()=>{validate();if(!submit.disabled)finish(fields.map(({question,select,custom})=>({id:question.id,selected:select.value?[select.value]:[],...(custom.value.trim()?{custom:custom.value}:{})})))}
    signal?.addEventListener('abort',abort,{once:true});doc.body.append(dialog);validate();dialog.showModal()
  })
}
