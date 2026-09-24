// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {DatabaseSync} from 'node:sqlite';
import {mkdirSync} from 'node:fs';
import {dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {actionKey} from '../../adapters/dsh-execution/actions.mjs';

export class Conflict extends Error {}
export class Ledger {
  constructor(path) {
    mkdirSync(dirname(path),{recursive:true,mode:0o700});
    this.db=new DatabaseSync(path);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, digest TEXT NOT NULL, session TEXT NOT NULL, status TEXT NOT NULL, response TEXT);
      CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY, request TEXT NOT NULL, key TEXT NOT NULL, tool TEXT NOT NULL, status TEXT NOT NULL, arguments TEXT, UNIQUE(request,key));`);
    if(!this.db.prepare('PRAGMA table_info(actions)').all().some(c=>c.name==='arguments'))this.db.exec('ALTER TABLE actions ADD COLUMN arguments TEXT');
    if(!this.db.prepare('PRAGMA table_info(requests)').all().some(c=>c.name==='owner'))this.db.exec("ALTER TABLE requests ADD COLUMN owner TEXT NOT NULL DEFAULT 'operator'");
    this.db.exec("UPDATE requests SET status='interrupted' WHERE status='running'; UPDATE actions SET status='unknown' WHERE status='running'");
  }
  begin(id,session,prompt,owner='operator') {
    const digest=createHash('sha256').update(JSON.stringify([session,prompt])).digest('hex');
    const old=this.db.prepare('SELECT * FROM requests WHERE id=?').get(id);
    if(old) {
      if(old.digest!==digest)throw new Conflict('Request ID already belongs to different input.');
      if(old.response)return JSON.parse(old.response);
      throw new Conflict('Earlier request is running or interrupted. Inspect its history and action outcomes; it will not be replayed.');
    }
    this.db.prepare("INSERT INTO requests(id,digest,session,status,response,owner) VALUES(?,?,?,'running',NULL,?)").run(id,digest,session,owner);
    return null;
  }
  finish(id,response) { this.db.prepare("UPDATE requests SET status='finished',response=? WHERE id=?").run(JSON.stringify(response),id); }
  reserve(request,tool,args) {
    if(this.pending().length)throw new Conflict('A previous home action has an unknown outcome. Inspect the home and acknowledge the action before another change.');
    const key=actionKey(tool,args);
    if(this.db.prepare('SELECT id FROM actions WHERE request=? AND key=?').get(request,key))throw new Conflict('This action already ran in this request. Inspect its result; do not repeat it.');
    return Number(this.db.prepare("INSERT INTO actions(request,key,tool,status,arguments) VALUES(?,?,?,'running',?)").run(request,key,tool,JSON.stringify(args)).lastInsertRowid);
  }
  outcome(id,status) { this.db.prepare('UPDATE actions SET status=? WHERE id=?').run(status,id); }
  pending() { return this.db.prepare("SELECT id,request,tool,status,arguments FROM actions WHERE status IN ('running','unknown')").all(); }
  request(id) {
    const row=this.db.prepare('SELECT id,session,status,response,owner FROM requests WHERE id=?').get(id);
    return row?{...row,response:row.response?JSON.parse(row.response):null}:null;
  }
  acknowledge(id) {
    if(!this.db.prepare("UPDATE actions SET status='acknowledged' WHERE id=? AND status='unknown'").run(id).changes)throw new Conflict('Only an unknown action can be acknowledged.');
  }
  close() { this.db.close(); }
}
