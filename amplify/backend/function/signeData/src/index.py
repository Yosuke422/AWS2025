import json
import os
import boto3
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
table = dynamodb.Table(os.environ['STORAGE_TABLECRYPTOPRICES_NAME'])
bucket_name = os.environ['STORAGE_STORAGEEXPORTCRYPTO_BUCKETNAME']

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj

def handler(event, context):
    try:
        # Scan DynamoDB table
        response = table.scan()
        items = response['Items']
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Clean data (convert Decimal to float)
        cleaned_items = decimal_to_float(items)
        
        # Sort data by timestamp
        sorted_items = sorted(cleaned_items, key=lambda x: x['timestamp'])
        
        # Generate timestamp for filename
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')
        filename = f'crypto_{timestamp}.json'
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=f'exports/{filename}',
            Body=json.dumps(sorted_items),
            ContentType='application/json'
        )
        
        # Generate pre-signed URL (valid for 1 hour)
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': f'exports/{filename}'
            },
            ExpiresIn=3600
        )
        
        # Check if the request wants HTML response
        if event.get('headers', {}).get('Accept') == 'text/html':
            html_response = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Crypto Export</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .button {{ 
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        margin-top: 20px;
                    }}
                    .info {{ margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Crypto Data Export</h1>
                    <div class="info">
                        <p>Your export is ready! Click the button below to download the data.</p>
                        <p>This link will expire in 1 hour.</p>
                    </div>
                    <a href="{presigned_url}" class="button">Download Export</a>
                </div>
            </body>
            </html>
            """
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': html_response
            }
        
        # Return JSON response
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'message': 'Export successful',
                'downloadUrl': presigned_url,
                'expiresIn': 3600,
                'filename': filename
            })
        }
        
    except ClientError as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'error': 'Failed to process export'
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'error': 'An unexpected error occurred'
            })
        }