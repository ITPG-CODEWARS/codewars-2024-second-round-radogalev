from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from postgrest.exceptions import APIError
from urllib.parse import urlparse
from datetime import datetime
import qrcode
import base64
from io import BytesIO
from config import Config

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('app_secret_key')

supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# In-memory storage for shortened URLs (temporary)
shortened_urls = {}


# Function to validate the url before processing
def validate_url(url):
    """Validate URL and return error message if invalid."""
    if not url or url == "None":
        return "Long URL cannot be empty. Please provide a valid URL."
    
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return "Invalid URL. Please make sure the URL starts with 'http://' or 'https://'"
    
    return None


@app.route('/api/validate-custom-url/<custom_url>', methods=['GET'])
def validate_custom_url(custom_url):
    try:
        response = supabase.table('url_data').select('id').eq('short_url', custom_url).execute()
        is_available = len(response.data) == 0
        return jsonify({'available': is_available})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Function to generate the short url sequence of characters
def generate_short_url(length=6):
    """Generate a random short URL."""
    chars = string.ascii_letters + string.digits
    short_url = "".join(random.choice(chars) for _ in range(length))
    return short_url

# Function to intiliaze the shortened url
@app.route('/shorten', methods=['POST'])
def shorten_url():
    long_url = request.form.get('long_url')
    custom_short_url = request.form.get('custom_short_url', '').strip()
    short_url_length = request.form.get('short_url_length', type=int)
    
    if not long_url:
        return jsonify({"error": "No URL provided"}), 400

    error_message = validate_url(long_url)
    if error_message:
        return {'error': error_message}

    if custom_short_url:
        response = supabase.table('url_data').select('short_url').eq('short_url', custom_short_url).execute()
        if response.data:
            return {'error': f"Error: '{custom_short_url}' is already taken."}
        short_url = custom_short_url
    elif short_url_length:
        short_url = generate_short_url(short_url_length)
        while True:
            response = supabase.table('url_data').select('short_url').eq('short_url', short_url).execute()
            if not response.data:
                break
            short_url = generate_short_url(short_url_length)
    else:
        short_url = generate_short_url()
        while True:
            response = supabase.table('url_data').select('short_url').eq('short_url', short_url).execute()
            if not response.data:
                break
            short_url = generate_short_url()

    try:
        response = supabase.table('url_data').insert({
            'user_id': session.get('user_id'),
            'long_url': long_url,
            'short_url': short_url,
            'number_of_clicks': 0,
            'created_at': datetime.now().isoformat()
        }).execute()
        
        full_short_url = f"{request.url_root}{short_url}"
        return {'short_url': full_short_url}
    except Exception as e:
        return {'error': str(e)}


