import json
import os
from http.server import BaseHTTPRequestHandler

def handler(event, context):
    try:
        if not os.path.exists('jerseys.json'):
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'No jerseys data found.'
                })
            }
            
        with open('jerseys.json', 'r', encoding='utf-8') as f:
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
            'body': json.dumps(gallery_data)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 