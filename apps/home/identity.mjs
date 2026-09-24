// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomBytes,createHash,timingSafeEqual,randomUUID} from 'node:crypto';
export const digest=value=>createHash('sha256').update(value).digest('hex');
const secret=()=>randomBytes(32).toString('base64url');
export const safeEqual=(a,b)=>timingSafeEqual(Buffer.from(digest(a)),Buffer.from(digest(b)));
export class Identity {
  constructor(db){
    this.db=db;
    db.exec(`CREATE TABLE IF NOT EXISTS home_clients(id TEXT PRIMARY KEY,name TEXT NOT NULL,role TEXT NOT NULL,hash TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,expires INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS home_invites(hash TEXT PRIMARY KEY,role TEXT NOT NULL,expires INTEGER NOT NULL);`);
  }
  hasOwner(){return !!this.db.prepare("SELECT id FROM home_clients WHERE role='owner' AND revoked=0 AND expires>?").get(Date.now());}
  invite(role='member'){
    if(!['owner','member','viewer'].includes(role))throw Error('Invalid role');
    const code=secret(),expires=Date.now()+10*60*1000;
    this.db.prepare('DELETE FROM home_invites WHERE expires<?').run(Date.now());
    this.db.prepare('INSERT INTO home_invites VALUES(?,?,?)').run(digest(code),role,expires);
    return {code,expires};
  }
  pair(code,name,kind){
    if(typeof code!=='string'||typeof name!=='string'||!name.trim()||name.length>80||!['browser','api'].includes(kind))throw Error('Invalid pairing request');
    const row=this.db.prepare('DELETE FROM home_invites WHERE hash=? AND expires>? RETURNING role').get(digest(code),Date.now());
    if(!row)throw Error('Pairing code expired or already used');
    const token=secret(),id=randomUUID(),expires=Date.now()+(kind==='browser'?7:90)*86400000;
    this.db.prepare('INSERT INTO home_clients VALUES(?,?,?,?,?,?,0)').run(id,name.trim(),row.role,digest(token),kind,expires);
    return {id,name:name.trim(),role:row.role,token,expires,csrf:digest(token+':csrf')};
  }
  authenticate(req,operatorToken){
    const bearer=req.headers.authorization?.startsWith('Bearer ')?req.headers.authorization.slice(7):null;
    if(bearer&&safeEqual(bearer,operatorToken))return {id:'operator',role:'owner',kind:'operator'};
    const cookie=req.headers.cookie?.split(';').map(x=>x.trim()).find(x=>x.startsWith('augmentor_home='))?.slice(15);
    const token=bearer??cookie;
    if(!token||token.length>200)return null;
    const client=this.db.prepare('SELECT id,name,role,kind FROM home_clients WHERE hash=? AND revoked=0 AND expires>?').get(digest(token),Date.now());
    if(!client||!!bearer!==(client.kind==='api'))return null;
    return {...client,csrf:digest(token+':csrf')};
  }
  list(){return this.db.prepare('SELECT id,name,role,kind,expires,revoked FROM home_clients ORDER BY name').all();}
  revoke(id){this.db.prepare('UPDATE home_clients SET revoked=1 WHERE id=?').run(id);}
}
