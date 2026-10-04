# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit opt-in UI testing of the actual native desktop process.

Disabled on normal launches. The existing same-user socket supplies commands;
no code evaluation, global keyboard events or control of other applications.
"""
from pathlib import Path
import os


def dispatch(window, request, *, enabled=False):
    if not enabled:raise ValueError('UI test control is disabled for this launch.')
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog
    controller=window.controller
    action=request.get('action')
    if action not in ('inspect','capture') and window.maintenance.phase()!='ready':
        raise ValueError('Augmentor maintenance is in progress. This request was not started.')
    if action=='inspect':
        return {'pid':os.getpid(),'visible':window.isVisible(),'active':window.isActiveWindow(),
                'online':bool(controller and controller.online),
                'session':controller.session if controller else None,
                'preset':controller.preset if controller else None,
                'running':bool(controller and controller.running),
                'model':window.model_picker.currentData(),
                'draft':window.composer.toPlainText(),
                'transcript':window.transcript.toPlainText(),
                'status':window.status.text(),
                'uiScale':window.ui_scale.percent,'width':window.width(),
                'fontPixels':window.brand.font().pixelSize(),'buttonWidth':window.send_button.width(),
                'dialogs':[d.windowTitle() for d in window.findChildren(QDialog) if d.isVisible()]}
    if action=='zoom':
        from .ui_scale import MINIMUM,MAXIMUM,STEP
        percent=request.get('percent')
        if type(percent) is not int or not MINIMUM<=percent<=MAXIMUM or percent%STEP:
            raise ValueError('Use a supported app size.')
        # Operates the actual Appearance control in this explicitly opted-in
        # window, including while a reply is streaming. No controller mutation.
        window.open_appearance()
        window.appearance_dialog.size_slider.setValue(percent)
        window.appearance_dialog.accept()
        return {'uiScale':window.ui_scale.percent,'width':window.width(),
                'fontPixels':window.brand.font().pixelSize(),'buttonWidth':window.send_button.width()}
    if action=='capture':
        path=Path(request['path'])
        if not path.is_absolute():raise ValueError('Use an absolute screenshot path.')
        # A test cannot accidentally overwrite a user's file or follow its symlink.
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(descriptor)
        if not window.grab().save(str(path),'PNG'):
            path.unlink();raise ValueError('Could not capture the app window.')
        return {'captured':True}
    if action=='draft':
        expected=request.get('expected');text=request.get('text')
        if (not isinstance(expected,str) or not isinstance(text,str) or len(text)>2000
                or not text.isascii() or window.composer.toPlainText()!=expected
                or bool(controller and (controller.running or controller.navigating or controller.repairing))
                or window.editing or window.composer.improving or any(d.isVisible() for d in window.findChildren(QDialog))):
            raise ValueError('Draft proof requires an idle window and the exact expected draft.')
        from PySide6.QtTest import QTest
        window.composer.setFocus();window.composer.selectAll()
        QTest.keyClick(window.composer,Qt.Key.Key_Backspace)
        QTest.keyClicks(window.composer,text)
        return {'draft':window.composer.toPlainText()}
    if action=='send':
        text=request.get('text');via=request.get('via','button')
        if not isinstance(text,str) or not text or len(text)>2000 or not text.isascii():
            raise ValueError('Use a short ASCII test message.')
        if via not in ('button','enter'):raise ValueError('Choose button or enter.')
        if (not controller or not controller.online or controller.running or controller.navigating
                or controller.repairing or window.composer.toPlainText()
                or not window.send_button.isEnabled() or not window.isVisible()
                or window.editing or window.voice_input is not None or window.voice_dialog
                or any(d.isVisible() for d in window.findChildren(QDialog))):
            raise ValueError('The window must be idle, visible and connected with an empty composer and no dialogs.')
        from PySide6.QtTest import QTest
        QTest.mouseClick(window.composer.viewport(),Qt.MouseButton.LeftButton)
        QTest.keyClicks(window.composer,text)
        if via=='button':QTest.mouseClick(window.send_button,Qt.MouseButton.LeftButton)
        else:QTest.keyClick(window.composer,Qt.Key.Key_Return)
        return {'submittedThrough':via}
    raise ValueError('Unknown UI test operation.')
