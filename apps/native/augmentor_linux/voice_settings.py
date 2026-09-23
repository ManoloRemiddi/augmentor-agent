# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local authenticated voice preferences, without starting a conversation or microphone."""
from .instances import current_name
import json
import os
import threading
import urllib.request
import urllib.error
from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QSlider,QGroupBox


def voice_request(path, values=None, raw=False):
    home=Path(os.environ.get('RESONANT_VOICE_HOME',Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'resonant-voice'))
    config=json.loads((home/'config.json').read_text())
    port=config.get('port',8877)
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('Invalid voice service port')
    request=urllib.request.Request(f'http://127.0.0.1:{port}/internal/{path}',data=json.dumps({**(values or {}),'profile':current_name()}).encode(),
        headers={'Content-Type':'application/json','x-resonant-token':(home/'token').read_text().strip()})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            data=response.read(4*1024*1024+1)
            if len(data)>4*1024*1024:raise ValueError('Voice response exceeded its limit')
            return data if raw else json.loads(data)
    except urllib.error.HTTPError as exc:
        try:message=json.loads(exc.read(8192)).get('error','Voice request failed')
        except ValueError:message='Voice request failed'
        raise RuntimeError(message) from None


class VoiceSettingsDialog(QDialog):
    completed=Signal(object,object)

    def __init__(self,window):
        super().__init__(window)
        self.owner=window;self.closing=False;self.voices=[];self.previewing=False
        self.preview_stop=threading.Event();self.saved=None
        self.completed.connect(lambda callback,result:callback(result) if not self.closing else None)
        self.setWindowTitle('Resonant Voice — '+('First agent' if current_name()=='main' else 'Second agent'));self.setMinimumWidth(410)
        from .settings_icons import settings_icon,settings_label
        layout=QVBoxLayout(self);layout.setSpacing(12)
        self.enabled=QCheckBox('Enable Resonant Voice');self.enabled.setChecked(window.preferences.values.get('resonant_voice',True))
        self.enabled.toggled.connect(window.set_voice_enabled);layout.addWidget(self.enabled)
        group=QGroupBox();form=QVBoxLayout(group);form.addWidget(settings_label('Voice','voice',window.accent))
        self.voice=QComboBox();self.voice.setAccessibleName('Speaking voice');form.addWidget(self.voice)
        self.description=QLabel('Loading voices…');self.description.setWordWrap(True);form.addWidget(self.description)
        self.preview=QPushButton('Play voice sample');self.preview.setEnabled(False);self.preview.clicked.connect(self.play_preview);form.addWidget(self.preview)
        layout.addWidget(group)
        playback=QGroupBox();rows=QVBoxLayout(playback);rows.addWidget(settings_label('Playback','playback',window.accent))
        self.speed,self.speed_value=self.slider(rows,'Speaking speed',75,150,100)
        self.volume,self.volume_value=self.slider(rows,'Output volume',0,100,100)
        self.speed.valueChanged.connect(self.refresh_values);self.volume.valueChanged.connect(self.refresh_values)
        layout.addWidget(playback)
        conversation=QGroupBox('Conversation');conversation_rows=QVBoxLayout(conversation)
        self.mode=QComboBox();self.mode.setAccessibleName('Conversation mode')
        self.mode.addItem('Hold or slide to lock','manual');self.mode.addItem('Hands-free conversation','hands-free')
        self.mode.setCurrentIndex(self.mode.findData(window.preferences.values.get('voice_mode','manual')))
        conversation_rows.addWidget(self.mode)
        self.pause,self.pause_value=self.slider(conversation_rows,'Pause before sending',400,2000,window.preferences.values.get('voice_pause_ms',800))
        self.pause.valueChanged.connect(lambda:self.pause_value.setText(f'{self.pause.value()/1000:.2f} s'))
        self.pause_value.setText(f'{self.pause.value()/1000:.2f} s')
        explanation=QLabel('Hands-free: tap to start, speak naturally, pause to send. Speak over a reply to interrupt. Tap or Esc stops the microphone. Longer pauses give you more time to think.');explanation.setWordWrap(True);conversation_rows.addWidget(explanation)
        layout.addWidget(conversation)
        self.note=QLabel('Changes apply to the next spoken reply. Preview uses the speed and volume shown here.');self.note.setWordWrap(True);layout.addWidget(self.note)
        guide=QLabel('Hold to record • Slide left to lock\nClick while locked to send • Esc to cancel\n10-minute maximum • Orange at 8 min • Red at 9 min');guide.setWordWrap(True);layout.addWidget(guide)
        row=QHBoxLayout();reset=QPushButton('Reset playback');reset.clicked.connect(lambda:(self.speed.setValue(100),self.volume.setValue(100)));row.addWidget(reset)
        self.apply=QPushButton('Save');self.apply.setEnabled(False);self.apply.clicked.connect(self.save);row.addWidget(self.apply)
        done=QPushButton('Done');done.clicked.connect(self.accept);row.addWidget(done);layout.addLayout(row)
        for button,name in [(self.preview,'play'),(reset,'recover'),(self.apply,'save'),(done,'done')]:button.setIcon(settings_icon(name,window.accent))
        self.enabled.setIcon(settings_icon('voice',window.accent))
        self.voice.currentIndexChanged.connect(self.selection_changed)
        self.finished.connect(self.finish)
        self.refresh_values();self.work(lambda:voice_request('preferences'),self.loaded)

    def slider(self,layout,name,minimum,maximum,value):
        row=QHBoxLayout();row.addWidget(QLabel(name));label=QLabel();row.addWidget(label,1,Qt.AlignmentFlag.AlignRight);layout.addLayout(row)
        slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(minimum,maximum);slider.setValue(value);slider.setAccessibleName(name);layout.addWidget(slider)
        return slider,label

    def refresh_values(self):
        self.speed_value.setText(f'{self.speed.value()/100:.2f}×');self.volume_value.setText(f'{self.volume.value()}%')
        self.stop_preview()

    def work(self,work,callback):
        def run():
            try:result=(work(),None)
            except Exception as error:result=(None,str(error))
            try:self.completed.emit(callback,result)
            except RuntimeError:pass
        threading.Thread(target=run,daemon=True).start()

    def loaded(self,result):
        data,error=result
        if error:self.note.setText('Voice settings unavailable: '+error);return
        self.saved=data['values'];self.voices=data['voices']
        self.voice.clear()
        for voice in self.voices:self.voice.addItem(voice['name'],voice['id'])
        self.voice.setCurrentIndex(self.voice.findData(self.saved['voiceId']))
        self.speed.setValue(round(self.saved['speed']*100));self.volume.setValue(round(self.saved['volume']*100))
        self.apply.setEnabled(True);self.selection_changed()

    def selection_changed(self,*_):
        self.stop_preview()
        voice=next((v for v in self.voices if v['id']==self.voice.currentData()),None)
        self.description.setText(voice.get('description','') if voice else 'Choose a voice')
        self.preview.setEnabled(bool(voice))

    def values(self):
        return {'voiceId':self.voice.currentData(),'speed':self.speed.value()/100,'volume':self.volume.value()/100}

    def stop_preview(self):
        self.preview_stop.set()

    def play_preview(self):
        if self.previewing:self.stop_preview();return
        voice=getattr(self.owner,'voice_dialog',None)
        if voice and voice.capture:self.note.setText('Finish recording before previewing a voice.');return
        if voice:voice.interrupt()
        self.preview_stop=threading.Event();stop=self.preview_stop;values=self.values()
        self.previewing=True;self.preview.setText('Stop preview');self.note.setText('Loading voice sample…')
        def play():
            pcm=voice_request('preview',values,raw=True)
            if stop.is_set():return
            import sounddevice as sd
            with sd.RawOutputStream(samplerate=24000,channels=1,dtype='int16',blocksize=480) as output:
                for offset in range(0,len(pcm),960):
                    if stop.is_set():break
                    output.write(pcm[offset:offset+960])
        def finished(result):
            _,error=result;self.previewing=False;self.preview.setText('Play voice sample')
            self.note.setText(error or 'Sample finished. Save to use these settings for replies.')
        self.work(play,finished)

    def save(self):
        self.stop_preview();values=self.values();self.apply.setEnabled(False)
        def finished(result):
            data,error=result;self.apply.setEnabled(True)
            if error:self.note.setText(error);return
            self.saved=data['values']
            changed=(self.owner.preferences.values.get('voice_mode','manual')!=self.mode.currentData() or self.owner.preferences.values.get('voice_pause_ms',800)!=self.pause.value())
            if changed and getattr(self.owner,'voice_dialog',None):self.owner.close_voice_panel()
            self.owner.preferences.values['voice_mode']=self.mode.currentData()
            self.owner.preferences.values['voice_pause_ms']=self.pause.value()
            self.owner.preferences.save();self.owner.update_controls()
            self.note.setText('Saved. Tap the voice icon to start.' if changed else 'Saved. These settings apply to the next spoken reply.')
        self.work(lambda:voice_request('preferences',{'values':values}),finished)

    def finish(self,*_):
        self.closing=True;self.stop_preview()

    def closeEvent(self,event):
        self.finish()
        super().closeEvent(event)
