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


# Function to delete a row from the dashboard table and from the database
@app.route('/api/url/<url_id>', methods=['DELETE'])
def delete_url(url_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        url_response = supabase.table("url_data").select('*').eq("id", url_id).eq("user_id", session['user_id']).execute()

        if not url_response.data:
            return jsonify({"error": "URL not found or unauthorized"}), 404

        delete_response = supabase.table("url_data").delete().eq("id", url_id).execute()

        if delete_response.data:
            return jsonify({"message": "URL deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete URL"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Function to get the details of the url
@app.route('/api/url/<url_id>', methods=['GET'])
def get_url_details(url_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        response = supabase.table('url_data').select('*').eq('id', url_id).execute()
        if not response.data:
            return jsonify({'error': 'URL not found'}), 404
        
        url_data = response.data[0]
        if url_data['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 401
        
        return jsonify({
            'clicks': url_data['number_of_clicks'],
            'click_limit': url_data.get('click_limit'),
            'end_date': url_data.get('end_date'),
            'password_protected': bool(url_data.get('password')),
            'short_url': url_data['short_url']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Function to update the url in the dasboard
@app.route('/api/url/<url_id>/update', methods=['POST'])
def update_url_settings(url_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        existing_url = supabase.table('url_data').select('*').eq('id', url_id).eq('user_id', session['user_id']).execute()
        
        if not existing_url.data:
            return jsonify({'error': 'URL not found or unauthorized'}), 404
            
        existing_data = existing_url.data[0]
        data = request.json
        update_data = {}
        
        if 'click_limit' in data:
            try:
                update_data['click_limit'] = int(data['click_limit']) if data['click_limit'] else None
            except ValueError:
                return jsonify({'error': 'Invalid click limit value'}), 400
        
        if 'end_date' in data:
            if data['end_date']:
                try:
                    datetime.strptime(data['end_date'], '%Y-%m-%d')
                    update_data['end_date'] = data['end_date']
                except ValueError:
                    return jsonify({'error': 'Invalid date format'}), 400
            else:
                update_data['end_date'] = None
        
        if 'password' in data:
            update_data['password'] = generate_password_hash(data['password']) if data['password'] else None
        
        if 'custom_url' in data and data['custom_url']:
            check_response = supabase.table('url_data').select('id').eq('short_url', data['custom_url']).execute()
            if check_response.data and str(check_response.data[0]['id']) != url_id:
                return jsonify({'error': 'Custom URL already taken'}), 400
            update_data['short_url'] = data['custom_url']
        else:
            update_data['short_url'] = existing_data['short_url']
        
        response = supabase.table('url_data').update(update_data).eq('id', url_id).eq('user_id', session['user_id']).execute()
        
        if not response.data:
            return jsonify({'error': 'Failed to update URL'}), 500
            
        return jsonify({'message': 'URL settings updated successfully', 'data': response.data[0]})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Function to generate the qr code
@app.route('/api/url/<url_id>/qr', methods=['GET'])
def generate_qr_code(url_id):
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}, 401
    
    try:
        response = supabase.table('url_data').select('short_url').eq('id', url_id).eq('user_id', session['user_id']).execute()
        if not response.data:
            return {'error': 'URL not found or unauthorized'}, 404
        
        short_url = f"{request.url_root}{response.data[0]['short_url']}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(short_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {'qr_code': f'data:image/png;base64,{img_str}'}
    except Exception as e:
        return {'error': str(e)}, 500

# Function to register a user
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error_message = "Passwords do not match. Please try again."
        else:
            response = supabase.table('users').select('*').eq('username', username).execute()
            if response.data:
                error_message = "User already exists"
            else:
                hashed_password = generate_password_hash(password)
                supabase.table('users').insert({
                    'username': username,
                    'password': hashed_password
                }).execute()
                return redirect(url_for('login'))

    return render_template('register.html', error_message=error_message)


#Function to log in a user
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = supabase.table('users').select('*').eq('username', username).execute()
        user = response.data[0] if response.data else None

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            error_message = "Invalid username or password"

    return render_template('login.html', error_message=error_message)

