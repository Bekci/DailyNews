import argparse
import os
import json
import logging
import wave
import scipy
import numpy as np

from downloader import S3APIClient
from generator import Generator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JSON_PATH = "input.json"
SAMPLE_WAV_PATH = "sample.wav"
OUTPUT_PATH = "outputs"
OUTPUT_WAV_PATH = os.path.join(OUTPUT_PATH, "news.wav")
OUTPUT_METADATA_PATH = os.path.join(OUTPUT_PATH, "metadata.json")


def download_from_s3(s3_client: S3APIClient, url_config_json: str):
    """
    Downloads necessary files from S3.
    The files are input JSON containing the text input, TTS model, and sample WAV file for reference speaker.
    """
    with open(url_config_json, "r", encoding="utf-8") as jf:
        config = json.load(jf)

    s3_client.download_file_with_link(config["input_json_url"], JSON_PATH)
    s3_client.download_file_with_link(config["sample_wav_url"], SAMPLE_WAV_PATH)


def generate_audio_file_from_sections(model_path: str, sections: list[dict[str, str]]):
    """
    Given sections (list of dicts with 'section_title' and 'text'),
    generates audio file and metadata using the TTS model.
    """
    gen = Generator(tts_model_path=model_path, speaker_audio_sample_path=SAMPLE_WAV_PATH)
    gen.generate_audio(sections)
    
    write_wav_int16(OUTPUT_WAV_PATH, gen.get_audio_data(), gen.get_sample_rate())
    
    with open(OUTPUT_METADATA_PATH, "w", encoding="utf-8") as mf:
        json.dump(gen.get_metadata(), mf, ensure_ascii=False, indent=4)
    

def write_wav_int16(path: str, samples: np.ndarray, sample_rate: int):
    # samples expected float32 in [-1, 1] or similar; convert to int16 PCM
    clipped = np.clip(samples, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # bytes for int16
        wf.setframerate(sample_rate)
        wf.writeframes(int16.tobytes())


def save_wav(path: str, samples: np.ndarray, sample_rate: int) -> None:
    """Save float waveform to a file using Scipy.

    Args:
        wav (np.ndarray): Waveform with float values in range [-1, 1] to save.
        path (str): Path to a output file.
        sr (int, optional): Sampling rate used for saving to the file. Defaults to None.
        pipe_out (BytesIO, optional): Flag to stdout the generated TTS wav file for shell pipe.
    """
    wav_norm = samples * (32767 / max(0.01, np.max(np.abs(samples))))
    wav_norm = wav_norm.astype(np.int16)
    scipy.io.wavfile.write(path, sample_rate, wav_norm)


def upload_results_to_s3(s3_client: S3APIClient, url_config_json: str):
    """
    Uploads the generated WAV file and metadata JSON to S3.
    """
    with open(url_config_json, "r", encoding="utf-8") as jf:
        config = json.load(jf)
    
    s3_client.upload_file_with_link(OUTPUT_WAV_PATH, config["output_wav_url"])
    s3_client.upload_file_with_link(OUTPUT_METADATA_PATH, config["output_metadata_url"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-path", help="Path of the XTTS model.")
    p.add_argument("--json-file", help="Path of the input config json file.")
    args = p.parse_args()

    s3_client = S3APIClient()
    
    logger.info("Downloading necessary files from S3")
    download_from_s3(s3_client, args.json_file)
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # load json content (UTF-8)
    with open(JSON_PATH, "r", encoding="utf-8") as jf:
        content = json.load(jf)

    logger.info("Generating audio...")
    generate_audio_file_from_sections(args.model_path, content)

    logger.info("Uploading results to S3")
    upload_results_to_s3(s3_client, args.json_file)


if __name__ == "__main__":
    main()
