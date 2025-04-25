from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import parse_qs

def handler(event, context):
    try:
        # Set up CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }
        
        # Get the jerseys.json file path relative to the function
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'jerseys.json')
        
        # Check if file exists
        if not os.path.exists(json_path):
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'No jerseys data found.'
                })
            }
            
        # Read and parse JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
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
            'headers': headers,
            'body': json.dumps(gallery_data)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Error loading gallery: {str(e)}'
            })
        } 