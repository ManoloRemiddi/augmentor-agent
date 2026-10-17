// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored current-format history with retained pre-renumbering identity text.
// No owner logs or supplier implementation. Public DSH migration contracts:
// d7432673 session-format-v1-to-v2 migration.ts; v2-to-v3 references.ts.
import {authoredToolRecoveryProject} from './dsh-tool-recovery-project.mjs';
export function authoredRecoveryIdentityProject(cwd,{ordinal=123456,cause='interrupted',started=true}={}){
 const f=authoredToolRecoveryProject(cwd,{cause,started});f.result.event.data.message.id=`${cause}-tool-result-${f.id}-${ordinal}`;return {...f,ordinal};
}
