import os
import boto3
import json

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



def lambda_handler(event, context):
    load_dotenv()
    key_result = get_secret()
    result = process_mail(key_result["MAIL_PASS"], key_result["PINECONE_API_KEY"], key_result["GOOGLE_API_KEY"])
    return {
        'statusCode': 200,
        'body': json.dumps(f'Processing mails finished with: {result}')
    }
