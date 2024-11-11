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


