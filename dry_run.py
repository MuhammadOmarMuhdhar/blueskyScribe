
import json
import os
from datetime import datetime
from bots.transcriptionBot import MediaProcessingBot

os.environ.setdefault('GEMINI_API_KEY', 'your_key_here')
os.environ.setdefault('BLUESKY_USERNAME', 'bskyscribe.bsky.social')
os.environ.setdefault('BLUESKY_PASSWORD', 'your_password_here')

bot = MediaProcessingBot()

# Fetch notifications
notifications = bot.bluesky_client.get_notifications(limit=50)
mentions = [n for n in notifications if getattr(n, 'reason', None) == 'mention']

print(f"Found {len(mentions)} mentions in last 50 notifications:")
for m in mentions:
    print(f"  - {m.uri} at {getattr(m, 'indexedAt', 'N/A')}")
    text = bot.bluesky_client.get_post_text(m.uri)
    print(f"    Text: {text[:100]}...")
    print(f"    Already replied? {bot.bluesky_client.has_bot_already_replied(m.uri, bot.bluesky_username)}")