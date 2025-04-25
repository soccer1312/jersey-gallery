import json
import os
from http.server import BaseHTTPRequestHandler

def handler(event, context):
    try:
        # Check if file exists
        if not os.path.exists('jerseys.json'):
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No jerseys data found.'
                })
            }
            
        # Read file in binary mode first to check for BOM
        with open('jerseys.json', 'rb') as f:
            content = f.read()
            # Remove BOM if present
            if content.startswith(b'\xef\xbb\xbf'):
                content = content[3:]
            # Decode to string
            content = content.decode('utf-8')
            
        # Parse JSON
        data = json.loads(content)
            
        # Transform data for frontend
        gallery_data = {
            'jerseys': [{
                'name': jersey['title'],
                'url': jersey['url'],
                'images': jersey['images'],
                'thumbnail': jersey['thumbnail'],
                'description': jersey['description']
            } for jersey in data['jerseys']]
        }
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(gallery_data)
        }
    except json.JSONDecodeError as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Invalid JSON format: {str(e)}',
                'location': f'Error at line {e.lineno}, column {e.colno}'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Error loading gallery: {str(e)}'
            })
        } 