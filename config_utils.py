import os
import json


class ConfigUtils:
    """Configuration-related utility functions"""

    @staticmethod
    def get_default_config():
        """Return default configuration settings"""
        return {
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

    @staticmethod
    def load_config(file_name="config.json", append_log_func=None):
        """Load configuration from file"""
        try:
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(config_dir, file_name)

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if append_log_func:
                    append_log_func(f"成功加载配置文件")
                return config
            else:
                if append_log_func:
                    append_log_func(f"配置文件 {file_name} 不存在，将使用默认配置")
                return ConfigUtils.get_default_config()
        except Exception as e:
            if append_log_func:
                append_log_func(f"加载配置失败: {str(e)}")
            return ConfigUtils.get_default_config()

    @staticmethod
    def save_config(config, file_name="config.json", append_log_func=None):
        """Save configuration to file"""
        try:
            config_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(config_dir, file_name)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            if append_log_func:
                append_log_func(f"配置已保存到 {config_path}")
            return True
        except Exception as e:
            if append_log_func:
                append_log_func(f"保存配置失败: {str(e)}")
            return False

    @staticmethod
    def format_config_summary(config):
        """Format configuration summary for display"""
        if not config:
            return "未找到配置信息，将使用默认配置"

        summary_text = "● 视频输出目录: {}\n".format(config.get("video_folder", "videos"))
        summary_text += "● 分辨率: {}\n".format(config.get("resolution", "1080p"))
        summary_text += "● 人声分离: {}, 设备: {}\n".format(
            config.get("model", "htdemucs_ft"),
            config.get("device", "auto")
        )
        summary_text += "● 语音识别: {}, 模型: {}\n".format(
            config.get("asr_model", "WhisperX"),
            config.get("whisperx_size", "large")
        )
        summary_text += "● 翻译方式: {}\n".format(config.get("translation_method", "LLM"))
        summary_text += "● TTS方式: {}, 语言: {}\n".format(
            config.get("tts_method", "EdgeTTS"),
            config.get("target_language_tts", "中文")
        )
        summary_text += "● 添加字幕: {}, 加速倍数: {}\n".format(
            "是" if config.get("add_subtitles", True) else "否",
            config.get("speed_factor", 1.00)
        )

        return summary_text