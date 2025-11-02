import os
import boto3
import json

from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from daily_news import process_mail


def get_secret(parameter_key: str):

    ssm = boto3.client('ssm')

    try:
        api_key = ssm.get_parameter(
            Name=parameter_key, 
            WithDecryption=True
        )['Parameter']['Value']
        return api_key

    except ClientError as e:
        raise e
    
    return None
    

def upload_to_bucket(bucket_name: str, file_key:str, content:list):
    s3_client = boto3.client('s3') 
    try:
        response = s3_client.put_object(Body=json.dumps(content, indent=4, ensure_ascii=False).encode('utf-8') , Bucket=bucket_name, Key=file_key)
        print(response)
    except ClientError as e:
        print(f"Cannot upload file: {e}")
        return False
    return True
    

def lambda_handler(event, context):
    load_dotenv()
    
    run_mode = os.environ.get("RUN_MODE", "TEST")

    parsed_content = process_mail(run_mode, get_secret("mail-key"), get_secret("pinecone-key"), get_secret("google-api"))

    bucket_name = os.environ["BUCKET_NAME"]

    date_today  = datetime.today()
    key_in_bucket = f"outputs/{date_today.strftime('%Y_%m_%d')}/parsed_news.json"
    upload_success =  upload_to_bucket(bucket_name, key_in_bucket, parsed_content)

    return {
        'statusCode': 200 if upload_success else 500,
        'body': json.dumps(f'Processing mails finished: {upload_success}')
    }