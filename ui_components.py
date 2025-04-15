# ui_components.py (已修正 AudioSelector 缩进错误)

import os
from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QSlider, QRadioButton, QLineEdit, QPushButton,
                               QFileDialog, QGroupBox)
from PySide6.QtCore import Qt, QUrl, Signal, Slot, QFileInfo # 导入 QFileInfo
from PySide6.QtGui import QIcon

# --- 多媒体组件导入和 HAS_MULTIMEDIA 定义 (保持修正后的逻辑) ---
_HAS_MULTIMEDIA_INTERNAL = False
try:
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
    _HAS_MULTIMEDIA_INTERNAL = True
    print("成功导入 Qt Multimedia 组件。")
except ImportError as e:
    print(f"警告: 无法导入 Qt Multimedia 组件 ({e})，视频播放功能将受限。")
    class QVideoWidget(QLabel): pass
    class QMediaPlayer:
        PlayingState=1; PausedState=2; StoppedState=0; NoMedia=0; LoadingMedia=1; LoadedMedia=3; EndOfMedia=6; InvalidMedia=7; ResourceError=1; FormatError=2; NetworkError=3; AccessDeniedError=4; ServiceMissingError=5
        mediaStatusChanged=Signal(int); playbackStateChanged=Signal(int); errorOccurred=Signal(int, str); durationChanged=Signal(int); positionChanged=Signal(int); metaDataChanged=Signal()
        def __init__(self): self._state = self.StoppedState; self._status = self.NoMedia; self._error = 0; self._error_str = ""
        def setSource(self, u): self._status = self.InvalidMedia; self.mediaStatusChanged.emit(self._status); print(f"模拟:设源{u.toString()},预览不可用")
        def play(self): self._state = self.PlayingState; self.playbackStateChanged.emit(self._state); print("模拟:播放(无效)")
        def pause(self): self._state = self.PausedState; self.playbackStateChanged.emit(self._state); print("模拟:暂停(无效)")
        def stop(self): self._state = self.StoppedState; self.playbackStateChanged.emit(self._state); print("模拟:停止(无效)")
        def playbackState(self): return self._state
        def mediaStatus(self): return self._status
        def errorString(self): return self._error_str
        def error(self): return self._error
        def duration(self): return 0
        def position(self): return 0
        def isMetaDataAvailable(self): return False
    class QAudioOutput:
        def __init__(self): self._volume = 0.7
        def setVolume(self, v): self._volume = v; print(f"模拟:设音量{v}")
        def volume(self): return self._volume
HAS_MULTIMEDIA = _HAS_MULTIMEDIA_INTERNAL


