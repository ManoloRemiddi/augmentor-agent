# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local authenticated voice preferences, without starting a conversation or microphone."""
from .instances import current_name
import json
import os
import threading
import urllib.request
import urllib.error
from pathlib import Path
from .ui_scale import scaled
from PySide6.QtCore import Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QSlider,QGroupBox,QLineEdit


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


class LocalVoiceSettingsDialog(QDialog):
    completed=Signal(object,object)

    def __init__(self,window):
        super().__init__(window)
        self.owner=window;self.closing=False;self.voices=[];self.previewing=False
        self.preview_stop=threading.Event();self.saved=None
        self.completed.connect(self.finish_work)
        self.setWindowTitle('Resonant Voice — '+('First agent' if current_name()=='main' else 'Second agent'));scaled(self).setMinimumWidth(410)
        from .settings_icons import settings_icon,settings_label
        layout=QVBoxLayout(self);scaled(layout).setSpacing(12)
        self.enabled=QCheckBox('Voice On');self.enabled.setChecked(window.preferences.values.get('resonant_voice',True))
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
        setup=QPushButton('Local installation guide')
        setup.setIcon(settings_icon('connect',window.accent))
        setup.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/ManoloRemiddi/augmentor-agent/blob/main/docs/COMPLETE-INSTALL.md#local-speech')))
        layout.addWidget(setup)
        retry=QPushButton('Check local service again');retry.setIcon(settings_icon('recover',window.accent))
        retry.clicked.connect(lambda:self.work(lambda:voice_request('preferences'),self.loaded));layout.addWidget(retry)

    def slider(self,layout,name,minimum,maximum,value):
        row=QHBoxLayout();row.addWidget(QLabel(name));label=QLabel();row.addWidget(label,1,Qt.AlignmentFlag.AlignRight);layout.addLayout(row)
        slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(minimum,maximum);slider.setValue(value);slider.setAccessibleName(name);layout.addWidget(slider)
        return slider,label

    def refresh_values(self):
        self.speed_value.setText(f'{self.speed.value()/100:.2f}×');self.volume_value.setText(f'{self.volume.value()}%')
        self.stop_preview()

    def finish_work(self,callback,result):
        self.owner.voice_settings_jobs=max(0,getattr(self.owner,'voice_settings_jobs',1)-1)
        if hasattr(self,'provider'):
            self.busy=False
            self.toggle(self.enabled.isChecked())
            self.apply.setEnabled(True)
        if not self.closing:callback(result)

    def work(self,work,callback):
        self.owner.voice_settings_jobs=getattr(self.owner,'voice_settings_jobs',0)+1
        if hasattr(self,'provider'):
            self.busy=True
            for control in (self.provider,self.local,self.cloud,self.apply):control.setEnabled(False)
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


