// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Bounded public release discovery and maintained TUF verification. No installer
// execution, shell command, token, model connection or user-configured URL.
import fs from 'node:fs/promises'
import syncFS from 'node:fs'
import path from 'node:path'
import {createHash,randomUUID} from 'node:crypto'
import {fileURLToPath} from 'node:url'
import {Updater, BaseFetcher} from 'tuf-js'
import {Metadata} from '@tufjs/models'
// The pinned client's root-rotation workflow distinguishes a missing next root
// through this error type. Preserve it in our bounded/cancellable fetch adapter.
import {DownloadHTTPError} from 'tuf-js/dist/error.js'

export const REPOSITORY = 'ManoloRemiddi/augmentor-agent'
export const ARTIFACT_BASE = `https://github.com/${REPOSITORY}/`
const MAX_METADATA = 2 * 1024 * 1024
const MAX_ARTIFACT = 2 * 1024 ** 3
const RELEASE_PATTERN = /^v(\d+\.\d+\.\d+)(?:-(complete|macos|windows)-preview\.(\d+))?$/

export class BoundedFetcher extends BaseFetcher {
  constructor({signal, fetchImpl = fetch, timeout = 30000, allowLocalhost = false, progress = () => {}} = {}) {
    super(); Object.assign(this, {signal, fetchImpl, timeout, allowLocalhost, progress})
  }
  async downloadFile(address,maxLength,handler){
    this.streams??=new Set()
    try{return await super.downloadFile(address,maxLength,handler)}
    finally{for(const stream of this.streams){if(!stream.locked)await stream.cancel().catch(()=>{})}this.streams.clear()}
  }
  async fetch(address) {
    const url = new URL(address)
    if (url.username || url.password || url.hash || (url.protocol !== 'https:' &&
        !(this.allowLocalhost && url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)))) {
      throw Error('Update delivery requires HTTPS.')
    }
    const response = await this.fetchImpl(url, {signal: AbortSignal.any([
      AbortSignal.timeout(this.timeout), ...(this.signal ? [this.signal] : [])]),
      headers: {'User-Agent': 'Augmentor-Updates/1', 'Accept': 'application/octet-stream'}})
    if (!response.ok || !response.body) throw new DownloadHTTPError(`Update server returned HTTP ${response.status}.`, response.status)
    const reader = response.body.getReader()
    let bytes = 0
    const stream = new ReadableStream({
      pull: async controller => {
        try {
          const result = await reader.read()
          if (result.done) {controller.close(); return}
          bytes += result.value.byteLength; this.progress(bytes)
          controller.enqueue(result.value)
        } catch (error) {controller.error(error)}
      },
      cancel: reason => reader.cancel(reason),
    })
    this.streams??=new Set();this.streams.add(stream)
    return stream
  }
}

export function validateArtifact(item) {
  if (!item || !Number.isSafeInteger(item.bytes) || item.bytes <= 0 || item.bytes > MAX_ARTIFACT ||
      !/^[a-f0-9]{64}$/.test(item.sha256) || typeof item.targetPath !== 'string' ||
      !/^releases\/download\/[A-Za-z0-9._-]{1,128}\/[A-Za-z0-9._-]{1,200}$/.test(item.targetPath) ||
      item.targetPath.split('/').some(p => ['.', '..'].includes(p))) throw Error('Invalid release artifact.')
  return item
}

async function privateDirectory(directory) {
  await fs.mkdir(directory, {recursive: true, mode: 0o700})
  const stat = await fs.lstat(directory)
  if (!stat.isDirectory() || stat.isSymbolicLink() || (process.platform !== 'win32' &&
      (stat.uid !== process.getuid() || (stat.mode & 0o077)))) throw Error('The update cache must be private.')
}

async function privateFile(file,{missing=false,maximum=MAX_METADATA}={}){
  let stat
  try{stat=await fs.lstat(file)}catch(error){if(missing&&error.code==='ENOENT')return;throw error}
  if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1||stat.size>maximum||
    (process.platform!=='win32'&&(stat.uid!==process.getuid()||(stat.mode&0o077))))throw Error('The update cache contains an unsafe file.')
}

