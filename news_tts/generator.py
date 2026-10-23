import os
from abc import ABC, abstractmethod
from typing import TypedDict

import numpy as np
import torch
from TTS.api import TTS
from tqdm import tqdm

from preprocess import chunk_text


class TTSSection(TypedDict):
    section_title: str
    text: list[str]


class Generator(ABC):
    def __init__(self) -> None:
        self._metadata: list[dict[str, str | int]] = []
        self._audio_data: list[float] = []
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._sample_rate: int

        if self._device == "cpu":
            print(
                "CUDA is not available. Using CPU for TTS inference, "
                "which will be really slow!!"
            )

    def generate_audio(self, sections: list[TTSSection]) -> None:
        """Generate audio for section titles and chunked news text."""
        for section in tqdm(sections):
            self._inference_text(section["section_title"])
            for news in section["text"]:
                for text_chunk in chunk_text(news):
                    if len(text_chunk) > 2:
                        self._inference_text(text_chunk)

    def _inference_text(self, text: str) -> None:
        result = self._infer_text(text)

        start_index = len(self._audio_data)
        self._audio_data.extend(float(sample) for sample in result)
        end_index = len(self._audio_data)

        self._metadata.append(
            {
                "text": text,
                "start_ms": int(start_index / self._sample_rate * 1000),
                "end_ms": int(end_index / self._sample_rate * 1000),
            }
        )

    @abstractmethod
    def _infer_text(self, text: str) -> list[float]:
        """Synthesize text using the model configured by the language subclass."""

    def get_audio_data(self) -> np.ndarray:
        return np.array(self._audio_data, dtype=np.float32)

    def get_metadata(self) -> list[dict[str, str | int]]:
        return self._metadata

    def get_sample_rate(self) -> int:
        return self._sample_rate


class TurkishGenerator(Generator):
    def __init__(self, tts_model_path: str, speaker_audio_sample_path: str) -> None:
        super().__init__()
        self._sample_path = speaker_audio_sample_path
        self._tts_model = TTS(
            model_path=tts_model_path,
            config_path=os.path.join(tts_model_path, "config.json"),
            progress_bar=False,
        ).to(self._device)
        self._sample_rate = self._tts_model.synthesizer.output_sample_rate

    def _infer_text(self, text: str) -> list[float]:
        return self._tts_model.tts(
            text=text,
            speaker_wav=self._sample_path,
            language="tr",
        )


class GermanGenerator(Generator):
    MODEL_NAME = "tts_models/de/thorsten/tacotron2-DDC"

    def __init__(self) -> None:
        super().__init__()
        self._tts_model = TTS(
            model_name=self.MODEL_NAME,
            progress_bar=False,
        ).to(self._device)
        self._sample_rate = self._tts_model.synthesizer.output_sample_rate

    def _infer_text(self, text: str) -> list[float]:
        return self._tts_model.tts(text=text)
