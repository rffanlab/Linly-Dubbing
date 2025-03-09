import os
import threading
import datetime
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QMessageBox, QSplitter, QProgressBar,
                               QTextEdit, QFileDialog, QTableView, QHeaderView)
from PySide6.QtCore import QTimer, Qt, Signal, QObject

from task_manager import TaskManager, Task, TaskTableModel
from ui_components import VideoPlayer

# Import utility modules
from task_utils import TaskUtils
from ui_utils import UIUtils
from config_utils import ConfigUtils

# 尝试导入实际的功能模块
try:
    from tools.do_everything import do_everything

    DISABLE_PROCESSING = False  # 已经能够导入实际处理模块
except ImportError:
    print("警告: 无法导入处理模块，将使用模拟处理")
    DISABLE_PROCESSING = True  # 无法导入实际处理模块，使用模拟处理

# 尝试导入SUPPORT_VOICE
try:
    from tools.utils import SUPPORT_VOICE
except ImportError:
    # 定义临时的支持语音列表
    SUPPORT_VOICE = ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural',
                     'en-US-JennyNeural', 'ja-JP-NanamiNeural']


# 创建一个信号类用于线程通信
class WorkerSignals(QObject):
    finished = Signal(str, str)  # 完成信号：状态, 视频路径
    progress = Signal(int, str)  # 进度信号：百分比, 状态信息
    log = Signal(str)  # 日志信号：日志文本


