import os
import boto3

def get_secret(parameter_key: str):

    ssm = boto3.client('ssm')

    try:
        api_key = ssm.get_parameter(
            Name=parameter_key, 
            WithDecryption=True
        )['Parameter']['Value']
        return api_key

    except Exception as e:
        print(f"Error getting secret: {parameter_key} from SSM:", e)
        raise e
    
    return None

# Set Kaggle config directory to /tmp/ for AWS Lambda environment
# Add kaggle.json to the /tmp/ directory during runtime
os.environ["KAGGLE_CONFIG_DIR"] = "/tmp/"


# Set kaggle environment variables
os.environ["KAGGLE_USERNAME"] = get_secret("kaggle-username")
os.environ["KAGGLE_KEY"] = get_secret("kaggle-key")
os.environ["KAGGLE_API_TOKEN"] = get_secret("kaggle-api-token")

import json
import shutil
import subprocess
import zipfile

from datetime import datetime
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from daily_news import process_mail
from kaggle_exporter import KaggleAPI

DOWNLOAD_EXPIRES_IN = 60 * 10  # 10 minutes
UPLOAD_EXPIRES_IN = 60 * 60  # 60 minutes

SAMPLE_WAV_FILE_KEY = "tts_model/samples/latest/sample.wav"
TMP_DATASET_PATH = "/tmp"
TMP_NOTEBOOK_PATH = "/tmp/xtts-inference"


    

def upload_to_bucket(bucket_name: str, file_key:str, content:list):
    s3_client = boto3.client('s3') 
    try:
        response = s3_client.put_object(Body=json.dumps(content, indent=4, ensure_ascii=False).encode('utf-8') , Bucket=bucket_name, Key=file_key)
        print(response)
    except ClientError as e:
        print(f"Cannot upload file: {e}")
        return False
    return True

def generate_s3_download_link(bucket_name: str, file_key: str):
    s3 = boto3.client("s3")

    download_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": file_key},
        ExpiresIn=DOWNLOAD_EXPIRES_IN
    )
    return download_url

def generate_s3_upload_link(bucket_name: str, file_key: str):
    s3 = boto3.client("s3")

    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket_name, "Key": file_key},
        ExpiresIn=UPLOAD_EXPIRES_IN
    )
    return upload_url


def upload_dataset_kaggle(bucket_name: str, json_file_key: str):
    print("Uploading dataset to Kaggle...")
    kaggle_api = KaggleAPI(dataset_path=TMP_DATASET_PATH, notebook_path=TMP_NOTEBOOK_PATH)

    kaggle_api.download_dataset()
    print("Downloaded the current dataset")

    # Replace input_url in config.json with the new S3 presigned URLs
    dataset_download_path = replace_input_url_config(bucket_name, json_file_key)
    print(f"URL file replaced in {dataset_download_path}/config.json")
    # Zip the content of the dataset_download_path
    current_working_directory = os.getcwd()
    
    os.chdir(dataset_download_path)
    create_zip("daily-news-inference.zip", ".", ".")
    os.chdir(current_working_directory)

    # Remove all files under than zip
    for file_name in os.listdir(dataset_download_path):
        if not file_name.endswith(".zip"):
            os.remove(os.path.join(dataset_download_path, file_name))

    shutil.copyfile(os.path.join("kaggle_configs", "dataset-metadata.json"), os.path.join(dataset_download_path, "dataset-metadata.json"))
    print("Files are prepared for upload")

    kaggle_api.upload_dataset(dataset_download_path)
    print("Uploaded the new dataset to Kaggle")

def replace_input_url_config(bucket_name: str, json_file_key: str):
    fname = os.path.basename(json_file_key)
    
    dataset_config = {
        "input_json_url": generate_s3_download_link(bucket_name, json_file_key),
        "sample_wav_url": generate_s3_download_link(bucket_name, SAMPLE_WAV_FILE_KEY),
        "output_wav_url": generate_s3_upload_link(bucket_name, json_file_key.replace(fname, "news.wav")),
        "output_metadata_url": generate_s3_upload_link(bucket_name, json_file_key.replace(fname, "output_metadata.json")),
    }
    
    for root, _, files in os.walk(TMP_DATASET_PATH):
        for fname in files:
            if fname == "config.json":
                path = os.path.join(root, fname)
                os.remove(path)
                with open(os.path.join(path), "w", encoding="utf-8") as f:
                    json.dump(dataset_config, f, indent=4, ensure_ascii=False)
    return root

def create_zip(zip_name: str, parent_path: str, source_dir):
    zip_path = os.path.join(parent_path, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, source_dir)
                zipf.write(full_path, arcname)
    return zip_path

def start_kaggle_notebook():
    kaggle_api = KaggleAPI(dataset_path=TMP_DATASET_PATH, notebook_path=TMP_NOTEBOOK_PATH)

    kaggle_api.download_notebook()

    shutil.copyfile(os.path.join("kaggle_configs", "kernel-metadata.json"), os.path.join(TMP_NOTEBOOK_PATH, "kernel-metadata.json"))

    kaggle_api.upload_notebook()


def lambda_handler(event, context):
    load_dotenv()
    
    run_mode = os.environ.get("RUN_MODE", "TEST")
    print(f"Runing mode: {run_mode}")

    parsed_content = process_mail(run_mode, get_secret("mail-key"), get_secret("pinecone-key"), get_secret("google-api"))

    bucket_name = os.environ["BUCKET_NAME"]

    date_today  = datetime.today()
    key_in_bucket = f"outputs/{date_today.year}/{date_today.month}/{date_today.day}/parsed_news.json"
    upload_success =  upload_to_bucket(bucket_name, key_in_bucket, parsed_content)

    if upload_success:
        upload_dataset_kaggle(bucket_name, key_in_bucket)
        start_kaggle_notebook()

    return {
        'statusCode': 200 if upload_success else 500,
        'body': json.dumps(f'Processing mails finished: {upload_success}')
    }