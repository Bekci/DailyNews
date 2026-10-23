import argparse
import os
import json
import logging
import wave
import scipy
import numpy as np

from downloader import S3APIClient
from generator import GermanGenerator, TurkishGenerator, TTSSection

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JSON_PATH = "input.json"
SAMPLE_WAV_PATH = "sample.wav"
OUTPUT_PATH = "outputs"
OUTPUT_WAV_PATH = os.path.join(OUTPUT_PATH, "news.wav")
OUTPUT_METADATA_PATH = os.path.join(OUTPUT_PATH, "metadata.json")


def download_from_s3(
    s3_client: S3APIClient, url_config_json: str, language: str
):
    """
    Downloads the input JSON and, for Turkish synthesis, its speaker sample.
    """
    with open(url_config_json, "r", encoding="utf-8") as jf:
        config = json.load(jf)

    s3_client.download_file_with_link(config["input_json_url"], JSON_PATH)
    if language == "turkish":
        s3_client.download_file_with_link(config["sample_wav_url"], SAMPLE_WAV_PATH)


def _prepare_sections(sections: object, language: str) -> list[TTSSection]:
    title_key = "section_title_de" if language == "german" else "section_title_tr"
    text_key = language
    tts_sections: list[TTSSection] = []

    for section in sections:
        section_title = section[title_key]
        news_items = section["news"]
        texts: list[str] = []
        for news_item in news_items:
            text = (
                news_item.get(text_key) if isinstance(news_item, dict) else None
            )
            if text.strip():
                texts.append(text)

        if texts:
            tts_sections.append({"section_title": section_title, "text": texts})
    
    return tts_sections


def generate_audio_file_from_sections(
    sections: object,
    language: str,
    model_path: str | None = None,
):
    """
    Generates audio and metadata in the selected language.
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    if language == "german":
        gen = GermanGenerator()
    elif language == "turkish":
        if not model_path:
            raise ValueError("A model path is required for Turkish synthesis.")
        gen = TurkishGenerator(
            tts_model_path=model_path,
            speaker_audio_sample_path=SAMPLE_WAV_PATH,
        )
    else:
        raise ValueError("Language must be 'german' or 'turkish'.")
    gen.generate_audio(_prepare_sections(sections, language))
    
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


def upload_results_to_s3(s3_client: S3APIClient, url_config_json: str, language: str):
    """
    Uploads the generated WAV file and metadata JSON to S3.
    """
    with open(url_config_json, "r", encoding="utf-8") as jf:
        config = json.load(jf)
    
    s3_client.upload_file_with_link(OUTPUT_WAV_PATH, config[f"{language}_output_wav_url"])
    # Metadata only required for Turkish, as it is the finetuned model
    if language == "turkish":
        s3_client.upload_file_with_link(OUTPUT_METADATA_PATH, config[f"output_metadata_url"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--json-file",
        required=True,
        help="Path of the input config json file.",
    )
    p.add_argument(
        "--language",
        choices=("german", "turkish"),
        default="german",
        help="Language to synthesize (default: german).",
    )
    p.add_argument(
        "--model-path",
        help="Path to the local XTTS model; required for Turkish.",
    )
    args = p.parse_args()
    if args.language == "turkish" and not args.model_path:
        p.error("--model-path is required when --language is turkish.")

    s3_client = S3APIClient()
    
    logger.info("Downloading necessary files from S3")
    download_from_s3(s3_client, args.json_file, args.language)
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # load json content (UTF-8)
    with open(JSON_PATH, "r", encoding="utf-8") as jf:
        content = json.load(jf)

    logger.info("Generating audio...")
    generate_audio_file_from_sections(content, args.language, args.model_path)

    logger.info("Uploading results to S3")
    upload_results_to_s3(s3_client, args.json_file, args.language)


if __name__ == "__main__":
    main()
