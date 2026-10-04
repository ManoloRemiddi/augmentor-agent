# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Explicit opt-in UI testing of the actual native desktop process.

Disabled on normal launches. The existing same-user socket supplies commands;
no code evaluation, global keyboard events or control of other applications.
"""
from pathlib import Path
import os


def shortcut_settings(window, request):
    """Operate only the actual opted-in window's bounded Settings controls."""
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QKeySequence
    from PySide6.QtWidgets import QDialog, QScrollArea
    from .shortcut_key_codec import encode
    operation = request.get('operation')
    fields = {'open': set(), 'inspect': set(), 'close': set(),
              'choose': {'instance', 'sequence', 'expectedCurrent'},
              'save': {'instance', 'expectedSequence', 'expectedCurrent'}}
    if (operation not in fields or set(request) != {'action', 'operation'} | fields[operation]):
        raise ValueError('Use an explicit bounded shortcut Settings operation.')
    controller = window.controller
    if (not window.isVisible() or window.composer.toPlainText() or window.editing
            or window.composer.improving or bool(controller and any(getattr(controller, key, False)
                for key in ('running', 'navigating', 'repairing')))):
        raise ValueError('Shortcut Settings proof requires a visible idle window with no draft.')
    dialog = window.shortcut_dialog
    visible = [d for d in window.findChildren(QDialog) if d.isVisible()]
    if any(d is not dialog for d in visible):
        raise ValueError('Shortcut Settings proof cannot operate behind another dialog.')
    if dialog is not None and (dialog.owner is not window or dialog.shortcuts.owner is not window):
        raise ValueError('Only the actual window Settings dialog may be inspected.')
    if operation == 'open':
        if dialog is not None or getattr(window, '_shortcut_proof_opening', False):
            raise ValueError('Shortcut Settings is already open or opening.')
        window._shortcut_proof_opening = True
        def opened():
            window._shortcut_proof_opening = False
            # The IPC reply precedes the normal modal exec(), and this callback
            # rechecks admission because another UI event can run in between.
            if (window.maintenance.phase() == 'ready' and window.isVisible()
                    and not window.composer.toPlainText() and not window.editing
                    and not window.composer.improving and not window.shortcut_dialog
                    and not any(d.isVisible() for d in window.findChildren(QDialog))
                    and not bool(window.controller and any(getattr(window.controller, key, False)
                        for key in ('running', 'navigating', 'repairing')))):
                window.open_settings()
        QTimer.singleShot(0, opened)
    elif operation != 'inspect':
        if (dialog is None or not dialog.isVisible() or dialog.owner is not window
                or dialog.shortcuts.owner is not window):
            raise ValueError('The actual window Settings dialog must be open.')
        rows = dialog.shortcuts.rows
        if any(row['saving'] for row in rows.values()):
            raise ValueError('Wait for the actual asynchronous shortcut Save to finish.')
        if operation == 'close':
            dialog.reject()
        else:
            from PySide6.QtTest import QTest
            name = request['instance']
            if name not in ('main', 'secondary'):
                raise ValueError('Choose one of the two shortcut rows.')
            row = rows[name]
            if (not isinstance(request['expectedCurrent'], str)
                    or row['keys'] is None or row['current'].text() != request['expectedCurrent']):
                raise ValueError('Shortcut Settings changed; inspect the current binding again.')
            for scroll in dialog.findChildren(QScrollArea):
                scroll.ensureWidgetVisible(row['editor'])
            if operation == 'choose':
                text = request['sequence']
                if not isinstance(text, str) or not 1 <= len(text) <= 80 or not text.isascii():
                    raise ValueError('Use one bounded shortcut combination.')
                sequence = QKeySequence(text, QKeySequence.SequenceFormat.PortableText)
                if sequence.count() != 1 or sequence.isEmpty():
                    raise ValueError('Use one shortcut combination.')
                encode(sequence)  # Same supported key contract as production Save.
                row['editor'].clear();row['editor'].setFocus()
                QTest.keyClick(row['editor'], sequence[0].key(), sequence[0].keyboardModifiers())
            else:
                expected = request['expectedSequence']
                if (not isinstance(expected, str) or len(expected) > 80
                        or row['editor'].keySequence().toString(QKeySequence.SequenceFormat.PortableText) != expected
                        or not row['button'].isEnabled() or not row['button'].isVisible()):
                    raise ValueError('Shortcut Save requires the exact selected combination and an enabled button.')
                QTest.mouseClick(row['button'], Qt.MouseButton.LeftButton)
    dialog = window.shortcut_dialog
    return {'pid': os.getpid(), 'buildRoot': str(Path(__file__).resolve().parents[3]),
            'open': bool(dialog and dialog.isVisible()),
            'opening': bool(getattr(window, '_shortcut_proof_opening', False)),
            'rows': {name: {'current': row['current'].text(), 'note': row['note'].text(),
                            'sequence': row['editor'].keySequence().toString(QKeySequence.SequenceFormat.PortableText),
                            'saving': row['saving'], 'ready': row['keys'] is not None,
                            'saveEnabled': row['button'].isEnabled()}
                     for name, row in dialog.shortcuts.rows.items()} if dialog and dialog.isVisible() else {}}


def dispatch(window, request, *, enabled=False):
    if not enabled:raise ValueError('UI test control is disabled for this launch.')
    if not isinstance(request, dict):raise ValueError('Use a UI test request object.')
    if request.get('action') == 'runtime-markers':
        if set(request) != {'action'}:
            raise ValueError('Runtime markers accept no additional fields.')
        from . import platform_runtime  # Shared services path, no OS/UI action.
        from platform_adapters.recipient_runtime_markers import collect
        return collect()
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog
    controller=window.controller
    action=request.get('action')
    if action not in ('inspect','capture') and window.maintenance.phase()!='ready':
        raise ValueError('Augmentor maintenance is in progress. This request was not started.')
    if action == 'shortcut-settings':
        return shortcut_settings(window, request)
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
                'pinned':bool(window.preferences.values['pinned']),
                'uiScale':window.ui_scale.percent,'width':window.width(),
                'fontPixels':window.brand.font().pixelSize(),'buttonWidth':window.send_button.width(),
                'dialogs':[d.windowTitle() for d in window.findChildren(QDialog) if d.isVisible()]}
    if action=='pin':
        expected=request.get('expected');pinned=request.get('pinned')
        if (type(expected) is not bool or type(pinned) is not bool
                or window.preferences.values['pinned'] is not expected
                or not window.isVisible() or not window.pin_button.isVisible() or not window.pin_button.isEnabled()
                or any(d.isVisible() for d in window.findChildren(QDialog))):
            raise ValueError('Pin proof requires a visible window, exact expected state and no dialogs.')
        if expected!=pinned:
            from PySide6.QtTest import QTest
            QTest.mouseClick(window.pin_button,Qt.MouseButton.LeftButton)
        return {'pinned':bool(window.preferences.values['pinned'])}
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
