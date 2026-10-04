// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real Ed25519 metadata, HTTP transfer and maintained TUF client; temporary keys.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import http from 'node:http'
import {generateKeyPairSync, sign, createHash} from 'node:crypto'
import {Metadata, Root, Targets, Snapshot, Timestamp, Key, Signature, TargetFile, MetaFile} from '@tufjs/models'
import {UpdateRepository, BoundedFetcher, publicReleases, downloadPublicArtifact} from '../services/updates/repository.mjs'

const digest = bytes => createHash('sha256').update(bytes).digest('hex')
const expires = () => new Date(Date.now() + 3600000).toISOString()

async function fixture(t) {
  const cache = await fs.mkdtemp(path.join(os.tmpdir(), 'augmentor-tuf-'))
  t.after(() => fs.rm(cache, {recursive: true, force: true}))
  const keys = {}
  for (const role of ['root', 'targets', 'snapshot', 'timestamp']) {
    const {privateKey, publicKey} = generateKeyPairSync('ed25519')
    const value = {keytype: 'ed25519', scheme: 'ed25519',
      keyval: {public: Buffer.from(publicKey.export({format: 'jwk'}).x, 'base64url').toString('hex')}}
    const id = digest(JSON.stringify(value))
    keys[role] = {privateKey, key: Key.fromJSON(id, value), id}
  }
  const serialize = (metadata, role) => {
    metadata.sign(bytes => new Signature({keyID: keys[role].id, sig: sign(null, bytes, keys[role].privateKey).toString('hex')}))
    return Buffer.from(JSON.stringify(metadata.toJSON()))
  }
  const root = new Root({version: 1, expires: expires(), consistentSnapshot: false})
  for (const role of Object.keys(keys)) root.addKey(keys[role].key, role)
  const rootBytes = serialize(new Metadata(root), 'root')
  const payload = Buffer.from('MZ synthetic inert installer; never executed')
  const artifact = {role: 'installer', targetPath: 'releases/download/v1.1.0-windows-preview.1/Augmentor-1.1.0-windows-x64-preview.exe',
    bytes: payload.length, sha256: digest(payload)}
  const catalog = Buffer.from(JSON.stringify({schema: 'augmentor-update-catalog/1', releases: []}))
  const files = new Map([['/metadata/root.json', rootBytes], ['/targets/catalog/preview.json', catalog], ['/' + artifact.targetPath, payload]])
  function publish(sequence = 1, timestampExpiry = expires()) {
    const targets = new Targets({version: sequence, expires: expires(), targets: {
      'catalog/preview.json': new TargetFile({path: 'catalog/preview.json', length: catalog.length, hashes: {sha256: digest(catalog)}}),
      [artifact.targetPath]: new TargetFile({path: artifact.targetPath, length: payload.length, hashes: {sha256: digest(payload)}}),
    }})
    const targetsBytes = serialize(new Metadata(targets), 'targets')
    const snapshot = serialize(new Metadata(new Snapshot({version: sequence, expires: expires(), meta: {
      'targets.json': new MetaFile({version: sequence, length: targetsBytes.length, hashes: {sha256: digest(targetsBytes)}}),
    }})), 'snapshot')
    const timestamp = serialize(new Metadata(new Timestamp({version: sequence, expires: timestampExpiry,
      snapshotMeta: new MetaFile({version: sequence, length: snapshot.length, hashes: {sha256: digest(snapshot)}})})), 'timestamp')
    files.set('/metadata/targets.json', targetsBytes); files.set('/metadata/snapshot.json', snapshot); files.set('/metadata/timestamp.json', timestamp)
  }
  publish()
  const requests = []
  const server = http.createServer((req, res) => {
    requests.push(req.url)
    if (!files.has(req.url)) {res.writeHead(404); res.end(); return}
    res.writeHead(200); res.end(files.get(req.url))
  })
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  t.after(() => new Promise(resolve => server.close(resolve)))
  const base = `http://127.0.0.1:${server.address().port}/`
  const config = {root: rootBytes, metadataBaseUrl: base + 'metadata/', catalogBaseUrl: base + 'targets/', artifactBaseUrl: base}
  const repository = () => new UpdateRepository({cache, config, fetcher: new BoundedFetcher({allowLocalhost: true})})
  return {cache, artifact, payload, catalog, files, publish, requests, repository, keys, config, serialize}
}

