import boto3

from datetime import datetime

class S3Client:
    _BUCKET_NAME = "bekci-daily-news-synthesizer-bucket"
    _date_str = datetime.now().strftime("%Y_%m_%d")

    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def download_json_file(self, local_path: str):
        """
        Downloads the JSON file from the specified S3 bucket to the local path.
        """
        json_s3_prefix = f"outputs/{S3Client._date_str}/parsed_news.json"
        print("Downloading JSON from S3:", json_s3_prefix)
        self.s3_client.download_file(S3Client._BUCKET_NAME, json_s3_prefix, local_path)

    def download_model_file(self, local_path: str):
        """
        Downloads the model file from the specified S3 bucket to the local path.
        """
        model_s3_prefix = "tts_model/latest/model.pth"
        print("Downloading model..")
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
