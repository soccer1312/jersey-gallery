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

        # Print current directory and list files for debugging
        current_dir = os.getcwd()
        files = os.listdir(current_dir)
        
        # Try to find jerseys.json in current directory or parent
        json_path = 'jerseys.json'
        if not os.path.exists(json_path):
            json_path = os.path.join('..', 'jerseys.json')
            
        if not os.path.exists(json_path):
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': f'No jerseys data found. Current directory: {current_dir}, Files found: {files}'
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
                'images': jersey['images'],  # Temporarily return direct URLs for testing
                'thumbnail': jersey['thumbnail'],  # Temporarily return direct URL for testing
                'description': jersey['description']
            } for jersey in data['jerseys']]
        }
            
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(gallery_data)
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
                'error': f'Error loading gallery: {str(e)}',
                'details': error_details
            })
        } 