test('signed catalog and exact payload download over HTTP, including cached verification', async t => {
  const f = await fixture(t), repository = f.repository()
  assert.deepEqual(await repository.catalog('preview'), {schema: 'augmentor-update-catalog/1', releases: []})
  const file = await repository.download(f.artifact)
  assert.deepEqual(await fs.readFile(file), f.payload)
  await fs.writeFile(file, 'corruption')
  assert.equal(await repository.download(f.artifact), file)
  assert.deepEqual(await fs.readFile(file), f.payload)
})

test('changed catalog, changed payload and relabeled artifact are refused', async t => {
  const f = await fixture(t)
  f.files.set('/targets/catalog/preview.json', Buffer.alloc(f.catalog.length, 32))
  await assert.rejects(f.repository().catalog('preview'))
  f.files.set('/targets/catalog/preview.json', f.catalog)
  const repository = f.repository(); await repository.catalog('preview')
  await assert.rejects(repository.download({...f.artifact, sha256: 'a'.repeat(64)}), /identity differs/)
  f.files.set('/' + f.artifact.targetPath, Buffer.alloc(f.payload.length, 32))
  await assert.rejects(repository.download(f.artifact))
  assert.equal(f.requests.filter(p => p === '/' + f.artifact.targetPath).length, 1)
})

test('expired and replayed timestamp metadata are refused', async t => {
  const f = await fixture(t)
  f.publish(2); await f.repository().catalog('preview')
  f.publish(1); await assert.rejects(f.repository().catalog('preview'))
  f.publish(3, new Date(Date.now() - 10000).toISOString())
  await assert.rejects(f.repository().catalog('preview'))
})

test('untrusted timestamp signature cannot reach target download', async t => {
  const f = await fixture(t)
  const timestamp = JSON.parse(f.files.get('/metadata/timestamp.json'))
  timestamp.signatures[0].sig = '00'.repeat(64)
  f.files.set('/metadata/timestamp.json', Buffer.from(JSON.stringify(timestamp)))
  await assert.rejects(f.repository().catalog('preview'))
  assert.equal(f.requests.some(p => p.startsWith('/targets/')), false)
})

test('root key rotation requires signatures from both old and new trusted roots', async t=>{
  const f=await fixture(t),{privateKey,publicKey}=generateKeyPairSync('ed25519')
  const value={keytype:'ed25519',scheme:'ed25519',keyval:{public:Buffer.from(publicKey.export({format:'jwk'}).x,'base64url').toString('hex')}}
  const id=digest(JSON.stringify(value)),root=new Root({version:2,expires:expires(),consistentSnapshot:false})
  root.addKey(Key.fromJSON(id,value),'root')
  for(const role of ['targets','snapshot','timestamp'])root.addKey(f.keys[role].key,role)
  const metadata=new Metadata(root)
  metadata.sign(bytes=>new Signature({keyID:id,sig:sign(null,bytes,privateKey).toString('hex')}))
  f.files.set('/metadata/2.root.json',Buffer.from(JSON.stringify(metadata.toJSON())))
  await assert.rejects(f.repository().catalog('preview'))
  metadata.sign(bytes=>new Signature({keyID:f.keys.root.id,sig:sign(null,bytes,f.keys.root.privateKey).toString('hex')}))
  f.files.set('/metadata/2.root.json',Buffer.from(JSON.stringify(metadata.toJSON())))
  await f.repository().catalog('preview')
  const cached=JSON.parse(await fs.readFile(path.join(f.cache,'metadata/root.json'),'utf8'))
  assert.equal(cached.signed.version,2)
  assert.deepEqual(cached.signed.roles.root.keyids,[id])
  await f.repository().catalog('preview') // A restart verifies the retained chain.
  await fs.unlink(path.join(f.cache,'metadata/2.root.json'))
  await assert.rejects(f.repository().catalog('preview'))
})

