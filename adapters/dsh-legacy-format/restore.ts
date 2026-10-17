// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Pure public MIT format assembly for an offline experiment, never a live Host.
import type {SessionFormatJsonValue} from '@deepseek-ai/dsh-session-format';
import {createSessionFormatCatalog} from '@deepseek-ai/dsh-session-format';
import {releasedV0SessionFormatCodec,releasedV1SessionFormatCodec,sessionFormatV0ToV1} from '@deepseek-ai/dsh-session-format-v0-to-v1';
import {releasedV2SessionFormatCodec,sessionFormatV1ToV2} from '@deepseek-ai/dsh-session-format-v1-to-v2';
import {releasedV3SessionFormatCodec,sessionFormatV2ToV3} from '@deepseek-ai/dsh-session-format-v2-to-v3';
import {releasedV4SessionFormatCodec,createSessionFormatV3ToV4,assertReleasedV4Header,restoreReleasedV4Artifact} from '@deepseek-ai/dsh-session-format-v3-to-v4';
import {KNOWN_SESSION_EVENT_TYPES} from '@augmentor/dsh-known-event-types';
export function restoreRows(rows:unknown[],children:SessionFormatJsonValue[]){
 if(!Array.isArray(children))throw Error('Explicit historical child facts are required');
 const catalog=createSessionFormatCatalog({currentVersion:4,codecs:[releasedV0SessionFormatCodec,releasedV1SessionFormatCodec,releasedV2SessionFormatCodec,releasedV3SessionFormatCodec,releasedV4SessionFormatCodec],currentEncoder:releasedV4SessionFormatCodec,migrations:[sessionFormatV0ToV1,sessionFormatV1ToV2,sessionFormatV2ToV3,createSessionFormatV3ToV4(structuredClone(children))],restoreCurrent:a=>restoreReleasedV4Artifact(a,KNOWN_SESSION_EVENT_TYPES),restoreTransformedCurrent:a=>restoreReleasedV4Artifact(a,KNOWN_SESSION_EVENT_TYPES),restoreCurrentHeader:h=>{assertReleasedV4Header(h);return h;}});
 const restore=catalog.createRestore(structuredClone(rows[0]),{recovery:'strict',validation:'transformed'});for(const row of rows.slice(1))restore.decodeRow(structuredClone(row));return restore.finish();
}