class DurableUpdater extends Updater {
  persistMetadata(name,bytes){
    // TUF performs trust checks. This override only makes its accepted local
    // metadata private and atomic; it cannot accept an unverified signature.
    const output=path.join(this.dir,encodeURIComponent(name)+'.json'),stage=output+'.'+randomUUID()+'.tmp'
    let fd
    try{
      if(name==='root'){
        const record=JSON.parse(bytes),archive=path.join(this.dir,record.signed.version+'.root.json')
        if(syncFS.existsSync(archive)){
          if(!syncFS.readFileSync(archive).equals(bytes))throw Error('A cached root version has conflicting signed bytes.')
        }else{
          const history=syncFS.openSync(archive,'wx',0o600)
          try{syncFS.writeFileSync(history,bytes);syncFS.fsyncSync(history)}finally{syncFS.closeSync(history)}
        }
      }
      fd=syncFS.openSync(stage,'wx',0o600);syncFS.writeFileSync(fd,bytes);syncFS.fsyncSync(fd);syncFS.closeSync(fd);fd=undefined
      syncFS.renameSync(stage,output)
      if(process.platform!=='win32'){const directory=syncFS.openSync(this.dir,'r');try{syncFS.fsyncSync(directory)}finally{syncFS.closeSync(directory)}}
    }finally{if(fd!==undefined)syncFS.closeSync(fd);syncFS.rmSync(stage,{force:true})}
  }
}

async function verifyRootHistory(initialBytes,metadata){
  let trusted=Metadata.fromJSON('root',JSON.parse(initialBytes))
  trusted.verifyDelegate('root',trusted)
  const current=Metadata.fromJSON('root',JSON.parse(await fs.readFile(path.join(metadata,'root.json'),'utf8')))
  if(current.signed.version<trusted.signed.version){
    // A newly installed trusted bridge can advance the bundled trust floor.
    // A network response cannot replace that embedded initial authority.
    DurableUpdater.prototype.persistMetadata.call({dir:metadata},'root',Buffer.from(initialBytes))
    return
  }
  if(current.signed.version-trusted.signed.version>48)throw Error('The cached trust root needs a supported bridge release.')
  for(let sequence=trusted.signed.version+1;sequence<=current.signed.version;sequence++){
    const next=Metadata.fromJSON('root',JSON.parse(await fs.readFile(path.join(metadata,sequence+'.root.json'),'utf8')))
    if(next.signed.version!==sequence)throw Error('The cached root chain is out of order.')
    trusted.verifyDelegate('root',next);next.verifyDelegate('root',next);trusted=next
  }
  if(JSON.stringify(trusted.signed.toJSON())!==JSON.stringify(current.signed.toJSON()))throw Error('The cached root differs from its bundled trust history.')
}

