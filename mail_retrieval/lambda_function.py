import os
import boto3
import json

from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from daily_news import process_mail


def get_secret():
    secret_name = os.environ["SECRET_NAME"]
    region_name = os.environ["REGION"]

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret_res = json.loads(get_secret_value_response["SecretString"])
    return secret_res


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
    key_result = get_secret()

    run_mode = os.environ.get("RUN_MODE", "TEST")
    bucket_name = os.environ["BUCKET_NAME"]

    parsed_content = process_mail(run_mode, key_result["MAIL_PASS"], key_result["PINECONE_API_KEY"], key_result["GOOGLE_API_KEY"])

    date_today  = datetime.today()
    key_in_bucket = f"outputs/{date_today.strftime('%Y_%m_%d')}/parsed_news.json"
    upload_success =  upload_to_bucket(bucket_name, key_in_bucket, parsed_content)

    return {
        'statusCode': 200 if upload_success else 500,
        'body': json.dumps(f'Processing mails finished: {upload_success}')
    }
