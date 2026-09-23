# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Native orb, searchable catalog, and appearance surfaces."""
import math
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QSize, QPointF, QEvent
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QDialog, QColorDialog, QLineEdit, QListWidget, QListWidgetItem, QComboBox, QSlider, QCheckBox, QButtonGroup, QStyle, QFileDialog, QInputDialog, QMessageBox, QScrollArea)
from .preferences import DEFAULTS
from .icons import theme_icon


def model_sections(catalog, query=''):
    groups = catalog.get('groups', [])
    entries = {m['provider'] + '/' + m['model']: (g, m) for g in groups for m in g.get('models', [])}
    pinned, seen = [], set()
    for key in catalog.get('pinned', []):
        if key in entries and key not in catalog.get('hidden', []) and key not in seen:
            pinned.append(entries[key]); seen.add(key)
    query = query.strip().casefold()
    def matches(g, m):
        return query in ' '.join([m['name'], m['model'], g['name'], g['provider']]).casefold()
    result = [('Pinned', [m for g,m in pinned if matches(g,m)])]
    for g in groups:
        rows = [m for m in g.get('models', []) if m['provider'] + '/' + m['model'] not in seen and m['provider'] + '/' + m['model'] not in catalog.get('hidden', []) and matches(g,m)]
        result.append((g['name'], rows))
    return [(name, rows) for name, rows in result if rows]


class ModelPicker(QPushButton):
    refresh_requested = Signal()
    selected = Signal(dict)
    pin_requested = Signal(dict, bool)

    def __init__(self, parent=None):
        super().__init__('Choose a model  ▾', parent)
        self.catalog = {'groups': []}
        self.selection = None
        self.popup = None
        self.setAccessibleName('Search and select a model')
        self.clicked.connect(self.open_picker)

    def count(self):
        return sum(len(g['models']) for g in self.catalog.get('groups', []))

    def currentData(self):
        return self.selection

    def set_catalog(self, catalog, preferred=None):
        self.catalog = catalog
        wanted = preferred or self.selection or catalog.get('default') or {}
        rows = [m for g in catalog.get('groups', []) for m in g['models']]
        selection = next((m for m in rows if all(m.get(k) == wanted.get(k) for k in ('provider','model'))), None)
        # Catalog refresh never silently substitutes an unavailable selection.
        if selection is None and not self.selection and not preferred:
            visible = [m for m in rows if m['provider']+'/'+m['model'] not in catalog.get('hidden', [])]
            selection = next((m for m in visible if m.get('location') == 'Local'), visible[0] if visible else None)
        self.selection = selection or (wanted if wanted.get('model') else None)
        self.refresh_label()
        if self.popup and self.popup.isVisible():
            self.render_rows()

    def refresh_label(self):
        if self.selection:
            text = self.selection.get('name', self.selection['model'])
            self.setText(self.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,max(50,self.width()-20)) + '  ▾')
            self.setToolTip(f"{self.selection['provider']} / {self.selection['model']} · {self.selection.get('location', 'Harness route')}")
        else:
            self.setText('Choose a model  ▾')

    def resizeEvent(self,event):
        super().resizeEvent(event);self.refresh_label()

    def choose(self, item):
        selection = item.data(Qt.ItemDataRole.UserRole)
        if not selection:
            return
        self.selection = selection
        self.refresh_label()
        self.selected.emit(selection)
        self.popup.accept()

    def open_picker(self):
        self.popup = QDialog(self.window())
        self.popup.setWindowTitle('Models')
        self.popup.setMinimumSize(420, 520)
        layout = QVBoxLayout(self.popup)
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search models or providers…')
        self.search.setClearButtonEnabled(True)
        row.addWidget(self.search)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh_requested.emit)
        row.addWidget(refresh); layout.addLayout(row)
        self.rows = QListWidget()
        self.rows.itemClicked.connect(self.choose)
        self.rows.itemActivated.connect(self.choose)
        self.rows.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rows.customContextMenuRequested.connect(self.pin_menu)
        layout.addWidget(self.rows)
        self.footer = QLabel()
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)
        self.search.textChanged.connect(self.render_rows)
        self.render_rows(); self.search.setFocus()
        self.refresh_requested.emit()
        self.popup.exec()

    def pin_menu(self, point):
        from PySide6.QtWidgets import QMenu
        item=self.rows.itemAt(point)
        model=item.data(Qt.ItemDataRole.UserRole) if item else None
        if not model:return
        pinned=model['provider']+'/'+model['model'] in self.catalog.get('pinned',[])
        menu=QMenu(self.rows);action=menu.addAction('Unpin model' if pinned else 'Pin model')
        if menu.exec(self.rows.mapToGlobal(point))==action:self.pin_requested.emit(model,not pinned)

    def render_rows(self):
        self.rows.clear()
        sections = model_sections(self.catalog, self.search.text())
        count = 0
        for group, rows in sections:
            heading = QListWidgetItem(group.upper())
            heading.setFlags(Qt.ItemFlag.NoItemFlags)
            font = heading.font(); font.setBold(True); font.setPointSize(9); heading.setFont(font)
            self.rows.addItem(heading)
            for model in rows:
                selected = self.selection and all(model[k] == self.selection.get(k) for k in ('provider','model'))
                item = QListWidgetItem(('✓  ' if selected else '    ') + model['name'] + '  ·  ' + model.get('location',model['provider']) + (' · needs credentials' if model.get('available') is False else ''))
                item.setData(Qt.ItemDataRole.UserRole, model)
                item.setToolTip(model['provider'] + ' / ' + model['model'])
                self.rows.addItem(item); count += 1
        self.footer.setText(f'{count} models · Pins follow the selected harness settings.' if count else 'No matching models. Try another search or refresh.')