export class UpdateRepository {
  constructor({cache, config, fetcher = new BoundedFetcher()}) {
    Object.assign(this, {cache, config, fetcher}); this.updater = null
  }
  async initialize() {
    if (this.updater) return
    await privateDirectory(this.cache)
    const metadata = path.join(this.cache, 'metadata')
    await privateDirectory(metadata)
    const root = path.join(metadata, 'root.json')
    try {
      await fs.writeFile(root, this.config.root, {flag: 'wx', mode: 0o600})
    } catch (error) {if (error.code !== 'EEXIST') throw error}
    const entries=await fs.readdir(metadata)
    if(entries.length>64)throw Error('The update metadata cache exceeds its supported size.')
    for(const entry of entries){
      if(!/^[A-Za-z0-9%._-]{1,256}\.json$/.test(entry))throw Error('Unsupported cached update metadata.')
      await privateFile(path.join(metadata,entry))
    }
    await verifyRootHistory(this.config.root,metadata)
    const updater = new DurableUpdater({metadataDir: metadata, metadataBaseUrl: this.config.metadataBaseUrl,
      targetBaseUrl: this.config.catalogBaseUrl, fetcher: this.fetcher,
      config: {fetchRetries: 0, fetchTimeout: 30000, rootMaxLength: MAX_METADATA,
        targetsMaxLength: MAX_METADATA, snapshotMaxLength: MAX_METADATA,
        timestampMaxLength: 65536, maxRootRotations: 32, maxDelegations: 8, prefixTargetsWithHash: false}})
    await updater.refresh()
    this.updater=updater // A failed refresh never leaves a usable client behind.
  }
  async target(target,output,base){
    await privateFile(output,{missing:true,maximum:MAX_ARTIFACT})
    const stage=output+'.'+randomUUID()+'.tmp'
    try{
      await this.updater.downloadTarget(target,stage,base)
      const handle=await fs.open(stage,syncFS.constants.O_RDWR|(syncFS.constants.O_NOFOLLOW||0))
      try{await handle.chmod(0o600);await handle.sync()}finally{await handle.close()}
      await fs.rename(stage,output)
    }finally{await fs.rm(stage,{force:true})}
  }
  async catalog(channel) {
    if (!['preview', 'stable'].includes(channel)) throw Error('Unsupported update channel.')
    await this.initialize()
    const target = await this.updater.getTargetInfo(`catalog/${channel}.json`)
    if (!target || target.length > MAX_METADATA) throw Error('A bounded signed catalog is unavailable.')
    const output = path.join(this.cache, 'catalog-' + channel + '.json')
    await this.target(target, output)
    return JSON.parse(await fs.readFile(output, 'utf8'))
  }
  async download(item) {
    validateArtifact(item); await this.initialize()
    const target = await this.updater.getTargetInfo(item.targetPath)
    if (!target || target.length !== item.bytes || target.hashes.sha256 !== item.sha256) {
      throw Error('The signed artifact identity differs from the selected release.')
    }
    const output = path.join(this.cache, item.sha256 + '.download')
    await privateFile(output,{missing:true,maximum:MAX_ARTIFACT})
    if (await this.updater.findCachedTarget(target, output)) return output
    await this.target(target, output, this.config.artifactBaseUrl)
    return output
  }
}

export async function publicReleases({channel, target, fetcher = new BoundedFetcher()} = {}) {
  if (!['preview', 'stable'].includes(channel)) throw Error('Unsupported update channel.')
  const raw = await fetcher.downloadBytes(`https://api.github.com/repos/${REPOSITORY}/releases?per_page=100`, MAX_METADATA)
  const records = JSON.parse(raw)
  if (!Array.isArray(records)) throw Error('The release server returned an invalid list.')
  const platform = {'linux-x64': 'complete', 'macos-arm64': 'macos', 'windows-x64': 'windows', 'windows-arm64': 'windows'}[target]
  if (!platform) return []
  const result = []
  for (const row of records) {
    if (row.draft || Boolean(row.prerelease) !== (channel === 'preview') || !Array.isArray(row.assets)) continue
    const parsed = RELEASE_PATTERN.exec(row.tag_name)
    if (!parsed || (channel === 'preview' && parsed[2] !== platform)) continue
    const productVersion = parsed[1], build = Number(parsed[3] || 1)
    const artifacts = []
    for (const asset of row.assets) {
      if (typeof asset.name !== 'string' || !/^[A-Za-z0-9._-]{1,200}$/.test(asset.name)) continue
      let role = null
      if (target === 'linux-x64') {
        if (asset.name === `augmentor-${productVersion}-complete-preview.${build}.tar.gz`) role = 'bundle'
        if (asset.name === `augmentor-runtime_${productVersion}_amd64.deb`) role = 'runtime'
        if (asset.name === `augmentor-desktop_${productVersion}_amd64.deb`) role = 'desktop'
        if (asset.name === `augmentor-browser-${productVersion}.zip`) role = 'browser'
      }
      if (target === 'macos-arm64' && asset.name === `augmentor-desktop-${productVersion}-macos-arm64-preview.dmg`) role = 'bundle'
      if (target.startsWith('windows-') && asset.name === `Augmentor-${productVersion}-${target}-${channel}.exe`) role = 'installer'
      if (!role || typeof asset.digest !== 'string' || !/^sha256:[a-f0-9]{64}$/.test(asset.digest)) continue
      const artifact = {role, targetPath: `releases/download/${row.tag_name}/${asset.name}`,
        bytes: asset.size, sha256: asset.digest.slice(7)}
      try {validateArtifact(artifact)} catch {continue}
      if (asset.browser_download_url !== ARTIFACT_BASE + artifact.targetPath) continue
      artifacts.push(artifact)
    }
    if (!artifacts.some(a => ['bundle', 'installer'].includes(a.role))) continue
    result.push({version: productVersion, build, channel, target,
      releaseUrl: `https://github.com/${REPOSITORY}/releases/tag/${row.tag_name}`,
      artifacts, authenticated: false})
  }
  return result
}

