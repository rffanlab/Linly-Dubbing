# tools/step045_tts_spark_tts.py (最终优化版)

import os
import time
import sys
import gc
import traceback

try:
    import torch
    import soundfile as sf
    from loguru import logger
    import numpy as np
    from SparkTTS.cli.SparkTTS import SparkTTS
    from SparkTTS.sparktts.utils.token_parser import LEVELS_MAP_UI
except ImportError as e:
    raise ImportError(f"关键库导入失败: {e}。") from e

model: SparkTTS | None = None
language_map = { '中文': 'zh', 'English': 'en', 'Japanese': 'ja', 'Korean': 'ko', 'French': 'fr', 'Spanish': 'es', 'Polish': 'pl' }
_model_device = None

def load_model(model_path: str = "SparkTTS/pretrained_models/Spark-TTS-0.5B", device: str = 'auto') -> bool:
    """加载模型，幂等操作。"""
    global model, _model_device
    if model is not None:
        logger.info("模型已加载，跳过。")
        return True

    # ...(设备选择逻辑不变)...
    selected_device: torch.device
    if device == 'auto':
        if torch.cuda.is_available(): selected_device = torch.device('cuda')
        elif sys.platform == "darwin" and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(): selected_device = torch.device('mps')
        else: selected_device = torch.device('cpu')
        logger.info(f"自动选择设备: {selected_device.type}")
    else:
        try: selected_device = torch.device(device)
        except Exception: selected_device = torch.device('cpu'); logger.warning("无效设备，回退到 CPU。")
        logger.info(f"用户指定设备: {selected_device}")

    logger.info(f"开始加载 SparkTTS 模型从 {model_path} 到 {selected_device}...")
    t_start = time.time()
    try:
        if not os.path.exists(model_path): raise FileNotFoundError(f"模型路径不存在: {model_path}")
        # 在加载前尝试清理一次，避免残留状态影响
        if selected_device.type == 'cuda': torch.cuda.empty_cache()
        gc.collect()
        model = SparkTTS(model_path, selected_device)
        _model_device = selected_device
        if _model_device.type == 'cuda':
             logger.info(f"模型加载后显存: A={torch.cuda.memory_allocated(_model_device)/1024**2:.1f}MB, R={torch.cuda.memory_reserved(_model_device)/1024**2:.1f}MB")
        t_end = time.time()
        logger.success(f"模型加载成功！耗时 {t_end - t_start:.2f} 秒。")
        return True
    except Exception as e:
        model = None; _model_device = None
        logger.error(f"加载模型失败: {e}\n{traceback.format_exc()}")
        raise RuntimeError(f"加载模型失败: {e}") from e

def save_wav(wav_cpu: np.ndarray | torch.Tensor, path: str, sample_rate: int = 16000):
    """保存 CPU 音频数据。"""
    wav_np = None
    try:
        output_dir = os.path.dirname(path)
        if output_dir and not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
        if isinstance(wav_cpu, torch.Tensor): wav_np = wav_cpu.detach().numpy()
        elif isinstance(wav_cpu, np.ndarray): wav_np = wav_cpu
        else: raise TypeError(f"不支持的输入类型: {type(wav_cpu)}.")
        sf.write(path, wav_np, samplerate=sample_rate)
    except Exception as e:
        logger.error(f"保存 WAV 文件 '{path}' 出错: {e}")
        raise
    finally:
        if 'wav_np' in locals() and wav_np is not None: del wav_np

