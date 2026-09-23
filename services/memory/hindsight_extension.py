# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Controlled synchronous stages for pinned Hindsight 0.10.0.

Loaded through Hindsight's documented HTTP extension. Its autonomous worker
must be disabled. Existing queued operations remain stored, never implicitly
claimed here. Augmentor's durable budgets also guard the model connection.
"""
import asyncio
from datetime import datetime
import hashlib
import hmac
import json
import logging
import re
import traceback
import urllib.request

from fastapi import APIRouter, HTTPException, Request
from hindsight_api.extensions.http import HttpExtension
from hindsight_api.models import RequestContext


class ControlledMemory(HttpExtension):
    def get_router(self, memory):
        router = APIRouter()
        lock = asyncio.Lock()
        key = self.config['key']
        gateway = self.config['gateway'].rstrip('/')

        def valid(window):
            request = urllib.request.Request(gateway + '/window', headers={
                'Authorization': 'Bearer ' + key, 'X-Augmentor-Window': window})
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(request, timeout=1) as response:
                    return json.load(response).get('allowed') is True
            except Exception:
                return False

        @router.get('/augmentor/policy')
        async def policy():
            from hindsight_api.config import get_config
            config = get_config()
            return {'protocol': 'augmentor-memory-processing/1', 'workerEnabled': config.worker_enabled,
                    'reconcileSeconds': config.consolidation_reconcile_interval_seconds,
                    'llmRetries': config.llm_max_retries}

        @router.post('/augmentor/stage')
        async def stage(request: Request):
            if not hmac.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + key):
                raise HTTPException(403, 'Controlled memory credential required')
            raw = await request.body()
            if len(raw) > 128000:
                raise HTTPException(413, 'Memory stage too large')
            body = json.loads(raw)
            window = body['window']
            if not await asyncio.to_thread(valid, window):
                raise HTTPException(409, 'No active processing window')
            if lock.locked():
                raise HTTPException(409, 'A memory stage is already active')
            async with lock:
                bank, kind, identity = body['bank'], body['stage'], body['id']
                if kind not in ('retain', 'consolidate', 'page') or not bank.startswith('aug-') or len(identity) > 128:
                    raise HTTPException(400, 'Invalid controlled memory stage')
                if kind in ('retain', 'consolidate') and not re.fullmatch(r'augmentor-job-[a-f0-9]{64}', body.get('sourceTag', '')):
                    raise HTTPException(400, 'An exact admitted source batch is required')
                payload = {k: v for k, v in body.items() if k != 'window'}
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                pool = await memory._get_pool()
                async with pool.acquire() as db:
                    await db.execute('''CREATE TABLE IF NOT EXISTS augmentor_memory_stages (
                        id TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL)''')
                    await db.execute("ALTER TABLE augmentor_memory_stages ADD COLUMN IF NOT EXISTS detail TEXT NOT NULL DEFAULT ''")
                    previous = await db.fetchrow('SELECT digest,status,detail FROM augmentor_memory_stages WHERE id=$1', identity)
                    if previous:
                        if previous['digest'] != digest:
                            raise HTTPException(409, 'Memory stage identity changed')
                        # A lost result or restart cannot replay an unknown operation.
                        return {'status': previous['status'], 'id': identity, 'failureType': previous['detail']}
                    await db.execute("INSERT INTO augmentor_memory_stages(id,digest,status) VALUES ($1,$2,'unknown')", identity, digest)
                context = RequestContext(internal=True)

                async def execute():
                    if kind == 'retain':
                        items = [{**item, 'event_date': datetime.fromisoformat(item['timestamp'])}
                                 for item in body['items']]
                        await memory.retain_batch_async(bank, items, request_context=context)
                    elif kind == 'consolidate':
                        from hindsight_api.engine.consolidation import run_consolidation_job
                        before = await memory.get_bank_freshness(bank, request_context=context)
                        # The public bank-wide wrapper would also drain old
                        # unconsolidated facts. Use the pinned scoped engine
                        # entrypoint, keeping old archive work untouched.
                        result = await run_consolidation_job(memory, bank, context,
                            observation_scopes=[[body['sourceTag']]])
                        after = await memory.get_bank_freshness(bank, request_context=context)
                        # 0.10.0's public consolidation result drops its internal
                        # memories_failed count. Verify the durable effect instead
                        # of treating a returned call as proof of success.
                        if (result.get('memories_failed') or result.get('llm_batch_failures') or
                                after['failed_consolidation'] > before['failed_consolidation']):
                            raise RuntimeError('Consolidation left newly failed memories')
                    else:
                        result = await memory.refresh_mental_model(bank, body['page'], request_context=context)
                        if result is None:
                            raise RuntimeError('The selected knowledge page no longer exists')

                task = asyncio.create_task(execute())
                state = 'completed'
                detail = ''
                try:
                    while not task.done():
                        if not await asyncio.to_thread(valid, window):
                            state = 'stopped'
                            task.cancel()
                            break
                        await asyncio.sleep(.2)
                    await task
                except asyncio.CancelledError:
                    state = 'stopped'
                except Exception as error:
                    state = 'failed'
                    detail = type(error).__name__
                    logging.getLogger(__name__).warning('Controlled memory stage failed: %s; frames=%s', detail,
                        [(frame.name, frame.lineno) for frame in traceback.extract_tb(error.__traceback__)])
                finally:
                    if not task.done():
                        task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    async with pool.acquire() as db:
                        await db.execute('UPDATE augmentor_memory_stages SET status=$1,detail=$2 WHERE id=$3', state, detail, identity)
                return {'status': state, 'id': identity, 'failureType': detail}

        return router
