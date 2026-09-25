# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Chromium DSH onboarding, role boundary, browser task and Branch/Edit."""
import json
import os
import sys
from pathlib import Path
import time

def prove(root,temp,panel,cdp,evaluate,click,fill,button,until,send,port,open_settings,back_to_chat):
    sys.path[:0]=[str(root/'apps/native'),str(root/'services')]
    from augmentor_linux.adapters.dsh import DshAdapter
    from dsh.branch import history
    dsh=DshAdapter()
    if evaluate('!!document.querySelector("dialog[open]")',panel):button('Later')
    assert send('harness/select',{'harness':'dsh'})['ok']
    until(lambda:(v:=send('log')).get('harness')=='dsh' and v.get('phase') in ('ready','needs-setup'),30)
    panel=open_settings('harnesses');until(lambda:evaluate('!!document.querySelector(".dsh-setup") && !document.querySelector(".dsh-setup fieldset").disabled',panel))
    # The fixture restarts DSH after installation, rotating its launch token.
    # Enter the current launch URL through the same form used for manual pairing.
    token=os.environ.get('AUGMENTOR_DSH_AUTH_TOKEN')
    if token:
        endpoint=evaluate('document.querySelector('+json.dumps('input[aria-label="DSH URL"]')+').value',panel)
        fill('input[aria-label="DSH URL"]',endpoint.split('?',1)[0]+'?token='+token)
    button('Check connection');until(lambda:evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).some(b=>b.textContent==="Save and use DSH"&&!b.disabled)',panel),20)
    button('Save and use DSH');until(lambda:send('log').get('phase')=='ready',30)
    back_to_chat()
    # Resolve the chat target again; Settings remains open in its own tab.
    chat=next(t for t in cdp('Target.getTargets')['targetInfos'] if t['url'].endswith('/sidepanel.html'))
    panel=cdp('Target.attachToTarget',{'targetId':chat['targetId'],'flatten':True})['sessionId']
    # The browser shares both personal aliases; internal update methods remain blocked.
    listed=send('session/list');assert listed['ok'],listed
    assert 'setup-linux' in json.dumps(listed),listed
    # Use the native pipe directly for unsupported/internal operations so the
    # test cannot pass merely because the panel lacks a matching message type.
    evaluate("window.boundaryPort=chrome.runtime.connectNative('com.augmentor.agent');window.boundaryReplies={};window.boundaryPort.onMessage.addListener(m=>window.boundaryReplies[m.id]=m)",panel)
    serial=0
    def direct(method,params={}):
        nonlocal serial
        serial+=1
        evaluate('window.boundaryPort.postMessage('+json.dumps({'id':str(serial),'method':method,'params':params})+')',panel)
        frame=until(lambda:evaluate('window.boundaryReplies['+json.dumps(str(serial))+']',panel))
        return {'ok':'error' not in frame,'value':frame.get('result'),'error':frame.get('error')}
    version=json.loads((root/'release/product.json').read_text())['version']
    assert direct('augmentor/handshake',{'protocol':'augmentor/1','version':version})['ok']
    assert direct('harness.select',{'harness':'dsh'})['ok']
    if os.environ.get('AUGMENTOR_PROOF_MODEL_PICKER'):
        curated=direct('augmentor/models');assert curated['ok'],curated
        assert 'fixture/fixture' in curated['value']['pinned'] and 'fixture/hidden-fixture' in curated['value']['hidden'],curated
    assert direct('session.history',{'sessionId':'setup-linux'})['ok']
    for method,p in [('session.history',{'sessionId':'not-a-personal-chat'}),('settings.describe',{'ns':'llm-pi-ai'}),('augmentor/update-plugin',{'version':'9.9.9'}),('trace/fence-probe',{'secret':'private'})]:
        result=direct(method,p);assert not result['ok'],(method,result)
    evaluate('window.boundaryPort.disconnect()',panel)
    send('model',{'provider':'fixture','model':'fixture'})
    if os.environ.get('AUGMENTOR_PROOF_MODEL_PICKER'):
        until(lambda:evaluate('!document.querySelector("#model").hidden',panel))
        click('#model')
        until(lambda:evaluate('!!document.querySelector("#modelpop .mp-row")',panel))
        assert not evaluate('Array.from(document.querySelectorAll("#modelpop .mp-row")).some(r=>r.title==="fixture / hidden-fixture")',panel)
        fill('#modelpop-search-input','Hidden Fixture')
        assert evaluate('document.querySelectorAll("#modelpop .mp-row").length',panel)==0
        fill('#modelpop-search-input','Fixture')
        evaluate('Array.from(document.querySelectorAll("#modelpop .mp-row")).find(r=>r.title==="fixture / fixture").id="proof-visible-model"',panel)
        click('#proof-visible-model')
        until(lambda:evaluate('document.querySelector("#modelpop").hidden',panel))

    fill('#input',f'DSH browser fixture http://127.0.0.1:{port}/fixture');click('#send')
    until(lambda:'DSH VERIFIED BROWSER' in evaluate('document.querySelector("#log").innerText',panel) and not send('log')['running'],60)
    page=next(t for t in cdp('Target.getTargets')['targetInfos'] if t['url']==f'http://127.0.0.1:{port}/fixture')
    ps=cdp('Target.attachToTarget',{'targetId':page['targetId'],'flatten':True})['sessionId']
    assert evaluate('document.querySelector("#result").textContent',ps)=='DSH VERIFIED BROWSER'
    source=send('log')['sessionId'];original=history(dsh.call,source)
    evaluate('Array.from(document.querySelectorAll(".msg-branch")).at(-1).id="fixture-branch"',panel);click('#fixture-branch')
    branch=until(lambda:(v if (v:=send('log')['sessionId'])!=source else None));assert history(dsh.call,source)==original
    # Browser tools activate the fixture page. Bring the chat target back before
    # delivering keyboard input, and wait for its branch refresh to be ready.
    cdp('Target.activateTarget',{'targetId':chat['targetId']})
    until(lambda:evaluate('!document.querySelector("#input").disabled && !document.querySelector("#send").disabled',panel))
    fill('#input','Reply exactly DSH BRANCH CONTINUED.')
    assert evaluate('document.querySelector("#input").value',panel)=='Reply exactly DSH BRANCH CONTINUED.'
    click('#send')
    until(lambda:'DSH BRANCH CONTINUED' in evaluate('document.querySelector("#log").innerText',panel) and not send('log')['running'],30)
    until(lambda:evaluate('document.querySelectorAll(".msg-edit").length===1',panel));click('.msg-edit')
    fill('#input','Reply exactly DSH EDIT VERIFIED.');click('#send')
    until(lambda:'DSH EDIT VERIFIED' in evaluate('document.querySelector("#log").innerText',panel) and not send('log')['running'],30)
    edited=send('log')['sessionId'];assert edited not in (source,branch)
    assert history(dsh.call,source)==original
    branch_events=history(dsh.call,branch)
    assert not any('DSH EDIT VERIFIED' in str(e['data']) for e in branch_events if e['type']=='user/message')
    edited_events=history(dsh.call,edited)
    inputs=[str(e['data']) for e in edited_events if e['type']=='user/message']
    assert any('DSH EDIT VERIFIED' in value for value in inputs)
    assert not any('DSH BRANCH CONTINUED' in value for value in inputs)
    return {'modelPickerUi':bool(os.environ.get('AUGMENTOR_PROOF_MODEL_PICKER')),'checkedBrowserSetup':True,'sharedPersonalChats':True,'legacyUpdateBlocked':True,'actualPageResult':True,'branchPreservesTools':True,'exactEditReplacesInput':True,'parentUnchanged':True}
