# full_auto_tab.py (彻底移除所有模拟类的 try...except)
import os
import sys
import datetime
import json
import time
import faulthandler
import traceback
from typing import Optional, List, Dict, Any
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QSplitter, QProgressBar,
    QTextEdit, QFileDialog, QTableView, QHeaderView,
    QGroupBox, QCheckBox, QSizePolicy
)
from PySide6.QtCore import (
    QTimer, Qt, Signal, QObject, QThread, QSize, SignalInstance,
    QModelIndex, QUrl, QMetaObject, Q_ARG, Slot
)
from PySide6.QtGui import QIcon, QDesktopServices, QColor, QTextCursor

# 启用故障处理
faulthandler.enable()

# --- 直接导入核心处理函数，失败则报错 ---
try:
    from tools.do_everything import do_everything
    print("成功导入 'tools.do_everything'。")
except ImportError as import_err:
    print(f"致命错误: 无法导入核心处理模块 'tools.do_everything' ({import_err})。程序无法运行。")
    raise # 直接抛出错误


# --- 修改点：直接导入所有依赖，不再使用 try...except 回退到模拟 ---
try:
    from task_manager import TaskManager, Task, TaskTableModel # 必须
    from ui_components import VideoPlayer # 必须
    from task_utils import TaskUtils # 必须
    from ui_utils import UIUtils # 必须
    from config_utils import ConfigUtils # 必须
    print("成功导入所有必要的辅助模块 (task_manager, ui_components, task_utils, ui_utils, config_utils)。")
except ImportError as e:
    # 任何一个必要模块导入失败，都直接报错退出
    print(f"致命错误: 无法导入必要的辅助模块: {e}。请确保所有依赖项都已正确安装并且路径配置正确。")
    raise ImportError(f"导入必要模块失败: {e}") from e
# --- 结束修改点 ---


# --- WorkerSignals (保持不变) ---
class WorkerSignals(QObject):
    finished = Signal(str, str); progress = Signal(int, str); log = Signal(str); error = Signal(str)
    def __init__(self, parent=None): super().__init__(parent); self._active = True
    def safe_emit(self, signal_instance: SignalInstance, *args):
        if not self._active: return
        try:
            if not isinstance(signal_instance, SignalInstance): print(f"错误: safe_emit 类型错误: {type(signal_instance)}"); return
            signal_instance.emit(*args)
        except RuntimeError as e: print(f"运行时错误: {e}"); self._active = False
        except Exception as e: print(f"发射信号错误: {e}\n{traceback.format_exc()}"); self._active = False

