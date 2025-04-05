# Copyright (c) 2025 SparkAudio
#               2025 Xinsheng Wang (w.xinshawn@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import torch
import soundfile as sf
from loguru import logger
import numpy as np
import time
from SparkTTS.cli.SparkTTS import SparkTTS
from SparkTTS.sparktts.utils.token_parser import LEVELS_MAP_UI

model = None

'''
Supported languages: English (en), Chinese (zh)
'''


def init_TTS():
    load_model()


def load_model(model_path="SparkTTS/pretrained_models/Spark-TTS-0.5B", device='auto'):
    global model
    if model is not None:
        return

    if device == 'auto':
        if torch.cuda.is_available():
            device = torch.device('cuda')
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = torch.device('mps')
        else:
            device = torch.device('cpu')

    logger.info(f'Loading SparkTTS model from {model_path}')
    t_start = time.time()

    model = SparkTTS(model_path, device)

    t_end = time.time()
    logger.info(f'SparkTTS model loaded in {t_end - t_start:.2f}s')


language_map = {
    '中文': 'zh',
    'English': 'en',
}


def save_wav(wav, path, sample_rate=16000):
    """Save audio waveform to file"""
    sf.write(path, wav, samplerate=sample_rate)


def tts(text, output_path, speaker_wav=None, model_name="SparkTTS/pretrained_models/Spark-TTS-0.5B",
        device='auto', target_language='中文', gender=None, pitch=None, speed=None):
    """
    Generate speech from text using SparkTTS

    Args:
        text: Input text to synthesize
        output_path: Path to save generated audio
        speaker_wav: Reference audio for voice cloning (optional)
        model_name: Path to model directory
        device: Device to use ('auto', 'cuda', 'cpu', etc.)
        target_language: Target language ('中文' or 'English')
        gender: Voice gender ('male' or 'female')
        pitch: Pitch level (1-5)
        speed: Speed level (1-5)
    """
    global model

    language = language_map.get(target_language, 'en')
    assert language in ['en', 'zh'], f"Unsupported language: {target_language}"

    if os.path.exists(output_path):
        logger.info(f'Audio {output_path} already exists')
        return

    if model is None:
        load_model(model_name, device)

    # Convert pitch/speed levels if provided
    pitch_val = LEVELS_MAP_UI[int(pitch)] if pitch is not None else None
    speed_val = LEVELS_MAP_UI[int(speed)] if speed is not None else None

    for retry in range(3):
        try:
            with torch.no_grad():
                wav = model.inference(
                    text,
                    prompt_speech=speaker_wav,
                    gender=gender,
                    pitch=pitch_val,
                    speed=speed_val,
                )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            save_wav(wav, output_path)
            logger.info(f'Successfully generated: {output_path}')
            break
        except Exception as e:
            logger.error(f'Attempt {retry + 1} failed: {str(e)}')
            if retry == 2:
                raise
            time.sleep(1)


if __name__ == '__main__':
    # Example usage
    speaker_wav = 'example/reference_audio.wav'
    os.makedirs('outputs', exist_ok=True)

    # Simple CLI interface
    while True:
        text = input('Enter text (or "q" to quit): ')
        if text.lower() == 'q':
            break

        output_path = f'outputs/{int(time.time())}.wav'

        # Default settings
        tts(text, output_path, speaker_wav=None, target_language='English')

        print(f"Audio saved to: {output_path}")