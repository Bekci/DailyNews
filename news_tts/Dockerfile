ARG BASE=nvidia/cuda:11.8.0-runtime-ubuntu22.04
FROM ${BASE}

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc g++ make python3 python3-dev python3-pip python3-venv python3-wheel \
        espeak-ng libsndfile1-dev git && \
    rm -rf /var/lib/apt/lists/*

# Install Dependencies:
RUN pip3 install --no-cache-dir \
    llvmlite \
    torch torchaudio --extra-index-url https://download.pytorch.org/whl/cu118 \
    tqdm
    
# Copy TTS repository contents:
WORKDIR /root
COPY TTS /root/TTS
COPY . /root
COPY tts_model_files/config.json /root
COPY tts_model_files/vocab.json /root

WORKDIR /root/TTS
RUN make install

WORKDIR /root

ENTRYPOINT ["python3", "/root/generate_main.py"]