class VoiceSettingsDialog(QDialog):
    """Provider hub remains available even when no local speech system exists."""
    completed=Signal(object,object)

    def __init__(self,window):
        super().__init__(window)
        from .settings_icons import settings_icon
        self.owner=window;self.closing=False;self.busy=False
        self.completed.connect(self.finish_work)
        self.setWindowTitle('Voice');scaled(self).setMinimumWidth(410)
        layout=QVBoxLayout(self)
        self.enabled=QCheckBox('Voice On');self.enabled.setChecked(window.preferences.values.get('resonant_voice',True))
        self.enabled.toggled.connect(self.toggle);layout.addWidget(self.enabled)
        description=QLabel('Voice uses the model selected in Augmentor. Choose where listening and speaking run.')
        description.setWordWrap(True);layout.addWidget(description)
        self.provider=QComboBox();self.provider.setAccessibleName('Voice provider')
        self.provider.addItem('Resonant Voice — local','local');self.provider.addItem('OpenAI GPT-Live — cloud','openai-live')
        layout.addWidget(self.provider)
        self.local=QPushButton('Set up / configure local voice');self.local.clicked.connect(self.configure_local);layout.addWidget(self.local)
        self.cloud=QPushButton('Set up / configure OpenAI GPT-Live');self.cloud.clicked.connect(self.configure_cloud);layout.addWidget(self.cloud)
        self.mode=QComboBox();self.mode.setAccessibleName('Conversation mode')
        self.mode.addItem('Hold or slide to lock','manual');self.mode.addItem('Hands-free conversation','hands-free')
        self.mode.setCurrentIndex(self.mode.findData(window.preferences.values.get('voice_mode','manual')));layout.addWidget(self.mode)
        self.pause=QSlider(Qt.Orientation.Horizontal);self.pause.setRange(400,2000);self.pause.setValue(window.preferences.values.get('voice_pause_ms',800));self.pause.setAccessibleName('Pause before sending')
        self.pause_label=QLabel();layout.addWidget(self.pause_label);layout.addWidget(self.pause)
        self.pause.valueChanged.connect(lambda value:self.pause_label.setText(f'Pause before sending: {value/1000:.2f} s'))
        self.pause_label.setText(f'Pause before sending: {self.pause.value()/1000:.2f} s')
        self.note=QLabel('Checking voice configuration…');self.note.setWordWrap(True);layout.addWidget(self.note)
        self.apply=QPushButton('Save');self.apply.clicked.connect(self.save);layout.addWidget(self.apply)
        done=QPushButton('Done');done.clicked.connect(self.accept);layout.addWidget(done)
        for button,name in [(self.local,'connect'),(self.cloud,'connect'),(self.apply,'save'),(done,'done')]:button.setIcon(settings_icon(name,window.accent))
        self.provider.currentIndexChanged.connect(self.provider_changed)
        self.finished.connect(lambda *_:self.finish())
        self.work(self.read_status,self.loaded)
        self.toggle(self.enabled.isChecked())

    def read_status(self):
        from .voice_provider import snapshot
        return snapshot()

    def finish_work(self,callback,result):
        self.owner.voice_settings_jobs=max(0,getattr(self.owner,'voice_settings_jobs',1)-1)
        if hasattr(self,'provider'):
            self.busy=False
            self.toggle(self.enabled.isChecked())
            self.apply.setEnabled(True)
        if not self.closing:callback(result)

    def work(self,work,callback):
        self.owner.voice_settings_jobs=getattr(self.owner,'voice_settings_jobs',0)+1
        if hasattr(self,'provider'):
            self.busy=True
            for control in (self.provider,self.local,self.cloud,self.apply):control.setEnabled(False)
        def run():
            try:result=(work(),None)
            except Exception as error:result=(None,str(error))
            try:self.completed.emit(callback,result)
            except RuntimeError:pass
        threading.Thread(target=run,daemon=True).start()

    def loaded(self,result):
        data,error=result
        if error:self.note.setText(error);return
        self.provider.blockSignals(True);self.provider.setCurrentIndex(self.provider.findData(data['provider']));self.provider.blockSignals(False)
        self.note.setText('Voice is ready.' if data['configured'] else data.get('audioError') or 'Voice needs setup. Configure the selected provider below.')
        self.owner.voice_configuration=data
        self.owner.update_controls()

    def toggle(self,enabled):
        self.owner.set_voice_enabled(enabled)
        for control in (self.provider,self.local,self.cloud,self.mode,self.pause,self.pause_label):
            control.setEnabled(enabled and not self.busy);control.setVisible(enabled)

    def provider_changed(self,*_):
        self.owner.close_voice_panel()
        from .voice_provider import select_provider
        provider=self.provider.currentData()
        self.work(lambda:select_provider(provider),self.loaded)

    def show_configuration(self,dialog_type):
        panel=getattr(self.owner,'settings_panel',None)
        if panel is not None and hasattr(panel,'open_editor'):
            panel.open_editor('Voice',lambda:dialog_type(self.owner))
            return True
        dialog_type(self.owner).exec()
        return False

    def configure_local(self):
        self.owner.close_voice_panel()
        from .voice_provider import select_provider
        def show(result):
            self.loaded(result)
            if result[1]:return
            if self.show_configuration(LocalVoiceSettingsDialog):return
            self.mode.setCurrentIndex(self.mode.findData(self.owner.preferences.values['voice_mode']))
            self.pause.setValue(self.owner.preferences.values['voice_pause_ms'])
            self.work(self.read_status,self.loaded)
        self.work(lambda:select_provider('local'),show)

    def configure_cloud(self):
        self.owner.close_voice_panel()
        from .voice_provider import select_provider
        def show(result):
            self.loaded(result)
            if result[1]:return
            if self.show_configuration(CloudVoiceSettingsDialog):return
            self.work(self.read_status,self.loaded)
        self.work(lambda:select_provider('openai-live'),show)

    def save(self):
        self.owner.close_voice_panel()
        self.owner.preferences.values['voice_mode']=self.mode.currentData()
        self.owner.preferences.values['voice_pause_ms']=self.pause.value()
        self.owner.preferences.save()
        self.provider_changed()

    def finish(self):self.closing=True

    def closeEvent(self,event):
        self.finish();super().closeEvent(event)


