from flask import Flask, jsonify, render_template, send_file, request
import os
import json
import requests
from urllib.parse import unquote
import io

app = Flask(__name__, template_folder='.')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/proxy/image')
def proxy_image():
    try:
        # Get the encoded URL from query parameter
        encoded_url = request.args.get('url')
        if not encoded_url:
            return 'No URL provided', 400
            
        # Decode the URL
        image_url = unquote(encoded_url)
        
        # Add headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://huahetian.x.yupoo.com/'
        }
        
        # Get the image
        response = requests.get(image_url, headers=headers, verify=False)
        response.raise_for_status()
        
        # Create file-like object from image data
        image_data = io.BytesIO(response.content)
        
        # Determine content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        # Send the image
        return send_file(
            image_data,
            mimetype=content_type
        )
        
    except Exception as e:
        return str(e), 500

@app.route('/api/gallery')
def get_gallery():
    try:
        if not os.path.exists('jerseys.json'):
            return jsonify({
                'error': 'No jerseys data found. Please run the scraper first.'
            }), 404
            
        with open('jerseys.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract categories from jersey titles
        categories = set()
        for jersey in data['jerseys']:
            title = jersey['title']
            # Add main categories based on jersey titles
            if 'Retro' in title:
                categories.add('Retro')
            if any(team in title for team in ['Manchester', 'Inter Milan', 'Celtic', 'Ajax', 'Bayern']):
                categories.add('Club Teams')
            if 'Special Edition' in title or 'Concept Edition' in title:
                categories.add('Special Editions')
            if 'KIDS' in title:
                categories.add('Kids')
            
        # Transform data for frontend and proxy the images
        gallery_data = {
            'categories': [{'name': cat} for cat in sorted(categories)],
            'jerseys': [{
                'name': jersey['title'],
                'url': jersey['url'],
                'images': [f'/proxy/image?url={requests.utils.quote(img)}' for img in jersey['images']],
                'thumbnail': f'/proxy/image?url={requests.utils.quote(jersey["thumbnail"])}',
                'description': jersey['description'],
                'category': next((cat for cat in categories if cat in jersey['title']), 'Other')
            } for jersey in data['jerseys']]
        }
            
        return jsonify(gallery_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting server on http://localhost:5000")
    print("Available endpoints:")
    print("  - Home page: http://localhost:5000/")
    print("  - Gallery API: http://localhost:5000/api/gallery")
    print("  - Image Proxy: http://localhost:5000/proxy/image?url=...")
    app.run(host='0.0.0.0', port=5000, debug=True) 