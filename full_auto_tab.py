import os
import datetime
import json
import time
import faulthandler
from typing import Optional, List, Dict, Any
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QSplitter, QProgressBar,
    QTextEdit, QFileDialog, QTableView, QHeaderView,
    QGroupBox, QCheckBox, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt, Signal, QObject, QThread, QSize, SignalInstance
from PySide6.QtGui import QIcon

# 启用故障处理
faulthandler.enable()

# 尝试导入实际功能模块
try:
    from tools.do_everything import do_everything
    from platform_publisher import MultiPlatformPublisher

    DISABLE_PROCESSING = False
except ImportError:
    print("警告: 无法导入处理模块，将使用模拟处理")
    DISABLE_PROCESSING = True

try:
    from task_manager import TaskManager, Task, TaskTableModel
    from ui_components import VideoPlayer
    from task_utils import TaskUtils
    from ui_utils import UIUtils
    from config_utils import ConfigUtils
except ImportError as e:
    print(f"导入错误: {e}")
    raise


class WorkerSignals(QObject):
    """
    自定义信号类，用于线程与主线程通信
    """
    finished = Signal(str, str)  # status, video_path
    progress = Signal(int, str)  # percent, message
    log = Signal(str)  # log message
    error = Signal(str)  # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = True

    def safe_emit(self, signal, *args):
        """线程安全的信号发射方法"""
        if not self._active:
            return
        try:
            # 确保是有效的信号实例
            if not isinstance(signal, SignalInstance):
                raise TypeError("参数不是有效的信号实例")

            # 正确获取信号的元方法
            meta_method = signal.signal.metaMethod()

            # 检查信号是否连接
            if self.isSignalConnected(meta_method):
                signal.emit(*args)
        except RuntimeError as e:
            print(f"运行时错误: {e}")
            self._active = False
        except (AttributeError, TypeError) as e:
            print(f"信号处理错误: {e}")
            self._active = False


