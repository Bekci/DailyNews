import boto3
import datetime

dynamo_client = boto3.resource('dynamodb', region_name="eu-central-1")

conversations_table = dynamo_client.Table("UlakConversations")
history_table = dynamo_client.Table("UlakHistory")

def get_conversations_by_user(user_id):
    response = conversations_table.query(
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={
            ':pk': "USER#{}".format(user_id)
        },
        ScanIndexForward=False
    )
    return response.get("Items", [])


def save_conversation(conversation_id, user_id, question):
    created_at = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    conversations_table.put_item(
        Item={
            'PK': "USER#{}".format(user_id),
            'SK': "CREATEDAT#{}".format(created_at),
            'conversation_id': conversation_id,
            'user_id': user_id,
            'first_question': question,
            'created_at': created_at
        }
    )
    return created_at


def get_messages_by_conversation(conversation_id):
    response = history_table.query(
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={
            ':pk': "CONVERSATION#{}".format(conversation_id)
        },
        ScanIndexForward=True
    )
    return response.get("Items", [])


def save_message(conversation_id, role, message):
    created_at = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    history_table.put_item(
        Item={
            'PK': "CONVERSATION#{}".format(conversation_id),
            'SK': "CREATEDAT#{}".format(created_at),
            'conversation_id': conversation_id,
            'role': role,
            'message': message,
            'created_at': created_at
        }
    )
