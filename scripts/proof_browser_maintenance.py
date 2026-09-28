# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual unpacked Chromium pages, runtime.getContexts and native frames.

Invoked only by browser-composable-proof.py with a disposable profile, actual Pi
SDK and actual private owner/native control. No model request is submitted.
"""
import json
import time


def prove(runtime,cdp,evaluate,until,send,open_settings,chat_panel,ext_id):
    from lifecycle.browser_control import PROTOCOL, Records
    from platform_adapters import locks
    from platform_adapters.private_files import descriptor
    from platform_adapters.transport import LocalSocket
    import os
    # Wait only on read-only registration evidence. Do not send a mutation to
    # an arbitrary winner while old and replacement hosts overlap.
    def discover():
        endpoints=[]
        for path in runtime.glob('augmentor-browser-*.lock'):
            fd=descriptor(path,writable=True)
            try:
                try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
                except BlockingIOError:endpoints.append(path.with_suffix('.sock'))
            finally:os.close(fd)
        if len(endpoints)!=1:return None
        try:
            with LocalSocket() as peer:
                peer.settimeout(5);peer.connect(str(endpoints[0]));records=Records(peer)
                records.write({'protocol':PROTOCOL,'kind':'describe'})
                reply=records.read(time.monotonic()+5)
                return endpoints[0] if reply.get('ok') and reply.get('connected') else None
        except (FileNotFoundError,ConnectionRefusedError):return None
    endpoint=until(discover)
    token='a'*32
    panels=[chat_panel]
    def control(action):
        with LocalSocket() as peer:
            peer.settimeout(15);peer.connect(str(endpoint));records=Records(peer)
            records.write({'protocol':PROTOCOL,'kind':'maintenance','method':'host.maintenance.'+action,
                           'params':{} if action=='status' else {'token':token}})
            reply=records.read(time.monotonic()+15)
        return reply if reply.get('ok') else {'error':{'message':reply.get('error','Unconfirmed maintenance.')}}
    def reserve():
        # Periodic UI reads can legitimately refuse a snapshot. Retrying
        # preparation never replays a model or tool request.
        try:
            result=until(lambda:(r if (r:=control('prepare')).get('result',{}).get('phase')=='prepared' else None))
        except AssertionError as error:
            # Metadata only: no form values, drafts, credentials or wire bodies.
            snapshot={'native':control('status'),'pages':[]}
            for panel in panels:
                snapshot['pages'].append(evaluate("import('./maintenance-page.mjs').then(m=>({formBusy:m.documentMaintenanceBusy(document),inert:document.body.inert,hasDraft:!!document.querySelector('#input')?.value}))",panel))
            state=send('log')
            snapshot['worker']={key:state.get(key) for key in ('phase','running','mutating','turnActive')}
            raise AssertionError('Browser reservation refused; metadata: '+json.dumps(snapshot)) from error
        return result['result']
    def refused():
        for _ in range(3):
            result=control('prepare')
            assert 'error' in result,result
            assert 'PRIVATE' not in json.dumps(result)
    def ready(*panels):
        until(lambda:all(not evaluate('document.body.inert',panel) for panel in panels))
    def open_panel():
        target=cdp('Target.createTarget',{'url':f'chrome-extension://{ext_id}/sidepanel.html'})['targetId']
        panel=cdp('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId']
        until(lambda:evaluate('!!document.querySelector("#input") && !document.body.inert',panel))
        return target,panel

    second_target,second=open_panel()
    panels.append(second)
    ready(chat_panel,second)
    evaluate('document.querySelector("#input").value="PRIVATE unsent draft"',second)
    refused();ready(chat_panel,second)
    assert evaluate('document.querySelector("#input").value',second)=='PRIVATE unsent draft'
    evaluate('document.querySelector("#input").value=""',second)
    settings=open_settings('models')
    panels.append(settings)
    until(lambda:evaluate('!!document.querySelector(".model-setup") && !document.body.inert',settings))
    evaluate('document.querySelector("input[type=password]").value="PRIVATE API key"',settings)
    refused();ready(chat_panel,second,settings)
    assert evaluate('document.querySelector("input[type=password]").value',settings)=='PRIVATE API key'
    evaluate('document.querySelector("input[type=password]").value=""',settings)
    status=reserve();assert status['pages']==3,status
    assert all(evaluate('document.body.inert',panel) for panel in (chat_panel,second,settings))
    assert 'not started' in send('newchat')['error']
    assert 'error' in control('commit')
    assert control('renew')['result']['phase']=='prepared'
    assert control('cancel')['result']['phase']=='ready';ready(chat_panel,second,settings)
    reserve()
    third_target,third=open_panel();ready(chat_panel,second,settings,third)
    assert control('status')['result']['phase']=='ready'
    cdp('Target.closeTarget',{'targetId':third_target})
    until(lambda:control('status')['result']['pages']==3)
    reserve();cdp('Target.closeTarget',{'targetId':second_target});ready(chat_panel,settings)
    panels.remove(second)
    assert control('status')['result']['phase']=='ready'
    reserve()
    # Actual page and MV3 worker monotonic timers, not an accelerated fake.
    end=time.monotonic()+35
    while time.monotonic()<end:
        if all(not evaluate('document.body.inert',panel) for panel in (chat_panel,settings)):break
        time.sleep(.2)
    else:raise AssertionError('Lost update reservation did not restore browser input.')
    assert control('status')['result']['phase']=='ready'
    return {'realChromiumExtensionDocuments':True,'realRuntimeContextInventory':True,
            'actualPrivateOwnerAndNativeControl':True,
            'nativeMessagingReservation':True,'multiplePageDraftRefusal':True,
            'unsavedApiKeyRefusal':True,'cancelPreservesPages':True,'renewal':True,
            'newAndClosedPageCancel':True,'lostReservationExpires':True,
            'commitNotEnabled':True,'liveWindowsBrowser':False}