class Orb(QWidget):
    expand_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.effect = "plasma"
        self.scenic = False
        self.background_image = ""
        self.dark = True
        self.phase = 0.0
        self.active = False
        self.animated = True
        self.accent = QColor('#a8dfce')
        self.background = QColor(19,35,39,220)
        self.label = QLabel('AUGMENTOR', self)
        self.label.setGeometry(34,46,140,20);self.label.hide()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet('font-size: 10px; letter-spacing: 2px; background: transparent;')
        self.activity = QLabel('Ready', self)
        self.activity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activity.setWordWrap(True)
        self.activity.setGeometry(31,72,146,47)
        self.activity.setStyleSheet('font-size: 10px; font-weight: bold; background: transparent;')
        self.model = QLabel('Pi', self)
        self.model.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.model.setGeometry(37,120,134,18);self.model.hide()
        self.model.setStyleSheet('font-size: 9px; background: transparent;')
        self.expand = QPushButton('↗',self)
        self.expand.setGeometry(60,146,40,27)
        self.expand.setToolTip('Expand conversation')
        self.expand.setAccessibleName('Expand conversation')
        self.expand.clicked.connect(self.expand_requested.emit)
        self.stop = QPushButton('■',self)
        self.stop.setGeometry(108,146,40,27)
        self.stop.setToolTip('Stop current turn')
        self.stop.setAccessibleName('Stop current turn')
        self.stop.clicked.connect(self.stop_requested.emit)
        self.stop.setEnabled(False)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)

    def tick(self):
        self.phase += .055 if self.active else .025
        self.update()

    def set_activity(self, text, active=False, model=''):
        self.active = active
        short = text.split(' · ')[0]
        self.activity.setText(short[:52])
        self.activity.setToolTip(text)
        self.stop.setEnabled(active)
        self.model.setText(self.model.fontMetrics().elidedText(model, Qt.TextElideMode.ElideRight, 134))
        self.model.setToolTip(model)

    def set_animated(self, enabled):
        self.animated = enabled
        if enabled and self.isVisible(): self.timer.start()
        else: self.timer.stop()
        self.update()

    def showEvent(self, event):
        if self.animated: self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def resizeEvent(self,event):
        cx=self.width()//2;cy=self.height()//2
        self.activity.setGeometry(cx-40,cy-24,80,26)
        self.expand.setGeometry(cx-28,cy+8,26,24);self.stop.setGeometry(cx+2,cy+8,26,24)
        for button in (self.expand,self.stop):button.setStyleSheet('QPushButton {padding:0;border:0;border-radius:6px;font-size:12px;}')
        super().resizeEvent(event)

    def wave_path(self):
        path = QPainterPath()
        amplitude = (5 if self.active else 2.5) if self.effect == "plasma" else 0
        phase = self.phase if self.animated else 0
        for i in range(181):
            angle = i * math.tau / 180
            radius = 86 + amplitude * math.sin(5 * angle + phase) + 1.7 * math.sin(9 * angle - 1.5 * phase)
            x, y = 104 + radius * math.cos(angle), 104 + radius * math.sin(angle)
            if i == 0: path.moveTo(x,y)
            else: path.lineTo(x,y)
        path.closeSubpath()
        return path

    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width()/208,self.height()/208)
        path=self.wave_path()
        for width, alpha in ([(16,12),(10,24),(5,45)] if self.effect == "plasma" else []):
            color=QColor(self.accent);color.setAlpha(alpha)
            p.setPen(QPen(color,width));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(path)
        gradient=QRadialGradient(94,75,125)
        inside=QColor(self.background);inside=inside.lighter(125)
        gradient.setColorAt(0,inside);gradient.setColorAt(1,self.background)
        p.setBrush(gradient);p.setPen(QPen(self.accent,1.5));p.drawPath(path)
        if self.scenic:
            from .scenery import paint_landscape
            paint_landscape(p,QRectF(18,18,172,172),self.dark,radius=86,encoded=self.background_image,tint=self.background)
        elif self.effect in ("butterflies", "butterflies-large"):
            from .nature import paint_foliage
            p.setClipPath(path);paint_foliage(p,QRectF(20,20,168,168),self.accent)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.expand_requested.emit()


