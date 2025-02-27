import requests
import time
from datetime import datetime
import json
import os

# Globals used by the Frontend
tracked_skins = {}  # Dictionary to store skin names and their thresholds
saved_skins = []    # List for saved skin data

def fetch_skins(limit=50):
    url = f"https://listing.bynogame.net/api/listings/cs2?page=0&limit={limit}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.bynogame.com',
        'Referer': 'https://www.bynogame.com/'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        listings = data.get("payload", [])
        return listings[::-1]  # Reverse to get newest first
    except requests.exceptions.Timeout:
        print("Request timed out.")
        return []
    except requests.exceptions.ConnectionError:
        print("Connection error.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching skins: {e}")
        return []
def save_tracked_skins():
    try:
        with open('tracked_skins.json', 'w') as f:
            json.dump(tracked_skins, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving tracked skins: {e}")
        return False

def save_saved_skins():
    try:
        with open('saved_skins.json', 'w') as f:
            json.dump(saved_skins, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving saved skins: {e}")
        return False

def load_tracked_skins():
    """Load tracked skins from JSON file"""
    global tracked_skins
    try:
        if os.path.exists('tracked_skins.json'):
            with open('tracked_skins.json', 'r') as f:
                tracked_skins = json.load(f)
            return True
        return False
    except Exception as e:
        print(f"Error loading tracked skins: {e}")
        return False

def load_saved_skins():
    """Load saved skins from JSON file"""
    global saved_skins
    try:
        if os.path.exists('saved_skins.json'):
            with open('saved_skins.json', 'r') as f:
                saved_skins = json.load(f)
            return True
        return False
    except Exception as e:
        print(f"Error loading saved skins: {e}")
        return False

def initialize_data():
    """Initialize application data by loading saved files"""
    load_tracked_skins()
    load_saved_skins()

