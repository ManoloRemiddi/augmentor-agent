// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored crash fixture: own process/profile/document only, no SDK/model work.
import {writeFile} from 'node:fs/promises';import {join} from 'node:path';
import {createLinuxNativeOfficeConverter} from '../../dist/runtime/src/office-native-linux.js';
import {previewDocx} from './preview-office.mjs';
const root=process.argv[2],inputPath=join(root,'authored.docx');await writeFile(inputPath,previewDocx('AUTHORED_PARENT_CRASH_'+ 'x'.repeat(100000)));
const converter=await createLinuxNativeOfficeConverter();
setInterval(()=>{},1000);converter.render({inputPath,outputPath:join(root,'converted.pdf')}).catch(()=>{});