# --- ProcessingThread (保持不变) ---
class ProcessingThread(QThread):
    def __init__(self, task_id: Optional[int], config: dict, video_url: str,
                 platform_checkboxes: Dict[str, QCheckBox], signals: WorkerSignals, parent=None):
        super().__init__(parent)
        self.task_id: Optional[int] = task_id; self.config: Dict[str, Any] = config if isinstance(config, dict) else {}
        self.video_url: str = video_url or ""; self.signals: WorkerSignals = signals; self._stopped: bool = False
        if not isinstance(self.signals, WorkerSignals): raise TypeError("需要 WorkerSignals 实例")
        self.selected_platforms: List[str] = []
        if isinstance(platform_checkboxes, dict): self.selected_platforms = [p for p, cb in platform_checkboxes.items() if isinstance(cb, QCheckBox) and cb.isChecked()]
        else: signals.safe_emit(signals.error, "[内部错误] platform_checkboxes 不是字典")

    def run(self):
        try:
            self.signals.safe_emit(self.signals.log, "=" * 50 + f"\n任务 {self.task_id or '无ID'} 开始实际处理");
            self.signals.safe_emit(self.signals.log, f"URL/路径: {self.video_url}"); self.signals.safe_emit(self.signals.log, f"发布平台: {self.selected_platforms or '无'}")
            self.signals.safe_emit(self.signals.progress, 0, "初始化...")

            video_path = ""; result = "未知状态"
            if not self.video_url: raise ValueError("视频 URL/路径为空")

            # --- 直接准备参数并调用实际的 do_everything ---
            self.signals.safe_emit(self.signals.log, "准备调用 'tools.do_everything'...")
            do_everything_args = {
                "root_folder": self.config.get('video_folder', 'videos'), "url": self.video_url,
                "num_videos": self.config.get('video_count', 1), "resolution": self.config.get('resolution', '1080p'),
                "demucs_model": self.config.get('model', 'htdemucs_ft'), "device": self.config.get('device', 'auto'), "shifts": self.config.get('shifts', 5),
                "asr_method": self.config.get('asr_model', 'WhisperX'), "whisper_model": self.config.get('whisperx_size', 'large'), "batch_size": self.config.get('batch_size', 32),
                "diarization": self.config.get('separate_speakers', False), "whisper_min_speakers": self.config.get('min_speakers', None), "whisper_max_speakers": self.config.get('max_speakers', None),
                "translation_method": self.config.get('translation_method', 'LLM'), "translation_target_language": self.config.get('target_language_translation', '简体中文'),
                "tts_method": self.config.get('tts_method', 'xtts'), "tts_target_language": self.config.get('target_language_tts', '中文'), "voice": self.config.get('edge_tts_voice', 'zh-CN-XiaoxiaoNeural'),
                "subtitles": self.config.get('add_subtitles', True), "speed_up": self.config.get('speed_factor', 1.0), "fps": self.config.get('frame_rate', 30),
                "background_music": self.config.get('background_music', None), "bgm_volume": self.config.get('bg_music_volume', 0.5), "video_volume": self.config.get('video_volume', 1.0),
                "target_resolution": self.config.get('output_resolution', '1080p'),
                "max_workers": self.config.get('max_workers', 1), "max_retries": self.config.get('max_retries', 3),
                "progress_callback": self.update_progress, "auto_publish_platforms": self.selected_platforms,
            }
            args_to_log = {k: v for k, v in do_everything_args.items() if k != 'progress_callback'}
            self.signals.safe_emit(self.signals.log, f"调用 do_everything 参数:\n{json.dumps(args_to_log, ensure_ascii=False, indent=2)}")

            video_folder = do_everything_args["root_folder"]
            if not isinstance(video_folder, str) or not video_folder: video_folder = 'videos'; self.signals.safe_emit(self.signals.log, "警告: root_folder 无效"); do_everything_args["root_folder"] = video_folder
            try: os.makedirs(video_folder, exist_ok=True)
            except OSError as e: raise OSError(f"无法创建文件夹 '{video_folder}': {e}") from e
            # if not callable(do_everything): raise TypeError("'do_everything' 不可调用") # 这行不再需要，导入失败时已报错

            result, video_path = do_everything(**do_everything_args) # 调用实际函数

            if self._stopped: result = "处理已取消"; video_path = ""
            final_result = result or ("处理完成" if video_path else "处理完成但无输出"); final_path = video_path or ""
            self.signals.safe_emit(self.signals.log, f"处理流程结束。结果: {final_result}")
            self.signals.safe_emit(self.signals.finished, final_result, final_path)

        except ValueError as e: error_msg=f"值错误:{e}"; self.signals.safe_emit(self.signals.error,error_msg); self.signals.safe_emit(self.signals.finished,f"失败:{e}","")
        except TypeError as e: error_msg=f"类型/参数错误:{e}\n{traceback.format_exc()}"; self.signals.safe_emit(self.signals.error,error_msg); self.signals.safe_emit(self.signals.finished,f"失败(参数错误):{e}","")
        except Exception as e: error_msg=f"严重错误:{e}\n{traceback.format_exc()}"; self.signals.safe_emit(self.signals.error,error_msg); self.signals.safe_emit(self.signals.finished,f"失败:{e}","")
        finally: self.signals.safe_emit(self.signals.log, f"处理线程退出 (ID: {self.task_id or '无'})"); self.signals.safe_emit(self.signals.log, "="*50)

    def is_stopped(self): return self._stopped
    def update_progress(self, percent: int, message: str):
        if not self._stopped:
            try: percent=int(max(0,min(100,percent))); message=str(message or ""); self.signals.safe_emit(self.signals.progress,percent,message); self.signals.safe_emit(self.signals.log,f"进度 {percent}%: {message}")
            except Exception as e: print(f"Update_progress Error: {e}")
    def stop(self):
        if not self._stopped: self._stopped=True; self.signals.safe_emit(self.signals.log,"收到停止请求 (将在当前视频处理完成后生效)...")