test('a replaced self-signed cache root cannot substitute for the bundled publisher root',async t=>{
  const f=await fixture(t);await f.repository().catalog('preview')
  const metadata=JSON.parse(await fs.readFile(path.join(f.cache,'metadata/root.json'),'utf8'))
  metadata.signed.roles.root.keyids=[f.keys.targets.id]
  const replacement=Metadata.fromJSON('root',metadata)
  replacement.sign(bytes=>new Signature({keyID:f.keys.targets.id,sig:sign(null,bytes,f.keys.targets.privateKey).toString('hex')}),false)
  await fs.writeFile(path.join(f.cache,'metadata/root.json'),JSON.stringify(replacement.toJSON()))
  await assert.rejects(f.repository().catalog('preview'),/bundled trust history/)
})

test('an installed trusted bridge can advance the embedded root floor past an old cache',async t=>{
  const f=await fixture(t);await f.repository().catalog('preview')
  const root=new Root({version:2,expires:expires(),consistentSnapshot:false})
  for(const role of Object.keys(f.keys))root.addKey(f.keys[role].key,role)
  f.config.root=f.serialize(new Metadata(root),'root')
  await f.repository().catalog('preview')
  assert.equal(JSON.parse(await fs.readFile(path.join(f.cache,'metadata/root.json'),'utf8')).signed.version,2)
})

test('unsafe linked cache targets refuse without modifying their destination',async t=>{
  const f=await fixture(t),outside=path.join(f.cache,'sentinel')
  await fs.writeFile(outside,'preserved',{mode:0o600})
  await fs.symlink(outside,path.join(f.cache,f.artifact.sha256+'.download'))
  await assert.rejects(f.repository().download(f.artifact),/unsafe file/)
  assert.equal(await fs.readFile(outside,'utf8'),'preserved')
})

test('bounded transfers cancel the HTTP body on size refusal and honour cancellation',async()=>{
  let cancelled=false
  const fetcher=new BoundedFetcher({fetchImpl:async()=>new Response(new ReadableStream({
    pull(controller){controller.enqueue(new Uint8Array(1024))},cancel(){cancelled=true}
  }))})
  await assert.rejects(fetcher.downloadBytes('https://example.test/oversized',100))
  assert.equal(cancelled,true)
  const controller=new AbortController();controller.abort()
  await assert.rejects(new BoundedFetcher({signal:controller.signal}).downloadBytes('https://example.test/cancelled',100))
})

test('public lookup includes previews, ignores drafts/wrong architecture and preserves manual trust', async () => {
  const name = 'Augmentor-0.2.13-windows-arm64-preview.exe'
  const row = {tag_name: 'v0.2.13-windows-preview.1', prerelease: true, draft: false,
    assets: [{name, size: 12, digest: 'sha256:' + 'a'.repeat(64),
      browser_download_url: 'https://github.com/ManoloRemiddi/augmentor-agent/releases/download/v0.2.13-windows-preview.1/' + name}]}
  const fetcher = new BoundedFetcher({fetchImpl: async url => {
    assert.equal(url.pathname, '/repos/ManoloRemiddi/augmentor-agent/releases')
    return new Response(JSON.stringify([row, {...row, draft: true}]))
  }})
  const releases = await publicReleases({channel: 'preview', target: 'windows-arm64', fetcher})
  assert.equal(releases.length, 1); assert.equal(releases[0].authenticated, false)
  assert.equal((await publicReleases({channel: 'preview', target: 'windows-x64', fetcher})).length, 0)
  assert.equal((await publicReleases({channel: 'stable', target: 'windows-arm64', fetcher})).length, 0)
})

test('public download verifies exact length/digest and never writes a mismatching artifact', async t => {
  const cache = await fs.mkdtemp(path.join(os.tmpdir(), 'augmentor-manual-'))
  t.after(() => fs.rm(cache, {recursive: true, force: true}))
  const bytes = Buffer.from('manual-download')
  const artifact = {targetPath: 'releases/download/v1.0.0/installer.exe', bytes: bytes.length, sha256: digest(bytes)}
  const fetcher = new BoundedFetcher({fetchImpl: async () => new Response(bytes)})
  assert.deepEqual(await fs.readFile(await downloadPublicArtifact(artifact, cache, fetcher)), bytes)
  await assert.rejects(downloadPublicArtifact({...artifact, sha256: 'a'.repeat(64)}, cache, fetcher), /published digest/)
  await assert.rejects(downloadPublicArtifact({...artifact, bytes: 1}, cache, fetcher))
  assert.deepEqual(await fs.readdir(cache), [artifact.sha256 + '.download'])
})
