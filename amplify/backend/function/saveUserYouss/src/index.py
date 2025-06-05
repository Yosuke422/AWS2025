import json
import os
import boto3
import uuid
from boto3.dynamodb.conditions import Key # Import Key for queries

def handler(event, context):
    print("Received event:", event)

    # Check HTTP Method
    http_method = event.get('httpMethod')
    if http_method != 'POST':
        print(f"Error: Invalid HTTP method: {http_method}. Expected POST.")
        return {
            'statusCode': 405, # Method Not Allowed
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': f"Method {http_method} Not Allowed. Please use POST."})
        }

    table_name = os.environ['STORAGE_USERSYOUSS_NAME']
    dynamodb = boto3.resource('dynamodb', region_name="eu-west-1")
    table = dynamodb.Table(table_name)

    # Parse the request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        print("Error: Invalid JSON in request body.")
        return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    
    # Ensure name and email are present and valid from the parsed body
    user_name = body.get('name')
    user_email = body.get('email')

    if not user_name or not user_name.strip():
        error_message = "Missing or empty 'name' in the event payload."
        print(f"Error: {error_message}")
        return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': error_message})
        }
    user_name = user_name.strip()

    if not user_email or not user_email.strip():
        error_message = "Missing or empty 'email' in the event payload."
        print(f"Error: {error_message}")
        return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': error_message})
        }
    user_email = user_email.strip()

    if "@" not in user_email or "." not in user_email.split('@')[-1]:
        error_message = "Invalid email format."
        print(f"Error: {error_message}")
        return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': error_message})
        }

    # Check if email already exists using GSI (assuming GSI name is 'EmailIndex')
    try:
        response = table.query(
            IndexName='EmailIndex',
            KeyConditionExpression=Key('email').eq(user_email)
        )
        if response.get('Items'):
            error_message = f"User with email {user_email} already exists."
            print(f"Error: {error_message}")
            return {
                'statusCode': 409, # Conflict
                'headers': { 'Content-Type': 'application/json' },
                'body': json.dumps({'error': error_message})
            }
    except Exception as e:
        print(f"Error querying GSI for email {user_email}: {e}")
        # Depending on the error, you might want to return a 500 or allow proceeding
        # For now, let's return a 500 if GSI query fails for an unknown reason
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': 'Internal server error while checking email uniqueness'})
        }

    item_id = str(uuid.uuid4())
    item_to_save = {
        'id': item_id,
        'name': user_name,
        'email': user_email
    }

    table.put_item(Item=item_to_save)
  
    return {
        'statusCode': 200,
        'headers': { 'Content-Type': 'application/json' },
        'body': json.dumps({'message': 'User saved successfully', 'id': item_id})
    }