# --- 自定义控件 (保持不变) ---
class CustomSlider(QWidget):
    def __init__(self, minimum, maximum, step, label, value, parent=None): super().__init__(parent); self.layout=QVBoxLayout(self); self.layout.setContentsMargins(0,5,0,5); self.label=QLabel(label); self.slider=QSlider(Qt.Horizontal); self.slider.setRange(minimum, maximum); self.slider.setSingleStep(step); self.slider.setValue(value); self.slider.setTickPosition(QSlider.TickPosition.TicksBelow); self.slider.setTickInterval((maximum-minimum)//10 or 1); self.value_label=QLabel(str(value)); self.value_label.setMinimumWidth(30); self.value_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter); self.slider.valueChanged.connect(self.update_value); self.layout.addWidget(self.label); slider_layout=QHBoxLayout(); slider_layout.addWidget(self.slider); slider_layout.addWidget(self.value_label); self.layout.addLayout(slider_layout)
    @Slot(int)
    def update_value(self, value): self.value_label.setText(str(value))
    def value(self): return self.slider.value()
    def setValue(self, value): self.slider.setValue(value)

class FloatSlider(QWidget):
    valueChanged = Signal(float)
    def __init__(self, minimum, maximum, step, label, value, decimals=2, parent=None): super().__init__(parent); self.layout=QVBoxLayout(self); self.layout.setContentsMargins(0,5,0,5); self.step=step; self.decimals=decimals; self._min_int=int(round(minimum/step)); self._max_int=int(round(maximum/step)); self._val_int=int(round(value/step)); self.label=QLabel(label); self.slider=QSlider(Qt.Horizontal); self.slider.setRange(self._min_int, self._max_int); self.slider.setSingleStep(1); self.slider.setValue(self._val_int); self.slider.setTickPosition(QSlider.TickPosition.TicksBelow); self.slider.setTickInterval((self._max_int-self._min_int)//10 or 1); self.value_label=QLabel(f"{value:.{self.decimals}f}"); self.value_label.setMinimumWidth(40); self.value_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter); self.slider.valueChanged.connect(self._update_value_internal); self.layout.addWidget(self.label); slider_layout=QHBoxLayout(); slider_layout.addWidget(self.slider); slider_layout.addWidget(self.value_label); self.layout.addLayout(slider_layout)
    @Slot(int)
    def _update_value_internal(self, int_value): float_value=round(int_value*self.step, self.decimals+1); min_float=self._min_int*self.step; max_float=self._max_int*self.step; float_value=max(min_float, min(max_float, float_value)); formatted_value=f"{float_value:.{self.decimals}f}"; self.value_label.setText(formatted_value); self.valueChanged.emit(float_value)
    def value(self)->float: return round(self.slider.value()*self.step, self.decimals+1)
    def setValue(self, float_value): int_value=int(round(float_value/self.step)); int_value=max(self._min_int, min(self._max_int, int_value)); self.slider.setValue(int_value)

class RadioButtonGroup(QWidget):
    valueChanged = Signal(object)
    def __init__(self, options, label, default_value, parent=None):
        super().__init__(parent); self.layout=QVBoxLayout(self); self.layout.setContentsMargins(0,0,0,0); self.group_box=QGroupBox(label); self.button_layout=QVBoxLayout(); self.button_layout.setSpacing(5); self.buttons={}; self.radio_buttons=[]
        for option in options:
            option_display=str(option) if option is not None else "None"; radio=QRadioButton(option_display)
            self.buttons[radio]=option; self.radio_buttons.append(radio); self.button_layout.addWidget(radio); radio.toggled.connect(self._on_button_toggled)
            if option==default_value: radio.setChecked(True)
        self.group_box.setLayout(self.button_layout); self.layout.addWidget(self.group_box)
    @Slot(bool)
    def _on_button_toggled(self, checked):
        if checked: sender_button=self.sender(); self.valueChanged.emit(self.buttons.get(sender_button))
    def value(self): return next((opt for radio, opt in self.buttons.items() if radio.isChecked()), None)
    def setValue(self, value_to_set): [radio.setChecked(True) for radio, opt in self.buttons.items() if opt==value_to_set]

class AudioSelector(QWidget):
    pathChanged = Signal(str)
    def __init__(self, label, filter="音频文件 (*.mp3 *.wav *.ogg *.aac *.flac *.m4a);;所有文件 (*)", parent=None): super().__init__(parent); self.layout=QVBoxLayout(self); self.layout.setContentsMargins(0,5,0,5); self.filter=filter; self.label=QLabel(label); self.layout.addWidget(self.label); self.file_layout=QHBoxLayout(); self.file_path=QLineEdit(); self.file_path.setPlaceholderText("选择或拖入音频文件"); self.file_path.textChanged.connect(self._emit_path_changed); self.browse_button=QPushButton(); self.browse_button.setIcon(QIcon.fromTheme("document-open", QIcon("icons/folder.png"))); self.browse_button.setToolTip("浏览文件"); self.browse_button.setFixedSize(30, 30); self.browse_button.clicked.connect(self.browse_file); self.file_layout.addWidget(self.file_path); self.file_layout.addWidget(self.browse_button); self.layout.addLayout(self.file_layout); self.setAcceptDrops(True)
    @Slot()
    def browse_file(self): start_dir=os.path.dirname(self.file_path.text()) if os.path.isfile(self.file_path.text()) else os.path.expanduser("~"); file_path,_ = QFileDialog.getOpenFileName(self,"选择音频文件",start_dir,self.filter); self.file_path.setText(os.path.normpath(file_path)) if file_path else None
    def value(self) -> Optional[str]: text=self.file_path.text().strip(); return text if text else None
    def setValue(self, path: Optional[str]): self.file_path.setText(path or "")
    @Slot(str)
    def _emit_path_changed(self, text): self.pathChanged.emit(text.strip())

    # --- 修改点：使用标准 Python 格式编写拖放事件处理 ---
    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            # 只处理第一个 URL，并且必须是本地文件
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                # 使用 QFileInfo 获取后缀，更可靠
                info = QFileInfo(file_path)
                suffix = info.suffix().lower()
                # 检查后缀是否在支持的列表中
                supported_suffixes = ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a']
                if suffix in supported_suffixes:
                    event.acceptProposedAction() # 接受拖放操作

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                info = QFileInfo(file_path)
                suffix = info.suffix().lower()
                supported_suffixes = ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a']
                if suffix in supported_suffixes:
                    self.setValue(os.path.normpath(file_path)) # 设置路径
                    event.acceptProposedAction()
    # --- 结束修改点 ---


class VideoPlayer(QWidget):
    """增强版视频播放控件，处理多媒体状态和错误"""
    videoLoaded = Signal(bool, str)
    def __init__(self, label="视频预览", parent=None):
        super().__init__(parent); self.layout=QVBoxLayout(self); self.video_path=None; self.media_player=None; self.audio_output=None; self.play_button=None; self.stop_button=None; self.volume_slider=None; self.video_widget=None
        self.label=QLabel(label); self.layout.addWidget(self.label); self.status_label=QLabel("就绪"); self.status_label.setWordWrap(True)
        if HAS_MULTIMEDIA:
            try:
                self.video_widget=QVideoWidget(); self.video_widget.setStyleSheet("background-color: black;"); self.video_widget.setMinimumHeight(200)
                self.media_player=QMediaPlayer(); self.media_player.setVideoOutput(self.video_widget)
                self.audio_output=QAudioOutput(); self.media_player.setAudioOutput(self.audio_output); self.audio_output.setVolume(0.7)
                self.play_button=QPushButton(icon=QIcon.fromTheme("media-playback-start", QIcon("icons/play.png")), toolTip="播放/暂停"); self.play_button.setEnabled(False); self.play_button.clicked.connect(self.play_pause)
                self.stop_button=QPushButton(icon=QIcon.fromTheme("media-playback-stop", QIcon("icons/stop.png")), toolTip="停止"); self.stop_button.setEnabled(False); self.stop_button.clicked.connect(self.stop_video)
                self.volume_slider=QSlider(Qt.Horizontal, toolTip="音量"); self.volume_slider.setRange(0, 100); self.volume_slider.setValue(70); self.volume_slider.valueChanged.connect(self.set_volume); volume_label=QLabel("🔊")
                controls_layout=QHBoxLayout(); controls_layout.addWidget(self.play_button); controls_layout.addWidget(self.stop_button); controls_layout.addStretch(); controls_layout.addWidget(volume_label); controls_layout.addWidget(self.volume_slider)
                status_layout=QHBoxLayout(); status_layout.addWidget(self.status_label)
                self.layout.addWidget(self.video_widget, stretch=1); self.layout.addLayout(controls_layout); self.layout.addLayout(status_layout)
                self.media_player.mediaStatusChanged.connect(self.handle_media_status); self.media_player.playbackStateChanged.connect(self.handle_playback_state); self.media_player.errorOccurred.connect(self.handle_error)
            except Exception as e: print(f"创建完整视频播放器失败: {e}"); self._use_simple_player()
        else: self._use_simple_player()
        self.setLayout(self.layout)
    def _use_simple_player(self): self.video_placeholder=QLabel("视频预览不可用\n(Qt多媒体组件缺失或初始化失败)"); self.video_placeholder.setAlignment(Qt.AlignCenter); self.video_placeholder.setStyleSheet("background:#222; color:white; min-height:200px; border-radius:5px;"); self.layout.addWidget(self.video_placeholder, stretch=1); self.layout.addWidget(self.status_label)
    @Slot(QMediaPlayer.MediaStatus)
    def handle_media_status(self, status):
        status_map={QMediaPlayer.NoMedia:"无媒体", QMediaPlayer.LoadingMedia:"加载中...", QMediaPlayer.LoadedMedia:"已加载", QMediaPlayer.StalledMedia:"缓冲中...", QMediaPlayer.BufferingMedia:"缓冲中...", QMediaPlayer.BufferedMedia:"缓冲完成", QMediaPlayer.EndOfMedia:"播放结束", QMediaPlayer.InvalidMedia:"无效媒体"}
        print(f"[VP Debug] MediaStatus: {status_map.get(status, '未知')}")
        if status==QMediaPlayer.LoadedMedia:
            base=os.path.basename(self.video_path or ''); dur=self.media_player.duration(); txt=f"已加载:{base}"
            if dur > 0: s=int((dur/1000)%60); m=int((dur/(1000*60))%60); h=int((dur/(1000*60*60))%24); ts=f"{h:02}:{m:02}:{s:02}" if h>0 else f"{m:02}:{s:02}"; txt+=f" ({ts})"
            self.status_label.setText(txt); self.play_button.setEnabled(True); self.stop_button.setEnabled(True); self.videoLoaded.emit(True,self.video_path)
        elif status==QMediaPlayer.InvalidMedia: err=self.media_player.errorString() or "无效媒体"; self.status_label.setText(f"错误:{err}"); self.play_button.setEnabled(False); self.stop_button.setEnabled(False); self.videoLoaded.emit(False, err)
        elif status==QMediaPlayer.LoadingMedia: self.status_label.setText("加载中..."); self.play_button.setEnabled(False); self.stop_button.setEnabled(False)
        elif status==QMediaPlayer.EndOfMedia: self.status_label.setText("播放结束"); self.stop_video()
        else: self.status_label.setText(status_map.get(status, '处理中...'))
    @Slot(QMediaPlayer.PlaybackState)
    def handle_playback_state(self, state):
        state_map={QMediaPlayer.PlayingState:"正在播放", QMediaPlayer.PausedState:"已暂停", QMediaPlayer.StoppedState:"已停止"}
        print(f"[VP Debug] PlaybackState: {state_map.get(state, '未知')}")
        if not self.play_button: return
        if state==QMediaPlayer.PlayingState: self.play_button.setIcon(QIcon.fromTheme("media-playback-pause", QIcon("icons/pause.png"))); self.status_label.setText("正在播放")
        elif state==QMediaPlayer.PausedState: self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("icons/play.png"))); self.status_label.setText("已暂停")
        elif state==QMediaPlayer.StoppedState:
            self.play_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("icons/play.png")))
            cur=self.status_label.text(); self.status_label.setText("已停止") if "播放结束" not in cur and "已加载" not in cur and "错误" not in cur else None
    @Slot(QMediaPlayer.Error, str)
    def handle_error(self, error, error_string=""):
        err=self.media_player.errorString() or error_string or "未知错误"; print(f"[VP Error] Code:{error}, Msg:{err}"); self.status_label.setText(f"播放错误:{err}")
        if self.play_button: self.play_button.setEnabled(False)
        if self.stop_button: self.stop_button.setEnabled(False)
        self.videoLoaded.emit(False, f"播放错误:{err}")
    @Slot(int)
    def set_volume(self, volume):
        if HAS_MULTIMEDIA and self.audio_output: vol=max(0, min(100, volume))/100.0; self.audio_output.setVolume(vol)
    @Slot(str)
    def set_video(self, path):
        print(f"[VP] set_video: {path}")
        if not path or not isinstance(path, str): self.status_label.setText("错误:无效路径"); self.videoLoaded.emit(False,"无效路径"); return
        if not os.path.exists(path): self.status_label.setText("错误:文件不存在"); print(f"[VP Error] Not found: {path}"); self.videoLoaded.emit(False,f"文件不存在:{path}"); return
        self.video_path=path; abs_path=os.path.abspath(self.video_path); print(f"[VP Debug] Abs path: {abs_path}"); self.status_label.setText(f"准备加载:{os.path.basename(path)}")
        if HAS_MULTIMEDIA and self.media_player:
            url=QUrl.fromLocalFile(abs_path); print(f"[VP Debug] QUrl: {url.toString()}, Valid: {url.isValid()}")
            if not url.isValid(): err="无效URL"; self.status_label.setText(f"错误:{err}"); print(f"[VP Error] {err} for {abs_path}"); self.videoLoaded.emit(False, err); return
            if self.media_player.playbackState()!=QMediaPlayer.StoppedState: self.media_player.stop()
            self.media_player.setSource(url)
        elif hasattr(self, 'video_placeholder'): self.video_placeholder.setText(f"已加载:{os.path.basename(path)}\n(预览不可用)"); self.status_label.setText("预览不可用"); self.videoLoaded.emit(False,"预览不可用")
        else: self.status_label.setText("播放器错误"); self.videoLoaded.emit(False,"播放器未初始化")
    @Slot()
    def play_pause(self):
        if not HAS_MULTIMEDIA or not self.media_player: return
        state=self.media_player.playbackState()
        if state==QMediaPlayer.PlayingState: self.media_player.pause()
        elif state in [QMediaPlayer.PausedState, QMediaPlayer.StoppedState]:
             if self.media_player.mediaStatus() >= QMediaPlayer.MediaStatus.LoadedMedia: self.media_player.play()
             else: self.status_label.setText("媒体未就绪")
    @Slot()
    def stop_video(self):
        if HAS_MULTIMEDIA and self.media_player: self.media_player.stop()
        elif hasattr(self,'status_label'): self.status_label.setText("已停止(无播放)")