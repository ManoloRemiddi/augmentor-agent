# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pointer-driven browser memory controls against a disposable real Hindsight."""
import base64
import json
import os
import uuid


def prove(root,temp,panel,cdp,evaluate,click,fill,button,until,send,prompts,open_settings,back_to_chat):
    endpoint=os.environ.get('HINDSIGHT_TEST_ENDPOINT','http://127.0.0.1:8887');assert endpoint.startswith('http://127.0.0.1:')
    suffix=uuid.uuid4().hex[:12];fact='The browser acceptance user nickname is Silver Meadow '+suffix+'.'
    def rpc(action,params=None):return prompts.call('memory.'+action,params or {})
    panel=open_settings('memory')
    until(lambda:evaluate('!!document.querySelector("#section-memory details > summary")',panel))
    click('#section-memory details > summary');until(lambda:evaluate('!!document.querySelector("#section-memory .memory-dialog[open]")',panel))
    until(lambda:evaluate('!document.querySelector("section:not([hidden]) dialog fieldset").disabled',panel))
    fill('input[aria-label="Endpoint"]',endpoint);fill('input[aria-label="User bank"]','augmentor-browser-'+suffix)
    button('Check connection');until(lambda:evaluate('Array.from(document.querySelectorAll("section:not([hidden]) dialog button")).some(b=>b.textContent==="Save and enable"&&!b.disabled)',panel))
    assert not rpc('describe')['enabled'];button('Save and enable')
    until(lambda:rpc('describe')['enabled'] and evaluate('!document.querySelector("section:not([hidden]) dialog fieldset").disabled',panel))
    fill('textarea[aria-label="Memory text"]',fact);button('Retain this text')
    until(lambda:rpc('operations')['items'],20);operation=rpc('operations')['items'][0]
    until(lambda:rpc('operation',{'id':operation['id']})['status']=='completed',120)
    until(lambda:evaluate('!document.querySelector("section:not([hidden]) dialog fieldset").disabled',panel));button('Refresh')
    until(lambda:evaluate('document.querySelector("select[aria-label=\\"Retained documents\\"]").options.length===1 && !document.querySelector("section:not([hidden]) dialog fieldset").disabled',panel))
    evaluate('(()=>{const e=document.querySelector("select[aria-label=\\"Retained documents\\"]");e.selectedIndex=0;e.dispatchEvent(new Event("change"))})()',panel)
    until(lambda:fact in evaluate('document.querySelector("textarea[aria-label=\\"Retained document text\\"]").value',panel))
    assert any(suffix in row['text'] for row in rpc('agentRecall',{'query':'What is the browser user nickname?'})['results'])
    # The actual export button must cause a browser download with the real facts.
    downloads=temp/'downloads';downloads.mkdir(exist_ok=True)
    cdp('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads)})
    button('Export facts');until(lambda:(downloads/'augmentor-memory.json').exists())
    assert any(suffix in row['text'] for row in json.loads((downloads/'augmentor-memory.json').read_text())['facts'])
    cdp('Emulation.setDeviceMetricsOverride',{'width':440,'height':920,'deviceScaleFactor':1,'mobile':False},panel)
    evaluate('document.querySelector("dialog").scrollTop=0',panel)
    (root/'outputs/memory-browser.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{},panel)['data']))
    button('Disable memory');until(lambda:not rpc('describe')['enabled'] and evaluate('!document.querySelector("section:not([hidden]) dialog fieldset").disabled',panel))
    assert rpc('document',{'id':operation['document']})['original_text']==fact
    button('Delete selected')
    until(lambda:rpc('documents')['total']==0)
    back_to_chat();assert not rpc('agentRecall',{'query':'nickname'})['results']
    return {'actualBrowserRetainViewDisableDelete':True,'downloadedExportFactsVerified':True,'independentCompanionRecall':True,'hindsight':'0.9.2'}