# --- FullAutoTab (UI 和其他逻辑保持不变) ---
class FullAutoTab(QWidget):
    PROGRESS_GREEN="#4CAF50"; PROGRESS_BLUE="#2196F3"; PROGRESS_YELLOW="#ffc107"; PROGRESS_RED="#f44336"
    def __init__(self, parent=None): super().__init__(parent); self._init_variables(); self._setup_ui(); self._apply_styles(); self._setup_connections(); QTimer.singleShot(0, self._load_resources_and_init)
    def _init_variables(self): self._processing=False; self.generated_video_path=None; self.current_task_id=None; self.current_progress=0; self.processing_thread=None; self.platform_checkboxes={}; self.task_manager=None; self.task_model=None; self.config={}; self.signals=None; self.log_text=None; self.progress_bar=None; self.progress_label=None; self.status_label=None; self.video_player=None
    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); self.main_layout=QHBoxLayout(self); self.main_layout.setContentsMargins(15,15,15,15); self.main_layout.setSpacing(15)
        self.left_panel=QWidget(); self.left_panel.setObjectName("leftPanel"); self.left_panel.setMinimumWidth(450); self.left_panel.setMaximumWidth(600)
        left_layout=QVBoxLayout(self.left_panel); left_layout.setContentsMargins(10,10,10,10); left_layout.setSpacing(12)
        left_layout.addWidget(self._create_url_group()); left_layout.addWidget(self._create_platform_group()); left_layout.addWidget(self._create_config_summary_group()); left_layout.addLayout(self._create_task_list_section())
        self.main_layout.addWidget(self.left_panel)
        self.right_panel=QWidget(); self.right_panel.setObjectName("rightPanel")
        right_layout=QVBoxLayout(self.right_panel); right_layout.setContentsMargins(10,10,10,10); right_layout.setSpacing(12)
        right_layout.addLayout(self._create_action_buttons_layout()); right_layout.addWidget(self._create_progress_group()); right_layout.addWidget(self._create_splitter(), stretch=1)
        self.main_layout.addWidget(self.right_panel, stretch=1)
        if not self.log_text: self.log_text=QTextEdit(); self.log_text.setReadOnly(True); self.log_text.ensureCursorVisible(); self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        if not self.progress_bar: self.progress_bar=QProgressBar()
        if not self.progress_label: self.progress_label=QLabel("...")
        if not self.status_label: self.status_label=QLabel("...")
    def _create_url_group(self): url_group=QGroupBox("① 视频来源"); layout=QVBoxLayout(url_group); self.video_url_label=QLabel("URL/路径:"); self.video_url=QLineEdit(); self.video_url.setPlaceholderText("粘贴URL或选择文件"); self.video_url.setFixedHeight(30); self.select_video_button=QPushButton("选择"); self.select_video_button.setIcon(QIcon.fromTheme("document-open")); input_layout=QHBoxLayout(); input_layout.addWidget(self.video_url, 1); input_layout.addWidget(self.select_video_button); layout.addWidget(self.video_url_label); layout.addLayout(input_layout); return url_group
    def _create_platform_group(self): self.auto_publish_group=QGroupBox("② 自动发布"); self.auto_publish_group.setCheckable(True); self.auto_publish_group.setChecked(False); layout=QVBoxLayout(self.auto_publish_group); platforms=["B站","头条","抖音","快手","YouTube"]; self.platform_checkboxes={}; checkbox_layout=QHBoxLayout(); [checkbox_layout.addWidget(cb) for cb in [self.platform_checkboxes.setdefault(p, QCheckBox(p)) for p in platforms]]; checkbox_layout.addStretch(); layout.addLayout(checkbox_layout); return self.auto_publish_group
    def _create_config_summary_group(self): config_group=QGroupBox("③ 配置摘要"); layout=QVBoxLayout(config_group); self.config_summary=QTextEdit(); self.config_summary.setReadOnly(True); self.config_summary.setFixedHeight(100); layout.addWidget(self.config_summary); return config_group
    def _create_task_list_section(self): task_layout=QVBoxLayout(); self.task_list_label=QLabel("④ 任务队列"); self.task_table=QTableView(); self.task_table.setSelectionBehavior(QTableView.SelectRows); self.task_table.setAlternatingRowColors(True); self.task_table.horizontalHeader().setStretchLastSection(True); self.task_table.verticalHeader().setVisible(False); self.task_table.setMinimumHeight(200); self.task_table.setSortingEnabled(True); task_button_layout=QHBoxLayout(); self.add_task_button=QPushButton("添加"); self.add_task_button.setIcon(QIcon.fromTheme("list-add")); self.clear_tasks_button=QPushButton("清空"); self.clear_tasks_button.setIcon(QIcon.fromTheme("edit-clear")); self.clear_tasks_button.setStyleSheet("color:#d32f2f;"); task_button_layout.addWidget(self.add_task_button); task_button_layout.addStretch(); task_button_layout.addWidget(self.clear_tasks_button); task_layout.addWidget(self.task_list_label); task_layout.addWidget(self.task_table, 1); task_layout.addLayout(task_button_layout); return task_layout
    def _create_action_buttons_layout(self): button_layout=QHBoxLayout(); self.run_button=QPushButton("⚡ 处理当前"); self.run_button.setObjectName("runButton"); self.run_button.setMinimumHeight(45); self.start_tasks_button=QPushButton("▶️ 开始队列"); self.start_tasks_button.setObjectName("startButton"); self.start_tasks_button.setMinimumHeight(45); self.stop_button=QPushButton("⏹️ 停止"); self.stop_button.setObjectName("stopButton"); self.stop_button.setMinimumHeight(45); self.stop_button.setEnabled(False); self.preview_button=QPushButton("👁️ 预览"); self.preview_button.setMinimumHeight(45); self.preview_button.setEnabled(False); self.open_folder_button=QPushButton("📁 打开目录"); self.open_folder_button.setMinimumHeight(45); self.open_folder_button.setEnabled(False); button_layout.addWidget(self.run_button); button_layout.addWidget(self.start_tasks_button); button_layout.addWidget(self.stop_button); button_layout.addStretch(); button_layout.addWidget(self.preview_button); button_layout.addWidget(self.open_folder_button); return button_layout
    def _create_progress_group(self): progress_group=QGroupBox("处理状态"); layout=QVBoxLayout(progress_group); self.status_label=QLabel("初始化中..."); self.status_label.setObjectName("statusLabel"); self.progress_bar=QProgressBar(); self.progress_bar.setRange(0,100); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(True); self.progress_bar.setFormat("%p%"); self.progress_bar.setFixedHeight(20); self.progress_label=QLabel("..."); self.progress_label.setObjectName("progressLabel"); layout.addWidget(self.status_label); layout.addWidget(self.progress_bar); layout.addWidget(self.progress_label); return progress_group
    def _create_splitter(self):
        self.splitter=QSplitter(Qt.Vertical); self.splitter.setHandleWidth(8)
        try: self.video_player=VideoPlayer("视频预览") # 尝试直接使用导入的
        except NameError: # 如果 VideoPlayer 确实没导入成功 (理论上不应发生，除非 ui_components 有问题)
            self.append_error("VideoPlayer类不可用!"); self.video_player=QLabel("预览区不可用", alignment=Qt.AlignCenter, styleSheet="background:#ccc;color:#555;")
        self.video_player.setMinimumHeight(250)
        log_widget=QWidget(); log_layout=QVBoxLayout(log_widget); log_layout.setContentsMargins(0,5,0,0)
        self.log_text=QTextEdit(); self.log_text.setReadOnly(True); self.log_text.setObjectName("logText"); self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap); self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        log_button_layout=QHBoxLayout(); self.clear_log_button=QPushButton("清空日志"); self.save_log_button=QPushButton("保存日志"); log_button_layout.addStretch(); log_button_layout.addWidget(self.clear_log_button); log_button_layout.addWidget(self.save_log_button)
        log_layout.addWidget(QLabel("日志:")); log_layout.addWidget(self.log_text, 1); log_layout.addLayout(log_button_layout)
        self.splitter.addWidget(self.video_player); self.splitter.addWidget(log_widget); self.splitter.setStretchFactor(0,6); self.splitter.setStretchFactor(1,4); self.splitter.setSizes([400,200]); return self.splitter
    def _apply_styles(self):
        style_sheet = """
        FullAutoTab { background-color: #f0f0f0; } QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; padding: 10px 5px 5px 5px; background-color: #ffffff; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; background-color: #e8e8e8; border-radius: 3px; color: #333; } QLineEdit, QTextEdit { border: 1px solid #ccc; border-radius: 3px; padding: 5px; background-color: #fff; } QLineEdit:focus, QTextEdit:focus { border-color: #2196F3; } QPushButton { padding: 8px 15px; border-radius: 4px; background-color: #e0e0e0; border: 1px solid #bdbdbd; color: #333; min-width: 80px; } QPushButton:hover { background-color: #d5d5d5; border-color: #aaa; } QPushButton:pressed { background-color: #bdbdbd; } QPushButton:disabled { background-color: #f5f5f5; color: #aaa; border-color: #e0e0e0; } #runButton { background-color: %(green)s; color: white; border: none; font-weight: bold; } #runButton:hover { background-color: #45a049; } #runButton:pressed { background-color: #3e8e41; } #startButton { background-color: %(blue)s; color: white; border: none; } #startButton:hover { background-color: #1e88e5; } #startButton:pressed { background-color: #1976d2; } #stopButton { background-color: %(red)s; color: white; border: none; } #stopButton:hover { background-color: #e53935; } #stopButton:pressed { background-color: #d32f2f; } QProgressBar { border: 1px solid #ccc; border-radius: 3px; text-align: center; height: 20px; } QProgressBar::chunk { background-color: %(blue)s; border-radius: 3px; } QTableView { border: 1px solid #ccc; gridline-color: #e0e0e0; alternate-background-color: #f9f9f9; } QHeaderView::section { background-color: #e8e8e8; padding: 4px; border: 1px solid #ccc; font-weight: bold; } #statusLabel { font-size: 14pt; font-weight: bold; color: #333; } #progressLabel { color: #555; } #logText { font-family: "Courier New", Courier, monospace; background-color: #fdfdfd; }
        """ % {"green": self.PROGRESS_GREEN, "blue": self.PROGRESS_BLUE, "yellow": self.PROGRESS_YELLOW, "red": self.PROGRESS_RED}
        self.setStyleSheet(style_sheet)
    def _setup_connections(self):
        if hasattr(self, 'run_button'): self.run_button.clicked.connect(self.process_url_then_tasks)
        if hasattr(self, 'start_tasks_button'): self.start_tasks_button.clicked.connect(self.start_processing_tasks)
        if hasattr(self, 'stop_button'): self.stop_button.clicked.connect(self.stop_process)
        if hasattr(self, 'preview_button'): self.preview_button.clicked.connect(self.safe_preview_video)
        if hasattr(self, 'open_folder_button'): self.open_folder_button.clicked.connect(self.open_output_folder)
        if hasattr(self, 'select_video_button'): self.select_video_button.clicked.connect(self.select_local_video)
        if hasattr(self, 'add_task_button'): self.add_task_button.clicked.connect(self.add_task)
        if hasattr(self, 'clear_tasks_button'): self.clear_tasks_button.clicked.connect(self.clear_tasks)
        if hasattr(self, 'clear_log_button'): self.clear_log_button.clicked.connect(self.clear_log)
        if hasattr(self, 'save_log_button'): self.save_log_button.clicked.connect(self.save_log)
        if hasattr(self, 'task_table'): self.task_table.doubleClicked.connect(self.on_task_double_clicked)
    def _load_resources_and_init(self): self._load_resources(); self._init_state()
    def _load_resources(self):
        self.append_log("加载资源...")
        try:
            if not self.task_manager: self.task_manager=TaskManager(); self.append_log("任务管理器OK")
            # 使用 ConfigUtils 加载配置
            if callable(getattr(ConfigUtils, 'load_config', None)):
                self.config=ConfigUtils.load_config(append_log_func=self.append_log) # 假设 load_config 能找到 config.json
                if not isinstance(self.config, dict): self.append_error("配置加载失败"); self.config = {}
                else: self.append_log("配置加载成功")
            else: self.append_error("ConfigUtils 无 load_config 方法!"); self.config = {}
            self.update_config_summary()
            if self.task_manager and hasattr(self,'task_table'): self.task_model=TaskUtils.load_tasks(self.task_manager, self.task_table, TaskTableModel, self.append_log)
            if not self.signals: self.signals=WorkerSignals(); self.signals.finished.connect(self.process_finished); self.signals.progress.connect(self.update_progress); self.signals.log.connect(self.append_log); self.signals.error.connect(self.append_error); self.append_log("信号OK")
        except Exception as e: self.append_error(f"加载资源错误: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"错误","加载资源失败")
    def _init_state(self): self.update_ui_state(False); self.append_log("界面OK"); QTimer.singleShot(500, self.check_pending_tasks)
    def update_config_summary(self):
        if not isinstance(self.config, dict): self.config={}
        # 使用 config.json 中的 key 来显示摘要
        summary_map = { "输出文件夹": 'video_folder', "下载分辨率": 'resolution', "分离模型": 'model', "处理设备": 'device', "ASR模型": 'asr_model', "Whisper尺寸": 'whisperx_size', "翻译方法": 'translation_method', "TTS方法": 'tts_method', "输出分辨率": 'output_resolution'}
        summary = ["当前配置摘要:"] + [f" • {display_name}: {self.config.get(config_key,'未设置')}" for display_name, config_key in summary_map.items()]
        if hasattr(self,'config_summary'): self.config_summary.setText("\n".join(summary))
    def update_config(self, new_config):
        if isinstance(new_config, dict): self.config = new_config; self.update_config_summary(); self.append_log("配置已更新")
        else: self.append_error("更新配置失败：无效数据类型")
    def select_local_video(self):
        start_dir = os.path.expanduser("~"); current_path = self.video_url.text()
        if current_path: start_dir = os.path.dirname(current_path) if os.path.exists(current_path) else (os.path.dirname(current_path) if os.path.exists(os.path.dirname(current_path)) else start_dir)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择视频", start_dir, "视频 (*.mp4 *.avi *.mov *.mkv);;所有 (*)")
        if file_path: self.video_url.setText(os.path.normpath(file_path)); self.append_log(f"已选择: {file_path}")
    @Slot(str)
    def append_log_main_thread(self, message):
        if not hasattr(self, 'log_text'): print(f"Log Err: {message}"); return
        try: ts=datetime.datetime.now().strftime("%H:%M:%S"); cursor = self.log_text.textCursor(); cursor.movePosition(QTextCursor.MoveOperation.End); self.log_text.setTextCursor(cursor); self.log_text.insertHtml(f"<b>[{ts}]</b> {message}<br>"); sb=self.log_text.verticalScrollBar(); sb.setValue(sb.maximum())
        except Exception as e: print(f"记录日志错误: {e}")
    def append_log(self, message):
        if QThread.currentThread()!=self.thread(): QMetaObject.invokeMethod(self,"append_log_main_thread",Qt.QueuedConnection,Q_ARG(str,message)); return
        self.append_log_main_thread(message)
    @Slot(str)
    def append_error_main_thread(self, message):
        if not hasattr(self, 'log_text'): print(f"Err Log Err: {message}"); return
        try: ts=datetime.datetime.now().strftime("%H:%M:%S"); cursor=self.log_text.textCursor(); cursor.movePosition(QTextCursor.MoveOperation.End); self.log_text.setTextCursor(cursor); self.log_text.insertHtml(f"<font color='{self.PROGRESS_RED}'><b>[{ts}] [错误]</b> {message}</font><br>"); sb=self.log_text.verticalScrollBar(); sb.setValue(sb.maximum())
        except Exception as e: print(f"Err Append Err: {e}")
    def append_error(self, message):
        if QThread.currentThread()!=self.thread(): QMetaObject.invokeMethod(self,"append_error_main_thread",Qt.QueuedConnection,Q_ARG(str,message)); return
        self.append_error_main_thread(message)
    def clear_log(self):
        if hasattr(self, 'log_text'): self.log_text.clear(); self.append_log("日志已清空")
    def save_log(self):
        if not hasattr(self, 'log_text'): QMessageBox.warning(self,"错误","日志不可用"); return
        content = self.log_text.toPlainText()
        if not content.strip(): QMessageBox.information(self,"提示","日志为空"); return
        fname=f"log_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
        fpath, _ = QFileDialog.getSaveFileName(self,"保存日志",fname,"日志(*.log);;文本(*.txt);;所有(*)")
        if fpath:
            try: open(fpath,'w',encoding='utf-8').write(content); self.append_log(f"日志已保存: {fpath}"); QMessageBox.information(self,"成功",f"日志已保存:\n{fpath}")
            except Exception as e: self.append_error(f"保存日志失败: {e}"); QMessageBox.critical(self,"失败",f"无法保存日志:\n{e}")
    def safe_preview_video(self):
        if not hasattr(self,'video_player') or not isinstance(self.video_player, VideoPlayer): self.append_error("播放器无效"); return
        path = self.generated_video_path
        if not path: self.append_log("无视频路径"); return
        if not os.path.exists(path): self.append_error(f"文件不存在: {path}"); QMessageBox.warning(self,"错误",f"找不到文件:\n{path}"); self.preview_button.setEnabled(False); self.open_folder_button.setEnabled(False); self.generated_video_path=None; return
        try: self.video_player.set_video(path); self.append_log(f"预览: {os.path.basename(path)}")
        except Exception as e: self.append_error(f"预览失败: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"错误",f"无法预览视频:\n{e}")
    def open_output_folder(self):
        path = self.generated_video_path
        if not path: self.append_log("无视频路径"); return
        folder = os.path.dirname(path)
        if not os.path.isdir(folder): self.append_error(f"文件夹无效: {folder}"); QMessageBox.warning(self,"错误",f"找不到文件夹:\n{folder}"); self.open_folder_button.setEnabled(False); return
        try:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(folder)): self.append_error(f"打开文件夹失败: {folder}"); QMessageBox.warning(self,"失败",f"无法打开文件夹:\n{folder}")
            else: self.append_log(f"已打开文件夹: {folder}")
        except Exception as e: self.append_error(f"打开文件夹出错: {e}"); QMessageBox.critical(self,"错误",f"打开文件夹出错:\n{e}")
    def update_progress(self, percent, message):
        try: percent=int(max(0,min(100,percent))); message=str(message or "")
        except: self.append_error(f"无效进度: {percent}, {message}"); return
        self.current_progress = percent
        if self.progress_bar: self.progress_bar.setValue(percent)
        if self.progress_label: self.progress_label.setText(message)
        if self.status_label and percent>0 and self._processing: self.status_label.setText("处理中..."); self.progress_bar.setStyleSheet(f"QProgressBar::chunk{{background:{self.PROGRESS_BLUE};}}")
    def add_task(self):
        url = self.video_url.text().strip()
        if not url: QMessageBox.warning(self, "输入无效", "请输入URL或选择文件"); return
        if not self.task_manager or not self.task_model: self.append_error("任务系统未就绪"); return
        try:
            task_id = TaskUtils.add_task(url, self.config, self.task_manager, self.task_model, self.append_log)
            if task_id: self.video_url.clear(); self.append_log(f"任务 #{task_id} 已添加")
            else: QMessageBox.warning(self, "添加失败", "无法添加任务")
        except Exception as e: self.append_error(f"添加任务出错: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"错误",f"添加任务出错:\n{e}")
    def clear_tasks(self):
        if not self.task_manager or not self.task_model: self.append_error("任务系统未就绪"); return
        if self.task_model.rowCount() == 0: QMessageBox.information(self,"提示","队列为空"); return
        reply = QMessageBox.question(self,'确认','确定清空所有任务?', QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Yes:
            self.append_log("清空任务...")
            try:
                if TaskUtils.clear_tasks(self.task_manager, self.append_log):
                    if self.task_model: self.task_model.clear(); self.append_log("任务队列已清空"); QMessageBox.information(self,"完成","任务队列已清空")
                else: self.append_error("清空任务失败"); QMessageBox.warning(self,"失败","清空任务出错")
            except Exception as e: self.append_error(f"清空任务出错: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"失败",f"清空任务出错:\n{e}")
        else: self.append_log("取消清空")
    def on_task_double_clicked(self, index):
        if not index.isValid(): return
        if self.task_model and 0 <= index.row() < self.task_model.rowCount():
            try:
                task = self.task_model.tasks[index.row()]
                if task and isinstance(task, Task): self.video_url.setText(task.url); self.append_log(f"已加载任务 #{task.id} URL")
            except Exception as e: self.append_error(f"处理双击出错: {e}")
    def check_pending_tasks(self):
        if self._processing or not self.task_manager: return
        try:
            next_task = TaskUtils.get_next_pending_task(self.task_manager, self.append_log)
            if next_task: self.append_log(f"发现待处理 #{next_task.id}..."); self.run_task(next_task)
            else:
                if not self._processing and self.status_label and "空闲" not in self.status_label.text() and all(s not in self.status_label.text() for s in ["完成","失败","取消"]):
                    self.update_ui_state(False); self.status_label.setText("空闲"); self.progress_label.setText("等待任务..."); self.progress_bar.setValue(0); self.progress_bar.setStyleSheet(f"QProgressBar::chunk{{background:{self.PROGRESS_BLUE};}}")
        except Exception as e: self.append_error(f"检查任务出错: {e}\n{traceback.format_exc()}")
    def start_processing_tasks(self):
        if self._processing: QMessageBox.warning(self,"处理中","已有任务在处理"); return
        if not self.task_manager: QMessageBox.critical(self,"错误","任务管理器未初始化"); return
        try:
            next_task = TaskUtils.get_next_pending_task(self.task_manager, self.append_log)
            if next_task: self.append_log(f"开始队列，处理 #{next_task.id}..."); self.run_task(next_task)
            else: QMessageBox.information(self,"空","无待处理任务"); self.append_log("队列为空")
        except Exception as e: self.append_error(f"启动队列出错: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"错误",f"启动队列出错:\n{e}")
    def process_url_then_tasks(self):
        url = self.video_url.text().strip()
        if not url: QMessageBox.warning(self,"输入无效","请输入URL或选择文件"); return
        if self._processing: QMessageBox.warning(self,"处理中","已有任务在处理"); return
        if not self.task_manager or not self.task_model: QMessageBox.critical(self,"错误","任务系统未初始化"); return
        self.append_log(f"请求一键处理: {url[:80]}...")
        try:
            task_id = TaskUtils.add_task(url, self.config, self.task_manager, self.task_model, self.append_log)
            if task_id:
                self.video_url.clear(); task = self.task_manager.get_task(task_id)
                if task: self.append_log(f"已添加 #{task_id}，准备运行"); self.run_task(task)
                else: self.append_error(f"添加后未找到 #{task_id}"); QMessageBox.critical(self,"内部错误","任务添加后未找到")
            else: QMessageBox.warning(self,"添加失败","无法添加任务")
        except Exception as e: self.append_error(f"处理当前URL出错: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"处理失败",f"处理当前URL出错:\n{e}")
    def run_task(self, task: Task):
        if not isinstance(task, Task) or task.id is None: self.append_error(f"无效任务对象: {task}"); return
        if self._processing: self.append_error(f"逻辑错误: 尝试运行 #{task.id} 但已在处理中"); return
        self.current_task_id = task.id; self.append_log(f"准备运行任务 #{task.id} (状态: {task.status})")
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not TaskUtils.update_task_status(task_id=task.id, task_manager=self.task_manager, task_model=self.task_model, status="处理中", started_at=now_str, append_log_func=self.append_log):
             self.append_error(f"无法更新 #{task.id} 状态"); QMessageBox.critical(self,"错误",f"无法更新任务 #{task.id} 状态"); self.current_task_id = None; return
        self.run_process(task_id=task.id, url_override=task.url)
    def run_process(self, task_id: Optional[int] = None, url_override: Optional[str] = None):
        if self._processing: self.append_error("处理中，无法启动新任务"); return
        url = url_override if url_override else self.video_url.text().strip()
        if not url:
            if task_id and self.task_manager: task=self.task_manager.get_task(task_id); url = task.url if task else None
            if not url: self.append_error("无有效URL"); QMessageBox.warning(self,"输入缺失","请输入或选择视频"); self.update_ui_state(False); return
        self._processing=True; self.current_task_id=task_id; self.update_ui_state(True)
        if self.progress_bar: self.progress_bar.setValue(0); self.progress_bar.setStyleSheet(f"QProgressBar::chunk{{background:{self.PROGRESS_BLUE};}}")
        if self.progress_label: self.progress_label.setText("初始化...")
        if self.status_label: self.status_label.setText("准备处理...")
        self.append_log("="*50 + f"\n启动处理: {url[:80]}..." + (f" (ID: {task_id})" if task_id else ""))
        if not self.signals: self.append_error("信号系统未初始化!"); QMessageBox.critical(self,"严重错误","信号系统异常"); self._processing=False; self.update_ui_state(False); return
        try:
            self.processing_thread = ProcessingThread(task_id, self.config.copy(), url, self.platform_checkboxes, self.signals, self)
            self.processing_thread.finished.connect(self.on_thread_finished)
            self.processing_thread.start(); self.append_log("处理线程已启动...")
        except Exception as e: self.append_error(f"启动线程失败: {e}\n{traceback.format_exc()}"); QMessageBox.critical(self,"启动失败",f"无法创建线程:\n{e}"); self._processing=False; self.update_ui_state(False); self.current_task_id=None
    def on_thread_finished(self):
        self.append_log("后台线程 finished")
        if self.processing_thread: self.processing_thread.deleteLater(); self.processing_thread=None
    def stop_process(self):
        if not self._processing or not self.processing_thread: self.append_log("无任务在处理"); return
        reply = QMessageBox.question(self,'确认','停止当前任务?', QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Yes:
            self.append_log("用户请求停止..."); self.status_label.setText("正在停止..."); self.stop_button.setEnabled(False)
            try:
                if hasattr(self.processing_thread,'stop'): self.processing_thread.stop()
                else: self.append_error("线程无 stop() 方法!")
            except Exception as e: self.append_error(f"停止线程出错: {e}"); self.stop_button.setEnabled(True)
        else: self.append_log("取消停止")
    def process_finished(self, result, video_path):
        self.append_log("-" * 30 + f"\n处理结束. 状态: {result}" + (f"\n输出: {video_path}" if video_path else ""))
        original_id = self.current_task_id; self._processing=False; self.current_task_id=None; self.update_ui_state(False)
        self.generated_video_path=None; status_text="未知"; color=self.PROGRESS_YELLOW
        if video_path and os.path.exists(video_path):
            self.generated_video_path=os.path.normpath(video_path)
            if self.preview_button: self.preview_button.setEnabled(True)
            if self.open_folder_button: self.open_folder_button.setEnabled(True)
            status_text="成功完成" if any(s in result for s in ["成功","完成"]) else f"完成({result.split(':')[0]})"; color=self.PROGRESS_GREEN
            if self.progress_bar: self.progress_bar.setValue(100)
        elif any(s in result for s in ["取消","停止"]): status_text="已取消"; color=self.PROGRESS_YELLOW; self.progress_label.setText("用户停止"); self.progress_bar.setValue(0)
        else: self.append_error(f"失败/无输出. 结果: {result}"); self.preview_button.setEnabled(False); self.open_folder_button.setEnabled(False); status_text=f"失败: {result.split(':')[0]}" if ':' in result else f"失败({result})"; color=self.PROGRESS_RED; self.progress_bar.setValue(self.current_progress if self.current_progress<100 else 0)
        self.status_label.setText(status_text); self.progress_label.setText(result if len(result)<80 else result[:77]+'...'); self.progress_bar.setStyleSheet(f"QProgressBar::chunk{{background:{color};}}")
        if original_id is not None and self.task_manager and self.task_model:
            status_map={"成功":"已完成", "完成":"已完成", "失败":"失败", "取消":"已取消", "停止":"已取消", "错误":"失败"}
            final_status="未知"; r_lower=result.lower()
            for k,v in status_map.items():
                if k.lower() in r_lower: final_status=v; break
            if final_status=="未知": final_status="已完成" if self.generated_video_path else "失败"
            self.append_log(f"更新任务 #{original_id} 状态: {final_status}")
            TaskUtils.update_task_status(original_id, self.task_manager, self.task_model, status=final_status, completed_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), result=result, output_path=self.generated_video_path or "", append_log_func=self.append_log)
        self.append_log("准备检查下一个任务..."); QTimer.singleShot(1000, self.check_pending_tasks)
    def update_ui_state(self, is_processing):
        self._processing = is_processing
        controls = [self.run_button, self.start_tasks_button, self.add_task_button, self.clear_tasks_button, self.video_url, self.select_video_button]
        for ctrl in controls:
             if ctrl: ctrl.setEnabled(not is_processing)
        if self.stop_button: self.stop_button.setEnabled(is_processing)
        has_path = bool(self.generated_video_path and os.path.exists(self.generated_video_path))
        if self.preview_button: self.preview_button.setEnabled(has_path and not is_processing)
        if self.open_folder_button: self.open_folder_button.setEnabled(has_path and not is_processing)
    def cleanup(self):
        self.append_log("清理...");
        if self.processing_thread and self.processing_thread.isRunning():
            self.append_log("停止线程..."); self.processing_thread.stop();
            if not self.processing_thread.wait(1500): self.append_log("警告:线程未停止")
            else: self.append_log("线程已停止"); self.processing_thread=None
        if self.signals: self.signals._active=False; self.append_log("信号禁用")
        if hasattr(self,'video_player') and hasattr(self.video_player,'stop'):
             try: self.video_player.stop(); self.append_log("播放器停止")
             except Exception as e: self.append_log(f"停止播放器出错:{e}")
        self.append_log("清理完成")
    def closeEvent(self, event):
        if self._processing:
            reply = QMessageBox.question(self,"退出","处理中,确认退出?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel: event.ignore(); return
        self.cleanup(); event.accept()

# (无 main guard)