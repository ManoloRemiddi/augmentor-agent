# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Settings navigation and cross-tab behavior in actual isolated Chromium."""
import base64
import json
import os
import time


def prove(root,temp,cdp,evaluate,click,fill,until,send,open_settings,back_to_chat,chat):
    # Use the actual More menu and OS pointer events; no fake chrome runtime.
    fill('#input','Keep my unfinished chat draft')
    before=send('log')['sessionId']
    panel=open_settings('appearance')
    assert evaluate('document.querySelectorAll("nav a").length',panel)==8
    assert evaluate('document.querySelectorAll("header button").length',chat)==5
    assert not evaluate('!!document.querySelector("#harness-picker")',chat)
    assert 'linear-gradient' in evaluate('getComputedStyle(document.querySelector("#accentHue")).backgroundImage',panel)
    assert not evaluate('!!document.querySelector("dialog[open]")',chat)
    settings=lambda:[t for t in cdp('Target.getTargets')['targetInfos'] if '/settings.html' in t['url']]
    first=settings()[0]['targetId'];back_to_chat()
    panel=open_settings('appearance');assert len(settings())==1 and settings()[0]['targetId']==first
    assert evaluate('document.querySelector("#input").value',chat)=='Keep my unfinished chat draft'
    assert send('log')['sessionId']==before
    # Actual slider key input changes the CSS on the already-open chat page.
    initial=evaluate('getComputedStyle(document.documentElement).getPropertyValue("--brand")',chat)
    click('#accentHue')
    cdp('Input.dispatchKeyEvent',{'type':'keyDown','key':'Home','code':'Home','windowsVirtualKeyCode':36},panel)
    cdp('Input.dispatchKeyEvent',{'type':'keyUp','key':'Home','code':'Home','windowsVirtualKeyCode':36},panel)
    until(lambda:evaluate('localStorage.getItem("augmentor-accent-hue")==="0"',chat))
    until(lambda:evaluate('getComputedStyle(document.documentElement).getPropertyValue("--brand")',chat)!=initial)
    evaluate('document.querySelector(".theme-choices button:last-child").id="light-theme"',panel);click('#light-theme')
    until(lambda:evaluate('document.documentElement.dataset.theme',chat)=='light')
    cdp('Page.reload',{},panel)
    until(lambda:evaluate('document.querySelector("#accentHue")?.value',panel)=='0')
    assert evaluate('document.documentElement.dataset.theme',panel)=='light'
    assert evaluate('getComputedStyle(document.documentElement).getPropertyValue("--text").trim()',panel)=='rgb(21, 43, 44)'
    # A form remains in normal page flow and retains its input across sections.
    panel=open_settings('models');click('.model-setup details summary');fill('input[aria-label="Connection name"]','Unfinished connection')
    assert not evaluate('!!document.querySelector(":modal")',panel)
    click('#nav-memory');until(lambda:evaluate('!document.querySelector("#section-memory").hidden',panel))
    assert not evaluate('!!document.querySelector("#section-memory dialog")',panel)
    cdp('Emulation.setDeviceMetricsOverride',{'width':1200,'height':850,'deviceScaleFactor':1,'mobile':False},panel)
    evaluate('window.scrollTo(0,0)',panel)
    (root/'outputs/browser-memory-onboarding.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{},panel)['data']))
    if os.environ.get('AUGMENTOR_PROOF_ONBOARDING'):
        click('#section-memory .onboarding-card button')
        until(lambda:'Continue in Augmentor Linux' in evaluate('document.querySelector("#section-memory .onboarding-card").textContent',panel),35)
        import sys
        sys.path.insert(0,str(root/'apps/native'))
        from augmentor_linux.pi_client import PiClient
        runtime=PiClient(base=str(temp/'pi-state/runtime.sock'))
        until(lambda:(temp/'pi-state/session.json').exists() and json.loads((temp/'pi-state/session.json').read_text()).get('session'),20)
        selected=json.loads((temp/'pi-state/session.json').read_text())
        session=selected['session']
        until(lambda:any('I checked your shared memory' in json.dumps(e) for e in runtime.call('session.history',{'sessionId':session,'maxMessages':100})['events']),30)
        history=runtime.call('session.history',{'sessionId':session,'maxMessages':100})
        assert 'bash' in json.dumps(history) and 'memory.describe' in json.dumps(history)
        click('#section-memory .onboarding-card button');time.sleep(.4)
        assert json.loads((temp/'pi-state/session.json').read_text())['session']==session
    click('#section-memory details > summary');until(lambda:evaluate('!!document.querySelector("#section-memory dialog[open]")',panel))
    until(lambda:evaluate('!document.querySelector("#section-memory fieldset").disabled',panel))
    fill('#section-memory input[aria-label="User bank"]','unfinished-bank')
    click('#nav-models')
    assert evaluate('document.querySelector('+json.dumps('.model-setup input[aria-label="Connection name"]')+').value',panel)=='Unfinished connection'
    click('#nav-memory');assert evaluate('document.querySelector('+json.dumps('#section-memory input[aria-label="User bank"]')+').value',panel)=='unfinished-bank'
    click('#nav-harnesses');until(lambda:evaluate('!!document.querySelector(".dsh-setup[open]")',panel))
    assert not evaluate('!!document.querySelector(":modal")',panel)
    # Backend refuses a provider write while DSH is selected (no silent Pi change).
    value=send('harness/select',{'harness':'dsh'});assert value['ok'],value
    until(lambda:send('connect').get('harness')=='dsh')
    click('#nav-models');until(lambda:evaluate('!document.querySelector("#dsh-model-settings").hidden',panel))
    assert evaluate('document.querySelector("#pi-model-settings").hidden',panel)
    refused=send('modelSetup',{'action':'save','params':{}});assert not refused['ok']
    value=send('harness/select',{'harness':'pi'});assert value['ok'],value
    until(lambda:send('connect').get('harness')=='pi')
    # Different callers racing to open Settings still get this same tab.
    r=evaluate('Promise.all(["appearance","prompts","memory"].map(section=>chrome.runtime.sendMessage({type:"settings/open",section})))',chat)
    assert all(v['ok'] for v in r) and len({v['tabId'] for v in r})==1 and len(settings())==1
    click('#nav-appearance')
    until(lambda:evaluate('!document.querySelector("#section-appearance").hidden',panel))
    # Return screenshot to the default dark palette.
    evaluate('document.querySelector(".theme-choices button:first-child").id="dark-theme"',panel);click('#dark-theme')
    until(lambda:evaluate('document.documentElement.dataset.theme',panel)=='dark')
    evaluate('window.scrollTo(0,0)',panel)
    cdp('Emulation.setDeviceMetricsOverride',{'width':1200,'height':900,'deviceScaleFactor':1,'mobile':False},panel)
    (root/'outputs/browser-settings-desktop.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{},panel)['data']))
    cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':False},panel)
    evaluate('window.scrollTo(0,0)',panel)
    assert evaluate('document.documentElement.scrollWidth<=innerWidth',panel)
    (root/'outputs/browser-settings-narrow.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{},panel)['data']))
    back_to_chat()
    cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':False},chat)
    assert evaluate('document.documentElement.scrollWidth<=innerWidth',chat)
    (root/'outputs/browser-toolbar-settings.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{},chat)['data']))
    assert evaluate('document.querySelector("#input").value',chat)=='Keep my unfinished chat draft'
    return {'isolatedState':str(temp),'toolbarButtons':5,'settingsSections':8,'singleSettingsTab':True,'concurrentOpenReusesTab':True,'chatDraftPreserved':True,'appearanceLiveAndPersistent':True,'formsNonmodal':True,'sectionDraftsPreserved':True,'bothHarnessViews':True,'narrowLayout':True,'harnessOnlyInSettings':True,'colourGradients':True,'guidedMemoryLinuxSession':bool(os.environ.get('AUGMENTOR_PROOF_ONBOARDING'))}
