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
    
    
def upload_to_bucket(bucket_name: str, file_key:str, file_name: str):
    s3_client = boto3.client('s3') 
    try:
        response = s3_client.upload_file(file_name, bucket_name, "{}/{}".format(file_key, file_name))
        print(response)
    except ClientError as e:
        print(f"Cannot upload file: {e}")
        return False
    return True
    

def lambda_handler(event, context):
    load_dotenv()
    
    run_mode = os.environ.get("RUN_MODE", "TEST")

    result_file_name = process_mail(run_mode, get_secret("mail-key"), get_secret("pinecone-key"), get_secret("google-api"))

    if not os.path.exists(result_file_name):
        raise Exception("The output file is not generated!")

    bucket_name = os.environ["BUCKET_NAME"]
    date_today  = datetime.today()
    key_in_bucket = f"outputs/{date_today.strftime('%Y_%m_%d')}"
    upload_success =  upload_to_bucket(bucket_name, key_in_bucket, result_file_name)

    return {
        'statusCode': 200 if upload_success else 500,
        'body': json.dumps(f'Processing mails finished: {upload_success}')
    }
