// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {promptCall} from '../../../dist/prompt-library/src/client.js';
export async function homeConnection(request={},call=promptCall){
 if(!['state','pair','disconnect'].includes(request.action))return {ok:false,error:'Unsupported Home connection operation'};
 try{const {action,...params}=request;return {ok:true,...await call('home.connection.'+action,params)};}catch(error){return {ok:false,error:error.message};}
}
