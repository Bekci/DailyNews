import os
import boto3
import requests

from datetime import datetime

def get_date_str():
    today = datetime.today()
    return "{}/{}/{}".format(today.year, today.month, today.day)

class S3Client:
    _BUCKET_NAME = "bekci-daily-news-synthesizer-bucket"
    _date_str = get_date_str()

    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def download_json_file(self, local_path: str):
        """
        Downloads the JSON file from the specified S3 bucket to the local path.
        """
        json_s3_prefix = f"outputs/{S3Client._date_str}/parsed_news.json"
        print("Downloading JSON from S3:", json_s3_prefix)
        self.s3_client.download_file(S3Client._BUCKET_NAME, json_s3_prefix, local_path)

    def download_model_files(self, local_dir: str):
        """
        Downloads the model file from the specified S3 bucket to the local path.
        """
        model_s3_prefix = "tts_model/latest/"
        print("Downloading model files..")
        
        paginator = self.s3_client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=S3Client._BUCKET_NAME, Prefix=model_s3_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                rel_path = os.path.relpath(key, model_s3_prefix)
                local_path = os.path.join(local_dir, rel_path)

                # If the key ends with "/", it's a folder — skip it
                if key.endswith("/"):
                    continue

                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                print(f"Downloading {key} → {local_path}")
                self.s3_client.download_file(S3Client._BUCKET_NAME, key, local_path)

        self.s3_client.download_file(S3Client._BUCKET_NAME, model_s3_prefix, local_path)

    def download_sample_wav(self, local_path: str):
        """
        Downloads the sample WAV file from the specified S3 bucket to the local path.
        """
        sample_wav_s3_prefix = "tts_model/samples/latest/sample.wav"
        print("Downloading the sample audio")
        self.s3_client.download_file(S3Client._BUCKET_NAME, sample_wav_s3_prefix, local_path)

    def upload_wav_file(self, local_path: str):
        """
        Uploads the generated WAV file to the S3 bucket.
        """
        s3_prefix = f"/generated/{S3Client._date_str}/news.wav"
        self.s3_client.upload_file(local_path, S3Client._BUCKET_NAME, s3_prefix)

    def upload_metadata_file(self, local_path: str):
        """
        Uploads the generated metadata json file to the S3 bucket.
        """
        s3_prefix = f"/generated/{S3Client._date_str}/inference_info.json"
        self.s3_client.upload_file(local_path, S3Client._BUCKET_NAME, s3_prefix)


class S3APIClient:
    def __init__(self):
        self.s3_client = boto3.client("s3")
    
    def download_file_with_link(self, url: str, local_path: str):
        """
        Downloads a file from a presigned URL to the local path.
        """
        print("Downloading file from URL:", url)
        response = requests.get(url)
        response.raise_for_status()
        
        with open(local_path, "wb") as f:
            f.write(response.content)
    
    def upload_file_with_link(self, local_path: str, url: str):
        """
        Uploads a file to a presigned URL.
        """
        print("Uploading file to URL:", url)
        with open(local_path, "rb") as f:
            response = requests.put(url, data=f)
            response.raise_for_status()