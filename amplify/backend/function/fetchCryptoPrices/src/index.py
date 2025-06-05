import json
import os
import boto3
import requests
from datetime import datetime
from dateutil import parser
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['STORAGE_TABLECRYPTOPRICES_NAME'])

def handler(event, context):
    try:
        # Fetch top 50 cryptocurrencies by market cap
        response = requests.get(
            'https://api.coingecko.com/api/v3/coins/markets',
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 50,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '24h'
            }
        )
        response.raise_for_status()
        crypto_data = response.json()
        
        # Get current timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Store each crypto price in DynamoDB
        for crypto in crypto_data:
            item = {
                'crypto_id': crypto['id'],
                'timestamp': timestamp,
                'name': crypto['name'],
                'symbol': crypto['symbol'].upper(),
                'price': Decimal(str(crypto['current_price'])),
                'market_cap': Decimal(str(crypto['market_cap'])) if crypto.get('market_cap') is not None else None,
                'market_cap_rank': Decimal(str(crypto['market_cap_rank'])) if crypto.get('market_cap_rank') is not None else None,
                'price_change_24h': Decimal(str(crypto['price_change_percentage_24h'])) if crypto.get('price_change_percentage_24h') is not None else None
            }
            
            # Remove None values before putting to avoid DynamoDB errors
            item = {k: v for k, v in item.items() if v is not None}
            
            table.put_item(Item=item)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'message': 'Successfully fetched and stored top 50 crypto prices',
                'timestamp': timestamp,
                'count': len(crypto_data)
            })
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'error': 'Failed to fetch crypto prices from CoinGecko'
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