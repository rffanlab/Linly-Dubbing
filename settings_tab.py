import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
                               QPushButton, QMessageBox, QSplitter, QComboBox,
                               QFormLayout, QFileDialog, QLineEdit)
from PySide6.QtCore import Qt, Signal

from ui_components import (CustomSlider, FloatSlider, AudioSelector, VideoPlayer)


class FolderSelector(QWidget):
    """文件夹选择组件"""

    def __init__(self, default_path="videos", parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 创建路径输入框
        self.path_edit = QLineEdit(default_path)

        # 创建浏览按钮
        self.browse_button = QPushButton("选择...")
        self.browse_button.clicked.connect(self.browse_folder)

        # 添加到布局
        self.layout.addWidget(self.path_edit, 1)  # 1是拉伸因子，使输入框占据更多空间
        self.layout.addWidget(self.browse_button)

        self.setLayout(self.layout)

    def browse_folder(self):
        """打开文件夹选择对话框"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择视频输出文件夹", self.path_edit.text(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self.path_edit.setText(folder)

    def text(self):
        """获取当前路径"""
        return self.path_edit.text()

    def setText(self, path):
        """设置路径"""
        self.path_edit.setText(path)


class DropdownSelector(QWidget):
    """下拉选择框，用于替代单选按钮组"""

    def __init__(self, options, label, default_value, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        # 创建标签
        if label:
            self.label = QLabel(label)
            self.layout.addWidget(self.label)

        # 创建下拉框
        self.comboBox = QComboBox()
        # 存储选项
        self.options = options

        # 根据选项类型，可能需要不同的显示方式
        for option in options:
            # 处理布尔类型选项
            if isinstance(option, bool):
                display_text = "是" if option else "否"
                self.comboBox.addItem(display_text, option)
            # 处理None类型选项
            elif option is None:
                self.comboBox.addItem("无", None)
            # 其他类型选项直接添加
            else:
                self.comboBox.addItem(str(option), option)

        # 设置默认值
        if default_value is not None:
            for i in range(self.comboBox.count()):
                if self.comboBox.itemData(i) == default_value:
                    self.comboBox.setCurrentIndex(i)
                    break

        self.layout.addWidget(self.comboBox)
        self.setLayout(self.layout)

    def value(self):
        """获取当前选中的值"""
        return self.comboBox.currentData()

    def setValue(self, value):
        """设置当前选中的值"""
        for i in range(self.comboBox.count()):
            if self.comboBox.itemData(i) == value:
                self.comboBox.setCurrentIndex(i)
                return


class SettingsTab(QWidget):
    """
    配置页面，允许用户设置所有处理参数并保存到config.json
    """
    # 定义配置变更信号
    config_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化配置页面UI"""
        self.layout = QVBoxLayout(self)

        # 创建一个滚动区域用于容纳配置项
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        # 添加所有配置控件
        self.add_config_widgets()

        # 创建保存配置按钮
        self.button_layout = QHBoxLayout()
        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.clicked.connect(self.save_config)
        self.save_config_button.setMinimumHeight(40)
        self.save_config_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.reset_config_button = QPushButton("重置配置")
        self.reset_config_button.clicked.connect(self.reset_config)
        self.reset_config_button.setMinimumHeight(40)
        self.button_layout.addWidget(self.reset_config_button)
        self.button_layout.addWidget(self.save_config_button)

        # 设置滚动区域
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)
        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

    def add_config_widgets(self):
        """添加所有配置控件，使用表单布局和下拉选择框"""
        # 视频配置
        self.add_section_header("视频下载配置")
        video_form = QFormLayout()
        video_form.setVerticalSpacing(4)

        # 视频输出文件夹 - 使用FolderSelector
        self.video_folder = FolderSelector("videos")
        self.video_folder.setToolTip("选择视频输出到的文件夹")
        video_form.addRow("视频输出文件夹:", self.video_folder)

        # 分辨率 - 使用下拉框
        self.resolution = DropdownSelector(
            ['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'],
            "",
            '1080p'
        )
        video_form.addRow("分辨率:", self.resolution)

        # 下载视频数量
        self.video_count = CustomSlider(1, 100, 1, "", 5)
        video_form.addRow("下载视频数量:", self.video_count)

        video_widget = QWidget()
        video_widget.setLayout(video_form)
        self.scroll_layout.addWidget(video_widget)

        # 音频处理配置
        self.add_section_header("音频处理配置")
        audio_form = QFormLayout()
        audio_form.setVerticalSpacing(4)

        # 人声分离模型
        self.model = DropdownSelector(
            ['htdemucs', 'htdemucs_ft', 'htdemucs_6s', 'hdemucs_mmi', 'mdx', 'mdx_extra', 'mdx_q', 'mdx_extra_q',
             'SIG'],
            "",
            'htdemucs_ft'
        )
        audio_form.addRow("人声分离模型:", self.model)

        # 计算设备
        self.device = DropdownSelector(['auto', 'cuda', 'cpu'], "", 'auto')
        audio_form.addRow("计算设备:", self.device)

        # 移位次数
        self.shifts = CustomSlider(0, 10, 1, "", 5)
        audio_form.addRow("移位次数:", self.shifts)

        audio_widget = QWidget()
        audio_widget.setLayout(audio_form)
        self.scroll_layout.addWidget(audio_widget)

        # ASR配置
        self.add_section_header("语音识别配置")
        asr_form = QFormLayout()
        asr_form.setVerticalSpacing(4)

        # ASR模型
        self.asr_model = DropdownSelector(['WhisperX', 'FunASR'], "", 'WhisperX')
        asr_form.addRow("ASR模型:", self.asr_model)

        # WhisperX模型大小
        self.whisperx_size = DropdownSelector(['large', 'medium', 'small', 'base', 'tiny'], "", 'large')
        asr_form.addRow("WhisperX模型大小:", self.whisperx_size)

        # 批处理大小
        self.batch_size = CustomSlider(1, 128, 1, "", 32)
        asr_form.addRow("批处理大小:", self.batch_size)

        # 分离多个说话人
        self.separate_speakers = DropdownSelector([True, False], "", True)
        asr_form.addRow("分离多个说话人:", self.separate_speakers)

        # 最小说话人数
        self.min_speakers = DropdownSelector([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], "", None)
        asr_form.addRow("最小说话人数:", self.min_speakers)

        # 最大说话人数
        self.max_speakers = DropdownSelector([None, 1, 2, 3, 4, 5, 6, 7, 8, 9], "", None)
        asr_form.addRow("最大说话人数:", self.max_speakers)

        asr_widget = QWidget()
        asr_widget.setLayout(asr_form)
        self.scroll_layout.addWidget(asr_widget)

        # 翻译配置
        self.add_section_header("翻译配置")
        translation_form = QFormLayout()
        translation_form.setVerticalSpacing(4)

        # 翻译方式
        self.translation_method = DropdownSelector(
            ['OpenAI', 'LLM', 'Google Translate', 'Bing Translate', 'Ernie', '火山引擎-deepseek',
             "deepseek-api", "阿里云-通义千问", "Ollama"],
            "",
            'LLM'
        )
        translation_form.addRow("翻译方式:", self.translation_method)

        # 目标语言 (翻译)
        self.target_language_translation = DropdownSelector(
            ['简体中文', '繁体中文', 'English', 'Cantonese', 'Japanese', 'Korean'],
            "",
            '简体中文'
        )
        translation_form.addRow("目标语言(翻译):", self.target_language_translation)

        translation_widget = QWidget()
        translation_widget.setLayout(translation_form)
        self.scroll_layout.addWidget(translation_widget)

        # TTS配置
        self.add_section_header("语音合成配置")
        tts_form = QFormLayout()
        tts_form.setVerticalSpacing(4)

        # AI语音生成方法
        self.tts_method = DropdownSelector(['xtts', 'cosyvoice', 'EdgeTTS'], "", 'EdgeTTS')
        tts_form.addRow("TTS方法:", self.tts_method)

        # 目标语言 (TTS)
        self.target_language_tts = DropdownSelector(
            ['中文', 'English', '粤语', 'Japanese', 'Korean', 'Spanish', 'French'],
            "",
            '中文'
        )
        tts_form.addRow("目标语言(TTS):", self.target_language_tts)

        # EdgeTTS声音选择
        self.edge_tts_voice = DropdownSelector(
            ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural', 'en-US-JennyNeural', 'ja-JP-NanamiNeural'],
            "",
            'zh-CN-XiaoxiaoNeural'
        )
        tts_form.addRow("EdgeTTS声音:", self.edge_tts_voice)

        tts_widget = QWidget()
        tts_widget.setLayout(tts_form)
        self.scroll_layout.addWidget(tts_widget)

        # 视频合成配置
        self.add_section_header("视频合成配置")
        synthesis_form = QFormLayout()
        synthesis_form.setVerticalSpacing(4)

        # 添加字幕
        self.add_subtitles = DropdownSelector([True, False], "", True)
        synthesis_form.addRow("添加字幕:", self.add_subtitles)

        # 加速倍数
        self.speed_factor = FloatSlider(0.5, 2, 0.05, "", 1.00)
        synthesis_form.addRow("加速倍数:", self.speed_factor)

        # 帧率
        self.frame_rate = CustomSlider(1, 60, 1, "", 30)
        synthesis_form.addRow("帧率:", self.frame_rate)

        # 背景音乐
        self.background_music = AudioSelector("")
        synthesis_form.addRow("背景音乐:", self.background_music)

        # 背景音乐音量
        self.bg_music_volume = FloatSlider(0, 1, 0.05, "", 0.5)
        synthesis_form.addRow("背景音乐音量:", self.bg_music_volume)

        # 视频音量
        self.video_volume = FloatSlider(0, 1, 0.05, "", 1.0)
        synthesis_form.addRow("视频音量:", self.video_volume)

        # 分辨率 (输出)
        self.output_resolution = DropdownSelector(
            ['4320p', '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'],
            "",
            '1080p'
        )
        synthesis_form.addRow("输出分辨率:", self.output_resolution)

        synthesis_widget = QWidget()
        synthesis_widget.setLayout(synthesis_form)
        self.scroll_layout.addWidget(synthesis_widget)

        # 高级配置
        self.add_section_header("高级配置")
        advanced_form = QFormLayout()
        advanced_form.setVerticalSpacing(4)

        # Max Workers
        self.max_workers = CustomSlider(1, 10, 1, "", 1)
        advanced_form.addRow("最大工作线程:", self.max_workers)

        # Max Retries
        self.max_retries = CustomSlider(1, 10, 1, "", 3)
        advanced_form.addRow("最大重试次数:", self.max_retries)

        advanced_widget = QWidget()
        advanced_widget.setLayout(advanced_form)
        self.scroll_layout.addWidget(advanced_widget)

    def add_section_header(self, title):
        """添加部分标题"""
        label = QLabel(f"=== {title} ===")
        label.setStyleSheet("font-weight: bold; color: #2196F3;")
        self.scroll_layout.addWidget(label)

    def get_config(self):
        """从UI控件中获取当前配置"""
        config = {
            "video_folder": self.video_folder.text(),  # 使用text()方法获取路径
            "resolution": self.resolution.value(),
            "video_count": self.video_count.value(),
            "model": self.model.value(),
            "device": self.device.value(),
            "shifts": self.shifts.value(),
            "asr_model": self.asr_model.value(),
            "whisperx_size": self.whisperx_size.value(),
            "batch_size": self.batch_size.value(),
            "separate_speakers": self.separate_speakers.value(),
            "min_speakers": self.min_speakers.value(),
            "max_speakers": self.max_speakers.value(),
            "translation_method": self.translation_method.value(),
            "target_language_translation": self.target_language_translation.value(),
            "tts_method": self.tts_method.value(),
            "target_language_tts": self.target_language_tts.value(),
            "edge_tts_voice": self.edge_tts_voice.value(),
            "add_subtitles": self.add_subtitles.value(),
            "speed_factor": self.speed_factor.value(),
            "frame_rate": self.frame_rate.value(),
            "background_music": self.background_music.value(),
            "bg_music_volume": self.bg_music_volume.value(),
            "video_volume": self.video_volume.value(),
            "output_resolution": self.output_resolution.value(),
            "max_workers": self.max_workers.value(),
            "max_retries": self.max_retries.value()
        }
        return config

    def apply_config(self, config):
        """将配置应用到UI控件"""
        try:
            # 基本设置
            self.video_folder.setText(config.get("video_folder", "videos"))  # 使用setText方法设置路径

            # 使用下拉框的setValue方法
            self.resolution.setValue(config.get("resolution", "1080p"))
            self.video_count.setValue(config.get("video_count", 5))
            self.model.setValue(config.get("model", "htdemucs_ft"))
            self.device.setValue(config.get("device", "auto"))
            self.shifts.setValue(config.get("shifts", 5))
            self.asr_model.setValue(config.get("asr_model", "WhisperX"))
            self.whisperx_size.setValue(config.get("whisperx_size", "large"))
            self.batch_size.setValue(config.get("batch_size", 32))
            self.separate_speakers.setValue(config.get("separate_speakers", True))
            self.min_speakers.setValue(config.get("min_speakers", None))
            self.max_speakers.setValue(config.get("max_speakers", None))
            self.translation_method.setValue(config.get("translation_method", "LLM"))
            self.target_language_translation.setValue(config.get("target_language_translation", "简体中文"))
            self.tts_method.setValue(config.get("tts_method", "EdgeTTS"))
            self.target_language_tts.setValue(config.get("target_language_tts", "中文"))
            self.edge_tts_voice.setValue(config.get("edge_tts_voice", "zh-CN-XiaoxiaoNeural"))
            self.add_subtitles.setValue(config.get("add_subtitles", True))
            self.speed_factor.setValue(config.get("speed_factor", 1.00))
            self.frame_rate.setValue(config.get("frame_rate", 30))

            # 背景音乐
            if config.get("background_music"):
                self.background_music.file_path.setText(config.get("background_music"))

            self.bg_music_volume.setValue(config.get("bg_music_volume", 0.5))
            self.video_volume.setValue(config.get("video_volume", 1.0))
            self.output_resolution.setValue(config.get("output_resolution", "1080p"))
            self.max_workers.setValue(config.get("max_workers", 1))
            self.max_retries.setValue(config.get("max_retries", 3))

        except Exception as e:
            QMessageBox.warning(self, "配置加载错误", f"加载配置时出错: {str(e)}")

    def save_config(self):
        """保存配置到JSON文件"""
        try:
            config = self.get_config()
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(config_dir, "config.json")

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            QMessageBox.information(self, "保存成功", f"配置已保存到 {config_path}")

            # 发送配置变更信号
            self.config_changed.emit(config)

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错: {str(e)}")

    def load_config(self):
        """从JSON文件加载配置"""
        try:
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(config_dir, "config.json")

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.apply_config(config)
        except Exception as e:
            QMessageBox.warning(self, "加载配置失败", f"加载配置时出错: {str(e)}")

    def reset_config(self):
        """重置配置为默认值"""
        if QMessageBox.question(self, "确认重置", "确定要重置所有配置到默认值吗？") == QMessageBox.Yes:
            # 应用默认配置
            default_config = {
                "video_folder": "videos",
                "resolution": "1080p",
                "video_count": 5,
                "model": "htdemucs_ft",
                "device": "auto",
                "shifts": 5,
                "asr_model": "WhisperX",
                "whisperx_size": "large",
                "batch_size": 32,
                "separate_speakers": True,
                "min_speakers": None,
                "max_speakers": None,
                "translation_method": "LLM",
                "target_language_translation": "简体中文",
                "tts_method": "EdgeTTS",
                "target_language_tts": "中文",
                "edge_tts_voice": "zh-CN-XiaoxiaoNeural",
                "add_subtitles": True,
                "speed_factor": 1.00,
                "frame_rate": 30,
                "background_music": None,
                "bg_music_volume": 0.5,
                "video_volume": 1.0,
                "output_resolution": "1080p",
                "max_workers": 1,
                "max_retries": 3
            }
            self.apply_config(default_config)
            QMessageBox.information(self, "重置成功", "所有配置已重置为默认值")