export async function downloadPublicArtifact(item, cache, fetcher = new BoundedFetcher()) {
  validateArtifact(item); await privateDirectory(cache)
  const output = path.join(cache, item.sha256 + '.download')
  await privateFile(output,{missing:true,maximum:MAX_ARTIFACT})
  // Published GitHub digests detect corruption; this path has no publisher
  // signature authority and must never authorize automatic installation.
  await fetcher.downloadFile(ARTIFACT_BASE + item.targetPath, item.bytes, async temporary => {
    const handle = await fs.open(temporary, 'r')
    const hash = createHash('sha256'); let count = 0
    try {for await (const chunk of handle.createReadStream()) {count += chunk.length; hash.update(chunk)}}
    finally {await handle.close()}
    if (count !== item.bytes || hash.digest('hex') !== item.sha256) throw Error('The download does not match the published digest.')
    const stage = output + '.' + randomUUID() + '.tmp'
    await fs.copyFile(temporary, stage, 1)
    try {
      await fs.chmod(stage, 0o600)
      const fd = await fs.open(stage, 'r+'); try {await fd.sync()} finally {await fd.close()}
      await fs.rename(stage, output)
    } finally {await fs.unlink(stage).catch(error => {if (error.code !== 'ENOENT') throw error})}
  })
  return output
}

async function main() {
  let input = ''
  for await (const chunk of process.stdin) {input += chunk; if (input.length > 65536) throw Error('Update request too large.')}
  const request = JSON.parse(input)
  if (!['discover', 'download'].includes(request.operation)) throw Error('Unsupported update operation.')
  const root = fileURLToPath(new URL('../../', import.meta.url))
  const configFile = path.join(root, 'release/updates.json')
  let configuration = null
  try {configuration = JSON.parse(await fs.readFile(configFile, 'utf8'))} catch (error) {if (error.code !== 'ENOENT') throw error}
  const fetcher = new BoundedFetcher({timeout: request.operation === 'download' ? 120000 : 20000,
    progress: bytes => process.stderr.write(JSON.stringify({bytes}) + '\n')})
  if (!configuration?.enabled) {
    if (request.operation === 'download') {
      const file = await downloadPublicArtifact(request.artifact, request.cache, fetcher)
      return {file, authenticated: false}
    }
    return {releases: await publicReleases({...request, fetcher}), authenticated: false}
  }
  if (configuration.schema !== 'augmentor-update-repository/1' ||
      configuration.artifactBaseUrl !== ARTIFACT_BASE ||
      !/^https:\/\/augmentoragent\.com\/updates\/[A-Za-z0-9/_-]+\/$/.test(configuration.metadataBaseUrl) ||
      !/^https:\/\/augmentoragent\.com\/updates\/[A-Za-z0-9/_-]+\/$/.test(configuration.catalogBaseUrl) ||
      configuration.rootFile !== 'updates/root.json') throw Error('Unsupported installed update repository.')
  const rootBytes = await fs.readFile(path.join(root, 'release', configuration.rootFile))
  const repository = new UpdateRepository({cache: request.cache, config: {...configuration, root: rootBytes}, fetcher})
  if (request.operation === 'discover') return {catalog: await repository.catalog(request.channel), authenticated: true}
  return {file: await repository.download(request.artifact), authenticated: true}
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then(value => process.stdout.write(JSON.stringify(value) + '\n')).catch(error => {
    process.stdout.write(JSON.stringify({error: error.message}) + '\n'); process.exitCode = 1
  })
}