class ProcessingThread(QThread):
    """
    处理线程类，继承自QThread
    """

    def __init__(self, task_id: Optional[str], config: dict, video_url: str,
                 platform_checkboxes: Dict[str, QCheckBox], signals: WorkerSignals, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.config = config
        self.video_url = video_url
        self.platform_checkboxes = platform_checkboxes
        self.signals = signals
        self._stopped = False

    def run(self):
        """线程主逻辑"""
        try:
            self.signals.safe_emit(self.signals.log, "=" * 50)
            self.signals.safe_emit(self.signals.log, f"开始处理任务 {self.task_id or ''}")
            self.signals.safe_emit(self.signals.log, f"视频URL: {self.video_url}")
            self.signals.safe_emit(self.signals.progress, 0, "初始化处理...")

            # 获取选中的发布平台
            selected_platforms = []
            for platform, checkbox in self.platform_checkboxes.items():
                if checkbox.isChecked():
                    selected_platforms.append(platform)

            if DISABLE_PROCESSING:
                # 模拟处理流程
                for i in range(1, 101):
                    if self._stopped:
                        break
                    time.sleep(0.05)
                    progress_msg = f"模拟进度 {i}%"
                    if i < 20:
                        progress_msg = "下载视频..."
                    elif i < 40:
                        progress_msg = "人声分离..."
                    elif i < 60:
                        progress_msg = "语音识别..."
                    elif i < 80:
                        progress_msg = "字幕翻译..."
                    elif i < 100:
                        progress_msg = "视频合成..."

                    self.signals.safe_emit(self.signals.progress, i, progress_msg)

                result = "模拟处理完成"
                video_path = os.path.abspath("sample_output.mp4") if not self._stopped else ""
            else:
                # 实际处理流程
                result, video_path = do_everything(
                    video_folder=self.config.get('video_folder', 'videos'),
                    url=self.video_url,
                    # 其他配置参数...
                    progress_callback=self.update_progress,
                    auto_publish_platforms=selected_platforms
                )

            if not self._stopped:
                self.signals.safe_emit(self.signals.finished, result, video_path)
            else:
                self.signals.safe_emit(self.signals.finished, "处理已取消", "")

        except Exception as e:
            import traceback
            error_msg = f"处理失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.safe_emit(self.signals.error, error_msg)
            self.signals.safe_emit(self.signals.finished, f"处理失败: {str(e)}", "")

    def update_progress(self, percent: int, message: str):
        """更新进度回调"""
        if not self._stopped:
            self.signals.safe_emit(self.signals.progress, percent, message)
            self.signals.safe_emit(self.signals.log, f"进度 {percent}%: {message}")

    def stop(self):
        """停止处理"""
        self._stopped = True
        self.signals.safe_emit(self.signals.log, "正在停止处理...")


class FullAutoTab(QWidget):
    """
    一键自动化处理标签页
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_variables()
        self._setup_ui()
        self._setup_connections()
        self._load_resources()
        self._init_state()

    def _init_variables(self):
        """初始化变量"""
        self._processing = False
        self.generated_video_path = None
        self.current_task_id = None
        self.current_progress = 0
        self.processing_thread = None
        self.platform_checkboxes = {}

    def _setup_ui(self):
        """设置用户界面"""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 左侧面板 - 配置区域
        self.left_panel = QWidget()
        self.left_panel.setMinimumWidth(400)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(5, 5, 5, 5)

        # URL输入区域
        self._setup_url_input()

        # 自动发布平台选择
        self._setup_platform_selection()

        # 配置摘要
        self._setup_config_summary()

        # 任务列表
        self._setup_task_list()

        # 右侧面板 - 操作和预览区域
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 5, 5, 5)

        # 操作按钮
        self._setup_action_buttons()

        # 进度条
        self._setup_progress_bar()

        # 分割器（视频预览和日志）
        self._setup_splitter()

        # 将左右面板添加到主布局
        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_panel)

    def _setup_url_input(self):
        """设置URL输入区域"""
        url_group = QGroupBox("视频输入")
        url_layout = QVBoxLayout(url_group)

        self.video_url_label = QLabel("视频URL:")
        self.video_url = QLineEdit()
        self.video_url.setPlaceholderText("请输入视频URL或选择本地视频文件")

        self.select_video_button = QPushButton("选择本地视频")
        self.select_video_button.setIcon(QIcon.fromTheme("folder-open"))

        url_layout.addWidget(self.video_url_label)
        url_layout.addWidget(self.video_url)
        url_layout.addWidget(self.select_video_button)

        self.left_layout.addWidget(url_group)

    def _setup_platform_selection(self):
        """设置平台选择区域"""
        self.auto_publish_group = QGroupBox("自动发布平台")
        self.auto_publish_layout = QVBoxLayout(self.auto_publish_group)

        platforms = ["哔哩哔哩", "今日头条", "抖音", "快手"]
        for platform in platforms:
            checkbox = QCheckBox(platform)
            self.platform_checkboxes[platform] = checkbox
            self.auto_publish_layout.addWidget(checkbox)

        self.left_layout.addWidget(self.auto_publish_group)

    def _setup_config_summary(self):
        """设置配置摘要区域"""
        self.config_summary_label = QLabel("当前配置摘要:")
        self.config_summary = QTextEdit()
        self.config_summary.setReadOnly(True)
        self.config_summary.setMaximumHeight(150)

        self.left_layout.addWidget(self.config_summary_label)
        self.left_layout.addWidget(self.config_summary)

    def _setup_task_list(self):
        """设置任务列表区域"""
        self.task_list_label = QLabel("任务列表:")
        self.task_table = QTableView()
        self.task_table.setSelectionBehavior(QTableView.SelectRows)
        self.task_table.setAlternatingRowColors(True)

        # 任务操作按钮
        task_button_layout = QHBoxLayout()
        self.add_task_button = QPushButton("添加任务")
        self.clear_tasks_button = QPushButton("清空任务")

        task_button_layout.addWidget(self.add_task_button)
        task_button_layout.addWidget(self.clear_tasks_button)

        self.left_layout.addWidget(self.task_list_label)
        self.left_layout.addWidget(self.task_table)
        self.left_layout.addLayout(task_button_layout)

    def _setup_action_buttons(self):
        """设置操作按钮区域"""
        button_layout = QHBoxLayout()

        self.run_button = QPushButton("一键处理")
        self.run_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.run_button.setMinimumHeight(50)

        self.start_tasks_button = QPushButton("开始任务")
        self.start_tasks_button.setIcon(QIcon.fromTheme("media-seek-forward"))
        self.start_tasks_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.start_tasks_button.setMinimumHeight(50)

        self.stop_button = QPushButton("停止处理")
        self.stop_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_button.setStyleSheet("background-color: #F44336; color: white;")
        self.stop_button.setMinimumHeight(50)
        self.stop_button.setEnabled(False)

        self.preview_button = QPushButton("预览视频")
        self.preview_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.preview_button.setMinimumHeight(50)
        self.preview_button.setEnabled(False)

        self.open_folder_button = QPushButton("打开目录")
        self.open_folder_button.setIcon(QIcon.fromTheme("folder-open"))
        self.open_folder_button.setMinimumHeight(50)
        self.open_folder_button.setEnabled(False)

        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.start_tasks_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.open_folder_button)

        self.right_layout.addLayout(button_layout)

    def _setup_progress_bar(self):
        """设置进度条区域"""
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)

        self.progress_label = QLabel("准备就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("空闲")
        self.status_label.setAlignment(Qt.AlignCenter)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.status_label)

        self.right_layout.addWidget(progress_group)

    def _setup_splitter(self):
        """设置分割器区域"""
        self.splitter = QSplitter(Qt.Vertical)

        # 视频预览区域
        self.video_player = VideoPlayer("视频预览:")

        # 日志区域
        log_group = QWidget()
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        log_button_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("清空日志")
        self.save_log_button = QPushButton("保存日志")

        log_button_layout.addWidget(self.clear_log_button)
        log_button_layout.addWidget(self.save_log_button)

        log_layout.addWidget(QLabel("处理日志:"))
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_button_layout)

        # 添加到分割器
        self.splitter.addWidget(self.video_player)
        self.splitter.addWidget(log_group)
        self.splitter.setSizes([300, 200])

        self.right_layout.addWidget(self.splitter)

    def _setup_connections(self):
        """设置信号槽连接"""
        # 按钮连接
        self.run_button.clicked.connect(self.process_url_then_tasks)
        self.start_tasks_button.clicked.connect(self.start_processing_tasks)
        self.stop_button.clicked.connect(self.stop_process)
        self.preview_button.clicked.connect(self.safe_preview_video)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.select_video_button.clicked.connect(self.select_local_video)
        self.add_task_button.clicked.connect(self.add_task)
        self.clear_tasks_button.clicked.connect(self.clear_tasks)
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button.clicked.connect(self.save_log)

        # 表格双击事件
        self.task_table.doubleClicked.connect(self.on_task_double_clicked)

    def _load_resources(self):
        """加载资源和配置"""
        # 初始化任务管理器
        self.task_manager = TaskManager()

        # 加载配置
        self.config = ConfigUtils.load_config(append_log_func=self.append_log)
        self.update_config_summary()

        # 加载任务模型
        self.task_model = TaskUtils.load_tasks(
            self.task_manager, self.task_table, TaskTableModel, self.append_log)

        # 初始化信号
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.process_finished)
        self.signals.progress.connect(self.update_progress)
        self.signals.log.connect(self.append_log)
        self.signals.error.connect(self.append_error)

    def _init_state(self):
        """初始化状态"""
        self.update_ui_state(False)
        self.append_log("系统初始化完成，准备就绪")
        QTimer.singleShot(1000, self.check_pending_tasks)

    def update_config_summary(self):
        """更新配置摘要显示"""
        summary = "当前配置:\n"
        summary += f"• 视频文件夹: {self.config.get('video_folder', 'videos')}\n"
        summary += f"• 分辨率: {self.config.get('resolution', '1080p')}\n"
        summary += f"• 语音模型: {self.config.get('asr_model', 'WhisperX')}\n"
        summary += f"• 翻译方法: {self.config.get('translation_method', 'LLM')}\n"
        summary += f"• TTS引擎: {self.config.get('tts_method', 'EdgeTTS')}"

        self.config_summary.setText(summary)

    def update_config(self, new_config):
        """更新配置"""
        self.config = new_config
        self.update_config_summary()
        self.append_log("配置已更新")

    def select_local_video(self):
        """选择本地视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
        )

        if file_path:
            self.video_url.setText(file_path)
            self.append_log(f"已选择本地视频: {file_path}")

    def append_log(self, message):
        """添加日志消息"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum())

    def append_error(self, message):
        """添加错误消息"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] [错误] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum())

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.append_log("日志已清空")

    def save_log(self):
        """保存日志到文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.append_log(f"日志已保存到: {file_path}")
            except Exception as e:
                self.append_error(f"保存日志失败: {str(e)}")

    def safe_preview_video(self):
        """安全的视频预览方法"""
        if not hasattr(self, 'video_player') or not self.video_player:
            self.append_error("视频播放器未初始化")
            return

        try:
            if self.generated_video_path and os.path.exists(self.generated_video_path):
                QTimer.singleShot(0, lambda: self.video_player.set_video(
                    self.generated_video_path))
                self.append_log(f"正在预览视频: {os.path.basename(self.generated_video_path)}")
            else:
                self.append_error("视频文件不存在或路径无效")
        except RuntimeError as e:
            self.append_error(f"预览失败: {str(e)}")

    def open_output_folder(self):
        """打开输出文件夹"""
        if self.generated_video_path and os.path.exists(self.generated_video_path):
            folder_path = os.path.dirname(self.generated_video_path)
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS/Linux
                    os.system(f'open "{folder_path}"' if sys.platform == 'darwin'
                              else f'xdg-open "{folder_path}"')
                self.append_log(f"已打开文件夹: {folder_path}")
            except Exception as e:
                self.append_error(f"打开文件夹失败: {str(e)}")
        else:
            self.append_error("无法打开文件夹 - 视频路径无效")

    def update_progress(self, percent, message):
        """更新进度显示"""
        self.current_progress = percent
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

        if percent == 100:
            self.status_label.setText("处理完成")
        elif percent > 0:
            self.status_label.setText("处理中...")

    def add_task(self):
        """添加新任务"""
        url = self.video_url.text().strip()
        if not url:
            QMessageBox.warning(self, "输入错误", "请输入视频URL或选择本地视频")
            return

        task_id = TaskUtils.add_task(
            url, self.config, self.task_manager,
            self.task_model, self.append_log
        )

        if task_id:
            self.video_url.clear()
            self.append_log(f"已添加任务 #{task_id}: {url}")

    def clear_tasks(self):
        """清空所有任务"""
        reply = QMessageBox.question(
            self, '确认', '确定要清空所有任务吗？此操作不可撤销！',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if TaskUtils.clear_tasks(self.task_manager, self.append_log):
                self.task_model = TaskUtils.load_tasks(
                    self.task_manager, self.task_table,
                    TaskTableModel, self.append_log
                )
                self.append_log("已清空所有任务")

    def on_task_double_clicked(self, index):
        """任务表格双击事件"""
        task = self.task_model.get_task(index)
        if task:
            self.video_url.setText(task.url)
            self.append_log(f"已加载任务 #{task.id}: {task.url}")

    def check_pending_tasks(self):
        """检查待处理任务"""
        if self._processing:
            return

        next_task = TaskUtils.get_next_pending_task(
            self.task_manager, self.append_log)

        if next_task:
            self.append_log(f"发现待处理任务 #{next_task.id}: {next_task.url}")
            self.run_task(next_task)

    def start_processing_tasks(self):
        """开始处理任务队列"""
        if self._processing:
            QMessageBox.warning(self, "处理中", "当前有任务正在处理，请等待完成")
            return

        next_task = TaskUtils.get_next_pending_task(
            self.task_manager, self.append_log)

        if next_task:
            self.append_log(f"开始处理任务 #{next_task.id}: {next_task.url}")
            self.run_task(next_task)
        else:
            QMessageBox.information(self, "提示", "没有待处理的任务")
            self.append_log("没有待处理的任务")

    def process_url_then_tasks(self):
        """处理当前URL然后继续任务队列"""
        url = self.video_url.text().strip()
        if not url:
            QMessageBox.warning(self, "输入错误", "请输入视频URL或选择本地视频")
            return

        if self._processing:
            QMessageBox.warning(self, "处理中", "当前有任务正在处理，请等待完成")
            return

        # 先添加到任务队列
        task_id = TaskUtils.add_task(
            url, self.config, self.task_manager,
            self.task_model, self.append_log
        )

        if task_id:
            self.video_url.clear()
            task = self.task_manager.get_task(task_id)
            if task:
                self.run_task(task)

    def run_task(self, task):
        """运行指定任务"""
        self.current_task_id = task.id
        self.video_url.setText(task.url)

        # 更新任务状态
        TaskUtils.update_task_status(
            task.id, self.task_manager, self.task_model,
            "处理中", started_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            append_log_func=self.append_log
        )

        # 开始处理
        self.run_process(task.id)

    def run_process(self, task_id=None):
        """启动处理流程"""
        if self._processing:
            self.append_error("已有任务正在处理")
            return

        self._processing = True
        self.update_ui_state(True)

        url = self.video_url.text()
        if not url:
            self.append_error("没有可处理的URL")
            self.process_finished("没有可处理的URL", "")
            return

        self.append_log("=" * 50)
        self.append_log(f"开始处理: {url}")

        # 创建处理线程
        self.processing_thread = ProcessingThread(
            task_id=task_id,
            config=self.config,
            video_url=url,
            platform_checkboxes=self.platform_checkboxes,
            signals=self.signals,
            parent=self
        )

        # 连接线程完成信号
        self.processing_thread.finished.connect(
            lambda: self.processing_thread.deleteLater())

        # 启动线程
        self.processing_thread.start()

    def stop_process(self):
        """停止处理"""
        if not self._processing:
            return

        if self.processing_thread:
            self.processing_thread.stop()
            self.processing_thread.quit()
            self.processing_thread.wait(500)

        self._processing = False
        self.update_ui_state(False)
        self.append_log("处理已停止")

        if self.current_task_id:
            TaskUtils.update_task_status(
                self.current_task_id, self.task_manager, self.task_model,
                "已取消", completed_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                result="用户手动停止", output_path="",
                append_log_func=self.append_log
            )
            self.current_task_id = None

    def process_finished(self, result, video_path):
        """处理完成回调"""
        self._processing = False
        self.update_ui_state(False)

        self.generated_video_path = video_path
        self.status_label.setText(result.split(':')[0] if ':' in result else result)

        if video_path and os.path.exists(video_path):
            self.preview_button.setEnabled(True)
            self.open_folder_button.setEnabled(True)
            self.safe_preview_video()
            self.append_log(f"生成视频: {video_path}")
        else:
            self.append_log("未生成有效视频文件")

        # 检查更多任务
        QTimer.singleShot(1000, self.check_pending_tasks)

    def update_ui_state(self, processing):
        """更新UI状态"""
        self.run_button.setEnabled(not processing)
        self.start_tasks_button.setEnabled(not processing)
        self.stop_button.setEnabled(processing)
        self.preview_button.setEnabled(not processing and bool(self.generated_video_path))
        self.open_folder_button.setEnabled(not processing and bool(self.generated_video_path))

        if processing:
            self.status_label.setText("处理中...")
        else:
            self.status_label.setText("准备就绪")

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'signals'):
            self.signals._active = False

        if hasattr(self, 'processing_thread') and self.processing_thread:
            self.processing_thread.stop()
            self.processing_thread.quit()
            self.processing_thread.wait(500)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = FullAutoTab()
    window.show()
    sys.exit(app.exec())