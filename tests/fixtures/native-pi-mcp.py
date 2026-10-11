# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual production Qt Window/Settings/MCP dialog against a private Pi owner."""
import json,os,time,urllib.request
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from augmentor_linux.pi_client import PiClient
from augmentor_linux.window import Window
from augmentor_linux.panels import SettingsDialog
from augmentor_linux.mcp_settings import McpDialog
app=QApplication([]);client=PiClient();sid='native-manager';errors=[]
pointer=Path(os.environ['AUGMENTOR_PI_STATE'])/'session.json';pointer.write_text(json.dumps({'endpoint':client.base,'session':sid,'selection':{'provider':'fixture','model':'manager-model'}}));pointer.chmod(0o600)
def until(check,label):
    end=time.monotonic()+12
    while time.monotonic()<end:
        app.processEvents()
        if check():return
        QTest.qWait(10)
    raise AssertionError('Native MCP timeout: '+label)
def click(button,label):
    until(lambda:button.isEnabled() and button.isVisible(),label+' control ready')
    QTest.mouseClick(button,Qt.MouseButton.LeftButton,delay=0)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*_):return None
window=Window(preview=False,harness='pi');window.show()
try:
    until(lambda:window.controller.online and window.controller.connected and window.send_button.isEnabled(),'controller connected')
    assert window.controller.capabilities.get('mcpManagement') is True
    with patch('augmentor_linux.shortcut_settings.current_keys',return_value=[]):
        settings=SettingsDialog(window);settings.show();app.processEvents()
        entry=next(button for button in settings.findChildren(QPushButton) if button.text()=='MCP servers');assert entry.isEnabled()
        def exercise():
            dialog=None
            try:
                dialog=window.findChildren(McpDialog)[-1];until(lambda:dialog.available and not dialog.reading,'MCP registrations');assert dialog.server.count()==3
                click(dialog.actions['login'],'Sign in');until(lambda:bool(dialog.authorization_url) and bool(dialog.receipt.get('waitingForRedirect')),'authorization URL')
                try:urllib.request.build_opener(NoRedirect()).open(dialog.authorization_url)
                except urllib.error.HTTPError as response:
                    assert response.code==302;redirect=response.headers['Location']
                dialog.redirect_input.setText(redirect);click(dialog.redirect_submit,'Submit redirect')
                until(lambda:dialog.receipt and dialog.receipt['state']=='completed' and not dialog.reading,'login settlement');assert dialog.receipt['result']=='sdk-reported-success';assert dialog.redirect_input.text()=='';assert not dialog.open_sign_in.isVisible()
                assert 'Observed connection:' in dialog.evidence.text();assert 'protocol negotiation observed' in dialog.evidence.text()
                click(dialog.enable_button,'Disable server');until(lambda:dialog.receipt and dialog.receipt['action']=='configure' and dialog.receipt['result']=='registration-events-settled' and dialog.enable_button.text()=='Enable server' and not dialog.reading,'disable settlement')
                click(dialog.enable_button,'Enable server');until(lambda:dialog.enable_button.text()=='Disable server' and not dialog.blocked and not dialog.reading,'enable settlement')
                dialog.exposure.setCurrentText('hidden');click(dialog.exposure_button,'Apply exposure');until(lambda:any(row['name']=='web' and row['exposure']=='hidden' for row in dialog.servers) and not dialog.blocked and not dialog.reading,'exposure settlement')
                click(dialog.edit_button,'Edit profile');until(lambda:dialog.editor.isVisible() and bool(dialog.profile.toPlainText()) and not dialog.reading,'profile editor');profile=json.loads(dialog.profile.toPlainText());profile['authoredUnrelated']='retained';profile['autoEnableCodemode']=False;profile['mcpServers']['header']['headers']['Authorization']='Bearer AUTHORED_CONFIG_PRIVATE_SECRET';dialog.profile.setPlainText(json.dumps(profile));previous=dialog.receipt['requestId'];click(dialog.save_button,'Save profile');until(lambda:dialog.receipt and dialog.receipt['requestId']!=previous and dialog.receipt['result']=='registration-events-settled' and not dialog.reading,'profile settlement');assert 'apply to new sessions' in dialog.evidence.text();dialog.close_editor();assert dialog.profile.toPlainText()==''
                click(dialog.actions['reconnect'],'Reconnect');until(lambda:dialog.receipt and dialog.receipt['action']=='reconnect' and dialog.receipt['state']=='completed' and not dialog.reading,'reconnect settlement')
                click(dialog.actions['logout'],'Sign out');until(lambda:dialog.receipt and dialog.receipt['action']=='logout' and dialog.receipt['state']=='completed' and not dialog.reading,'sign-out settlement')
                click(dialog.actions['login'],'Sign in again');until(lambda:bool(dialog.authorization_url) and not dialog.reading,'cancellable login');click(dialog.cancel_button,'Cancel');until(lambda:dialog.receipt and dialog.receipt['state']=='cancelled','cancellation settlement')
                assert not dialog.authorization_url
                window.controller.navigating=True;dialog.poll();assert dialog.closed;window.controller.navigating=False
            except Exception as error:errors.append(str(error))
            finally:
                if dialog is not None:dialog.accept()
        QTimer.singleShot(0,exercise);QTest.mouseClick(entry,Qt.MouseButton.LeftButton);settings.reject()
    assert not errors,errors
    print(json.dumps({'fixture':'native-pi-mcp','controls':'Settings MCP entry; login/paste/reconnect/logout/cancel; controller guard','inference':'none'}))
finally:
    window.controller.close();window.close();app.processEvents()
