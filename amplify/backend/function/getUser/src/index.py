import json
import os
import boto3
from boto3.dynamodb.conditions import Key

DYNAMODB_TABLE_NAME = os.environ.get('STORAGE_USERSYOUSS_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

def handler(event, context):
    print("Received event:", json.dumps(event))

    http_method = event.get('httpMethod')
    if http_method != 'GET':
        print(f"Error: Invalid HTTP method: {http_method}. Expected GET.")
        return {
            'statusCode': 405,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': f"Method {http_method} Not Allowed. Please use GET."})
        }

    path = event.get('path', '')
    path_parameters = event.get('pathParameters', {})
    user_data = None
    error_occurred = False

    try:
        if path.startswith('/usersyouss/id/') and path_parameters and 'id' in path_parameters:
            user_id = path_parameters.get('id')
            if not user_id or not user_id.strip():
                return {
                    'statusCode': 400,
                    'headers': { 'Content-Type': 'application/json' },
                    'body': json.dumps({'error': 'User ID in path cannot be empty.'})
                }
            print(f"Fetching user by ID: {user_id}")
            response = table.get_item(Key={'id': user_id})
            user_data = response.get('Item')
        
        elif path.startswith('/usersyouss/email/') and path_parameters and 'email' in path_parameters:
            user_email = path_parameters.get('email')
            if not user_email or not user_email.strip() or '@' not in user_email:
                return {
                    'statusCode': 400,
                    'headers': { 'Content-Type': 'application/json' },
                    'body': json.dumps({'error': 'Valid email in path is required.'})
                }
            print(f"Fetching user by email: {user_email} using GSI: EmailIndex")
            response = table.query(
                IndexName='EmailIndex',
                KeyConditionExpression=Key('email').eq(user_email)
            )
            if response.get('Items') and len(response.get('Items')) > 0:
                # A GSI query can return multiple items if emails are not strictly unique
                # across other potential (non-ID) attributes, or if the GSI wasn't set up for unique emails.
                # For this use case, we assume email should be unique for a user and take the first.
                user_data = response.get('Items')[0]
            else:
                user_data = None # Ensure user_data is None if no items found
        else:
            return {
                'statusCode': 400,
                'headers': { 'Content-Type': 'application/json' },
                'body': json.dumps({'error': 'Invalid path or missing ID/email in path parameters.'})
            }

    except Exception as e:
        print(f"Error accessing DynamoDB: {e}")
        error_occurred = True
        user_data = None # Ensure user_data is None on error
        # For a real application, you might want to log more details about the exception.

    if error_occurred:
         return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({'error': 'Internal server error while fetching user data.'})
        }
    
    if user_data:
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps(user_data)
        }
    else:
        return {
            'statusCode': 404,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'User not found.'})
        }