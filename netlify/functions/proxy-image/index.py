import json
import os
import requests
from urllib.parse import quote, unquote

def handler(event, context):
    """Netlify function handler for the proxy-image endpoint"""
    try:
        # Set up CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }

        # Get the image URL from the path
        path = event.get('path', '')
        image_url = unquote(path.split('/proxy/image/')[-1])
        
        if not image_url:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'No image URL provided'
                })
            }
            
        # Fetch the image
        response = requests.get(image_url, stream=True)
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Failed to fetch image: {response.status_code}'
                })
            }
            
        # Return the image with appropriate headers
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': response.headers.get('Content-Type', 'image/jpeg'),
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=31536000'
            },
            'body': response.content,
            'isBase64Encoded': True
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Error proxying image: {str(e)}',
                'details': error_details
            })
        } 