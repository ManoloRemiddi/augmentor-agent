// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';

/** Backend availability is separate from the user's live OS permission grant. */
export function desktopCapabilities(platform:NodeJS.Platform=process.platform,env:NodeJS.ProcessEnv=process.env,present:(path:string)=>boolean=existsSync){
 const mac=platform==='darwin';
 const helper=env.AUGMENTOR_MACOS_HELPER??fileURLToPath(new URL('../../../native/augmentor-desktop-control',import.meta.url));
 const available=env.AUGMENTOR_PI_LINUX_TOOLS!=='0'&&(platform==='linux'||(mac&&present(helper)));
 return {available,preview:true,backend:mac?'macos-screencapturekit':platform==='linux'?'kde-wayland-portal':null,monitors:1,text:mac?'Unicode':'ASCII',requiresImageModel:true,requiresUserConsent:true};
}
