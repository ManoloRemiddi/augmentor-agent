# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual DSH approval service plus Qt decisions in the isolated fixture."""
from types import SimpleNamespace
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from augmentor_linux.window import Window
from augmentor_linux.pi_client import ContractError
from dsh.branch import history


def prove(adapter,session,until):
    for button,outcome in [(QMessageBox.StandardButton.No,'rejected'),(QMessageBox.StandardButton.Yes,'allowed-once'),(None,'cancelled')]:
        frames=[];errors=[]
        stream=adapter.stream_type(adapter,session,frames.append,errors.append);stream.start()
        window=Window();answers=[]
        def answer(frame,value):
            answers.append(value);adapter.respond(frame['rpcId'],value)
        window.controller=SimpleNamespace(answer=answer)
        try:
            prior=history(adapter.call,session)
            cursor=prior[-1]['seq']
            adapter.call('session.prompt',{'sessionId':session,'mode':'queue','content':[{'type':'text','text':'native approval fixture '+outcome}]})
            until(lambda:any(f.get('method')=='approval/requested' for f in frames) or errors)
            assert not errors,errors
            frame=next(f for f in frames if f.get('method')=='approval/requested')
            cancellation_errors=[]
            def decide():
                if button is not None:
                    QApplication.activeModalWidget().button(button).click();return
                try:
                    adapter.call('session.cancel',{'sessionId':session})
                    until(lambda:any(f.get('method')=='interaction/resolved' and f.get('rpcId')==frame['rpcId'] for f in frames))
                    window.on_interaction({'method':'interaction/resolved','rpcId':frame['rpcId']})
                except Exception as exc:
                    cancellation_errors.append(str(exc))
                    if QApplication.activeModalWidget():QApplication.activeModalWidget().reject()
            QTimer.singleShot(50,decide)
            watchdog=QTimer();watchdog.setSingleShot(True);watchdog.timeout.connect(lambda:QApplication.activeModalWidget().reject() if QApplication.activeModalWidget() else None);watchdog.start(5000)
            try:window.on_interaction(frame)
            finally:watchdog.stop()
            assert not cancellation_errors,cancellation_errors
            if button is None:
                assert not answers,answers
                try:
                    adapter.respond(frame['rpcId'],{'sessionId':session,'approvalId':frame['rpcId'],'outcome':'allowed-once'})
                    raise AssertionError('Late approval accepted')
                except ContractError:pass
            else:assert len(answers)==1 and answers[0]['outcome']==outcome,answers
            until(lambda:not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==session)['running'])
            events=[e for e in history(adapter.call,session) if e['seq']>cursor]
            asked=[e for e in events if e['type']=='approval/asked']
            decided=[e for e in events if e['type']=='approval/decided']
            assert len(asked)==len(decided)==1,(asked,decided)
            assert asked[0]['data']['id']==decided[0]['data']['id']
            assert decided[0]['data']['outcome']==outcome,decided
            assert any(e['type']=='turn/end' and e['seq']>decided[0]['seq'] for e in events)
            print('Actual DSH approval audit and Qt decision verified: '+outcome,flush=True)
        finally:
            stream.close();window.controller=None;window.close()
