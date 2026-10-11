// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Product structural boundary for the separately licensed DSH output ring.
export type JobChannel='stdout'|'stderr'|'assistant'|'notice';
export type JobAppendOptions={channel?:JobChannel;gapBefore?:true};
export type JobOutputRead={chunks:{at:number;text:string;channel?:JobChannel;gapBefore?:true}[];next:number;lossy:boolean};