class ColourSlider(QSlider):
    """Click a colour directly or drag the thumb; keyboard controls stay native."""
    def pick(self,event):
        position=round(event.position().x())-9
        self.setSliderPosition(QStyle.sliderValueFromPosition(self.minimum(),self.maximum(),position,max(1,self.width()-18)))

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.setFocus();self.setSliderDown(True);self.pick(event);event.accept()
        else:super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self.isSliderDown():self.pick(event);event.accept()
        else:super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.isSliderDown():
            self.pick(event);self.setSliderDown(False);event.accept()
        else:super().mouseReleaseEvent(event)


class AppearanceDialog(QDialog):
    changed = Signal(dict)

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Colors & skins')
        self.setMinimumWidth(350)
        from copy import deepcopy
        self.values = deepcopy(values)
        outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content=QWidget();content.setObjectName('appearanceControls');scroll.setWidget(content);outer.addWidget(scroll)
        layout=QVBoxLayout(content);layout.setSpacing(8);self.controls_layout=layout
        self.resize(430,740)
        self.skin_picker=QComboBox();self.skin_picker.setAccessibleName('Skin')
        layout.addWidget(QLabel('Skin'));layout.addWidget(self.skin_picker)
        self.reload_skins();self.skin_picker.activated.connect(self.select_skin)
        row=QHBoxLayout()
        for title,callback in [('Save as…',self.save_skin),('Import…',self.import_skin),('Export…',self.export_skin)]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        layout.addLayout(row)
        self.effect_picker=QComboBox();self.effect_picker.setAccessibleName('Activity effect')
        for title,key in [('Plasma & flares','plasma'),('Butterfly glitter','butterflies'),('Butterflies · 3× larger','butterflies-large'),('None','none')]:self.effect_picker.addItem(title,key)
        self.effect_picker.setCurrentIndex(self.effect_picker.findData(values.get('effect','plasma')))
        self.effect_picker.currentIndexChanged.connect(lambda _:self.change('effect',self.effect_picker.currentData()))
        layout.addWidget(QLabel('Activity effect'));layout.addWidget(self.effect_picker)
        self.background_picker=QComboBox();self.background_picker.setAccessibleName('Background')
        self.background_picker.addItem('Plain','none');self.background_picker.addItem('Blossom lake','blossom-lake')
        if values.get('background')=='uploaded':self.background_picker.addItem('Uploaded image','uploaded')
        self.background_picker.setCurrentIndex(self.background_picker.findData(values.get('background','none')))
        self.background_picker.currentIndexChanged.connect(lambda _:self.change('background',self.background_picker.currentData()))
        layout.addWidget(QLabel('Background'));layout.addWidget(self.background_picker)
        upload=QPushButton('Upload background…');upload.clicked.connect(self.upload_background);layout.addWidget(upload)
        theme_row=QHBoxLayout();theme_row.addWidget(QLabel('Theme'));theme_row.addStretch()
        self.theme_group=QButtonGroup(self);self.theme_buttons={}
        for mode in ('light','dark'):
            button=QPushButton();button.setCheckable(True);button.setChecked(values['theme']==mode)
            button.setFixedSize(38,30);button.setIconSize(QSize(18,18))
            button.setToolTip(mode.title()+' mode');button.setAccessibleName(mode.title()+' mode')
            button.clicked.connect(lambda checked,m=mode:self.change('theme',m))
            self.theme_group.addButton(button);self.theme_buttons[mode]=button;theme_row.addWidget(button)
        layout.addLayout(theme_row)
        self.sliders={}
        for key,title,lo,hi in [('hue','Panel colour',0,359),('brightness','Panel brightness',-15,15),('accent_hue','Accent colour',0,359),('accent_brightness','Accent brightness',-15,15),('saturation','Theme saturation',0,100),('opacity','Opacity',35,100)]:
            label=QLabel(title);layout.addWidget(label)
            slider=ColourSlider(Qt.Orientation.Horizontal);slider.setRange(lo,hi);slider.setValue(values[key]);slider.setFixedHeight(24)
            slider.setAccessibleName(title);layout.addWidget(slider);self.sliders[key]=slider
            slider.valueChanged.connect(lambda v,k=key,l=label,t=title:self.change_slider(k,v,l,t))
            label.setText(f'{title} · {values[key]}' + ('%' if key in ('opacity','saturation') else ''))
        from .markdown import FORMAT_LABELS, FORMAT_ROLES
        row=QHBoxLayout();self.format_role=QComboBox()
        for label,role in zip(FORMAT_LABELS,FORMAT_ROLES):self.format_role.addItem(label,role)
        self.format_role.setAccessibleName('Formatting colour category');row.addWidget(self.format_role)
        colour=QPushButton('Choose colour…');colour.clicked.connect(self.choose_format_colour);row.addWidget(colour)
        layout.addWidget(QLabel('Formatting colours'));layout.addLayout(row)
        self.flares=QCheckBox('Show activity effects');self.flares.setChecked(values.get('flares',True));layout.addWidget(self.flares)
        self.flares.toggled.connect(lambda value:self.change('flares',value))
        self.animate=QCheckBox('Animate activity effects');self.animate.setChecked(values['animation']);layout.addWidget(self.animate)
        self.animate.toggled.connect(lambda value:self.change('animation',value))
        buttons=QHBoxLayout();reset=QPushButton('Reset');buttons.addWidget(reset);reset.clicked.connect(self.reset)
        close=QPushButton('Done');buttons.addWidget(close);close.clicked.connect(self.accept);layout.addLayout(buttons)
        self.refresh_colours()

    def choose_format_colour(self):
        from .markdown import format_defaults
        role=self.format_role.currentData();saved=self.values.get('format_colours',{})
        value=saved.get(role,format_defaults(self.values['theme'])[role])
        colour=QColorDialog.getColor(QColor(value),self,'Choose '+self.format_role.currentText().lower())
        if colour.isValid():self.change('format_colours',{**saved,role:colour.name()})

    def refresh_colours(self):
        v=self.values;dark=v['theme']=='dark'
        panel=QColor.fromHslF(v['hue']/360,v.get('saturation',48)/100*.5625,max(.025,min(.99,(.12 if dark else .92)+v['brightness']/150)))
        accent=QColor.fromHslF(v['accent_hue']/360,v.get('saturation',48)/100,max(.15,min(.9,(.73 if dark else .30)+v['accent_brightness']/150)))
        for mode,button in self.theme_buttons.items():
            selected=mode==v['theme'];button.setChecked(selected)
            button.setIcon(theme_icon(mode,panel.name() if selected else ('#edf3f3' if dark else '#152b2c')))
            button.setStyleSheet(f'QPushButton {{padding:0;border:1px solid {accent.name()};border-radius:7px;background:{accent.name() if selected else "transparent"};}}')
        hue_stops=','.join(f'stop:{i/6:.4f} {QColor.fromHslF((i/6)%1,.80,.55).name()}' for i in range(7))
        for key,slider in self.sliders.items():
            if key in ('hue','accent_hue'):stops=hue_stops
            elif key=='saturation':stops=f"stop:0 #999999,stop:1 {QColor.fromHslF(v['accent_hue']/360,1,.5).name()}"
            elif key=='opacity':stops=f'stop:0 rgba(127,150,150,60),stop:1 {accent.name()}'
            else:stops='stop:0 #232326,stop:1 #ffffff'
            slider.setStyleSheet(f"""
              QSlider::groove:horizontal {{height:10px;border-radius:5px;margin:0 8px;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,{stops});}}
              QSlider::handle:horizontal {{width:14px;margin:-4px -7px;background:#ffffff;border:2px solid #63716f;border-radius:9px;}}
            """)

    def change_slider(self,key,value,label,title):
        label.setText(f'{title} · {value}' + ('%' if key in ('opacity','saturation') else ''));self.change(key,value)

    def change(self,key,value):
        if key=='background' and value!='uploaded':
            self.values['background_image']=''
            index=self.background_picker.findData('uploaded')
            if index>=0:
                self.background_picker.blockSignals(True);self.background_picker.removeItem(index);self.background_picker.blockSignals(False)
        self.values[key]=value;self.values['skin_name']='Custom';self.skin_picker.setCurrentIndex(0)
        self.changed.emit(dict(self.values));self.refresh_colours()

    def reload_skins(self):
        from .skins import BUILTINS, skin_document
        self.skin_picker.clear();self.skin_picker.addItem('Custom',None)
        for name,appearance in BUILTINS.items():self.skin_picker.addItem(name,skin_document(name,appearance))
        for document in self.values.get('custom_skins',[]):self.skin_picker.addItem(document['name']+' (saved)',document)
        for i in range(1,self.skin_picker.count()):
            document=self.skin_picker.itemData(i)
            if document['name']==self.values.get('skin_name'):
                self.skin_picker.setCurrentIndex(i)

    def select_skin(self,index):
        document=self.skin_picker.itemData(index)
        if document:self.apply_skin(document)

    def apply_skin(self,document):
        from copy import deepcopy
        self.values.update(deepcopy(document['appearance']));self.values['skin_name']=document['name']
        for key,slider in self.sliders.items():
            slider.blockSignals(True);slider.setValue(self.values[key]);slider.blockSignals(False)
            label=self.controls_layout.itemAt(self.controls_layout.indexOf(slider)-1).widget()
            title=slider.accessibleName();label.setText(f'{title} · {self.values[key]}' + ('%' if key in ('opacity','saturation') else ''))
        for widget,value in [(self.flares,self.values['flares']),(self.animate,self.values['animation'])]:
            widget.blockSignals(True);widget.setChecked(value);widget.blockSignals(False)
        self.effect_picker.blockSignals(True);self.effect_picker.setCurrentIndex(self.effect_picker.findData(self.values['effect']));self.effect_picker.blockSignals(False)
        self.background_picker.blockSignals(True)
        self.background_picker.clear();self.background_picker.addItem('Plain','none');self.background_picker.addItem('Blossom lake','blossom-lake')
        if self.values.get('background')=='uploaded':self.background_picker.addItem('Uploaded image','uploaded')
        self.background_picker.setCurrentIndex(self.background_picker.findData(self.values.get('background','none')));self.background_picker.blockSignals(False)
        self.reload_skins();self.refresh_colours();self.changed.emit(dict(self.values))

    def remember_skin(self,document):
        from .skins import BUILTINS
        if document['name'] in BUILTINS:raise ValueError('Choose a different name from the built-in skins.')
        skins=self.values.get('custom_skins',[])
        if any(s['name']==document['name'] for s in skins):raise ValueError('A saved skin already has this name. Choose another name.')
        if len(skins)>=100:raise ValueError('The library holds up to 100 skins.')
        self.values['custom_skins']=[*skins,document];self.apply_skin(document)

    def upload_background(self):
        from .backgrounds import upload_background
        from .skins import skin_document
        path,_=QFileDialog.getOpenFileName(self,'Upload background','','Images (*.png *.jpg *.jpeg *.webp)')
        if not path:return
        try:
            appearance={**self.values,**upload_background(path,self.values['theme']=='dark')}
            self.apply_skin(skin_document('Custom',appearance))
        except (OSError,ValueError) as error:QMessageBox.warning(self,'Cannot use background',str(error))

    def save_skin(self):
        from .skins import skin_document
        name,ok=QInputDialog.getText(self,'Save skin','Name for your skin')
        if not ok:return
        try:self.remember_skin(skin_document(name,self.values))
        except ValueError as error:QMessageBox.warning(self,'Cannot save skin',str(error))

    def import_skin(self):
        from .skins import read_skin
        path,_=QFileDialog.getOpenFileName(self,'Import skin','','Augmentor skin (*.json)')
        if not path:return
        try:
            from .skins import BUILTINS, validate_skin
            document=read_skin(path)
            existing=set(BUILTINS) | {s['name'] for s in self.values.get('custom_skins',[])}
            if document['name'] in existing:
                name,ok=QInputDialog.getText(self,'Name imported skin','This name already exists. Choose a new name:',text=document['name']+' copy')
                if not ok:return
                document=validate_skin({**document,'name':name})
            self.remember_skin(document)
        except (OSError,ValueError) as error:QMessageBox.warning(self,'Cannot import skin',str(error))

    def export_skin(self):
        from .skins import write_skin
        path,_=QFileDialog.getSaveFileName(self,'Export skin','my-skin.augmentor-skin.json','Augmentor skin (*.json)')
        if not path:return
        if not path.lower().endswith('.json'):path+='.json'
        try:write_skin(path,self.values.get('skin_name','Custom'),self.values)
        except (OSError,ValueError) as error:QMessageBox.warning(self,'Cannot export skin',str(error))

    def reset(self):
        from .skins import BASE, skin_document
        self.apply_skin(skin_document('Futuristic',BASE))


