// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root=new URL('../vendor/photon-node/',import.meta.url);
const require=createRequire(import.meta.url);

test('reviewed image module matches its source build and license inventory',()=>{
  const record=JSON.parse(readFileSync(new URL('BUILD.json',root)));
  for(const [path,hash] of Object.entries(record.files)){
    assert.equal(createHash('sha256').update(readFileSync(new URL(path,root))).digest('hex'),hash,path);
  }
  const lock=readFileSync(new URL('../release/photon/Cargo.lock',import.meta.url));
  assert.equal(createHash('sha256').update(lock).digest('hex'),record.cargoLockSha256);
});

test('rebuilt Photon decodes PNG and resizes without changing fixture pixels',()=>{
  const photon=require('../vendor/photon-node/photon_rs.js');
  const pixels=new Uint8Array(Array(4).fill([17,34,51,255]).flat());
  const image=new photon.PhotonImage(pixels,2,2);
  const decoded=photon.PhotonImage.new_from_byteslice(image.get_bytes());
  const resized=photon.resize(decoded,1,1,photon.SamplingFilter.Nearest);
  try{
    assert.equal(decoded.get_width(),2);assert.equal(decoded.get_height(),2);
    assert.deepEqual([...decoded.get_raw_pixels()],[...pixels]);
    assert.equal(resized.get_width(),1);assert.equal(resized.get_height(),1);
    assert.deepEqual([...resized.get_raw_pixels()],[17,34,51,255]);
  }finally{resized.free();decoded.free();image.free();}
});
