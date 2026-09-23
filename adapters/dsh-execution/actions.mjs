// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';

// Exact adapters for the pinned DSH/product tools. Never infer safety from a
// model-supplied description, a shell command prefix, or arbitrary result text.
const reads=new Set(['read','glob','grep','web_search','web_fetch','job_output','job_list',
  'browser_tabs_list','browser_snapshot','browser_screenshot','linux_desktop_snapshot']);
const effects=new Set(['read','change','external','unknown']);
const outcomes=new Set(['completed','failed','failed-before-dispatch','unknown','running','waiting']);
const stable=value=>Array.isArray(value)?value.map(stable):value&&typeof value==='object'?
  Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])])):value;
export function actionKey(name,args) {
  // Display wording and wait budgets do not make a shell operation new.
  const identity=name==='bash'?{command:args?.command,workdir:args?.workdir??null}:args;
  return createHash('sha256').update(JSON.stringify([name,stable(identity)])).digest('hex');
}
export function actionEffect(name,args,definition) {
  try {
    const declared=definition?.augmentorExecution?.effect?.(args);
    if(declared!==undefined)return effects.has(declared)?declared:'unknown';
  } catch { return 'unknown'; }
  return reads.has(name)?'read':'unknown';
}
export function actionOutcome(exec,result,definition,effect) {
  // A final error after dispatch can follow a successful external side effect.
  if(result.isError)return {status:['ABORTED_BEFORE_DISPATCH','UNKNOWN_TOOL','INVALID_ARGS'].includes(result.error?.info?.code)?
    'failed-before-dispatch':effect==='read'?'failed':'unknown'};
  if(result.concludesTurn)return {status:'waiting'};
  try {
    const declared=definition?.augmentorExecution?.outcome?.(exec.arguments,result.value);
    if(declared!==undefined) {
      if(!outcomes.has(declared?.status))return {status:'unknown'};
      return {status:declared.status,...typeof declared.jobId==='string'?{jobId:declared.jobId}:{}};
    }
  } catch { return {status:'unknown'}; }
  const value=result.value;
  if(exec.name==='bash') {
    if(value?.kind==='background'&&typeof value.jobId==='string')return {status:'running',jobId:value.jobId};
    if(value?.kind==='foreground')return {status:value.exitCode===0&&!value.signal&&!value.timedOut&&!value.aborted?'completed':'unknown'};
    return {status:'unknown'};
  }
  if(exec.name==='job_output'&&typeof value?.job?.id==='string') {
    const status=value.job.status;
    return {jobId:value.job.id,status:['running','stopping'].includes(status)?'running':status==='completed'?'completed':'unknown'};
  }
  // "Completed" is execution acknowledgment, never semantic task verification.
  return {status:'completed'};
}

export function recoveryDenial(ledger,key,effect) {
  if(effect==='read')return null;
  if([...ledger.values()].some(x=>['unknown','running','waiting'].includes(x.status)))
    return 'A previous action is uncertain, running, or waiting for input. Inspect its existing outcome before another change; automatic recovery cannot authorize a retry.';
  const previous=ledger.get(key);
  if(previous&&previous.status!=='failed-before-dispatch')
    return 'This action already ran in the current turn. Automatic recovery cannot repeat it. Inspect the result or give an honest partial handoff.';
  return null;
}
