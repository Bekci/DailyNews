import os
import boto3

def get_key_from_ssm(key_name):
    """Fetch API token from AWS SSM Parameter Store once at startup"""
    ssm_client = boto3.client('ssm')
    try:
        response = ssm_client.get_parameter(
            Name=key_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve API token from SSM Parameter Store: {str(e)}")
