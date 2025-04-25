import json
import requests
import base64

def handler(event, context):
    """Netlify function handler for proxying images"""
    try:
        # Get the image URL from the query parameters
        query_params = event.get('queryStringParameters', {})
        if not query_params or 'url' not in query_params:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No image URL provided'
                })
            }
            
        image_url = query_params['url']
            
        # Fetch the image
        response = requests.get(image_url)
        
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Failed to fetch image: {response.status_code}'
                })
            }
            
        # Get the content type from the response
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        # Convert image content to base64
        image_content = response.content
        base64_content = base64.b64encode(image_content).decode('utf-8')
        
        # Return the image with appropriate headers
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': content_type,
                'Cache-Control': 'public, max-age=31536000',
                'Access-Control-Allow-Origin': '*'
            },
            'body': base64_content,
            'isBase64Encoded': True
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Error proxying image: {str(e)}'
            })
        } 