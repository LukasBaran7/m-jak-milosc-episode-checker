import json
import os
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SHOW_URL = "https://vod.tvp.pl/api/products/vods/serials/274703/seasons/1251177/episodes?lang=PL&platform=BROWSER"
MONGODB_URL = os.getenv('MONGODB_URL')
DATABASE_NAME = os.getenv('DATABASE_NAME')

def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(MONGODB_URL)
    return client[DATABASE_NAME]

def fetch_episodes() -> list:
    """Fetch episodes data from the API"""
    response = requests.get(SHOW_URL)
    response.raise_for_status()
    episodes = response.json()
    # Sort episodes by number in descending order to get the latest first
    return sorted(episodes, key=lambda x: x['number'], reverse=True)

def get_last_checked_episode() -> int:
    """Get the last checked episode number from MongoDB"""
    db = get_db()
    state = db.episode_state.find_one({"_id": "last_episode"})
    return state["episode_number"] if state else 0

def save_last_checked_episode(episode_number: int):
    """Save the last checked episode number to MongoDB"""
    db = get_db()
    db.episode_state.update_one(
        {"_id": "last_episode"},
        {"$set": {
            "episode_number": episode_number,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )

def send_email(episode_info: dict):
    """Send email notification about new episode"""
    sender = os.getenv('EMAIL_SENDER')
    password = os.getenv('EMAIL_PASSWORD')
    recipient = os.getenv('EMAIL_RECIPIENT')
    
    print(f"Attempting to send email from: {sender} to: {recipient}")
    
    # Format the email content
    air_date = datetime.fromisoformat(episode_info['since'].replace('Z', '+00:00'))
    subject = f"New Episode Available: M jak miłość - Episode {episode_info['number']}"
    body = f"""
    New episode of M jak miłość is available!
    
    Episode: {episode_info['number']}
    Title: {episode_info['title']}
    Air Date: {air_date.strftime('%Y-%m-%d %H:%M')}
    Watch here: {episode_info['webUrl']}
    """
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    
    try:
        # Send the email using Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            print("Connecting to SMTP server...")
            smtp.login(sender, password)
            print("SMTP login successful")
            smtp.send_message(msg)
            print("Email sent successfully")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {str(e)}")
        print("Please check:")
        print("1. Email address is correct")
        print("2. App Password is correct (16-character code)")
        print("3. 2-Step Verification is enabled in your Google Account")
        raise
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise

def check_new_episode():
    """Main function to check for new episodes"""
    try:
        episodes = fetch_episodes()
        if not episodes:
            print("No episodes found")
            return
        
        latest_episode = episodes[0]  # First episode is the latest after sorting
        last_checked = get_last_checked_episode()
        
        if latest_episode['number'] > last_checked:
            print(f"New episode found: {latest_episode['number']}")
            send_email(latest_episode)
            save_last_checked_episode(latest_episode['number'])
        else:
            print(f"No new episodes. Latest: {latest_episode['number']}, Last checked: {last_checked}")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise





if __name__ == "__main__":
    # Uncomment to test specific components
    # test_db_connection()
    # test_api_connection()
    # test_email_connection()  # Test email first
    
    # Regular check
    check_new_episode()
