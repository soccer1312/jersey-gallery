import json
import logging
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_session():
    session = requests.Session()
    session.verify = False  # Disable SSL verification
    
    # Configure retry strategy
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    # Add retry adapter to session
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers to mimic a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1'
    })
    
    return session

def safe_request(session, url, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            time.sleep(delay * (attempt + 1))
    return None

def extract_title(soup):
    """Extract a meaningful title from the page."""
    # Try to get the title from album_main first
    album_main = soup.find('a', class_='album_main')
    if album_main:
        title = album_main.get('title')
        if title and title != "2" and title != "1":
            return title

    # Try text_overflow_album_title
    title_element = soup.find('div', class_='text_overflow_album_title')
    if title_element:
        title = title_element.get_text(strip=True)
        if title and title != "2" and title != "1":
            return title

    return "Untitled Jersey"

def find_images(soup, base_url):
    """Try different selectors to find images."""
    images = []
    
    # Look for img tags with photo.yupoo.com URLs
    img_elements = soup.find_all('img', src=lambda x: x and 'photo.yupoo.com' in x)
    
    for img in img_elements:
        src = img.get('src')
        if src:
            # Make sure URL is absolute
            if src.startswith('//'):
                src = 'https:' + src
            elif not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            
            # Try to get highest quality version
            if '/medium.' in src:
                # Try big first, then original
                big_src = src.replace('/medium.', '/big.')
                original_src = src.replace('/medium.', '/original.')
                
                try:
                    # Try big version first
                    response = requests.head(big_src, verify=False, timeout=5)
                    if response.status_code == 200:
                        images.append(big_src)
                        continue
                        
                    # If big fails, try original
                    response = requests.head(original_src, verify=False, timeout=5)
                    if response.status_code == 200:
                        images.append(original_src)
                        continue
                except:
                    pass
                    
                # If both fail, use medium
                images.append(src)
            elif '/small.' in src:
                # Try to upgrade small to better quality
                better_src = src.replace('/small.', '/medium.')
                try:
                    response = requests.head(better_src, verify=False, timeout=5)
                    if response.status_code == 200:
                        images.append(better_src)
                    else:
                        images.append(src)
                except:
                    images.append(src)
            else:
                images.append(src)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_images = []
    for img in images:
        if img not in seen:
            seen.add(img)
            unique_images.append(img)
    
    return unique_images

def scrape_jerseys():
    jerseys = []
    base_url = 'https://huahetian.x.yupoo.com'
    total_pages = 59
    
    try:
        session = create_session()
        
        # Iterate through all pages
        for page in range(1, total_pages + 1):
            logger.info(f"Processing page {page}/{total_pages}")
            
            # Get the categories page with page number
            page_url = f"{base_url}/categories?page={page}"
            logger.info(f"Fetching page: {page_url}")
            
            response = safe_request(session, page_url)
            if not response:
                logger.error(f"Failed to fetch page {page}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.info(f"Successfully parsed page {page}")
            
            # Find all album links using the exact structure we see
            logger.info("Looking for album links...")
            album_links = soup.find_all('a', class_='album_main', href=lambda x: x and '/albums/' in x)
            
            if not album_links:
                logger.warning("No album_main links found, trying alternative selectors...")
                album_links = soup.find_all('a', href=lambda x: x and '/albums/' in x)
            
            album_urls = []
            for link in album_links:
                try:
                    url = urljoin(base_url, link.get('href'))
                    title = link.get('title', '')
                    if url and '/albums/' in url:
                        album_urls.append((url, title))
                        logger.info(f"Found album: {title} - {url}")
                except Exception as e:
                    logger.warning(f"Failed to get album URL: {str(e)}")
                    continue
            
            logger.info(f"Found {len(album_urls)} album URLs on page {page}")
            
            # Process each album on this page
            for i, (url, initial_title) in enumerate(album_urls, 1):
                try:
                    logger.info(f"Processing album {i}/{len(album_urls)} on page {page}: {url}")
                    
                    # Get the album page
                    response = safe_request(session, url)
                    if not response:
                        logger.error(f"Failed to fetch album page: {url}")
                        continue
                    
                    album_soup = BeautifulSoup(response.text, 'html.parser')
                    logger.info(f"Successfully parsed album page")
                    
                    # Get the title, using the initial title as fallback
                    title = extract_title(album_soup) or initial_title
                    if title == "Untitled Jersey" and initial_title:
                        title = initial_title
                    logger.info(f"Extracted title: {title}")
                    
                    # Get all images
                    images = find_images(album_soup, base_url)
                    logger.info(f"Found {len(images)} images")
                    
                    # Get description if available
                    description = ""
                    try:
                        desc_elem = album_soup.find(class_='album__desc')
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)
                        logger.info(f"Found description: {description[:100]}...")
                    except Exception as e:
                        logger.warning(f"Could not get description: {str(e)}")
                    
                    jersey = {
                        "title": title,
                        "url": url,
                        "images": images,
                        "thumbnail": images[0] if images else "",
                        "description": description,
                        "page": page  # Add page number to help with frontend pagination
                    }
                    
                    jerseys.append(jersey)
                    logger.info(f"Added jersey: {title} with {len(images)} images")
                    
                    # Save progress after each jersey
                    try:
                        result = {
                            "total": len(jerseys),
                            "total_pages": total_pages,
                            "jerseys": jerseys
                        }
                        with open('jerseys.json', 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        logger.info("Progress saved to jerseys.json")
                    except Exception as e:
                        logger.error(f"Error saving progress: {str(e)}")
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error processing album {url}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing album {url}: {str(e)}")
                    continue
                
                time.sleep(2)  # Delay between albums
            
            # Add a delay between pages
            time.sleep(5)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Fatal request error: {str(e)}")
    except Exception as e:
        logger.error(f"Fatal error during scraping: {str(e)}")
    
    logger.info(f"Scraping completed. Found {len(jerseys)} jerseys across {total_pages} pages.")
    return jerseys

if __name__ == "__main__":
    scrape_jerseys() 