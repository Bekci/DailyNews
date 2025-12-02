import torch
import numpy as np
from preprocess import chunk_text
from tqdm import tqdm
from TTS.api import TTS

class Generator:
    def __init__(self, tts_model_path:str, speaker_audio_sample_path: str):
        self._metadata = []
        self._audio_data = []
        
        self._sample_path = speaker_audio_sample_path
        self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        if not torch.cuda.is_available():
            print("CUDA is not available. Using CPU for TTS inference, which will be really slow!!")

        self._tts_model = TTS(model_path=".", config_path="./config.json", progress_bar=False).to('cuda' if torch.cuda.is_available() else 'cpu')
        # TTS(model_path="/path/to", config_path="/path/to/config.json", progress_bar=False)
        self._sample_rate = 22050

    
    def generate_audio(self, sections:list[dict[str,str]]):
        """
        Given a list of sections, feeds TTS model with each section (title and text)
        to generate an audio. 
        Stores metadata information that keeps the text provided the model and start and
        stop miliseconds in the audio file
        """
        for section in tqdm(sections):
            self._inference_text(section['section_title'])
            for news in section['text']:
                detail_text_chunks = chunk_text(news)
                for text_chunk in detail_text_chunks:
                    if len(text_chunk) > 2:
                        self._inference_text(text_chunk)
                

    def _inference_text(self, text: str):
        """
        Given a text, feeds the TTS model, save results in metadata and the audio data
        """
        
        result = self._infererence(text)
        
        start_index = len(self._audio_data)
        self._audio_data.extend(float(n) for n in result)
        end_index = len(self._audio_data)
        
        self._metadata.append({
            "text": text,
            "start_ms": int((start_index / self._sample_rate) * 1000),
            "end_ms": int((end_index / self._sample_rate) * 1000)
        })

    
    def _infererence(self, text: str):
        """
        Given a text, feeds the TTS model and returns the audio data
        """
        result = self._tts_model.tts(
            text=text,
            speaker_wav=self._sample_path,
            language="tr"
        )
        return result
    
    def get_audio_data(self) -> np.ndarray:
        """
        Returns the generated audio data as a numpy array
        """
        return np.array(self._audio_data, dtype=np.float32)
    
    def get_metadata(self) -> list[dict[str, str]]:
        """
        Returns the metadata information as a list of dictionaries
        """
        return self._metadata
    
    def get_sample_rate(self) -> int:
        """
        Returns the sample rate of the generated audio
        """
        return self._sample_rate
