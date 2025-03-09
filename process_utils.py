import threading
import traceback
import datetime
from PySide6.QtCore import QObject, Signal


# Create a signal class for thread communication
class WorkerSignals(QObject):
    finished = Signal(str, str)  # completion signal: status, video path
    progress = Signal(int, str)  # progress signal: percentage, status info
    log = Signal(str)  # log signal: log text


class ProcessUtils:
    """Process-related utility functions for video processing"""

    @staticmethod
    def create_progress_callback(signals):
        """Create a progress callback function for do_everything"""

        def progress_callback(percent, status):
            signals.progress.emit(percent, status)

        return progress_callback

    @staticmethod
    def run_process_thread(url, config, signals, task_id=None, do_everything_func=None):
        """Run processing in a separate thread"""
        if not do_everything_func:
            signals.log.emit("错误: 未提供处理函数")
            signals.finished.emit("处理失败: 未提供处理函数", "")
            return

        def process_thread():
            try:
                signals.log.emit("开始处理...")
                signals.progress.emit(0, "初始化处理...")

                # Log important parameters
                signals.log.emit(f"视频文件夹: {config.get('video_folder', 'videos')}")
                signals.log.emit(f"视频URL: {url}")
                signals.log.emit(f"分辨率: {config.get('resolution', '1080p')}")

                # More detailed parameter logging
                signals.log.emit("-" * 50)
                signals.log.emit("处理参数:")
                signals.log.emit(f"下载视频数量: {config.get('video_count', 5)}")
                signals.log.emit(f"分辨率: {config.get('resolution', '1080p')}")
                signals.log.emit(f"人声分离模型: {config.get('model', 'htdemucs_ft')}")
                signals.log.emit(f"计算设备: {config.get('device', 'auto')}")
                signals.log.emit(f"移位次数: {config.get('shifts', 5)}")
                signals.log.emit(f"ASR模型: {config.get('asr_method', 'WhisperX')}")
                signals.log.emit(f"WhisperX模型大小: {config.get('whisperx_size', 'large')}")
                signals.log.emit(f"翻译方法: {config.get('translation_method', 'LLM')}")
                signals.log.emit(f"TTS方法: {config.get('tts_method', 'EdgeTTS')}")
                signals.log.emit("-" * 50)

                # Custom progress callback function
                progress_callback = ProcessUtils.create_progress_callback(signals)

                # Actual processing call
                result, video_path = do_everything_func(
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

                # Complete processing, set 100% progress
                signals.progress.emit(100, "处理完成!")
                signals.log.emit(f"处理完成: {result}")
                if video_path:
                    signals.log.emit(f"生成视频路径: {video_path}")

                # Processing complete, send signal
                signals.finished.emit(result, video_path if video_path else "")

            except Exception as e:
                # Capture and log complete stack trace
                stack_trace = traceback.format_exc()
                error_msg = f"处理失败: {str(e)}\n\n堆栈跟踪:\n{stack_trace}"
                signals.log.emit(error_msg)
                signals.progress.emit(0, "处理失败")
                signals.finished.emit(f"处理失败: {str(e)}", "")

        # Create and start processing thread
        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()

        return thread