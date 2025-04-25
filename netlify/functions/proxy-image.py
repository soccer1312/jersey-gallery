import requests
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse

def handler(event, context):
    try:
        # Get the image URL from the query parameters
        query_params = parse_qs(event.get('queryStringParameters', {}))
        image_url = query_params.get('url', [None])[0]
        
        if not image_url:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'No image URL provided'
                })
            }
            
        # Fetch the image
        response = requests.get(image_url, stream=True)
        
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': f'Failed to fetch image: {response.status_code}'
                })
            }
            
        # Get the content type from the response
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        # Return the image with appropriate headers
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': content_type,
                'Cache-Control': 'public, max-age=31536000'
            },
            'body': response.content,
            'isBase64Encoded': True
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': f'Error proxying image: {str(e)}'
            })
        } 