class CloudVoiceSettingsDialog(QDialog):
    completed=Signal(object,object)

    def __init__(self,window):
        super().__init__(window)
        from .voice_provider import load_config, usage_receipt, VOICES
        self.owner=window;self.closing=False;self.busy=False;self.completed.connect(self.loaded)
        self.setWindowTitle('OpenAI GPT-Live setup');scaled(self).setMinimumWidth(410)
        layout=QVBoxLayout(self)
        note=QLabel('OpenAI processes microphone audio and supplied context. Voice costs $0.05/minute ($3/hour), including silence, plus your selected model’s costs. Test and save opens a short billed session without recording.');note.setWordWrap(True);layout.addWidget(note)
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText('OpenAI project API key');self.key.setAccessibleName('OpenAI Voice API key');layout.addWidget(self.key)
        self.voice=QComboBox();self.voice.setAccessibleName('OpenAI speaking voice')
        for voice in VOICES:self.voice.addItem(voice.capitalize(),voice)
        self.voice.setCurrentIndex(self.voice.findData(load_config()['cloudVoice']));layout.addWidget(self.voice)
        self.consent=QCheckBox('I agree to cloud audio processing and API duration charges');layout.addWidget(self.consent)
        receipt=usage_receipt()
        receipt_note=(' Last session: '+(str(receipt['seconds'])+' seconds' if receipt['seconds'] is not None else 'duration unknown')+(' (API confirmed).' if receipt['confirmed'] else ' (final API usage unconfirmed).')) if receipt else ''
        self.note=QLabel('The key is stored in your operating system’s credential vault.'+receipt_note);self.note.setWordWrap(True);layout.addWidget(self.note)
        self.apply=QPushButton('Test and save');self.apply.clicked.connect(self.save);layout.addWidget(self.apply)
        self.remove_button=QPushButton('Remove saved API key');self.remove_button.clicked.connect(self.remove);layout.addWidget(self.remove_button)
        done=QPushButton('Done');done.clicked.connect(self.accept);layout.addWidget(done)
        from .settings_icons import settings_icon
        for button,name in [(self.apply,'save'),(self.remove_button,'recover'),(done,'done')]:button.setIcon(settings_icon(name,window.accent))
        self.finished.connect(lambda *_:self.finish())

    def work(self,operation):
        if self.busy:return
        self.busy=True
        self.owner.voice_settings_jobs=getattr(self.owner,'voice_settings_jobs',0)+1
        for control in (self.apply,self.remove_button,self.key,self.voice,self.consent):control.setEnabled(False)
        def run():
            try:result=(operation(),None)
            except Exception as error:result=(None,str(error))
            try:self.completed.emit(*result)
            except RuntimeError:pass
        threading.Thread(target=run,daemon=True).start()

    def save(self):
        from .voice_provider import configure_cloud
        key=self.key.text();voice=self.voice.currentData();consent=self.consent.isChecked()
        self.key.clear();self.note.setText('Checking OpenAI GPT-Live access…')
        self.work(lambda:configure_cloud(key,voice,consent))

    def remove(self):
        from .voice_provider import remove_cloud
        self.work(remove_cloud)

    def loaded(self,data,error):
        self.owner.voice_settings_jobs=max(0,getattr(self.owner,'voice_settings_jobs',1)-1)
        self.busy=False
        if self.closing:return
        for control in (self.apply,self.remove_button,self.key,self.voice,self.consent):control.setEnabled(True)
        self.apply.setEnabled(True);self.note.setText(error or (data.get('audioError') or ('OpenAI Voice configured.' if data.get('cloudVerified') else 'Saved API key removed.')))

    def finish(self):self.closing=True;self.key.clear()

    def closeEvent(self,event):
        self.finish();super().closeEvent(event)
