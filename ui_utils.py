import os
import datetime
import subprocess
from PySide6.QtWidgets import QFileDialog


class UIUtils:
    """UI-related utility functions for the FullAutoTab"""

    @staticmethod
    def select_local_video(parent, append_log_func=None):
        """Select a local video file using a file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov *.flv)"
        )
        if file_path:
            if append_log_func:
                append_log_func(f"已选择本地视频文件: {file_path}")
            return file_path
        return None

    @staticmethod
    def preview_video(video_player, video_path, append_log_func=None):
        """Preview a video in the video player"""
        if not video_path or not os.path.exists(video_path):
            return False

        # If already loaded, just play
        if (hasattr(video_player, 'video_path') and
                video_player.video_path == video_path):
            video_player.play_pause()
        else:
            # Otherwise, load and play
            video_player.set_video(video_path)
            video_player.play_pause()

        if append_log_func:
            append_log_func(f"预览视频: {video_path}")

        return True

    @staticmethod
    def open_folder(folder_path, append_log_func=None):
        """Open the folder containing a file in the system file explorer"""
        if not folder_path:
            return False

        if os.path.isfile(folder_path):
            folder_path = os.path.dirname(folder_path)

        if not os.path.exists(folder_path):
            return False

        if append_log_func:
            append_log_func(f"打开文件夹: {folder_path}")

        # Open folder based on OS
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS, Linux
                if 'darwin' in os.sys.platform:  # macOS
                    subprocess.run(['open', folder_path])
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path])
            return True
        except Exception as e:
            if append_log_func:
                append_log_func(f"打开文件夹失败: {str(e)}")
            return False

    @staticmethod
    def append_log(log_text, message, auto_scroll=True):
        """Append message to log text widget with timestamp"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        log_text.append(log_message)

        # Scroll to bottom if requested
        if auto_scroll and hasattr(log_text, 'verticalScrollBar'):
            scrollbar = log_text.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

        return log_message

    @staticmethod
    def clear_log(log_text, append_log_func=None):
        """Clear log text"""
        log_text.clear()
        if append_log_func:
            append_log_func("日志已清空")

    @staticmethod
    def save_log(log_text, append_log_func=None):
        """Save log text to a file"""
        try:
            # Create logs directory
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Create log filename with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(log_dir, f"process_log_{timestamp}.txt")

            # Save log content
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_text.toPlainText())

            if append_log_func:
                append_log_func(f"日志已保存到: {log_file}")
            return log_file
        except Exception as e:
            if append_log_func:
                append_log_func(f"保存日志失败: {str(e)}")
            return None

    @staticmethod
    def update_progress(progress_bar, progress_label, progress, status, append_log_func=None):
        """Update progress bar and label"""
        progress_bar.setValue(progress)
        progress_label.setValue(status)

        if append_log_func:
            append_log_func(f"进度更新: {progress}% - {status}")