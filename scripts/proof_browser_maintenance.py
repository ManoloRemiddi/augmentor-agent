# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual unpacked Chromium pages, runtime.getContexts and native frames.

Invoked only by browser-composable-proof.py with a disposable profile, actual Pi
SDK and qualification-only native framing proxy. No model request is submitted.
"""
import json
import time


def prove(temp,cdp,evaluate,until,send,open_settings,chat_panel,ext_id):
    sequence=0
    token='a'*32
    directory=temp/'maintenance'
    def control(action):
        nonlocal sequence
        sequence+=1
        pid=json.loads((directory/'host.json').read_text())['pid']
        request=directory/f'{pid}-request.json';response=directory/f'{pid}-response.json'
        value={'id':f'maintenance-proof-{sequence}','method':'augmentor/maintenance',
               'params':{'method':'host.maintenance.'+action,'params':{} if action=='status' else {'token':token}}}
        if action=='browser-action':value.update(method='browser/execute',params={'action':'tabs_list'})
        stage=request.with_suffix('.tmp');stage.write_text(json.dumps(value));stage.replace(request)
        end=time.monotonic()+10
        while time.monotonic()<end:
            if response.exists():
                reply=json.loads(response.read_text())
                if reply.get('id')==value['id']:return reply
            time.sleep(.05)
        raise AssertionError('Native maintenance request did not return.')
    def reserve():
        # Periodic UI reads can legitimately refuse a snapshot. Retrying
        # preparation never replays a model or tool request.
        result=until(lambda:(r if (r:=control('prepare')).get('result',{}).get('phase')=='prepared' else None))
        return result['result']
    def refused():
        result=until(lambda:(r if 'page' in (r:=control('prepare')).get('error',{}).get('message','') else None))
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
    assert 'not started' in control('browser-action')['error']['message']
    assert 'handoff' in control('commit')['error']['message']
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
            'nativeMessagingReservation':True,'multiplePageDraftRefusal':True,
            'unsavedApiKeyRefusal':True,'cancelPreservesPages':True,'renewal':True,
            'newAndClosedPageCancel':True,'lostReservationExpires':True,
            'commitNotEnabled':True,'liveWindowsBrowser':False}
