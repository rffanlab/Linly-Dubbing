import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QSlider, QRadioButton, QLineEdit, QPushButton,
                               QFileDialog, QGroupBox)
from PySide6.QtCore import Qt, QUrl

try:
    # 尝试导入媒体相关组件
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

    HAS_MULTIMEDIA = True
except ImportError:
    print("警告: 无法导入Qt多媒体组件，将使用简化版视频播放器")
    HAS_MULTIMEDIA = False


class CustomSlider(QWidget):
    """整数值滑块控件"""

    def __init__(self, minimum, maximum, step, label, value, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.label = QLabel(label)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setSingleStep(step)
        self.slider.setValue(value)

        self.value_label = QLabel(str(value))
        self.slider.valueChanged.connect(self.update_value)

        self.layout.addWidget(self.label)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.value_label)

        self.layout.addLayout(slider_layout)
        self.setLayout(self.layout)

    def update_value(self, value):
        self.value_label.setText(str(value))

    def value(self):
        return self.slider.value()

    def setValue(self, value):
        self.slider.setValue(value)
        self.value_label.setText(str(value))


class FloatSlider(QWidget):
    """浮点值滑块控件"""

    def __init__(self, minimum, maximum, step, label, value, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.step = step

        self.label = QLabel(label)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(minimum / step))
        self.slider.setMaximum(int(maximum / step))
        self.slider.setSingleStep(1)
        self.slider.setValue(int(value / step))

        self.value_label = QLabel(f"{value:.2f}")
        self.slider.valueChanged.connect(self.update_value)

        self.layout.addWidget(self.label)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.value_label)

        self.layout.addLayout(slider_layout)
        self.setLayout(self.layout)

    def update_value(self, value):
        float_value = value * self.step
        self.value_label.setText(f"{float_value:.2f}")

    def value(self):
        return self.slider.value() * self.step

    def setValue(self, value):
        self.slider.setValue(int(value / self.step))
        self.value_label.setText(f"{value:.2f}")


class RadioButtonGroup(QWidget):
    """单选按钮组控件"""

    def __init__(self, options, label, default_value, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.group_box = QGroupBox(label)
        self.button_layout = QVBoxLayout()

        self.buttons = []
        for option in options:
            option_str = str(option) if option is not None else "None"
            radio = QRadioButton(option_str)
            self.buttons.append((option, radio))
            if option == default_value:
                radio.setChecked(True)
            self.button_layout.addWidget(radio)

        self.group_box.setLayout(self.button_layout)
        self.layout.addWidget(self.group_box)
        self.setLayout(self.layout)

    def value(self):
        for option, button in self.buttons:
            if button.isChecked():
                return option
        return None


class AudioSelector(QWidget):
    """音频文件选择控件"""

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.label = QLabel(label)
        self.layout.addWidget(self.label)

        self.file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_file)

        self.file_layout.addWidget(self.file_path)
        self.file_layout.addWidget(self.browse_button)

        self.layout.addLayout(self.file_layout)
        self.setLayout(self.layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg)")
        if file_path:
            self.file_path.setText(file_path)

    def value(self):
        return self.file_path.text() if self.file_path.text() else None


