import json
import os
from urllib.parse import quote

def handler(event, context):
    """Netlify function handler for the API endpoint"""
    try:
        # Set up CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }
        
        # Get the jerseys.json file path
        json_path = 'jerseys.json'  # File should be in the publish directory
        
        # Check if file exists
        if not os.path.exists(json_path):
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'No jerseys data found. Please ensure jerseys.json exists.'
                })
            }
            
        # Read and parse JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Transform data for frontend and proxy the images
        gallery_data = {
            'jerseys': [{
                'name': jersey['title'],
                'url': jersey['url'],
                'images': [f'/.netlify/functions/proxy-image?url={quote(img)}' for img in jersey['images']],
                'thumbnail': f'/.netlify/functions/proxy-image?url={quote(jersey["thumbnail"])}',
                'description': jersey['description']
            } for jersey in data['jerseys']]
        }
            
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(gallery_data)
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