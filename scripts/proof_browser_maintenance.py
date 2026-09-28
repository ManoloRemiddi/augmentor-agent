# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual unpacked Chromium pages, runtime.getContexts and native frames.

Invoked only by browser-composable-proof.py with a disposable profile, actual Pi
SDK and actual private owner/native control. No model request is submitted.
"""
import json
import time


def prove(owner,cdp,evaluate,until,send,open_settings,chat_panel,ext_id):
    from lifecycle.browser_control import PROTOCOL, Records
    from platform_adapters.transport import LocalSocket
    token='a'*32
    def control(action):
        with LocalSocket() as peer:
            peer.settimeout(15);peer.connect(str(owner.endpoint));records=Records(peer)
            records.write({'protocol':PROTOCOL,'kind':'maintenance','method':'host.maintenance.'+action,
                           'params':{} if action=='status' else {'token':token}})
            reply=records.read(time.monotonic()+15)
        return reply if reply.get('ok') else {'error':{'message':reply.get('error','Unconfirmed maintenance.')}}
    def reserve():
        # Periodic UI reads can legitimately refuse a snapshot. Retrying
        # preparation never replays a model or tool request.
        result=until(lambda:(r if (r:=control('prepare')).get('result',{}).get('phase')=='prepared' else None))
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
    ready(chat_panel,second)
    evaluate('document.querySelector("#input").value="PRIVATE unsent draft"',second)
    refused();ready(chat_panel,second)
    assert evaluate('document.querySelector("#input").value',second)=='PRIVATE unsent draft'
    evaluate('document.querySelector("#input").value=""',second)
    settings=open_settings('models')
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