class VideoPlayer(QWidget):
    """简化版视频播放控件，可处理多媒体组件不可用的情况"""

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.video_path = None

        self.label = QLabel(label)
        self.layout.addWidget(self.label)

        # 创建简单的视频状态显示
        self.status_label = QLabel("就绪")

        if HAS_MULTIMEDIA:
            # 如果多媒体组件可用，创建完整播放器
            try:
                # 创建视频部件
                self.video_widget = QVideoWidget()
                self.video_widget.setMinimumHeight(200)  # 设置最小高度确保可见

                # 创建媒体播放器并配置音频输出
                self.media_player = QMediaPlayer()
                self.media_player.setVideoOutput(self.video_widget)

                # 使用音频输出对象控制音量
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)  # 设置音频输出
                self.audio_output.setVolume(0.7)  # 设置默认音量为70%

                # 添加音量控制滑块
                self.volume_slider = QSlider(Qt.Horizontal)
                self.volume_slider.setRange(0, 100)
                self.volume_slider.setValue(70)
                self.volume_slider.setToolTip("音量")
                self.volume_slider.valueChanged.connect(self.set_volume)

                # 创建控制部件
                self.controls_layout = QHBoxLayout()
                self.play_button = QPushButton("播放")
                self.play_button.clicked.connect(self.play_pause)

                # 添加暂停和停止按钮
                self.stop_button = QPushButton("停止")
                self.stop_button.clicked.connect(self.stop_video)

                # 组装控制栏
                self.controls_layout.addWidget(self.play_button)
                self.controls_layout.addWidget(self.stop_button)

                # 添加音量控制
                volume_layout = QHBoxLayout()
                volume_layout.addWidget(QLabel("音量:"))
                volume_layout.addWidget(self.volume_slider)

                self.controls_layout.addLayout(volume_layout)
                self.controls_layout.addWidget(self.status_label)

                self.layout.addWidget(self.video_widget)
                self.layout.addLayout(self.controls_layout)
            except Exception as e:
                print(f"创建视频播放器失败，使用简化版: {e}")
                self._use_simple_player()
        else:
            # 如果多媒体组件不可用，使用简化版播放器
            self._use_simple_player()

        self.setLayout(self.layout)

    def _use_simple_player(self):
        """当无法创建标准视频播放器时使用的简化版"""
        self.video_placeholder = QLabel("视频预览不可用")
        self.video_placeholder.setAlignment(Qt.AlignCenter)
        self.video_placeholder.setStyleSheet("background-color: #222; color: white; min-height: 200px;")

        self.controls_layout = QHBoxLayout()
        self.play_button = QPushButton("播放")
        self.play_button.setEnabled(False)

        self.controls_layout.addWidget(self.play_button)
        self.controls_layout.addWidget(self.status_label)

        self.layout.addWidget(self.video_placeholder)
        self.layout.addLayout(self.controls_layout)

    def set_volume(self, volume):
        """设置音量，仅在多媒体组件可用时有效"""
        if HAS_MULTIMEDIA and hasattr(self, 'audio_output'):
            # 转换音量范围从0-100到0.0-1.0
            self.audio_output.setVolume(volume / 100.0)
            self.status_label.setText(f"音量: {volume}%")

    def set_video(self, path):
        """设置视频源"""
        if not os.path.exists(path):
            self.status_label.setText(f"错误: 文件不存在")
            return

        self.video_path = path
        self.status_label.setText(f"已加载: {os.path.basename(path)}")

        if HAS_MULTIMEDIA and hasattr(self, 'media_player'):
            try:
                # 使用QUrl构建文件路径
                url = QUrl.fromLocalFile(os.path.abspath(path))
                self.media_player.setSource(url)
                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
            except Exception as e:
                self.status_label.setText(f"错误: {str(e)}")
        else:
            # 简化版播放器只更新状态
            if hasattr(self, 'video_placeholder'):
                self.video_placeholder.setText(f"视频已加载: {os.path.basename(path)}\n(预览不可用)")

    def play_pause(self):
        """播放或暂停视频"""
        if not self.video_path:
            self.status_label.setText("错误: 未加载视频")
            return

        if HAS_MULTIMEDIA and hasattr(self, 'media_player'):
            if self.media_player.playbackState() == QMediaPlayer.PlayingState:
                self.media_player.pause()
                self.play_button.setText("播放")
                self.status_label.setText("已暂停")
            else:
                self.media_player.play()
                self.play_button.setText("暂停")
                self.status_label.setText("正在播放")
        else:
            # 简化版播放器只更新状态
            self.status_label.setText("播放功能不可用")

    def stop_video(self):
        """停止视频播放"""
        if HAS_MULTIMEDIA and hasattr(self, 'media_player'):
            self.media_player.stop()
            self.play_button.setText("播放")
            self.status_label.setText("已停止")
        else:
            # 简化版播放器只更新状态
            self.status_label.setText("停止功能不可用")