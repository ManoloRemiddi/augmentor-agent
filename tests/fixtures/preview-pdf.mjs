// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Independently authored two-page PDF: ASCII text and a red vector rectangle.
 * No private document, upstream test data or external resource is embedded. */
export function previewPdf(label='AUTHORED_PDF'){
 const streams=[1,2].map(page=>'0.8 0.1 0.1 rg 20 300 200 30 re f\n0 0 0 rg BT /F1 16 Tf 20 260 Td ('+label+'_PAGE_'+page+') Tj ET\n');
 const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>',
  '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] /Resources << /Font << /F1 7 0 R >> >> /Contents 4 0 R >>',
  '<< /Length '+Buffer.byteLength(streams[0])+' >>\nstream\n'+streams[0]+'endstream',
  '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>',
  '<< /Length '+Buffer.byteLength(streams[1])+' >>\nstream\n'+streams[1]+'endstream','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'];
 let body='%PDF-1.7\n';const offsets=[0];for(const [index,object] of objects.entries()){offsets.push(Buffer.byteLength(body));body+=(index+1)+' 0 obj\n'+object+'\nendobj\n';}
 const start=Buffer.byteLength(body);body+='xref\n0 '+(objects.length+1)+'\n0000000000 65535 f \n'+offsets.slice(1).map(offset=>String(offset).padStart(10,'0')+' 00000 n \n').join('')+'trailer\n<< /Size '+(objects.length+1)+' /Root 1 0 R >>\nstartxref\n'+start+'\n%%EOF\n';return Buffer.from(body);
}

/** Authored solid-red JPEG2000 data generated with Pillow/OpenJPEG; no source image. */
const jpx=Buffer.from('AAAADGpQICANCocKAAAAFGZ0eXBqcDIgAAAAAGpwMiAAAAAtanAyaAAAABZpaGRyAAAABAAAAAQAAwcHAAAAAAAPY29scgEAAAAAABAAAAChanAyY/9P/1EALwAAAAAABAAAAAQAAAAAAAAAAAAAAAQAAAAEAAAAAAAAAAAAAwcBAQcBAQcBAf9SAAwAAAABAAIEBAAB/1wACkBASEhQSEhQ/2QAJQABQ3JlYXRlZCBieSBPcGVuSlBFRyB2ZXJzaW9uIDIuNS4z/5AACgAAAAAAIwAB/5PPtAgCt8+0CAgfz7QICB+AgICAgID/2Q==','base64');
export function previewJpxPdf(){
 const content=Buffer.from('q 220 0 0 220 20 40 cm /Im0 Do Q\n');
 const objects=[Buffer.from('<< /Type /Catalog /Pages 2 0 R >>'),Buffer.from('<< /Type /Pages /Kids [3 0 R] /Count 1 >>'),Buffer.from('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] /Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>'),Buffer.concat([Buffer.from('<< /Length '+content.length+' >>\nstream\n'),content,Buffer.from('endstream')]),Buffer.concat([Buffer.from('<< /Type /XObject /Subtype /Image /Width 4 /Height 4 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /JPXDecode /Length '+jpx.length+' >>\nstream\n'),jpx,Buffer.from('\nendstream')])];
 const pieces=[Buffer.from('%PDF-1.7\n')],offsets=[];let length=pieces[0].length;
 for(const [index,object] of objects.entries()){offsets.push(length);const next=Buffer.concat([Buffer.from((index+1)+' 0 obj\n'),object,Buffer.from('\nendobj\n')]);pieces.push(next);length+=next.length;}
 pieces.push(Buffer.from('xref\n0 6\n0000000000 65535 f \n'+offsets.map(offset=>String(offset).padStart(10,'0')+' 00000 n \n').join('')+'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+length+'\n%%EOF\n'));return Buffer.concat(pieces);
}
