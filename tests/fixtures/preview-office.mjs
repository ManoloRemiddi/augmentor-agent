// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {zipSync,strToU8} from 'fflate';
const xml=value=>value.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
/** Independently authored OOXML fixture; no private or supplier document bytes. */
export function previewDocx(label='AUTHORED_OFFICE',font='Augmentor Fixture Missing Font'){
  const parts={
    '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
    '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    'word/document.xml':'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+[1,2].map(page=>'<w:p><w:r><w:rPr><w:rFonts w:ascii="'+xml(font)+'" w:hAnsi="'+xml(font)+'"/><w:sz w:val="28"/></w:rPr><w:t>'+xml(label)+'_PAGE_'+page+'</w:t></w:r></w:p>'+(page===1?'<w:p><w:r><w:br w:type="page"/></w:r></w:p>':'')).join('')+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>',
  };
  return zipSync(Object.fromEntries(Object.entries(parts).map(([name,value])=>[name,strToU8('<?xml version="1.0" encoding="UTF-8"?>'+value)])),{level:6});
}