def tts(
    text: str,
    output_path: str,
    speaker_wav: str | None = None, # 明确这个参数的用途
    model_name: str = "SparkTTS/pretrained_models/Spark-TTS-0.5B",
    device: str = 'auto',
    target_language: str = '中文',
    gender: str | None = None,
    pitch: int | str | None = None,
    speed: int | str | None = None
):
    """使用 SparkTTS 生成语音，并在每次调用后进行核心清理。"""
    global model, _model_device
    # --- 按需加载模型 ---
    if model is None:
        logger.info("尝试加载模型...")
        try:
            load_model(model_path=model_name, device=device)
            if model is None: raise RuntimeError("模型加载失败。")
        except Exception as e:
             raise RuntimeError(f"模型加载失败: {e}") from e

    # --- 检查输出路径 ---
    if os.path.exists(output_path):
        logger.info(f"文件已存在，跳过: {os.path.basename(output_path)}")
        return

    # --- 参数处理 ---
    language_code = language_map.get(target_language)
    if language_code is None: raise ValueError(f"不支持的语言: {target_language}")
    pitch_val, speed_val = None, None
    try:
        if pitch is not None: pitch_level = int(pitch); pitch_val = LEVELS_MAP_UI.get(pitch_level)
        if speed is not None: speed_level = int(speed); speed_val = LEVELS_MAP_UI.get(speed_level)
        if pitch is not None and pitch_val is None: logger.warning(f"无效音高等级: {pitch}")
        if speed is not None and speed_val is None: logger.warning(f"无效语速等级: {speed}")
    except (ValueError, TypeError, KeyError): logger.warning("无效音高/语速参数。")

    wav_result_gpu = None
    wav_result_cpu = None
    inference_successful = False
    start_time = time.time()
    try:
        # --- 执行推理 ---
        logger.info(f"开始合成: '{text[:30]}...' -> {os.path.basename(output_path)}")
        if _model_device and _model_device.type == 'cuda':
            logger.debug(f"推理前显存: A={torch.cuda.memory_allocated(_model_device)/1024**2:.1f}MB, R={torch.cuda.memory_reserved(_model_device)/1024**2:.1f}MB")

        with torch.no_grad():
            # *** 确认 speaker_wav 的使用 ***
            # 如果你的应用场景确实不需要声音克隆，或者 speaker_wav 总是 None，
            # 确保这里传递 None。如果需要克隆，确保 speaker_wav 路径有效。
            effective_speaker_wav = speaker_wav if speaker_wav and os.path.exists(speaker_wav) else None
            if speaker_wav and not effective_speaker_wav:
                 logger.warning(f"提供的 speaker_wav路径无效或不存在: {speaker_wav}，将不使用声音克隆。")

            wav_result_gpu = model.inference(
                text,
                effective_speaker_wav, # 使用处理过的路径或 None
                None, # prompt_text 通常为 None
                gender,
                pitch_val,
                speed_val
            )

        if wav_result_gpu is None or (isinstance(wav_result_gpu, torch.Tensor) and wav_result_gpu.numel() == 0):
             raise ValueError("模型推理返回空结果。")

        # --- 立即转移到 CPU ---
        if isinstance(wav_result_gpu, torch.Tensor) and wav_result_gpu.is_cuda:
            wav_result_cpu = wav_result_gpu.cpu()
            del wav_result_gpu; wav_result_gpu = None
        else:
             wav_result_cpu = wav_result_gpu # NumPy or CPU Tensor
             wav_result_gpu = None

        inference_successful = True
        logger.debug("推理成功完成。")

        # --- 保存音频 ---
        save_wav(wav_result_cpu, output_path, sample_rate=16000)
        end_time = time.time()
        logger.info(f"合成成功 (耗时 {end_time - start_time:.2f} 秒): {os.path.basename(output_path)}")

    except Exception as e:
        end_time = time.time()
        logger.error(f"TTS 处理失败 (耗时 {end_time - start_time:.2f} 秒) for text '{text[:50]}...': {e}")
        logger.error(traceback.format_exc()) # 打印详细错误堆栈
        raise # 重新抛出异常，让 generate_wavs 知道出错了
    finally:
        # --- 核心清理 ---
        del wav_result_gpu # 确保删除
        del wav_result_cpu # 确保删除
        gc.collect()
        if _model_device and _model_device.type == 'cuda':
            torch.cuda.empty_cache()
            # 只在 Debug 级别打印最终显存，避免过多日志
            logger.debug(f"清理后显存: A={torch.cuda.memory_allocated(_model_device)/1024**2:.1f}MB, R={torch.cuda.memory_reserved(_model_device)/1024**2:.1f}MB")


# --- 主程序入口 (用于独立测试) ---
if __name__ == '__main__':
    # ...(测试代码不变)...
    TEST_MODEL_PATH = "SparkTTS/pretrained_models/Spark-TTS-0.5B"
    TEST_DEVICE = 'auto'
    TEST_OUTPUT_DIR = 'outputs_sparktts_test'
    TEST_SPEAKER_WAV = None # 测试时不使用声音克隆
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    logger.add("sparktts_service_test.log", level="DEBUG")
    logger.info("--- SparkTTS 服务独立测试启动 ---")
    test_sentences = [
        ("你好，世界！", "中文"), ("Hello world!", "English"),
        ("这已经是第三个句子了。", "中文"), ("This is the third sentence.", "English"),
        ("我们继续测试，看看这次会不会卡住。", "中文"), ("Let's keep testing to see if it gets stuck this time.", "English"),
        ("这是一个可能比较长的中文句子，用来模拟实际应用中可能遇到的情况，观察其处理时间和资源占用。", "中文"),
        ("This is a potentially long English sentence, used to simulate situations encountered in practical applications, observing its processing time and resource consumption.", "English"),
         # 添加你之前卡住的那个句子或类似的句子
        ("但最令人兴奋的一点是我们能够使 G P T-四 O", "中文"), # 之前卡住的句子编号是 0009
        ("这是第十个句子。", "中文"),
        ("This is the tenth sentence.", "English"),
    ]
    try:
        for i, (text, lang) in enumerate(test_sentences):
            logger.info(f"\n--- 测试 {i+1}/{len(test_sentences)} ---")
            output_filename = os.path.join(TEST_OUTPUT_DIR, f'test_{i+1}_{lang}.wav')
            if os.path.exists(output_filename): os.remove(output_filename)
            try:
                tts(text=text, output_path=output_filename, speaker_wav=TEST_SPEAKER_WAV,
                    model_name=TEST_MODEL_PATH, device=TEST_DEVICE, target_language=lang)
            except Exception as e:
                logger.error(f"测试 {i+1} ('{text[:20]}...') 失败: {e}")
                # 遇到错误时可以选择停止测试或继续
                # break
            # time.sleep(0.1) # 微小延迟，模拟调用间隔
    except KeyboardInterrupt: logger.warning("测试中断。")
    except Exception as e: logger.exception("测试中发生严重错误。")
    finally: logger.info("--- SparkTTS 服务独立测试结束 ---")