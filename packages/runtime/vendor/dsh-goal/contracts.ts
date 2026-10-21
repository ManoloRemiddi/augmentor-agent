// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Minimal public-event adapter for the selected MIT fold; no DSH runtime dependency.
export const GOAL_CHANGE_VERSION=1;
export type GoalId=string;
export const GoalId=(id:string):GoalId=>id;
export type GoalPhase='active'|'paused'|'blocked'|'complete';
export type GoalBlockReason={code:string;message:string};
export type GoalRef={id:GoalId;revision:number};
export type GoalSnapshot=GoalRef&{objective:string;phase:GoalPhase;maxGoalRounds:number;blockedReason?:GoalBlockReason};
export type GoalOperation='create'|'edit'|'pause'|'resume'|'complete'|'block'|'clear';
export type GoalSnapshotChangeMeta={kind:'goal/change';version:1;operation:Exclude<GoalOperation,'clear'>;goal:GoalSnapshot;roundsStarted:number;createdAt:number;updatedAt:number};
export type GoalClearChangeMeta={kind:'goal/change';version:1;operation:'clear';cleared:GoalRef;clearedAt:number};
export type GoalChangeMeta=GoalSnapshotChangeMeta|GoalClearChangeMeta;
export type GoalMessageSource={kind:'goal';goalId:GoalId;revision:number;round:number};
export type MessageSource=GoalMessageSource|{kind:'user'};
export type SessionEvent={seq:number;type:'goal/change';data:unknown}|{seq:number;type:'user/message';data:{source:MessageSource}};
export type FoldedGoal={goal?:GoalSnapshot;roundsStarted:number;createdAt?:number;updatedAt?:number;lastRef?:GoalRef};