class MorphSurface(QWidget):
    """Shrink content about the selected control, not the snapshot's centre."""
    def __init__(self,parent,snapshot,source_anchor,fixed_anchor,orb_snapshot=None):
        super().__init__(parent);self.snapshot=snapshot;self.progress=0.
        self.source_anchor=source_anchor;self.fixed_anchor=fixed_anchor;self.orb_snapshot=orb_snapshot
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(parent.rect())

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        anchor=self.mapFromGlobal(self.fixed_anchor)
        ratio=self.snapshot.devicePixelRatioF();width=self.snapshot.width()/ratio;height=self.snapshot.height()/ratio
        end=104/max(width,height) if self.orb_snapshot is not None else max(self.parent().expanded_size.width(),self.parent().expanded_size.height())/104
        scale=1+(end-1)*self.progress
        target=QRectF(anchor.x()-self.source_anchor.x()*scale,anchor.y()-self.source_anchor.y()*scale,width*scale,height*scale)
        painter.setOpacity(1-self.progress);painter.drawPixmap(target,self.snapshot,QRectF(self.snapshot.rect()))
        if self.orb_snapshot is not None:
            painter.setOpacity(self.progress)
            painter.drawPixmap(QRectF(anchor.x()-51,anchor.y()-51,104,104),self.orb_snapshot,QRectF(self.orb_snapshot.rect()))


class TitleEditor(QLineEdit):
    """An inline title field; leaving it or pressing Escape cancels the edit."""
    cancelled = Signal()

    def event(self,event):
        if event.type()==QEvent.Type.ShortcutOverride and event.key()==Qt.Key.Key_Escape:
            event.accept();return True
        return super().event(event)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            self.cancelled.emit();event.accept();return
        super().keyPressEvent(event)

    def focusOutEvent(self,event):
        super().focusOutEvent(event)
        self.cancelled.emit()
