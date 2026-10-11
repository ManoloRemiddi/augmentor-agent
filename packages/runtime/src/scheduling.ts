// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {setImmediate} from 'node:timers/promises';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';

/** Awaited public hooks let RPC/Stop run between buffered provider events.
 * Listeners and pre-effect checkpoints still finish before the next event.
 */
export function piScheduling(pi:ExtensionAPI){
 const yieldToHost=async()=>{await setImmediate();};
 pi.on('message_update',yieldToHost);
 pi.on('message_end',yieldToHost);
}