class FullAutoTab(QWidget):
    """一键自动化标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化UI
        self.setup_ui()

        # 存储生成的视频路径
        self.generated_video_path = None

        # 当前任务ID
        self.current_task_id = None

        # 进度
        self.current_progress = 0

        # 创建任务管理器
        self.task_manager = TaskManager()

        # 加载配置
        self.config = ConfigUtils.load_config(append_log_func=self.append_log)

        # 更新配置摘要
        self.update_config_summary()

        # 加载任务数据
        self.task_model = TaskUtils.load_tasks(
            self.task_manager, self.task_table, TaskTableModel, self.append_log)

        # 处理线程
        self.worker_thread = None
        self._processing = False
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.process_finished)
        self.signals.progress.connect(self.update_progress)
        self.signals.log.connect(self.append_log)

        # 进度步骤
        self.progress_steps = [
            "下载视频...", "人声分离...", "AI智能语音识别...",
            "字幕翻译...", "AI语音合成...", "视频合成..."
        ]
        self.current_step = 0

        # 初始化日志
        self.append_log("系统初始化完成，准备就绪")

        # 检查任务
        QTimer.singleShot(1000, self.check_pending_tasks)

    def setup_ui(self):
        """设置用户界面"""
        self.main_layout = QHBoxLayout(self)

        # 左侧配置区域
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)

        # URL输入
        self.video_url_label = QLabel("视频URL")
        self.video_url = QLineEdit()
        self.video_url.setPlaceholderText("请输入视频URL或选择本地视频文件")

        # 本地视频选择
        self.select_video_button = QPushButton("选择本地视频")
        self.select_video_button.clicked.connect(self.select_local_video)

        self.left_layout.addWidget(self.video_url_label)
        self.left_layout.addWidget(self.video_url)

        local_video_layout = QHBoxLayout()
        local_video_layout.addWidget(self.select_video_button)
        self.left_layout.addLayout(local_video_layout)

        # 配置信息
        self.config_summary = QTextEdit()
        self.config_summary.setReadOnly(True)
        self.config_summary.setMaximumHeight(150)

        self.config_summary_label = QLabel("当前配置摘要：")
        self.left_layout.addWidget(self.config_summary_label)
        self.left_layout.addWidget(self.config_summary)

        # 任务列表
        self.task_list_label = QLabel("任务列表：")
        self.left_layout.addWidget(self.task_list_label)

        self.task_table = QTableView()
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.left_layout.addWidget(self.task_table)

        # 任务管理按钮
        self.task_button_layout = QHBoxLayout()

        self.add_task_button = QPushButton("添加任务")
        self.add_task_button.clicked.connect(self.add_task)

        self.clear_tasks_button = QPushButton("清空任务")
        self.clear_tasks_button.clicked.connect(self.clear_tasks)

        self.task_button_layout.addWidget(self.add_task_button)
        self.task_button_layout.addWidget(self.clear_tasks_button)

        self.left_layout.addLayout(self.task_button_layout)

        # 右侧区域
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)

        # 执行按钮区域
        self.button_layout = QHBoxLayout()

        # 一键处理按钮
        self.run_button = QPushButton("一键处理")
        self.run_button.clicked.connect(self.process_url_then_tasks)
        self.run_button.setMinimumHeight(50)
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white;")

        # 添加开始任务按钮
        self.start_tasks_button = QPushButton("开始任务")
        self.start_tasks_button.clicked.connect(self.start_processing_tasks)
        self.start_tasks_button.setMinimumHeight(50)
        self.start_tasks_button.setStyleSheet("background-color: #2196F3; color: white;")

        # 停止处理按钮
        self.stop_button = QPushButton("停止处理")
        self.stop_button.clicked.connect(self.stop_process)
        self.stop_button.setMinimumHeight(50)
        self.stop_button.setEnabled(False)  # 初始禁用

        # 预览按钮
        self.preview_button = QPushButton("预览视频")
        self.preview_button.clicked.connect(self.preview_video)
        self.preview_button.setMinimumHeight(50)
        self.preview_button.setEnabled(False)

        # 打开文件夹按钮
        self.open_folder_button = QPushButton("打开所在目录")
        self.open_folder_button.clicked.connect(self.open_folder)
        self.open_folder_button.setMinimumHeight(50)
        self.open_folder_button.setEnabled(False)

        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.start_tasks_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.open_folder_button)
        self.button_layout.addWidget(self.preview_button)
        self.right_layout.addLayout(self.button_layout)

        # 进度条
        self.progress_layout = QVBoxLayout()
        self.progress_label = QLabel("准备就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.progress_layout.addWidget(QLabel("处理进度:"))
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.progress_label)
        self.right_layout.addLayout(self.progress_layout)

        # 状态显示
        self.status_label = QLabel("准备就绪")
        self.right_layout.addWidget(QLabel("处理状态:"))
        self.right_layout.addWidget(self.status_label)

        # 创建垂直分割器
        self.right_splitter = QSplitter(Qt.Vertical)

        # 视频播放器容器
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.addWidget(QLabel("视频预览:"))
        self.video_player = VideoPlayer("视频播放器")
        self.video_layout.addWidget(self.video_player)

        # 日志容器
        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.addWidget(QLabel("处理日志:"))

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_layout.addWidget(self.log_text)

        # 日志按钮
        self.log_button_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("清空日志")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button = QPushButton("保存日志")
        self.save_log_button.clicked.connect(self.save_log)
        self.log_button_layout.addWidget(self.clear_log_button)
        self.log_button_layout.addWidget(self.save_log_button)
        self.log_layout.addLayout(self.log_button_layout)

        self.log_container.setLayout(self.log_layout)

        # 添加到分割器
        self.right_splitter.addWidget(self.video_container)
        self.right_splitter.addWidget(self.log_container)
        self.right_splitter.setSizes([600, 400])

        self.right_layout.addWidget(self.right_splitter)

        # 主分割器
        self.main_splitter = QSplitter()
        self.main_splitter.addWidget(self.left_widget)
        self.main_splitter.addWidget(self.right_widget)
        self.main_splitter.setSizes([400, 600])

        self.main_layout.addWidget(self.main_splitter)

    # 配置方法
    def update_config_summary(self):
        """更新配置摘要显示"""
        summary_text = ConfigUtils.format_config_summary(self.config)
        self.config_summary.setText(summary_text)

    def update_config(self, new_config):
        """更新当前配置"""
        self.config = new_config
        self.update_config_summary()

    # UI交互方法
    def select_local_video(self):
        """选择本地视频文件"""
        file_path = UIUtils.select_local_video(self, self.append_log)
        if file_path:
            self.video_url.setText(file_path)

    def append_log(self, message):
        """添加日志消息"""
        UIUtils.append_log(self.log_text, message)

    def clear_log(self):
        """清空日志"""
        UIUtils.clear_log(self.log_text, self.append_log)

    def save_log(self):
        """保存日志"""
        UIUtils.save_log(self.log_text, self.append_log)

    def preview_video(self):
        """预览视频"""
        if self.generated_video_path and os.path.exists(self.generated_video_path):
            UIUtils.preview_video(self.video_player, self.generated_video_path, self.append_log)

    def open_folder(self):
        """打开视频所在目录"""
        if self.generated_video_path and os.path.exists(self.generated_video_path):
            UIUtils.open_folder(self.generated_video_path, self.append_log)

    def update_progress(self, progress, status):
        """更新进度条和标签"""
        self.current_progress = progress
        self.progress_bar.setValue(progress)
        self.progress_label.setText(status)
        self.append_log(f"进度更新: {progress}% - {status}")

    # 任务管理方法
    def add_task(self):
        """添加新任务到列表"""
        url = self.video_url.text().strip()
        task_id = TaskUtils.add_task(url, self.config, self.task_manager, self.task_model, self.append_log)

        if task_id:
            self.video_url.clear()

    def clear_tasks(self):
        """清空所有任务"""
        reply = QMessageBox.question(
            self, '确认操作', '确定要清空所有任务吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if TaskUtils.clear_tasks(self.task_manager, self.append_log):
                self.task_model = TaskUtils.load_tasks(
                    self.task_manager, self.task_table, TaskTableModel, self.append_log)

    def check_pending_tasks(self):
        """检查待处理任务并启动下一个"""
        if self.is_processing():
            return

        next_task = TaskUtils.get_next_pending_task(self.task_manager, self.append_log)
        if next_task:
            self.append_log(f"发现待处理任务 #{next_task.id}: {next_task.url}")
            self.run_task(next_task)

    def start_processing_tasks(self):
        """开始处理任务列表中的任务"""
        if self.is_processing():
            QMessageBox.warning(self, "处理中", "当前有任务正在处理，请等待完成")
            return

        next_task = TaskUtils.get_next_pending_task(self.task_manager, self.append_log)
        if next_task:
            self.append_log(f"开始处理任务 #{next_task.id}: {next_task.url}")
            self.run_task(next_task)
        else:
            self.append_log("没有待处理的任务")
            QMessageBox.information(self, "无待处理任务", "任务列表中没有待处理的任务")

    def process_url_then_tasks(self):
        """处理URL输入框中的URL，完成后继续处理任务列表"""
        url = self.video_url.text().strip()
        if not url:
            QMessageBox.warning(self, "输入错误", "请输入要处理的URL")
            return

        if self.is_processing():
            QMessageBox.warning(self, "处理中", "当前有任务正在处理，请等待完成")
            return

        # 先添加到任务列表，设为最高优先级
        task_id = TaskUtils.add_task(url, self.config, self.task_manager, self.task_model, self.append_log)
        if task_id:
            self.append_log(f"已添加并将开始处理URL: {url}")
            self.video_url.clear()

            # 立即开始处理此任务
            task = self.task_manager.get_task(task_id)
            if task:
                self.run_task(task)

    def is_processing(self):
        """检查是否有任务正在处理中"""
        return self._processing

    def run_task(self, task):
        """运行指定任务"""
        self._processing = True  # 设置处理标志

        self.current_task_id = task.id
        self.video_url.setText(task.url)

        # 更新任务状态为处理中
        TaskUtils.update_task_status(
            task.id,
            self.task_manager,
            self.task_model,
            "处理中",
            started_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            append_log_func=self.append_log
        )

        # 开始处理
        self.run_process(task_id=task.id)

    def process_thread(self, task_id=None):
        """异步处理线程"""
        config = self.config or {}
        try:
            self.signals.log.emit("开始处理...")
            self.signals.progress.emit(0, "初始化处理...")
            url = self.video_url.text()

            # 记录重要参数
            self.signals.log.emit(f"视频文件夹: {config.get('video_folder', 'videos')}")
            self.signals.log.emit(f"视频URL: {url}")
            self.signals.log.emit(f"分辨率: {config.get('resolution', '1080p')}")

            # 更详细的参数记录
            self.signals.log.emit("-" * 50)
            self.signals.log.emit("处理参数:")
            self.signals.log.emit(f"下载视频数量: {config.get('video_count', 5)}")
            self.signals.log.emit(f"分辨率: {config.get('resolution', '1080p')}")
            self.signals.log.emit(f"人声分离模型: {config.get('model', 'htdemucs_ft')}")
            self.signals.log.emit(f"计算设备: {config.get('device', 'auto')}")
            self.signals.log.emit(f"移位次数: {config.get('shifts', 5)}")
            self.signals.log.emit(f"ASR模型: {config.get('asr_model', 'WhisperX')}")
            self.signals.log.emit(f"WhisperX模型大小: {config.get('whisperx_size', 'large')}")
            self.signals.log.emit(f"翻译方法: {config.get('translation_method', 'LLM')}")
            self.signals.log.emit(f"TTS方法: {config.get('tts_method', 'EdgeTTS')}")
            self.signals.log.emit("-" * 50)

            # 自定义进度回调函数
            def progress_callback(percent, status):
                self.signals.progress.emit(percent, status)

            # 实际的处理调用
            result, video_path = do_everything(
                config.get('video_folder', 'videos'),
                url,
                config.get('video_count', 5),
                config.get('resolution', '1080p'),
                config.get('model', 'htdemucs_ft'),
                config.get('device', 'auto'),
                config.get('shifts', 5),
                config.get('asr_model', 'WhisperX'),
                config.get('whisperx_size', 'large'),
                config.get('batch_size', 32),
                config.get('separate_speakers', True),
                config.get('min_speakers', None),
                config.get('max_speakers', None),
                config.get('translation_method', 'LLM'),
                config.get('target_language_translation', '简体中文'),
                config.get('tts_method', 'EdgeTTS'),
                config.get('target_language_tts', '中文'),
                config.get('edge_tts_voice', 'zh-CN-XiaoxiaoNeural'),
                config.get('add_subtitles', True),
                config.get('speed_factor', 1.00),
                config.get('frame_rate', 30),
                config.get('background_music', None),
                config.get('bg_music_volume', 0.5),
                config.get('video_volume', 1.0),
                config.get('output_resolution', '1080p'),
                config.get('max_workers', 1),
                config.get('max_retries', 3),
                progress_callback
            )

            # 完成处理，设置100%进度
            self.signals.progress.emit(100, "处理完成!")
            self.signals.log.emit(f"处理完成: {result}")
            if video_path:
                self.signals.log.emit(f"生成视频路径: {video_path}")

            # 更新任务状态（如果是来自任务队列的请求）
            if task_id:
                TaskUtils.update_task_status(
                    task_id,
                    self.task_manager,
                    self.task_model,
                    "已完成" if video_path else "失败",
                    completed_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    result=result,
                    output_path=video_path if video_path else "",
                    append_log_func=self.signals.log.emit
                )

            # 处理完成，发送信号
            self.signals.finished.emit(result, video_path if video_path else "")

        except Exception as e:
            # 捕获并记录完整的堆栈跟踪信息
            import traceback
            stack_trace = traceback.format_exc()
            error_msg = f"处理失败: {str(e)}\n\n堆栈跟踪:\n{stack_trace}"
            self.signals.log.emit(error_msg)
            self.signals.progress.emit(0, "处理失败")

            # 更新任务状态为失败（如果是来自任务队列的请求）
            if task_id:
                TaskUtils.update_task_status(
                    task_id,
                    self.task_manager,
                    self.task_model,
                    "失败",
                    completed_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    result=f"处理失败: {str(e)}",
                    output_path="",
                    append_log_func=self.signals.log.emit
                )

            self.signals.finished.emit(f"处理失败: {str(e)}", "")

    def run_process(self, task_id=None):
        """开始处理"""
        # 设置处理中状态
        self._processing = True

        # 更新UI状态
        self.run_button.setEnabled(False)
        self.start_tasks_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.preview_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.status_label.setText("正在处理...")

        # 重置进度
        self.current_progress = 0
        self.current_step = 0
        self.progress_bar.setValue(0)
        self.progress_label.setText("准备处理...")

        # 记录处理开始
        self.append_log("-" * 50)
        self.append_log(f"开始处理 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.append_log(f"视频URL: {self.video_url.text()}")

        if DISABLE_PROCESSING:
            # 模拟处理过程
            self.append_log("处理功能已禁用，仅显示UI")
            self.status_label.setText("模拟处理中...")
            self.progress_bar.setValue(50)
            self.progress_label.setText("模拟进度: 50%")

            # 5秒后显示模拟完成
            QTimer.singleShot(5000, lambda: self.process_finished("模拟处理完成", "", task_id))
        else:
            # 创建并启动处理线程
            self.worker_thread = threading.Thread(target=lambda: self.process_thread(task_id))
            self.worker_thread.daemon = True
            self.worker_thread.start()

    def stop_process(self):
        """停止处理"""
        if not self._processing:
            return

        # TODO: 添加中断处理线程的代码
        # 注意：这里仅设置状态并更新UI，实际中断需要在process_thread中实现

        self._processing = False
        self.run_button.setEnabled(True)
        self.start_tasks_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("处理已停止")
        self.append_log("用户手动停止处理")

        # 更新当前任务状态为失败（如果有）
        if self.current_task_id:
            TaskUtils.update_task_status(
                self.current_task_id,
                self.task_manager,
                self.task_model,
                "失败",
                completed_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                result="用户手动停止处理",
                output_path="",
                append_log_func=self.append_log
            )
            self.current_task_id = None

    def process_finished(self, result, video_path, task_id=None):
        """处理完成的回调"""
        self._processing = False

        # 更新UI状态
        self.run_button.setEnabled(True)  # 重新启用一键处理按钮
        self.start_tasks_button.setEnabled(True)  # 重新启用开始任务按钮
        self.stop_button.setEnabled(False)  # 禁用停止处理按钮
        self.status_label.setText(result)

        # 存储生成的视频路径
        self.generated_video_path = video_path

        # 记录处理完成
        self.append_log(f"处理完成 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.append_log(f"结果: {result}")

        # 如果有视频路径，启用预览按钮和打开文件夹按钮，并加载视频
        if video_path and os.path.exists(video_path):
            self.preview_button.setEnabled(True)
            self.open_folder_button.setEnabled(True)
            self.video_player.set_video(video_path)
            self.append_log(f"生成视频路径: {video_path}")
        else:
            self.append_log("未生成视频或视频路径无效")

        # 更新任务状态（如果是任务完成的回调）
        if task_id:
            TaskUtils.update_task_status(
                task_id,
                self.task_manager,
                self.task_model,
                "已完成" if video_path else "失败",
                completed_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                result=result,
                output_path=video_path if video_path else "",
                append_log_func=self.append_log
            )
            self.current_task_id = None

        # 检查是否有更多任务
        QTimer.singleShot(1000, self.start_processing_tasks)