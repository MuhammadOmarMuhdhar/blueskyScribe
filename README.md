# [@bskyscribe.bsky.social](https://bsky.app/profile/bskyscribe.bsky.social)

A media processing bot for Bluesky that describes images and summarizes audio/video content from posts.


### Processing Workflow

1. **Mention Detection**: Bot monitors Bluesky for mentions using AT Protocol notifications
2. **Media Retrieval**: When mentioned, retrieves media from the post being replied to
3. **AI Processing**: Sends media to Google Gemini for analysis and summarization
4. **Response Generation**: Creates concise description/summary (under 250 chars)
5. **Reply Posting**: Automatically posts media description as a reply

### What it does

- **Images**: Describes visual content or extracts text (OCR)
- **Videos**: Summarizes spoken content and key points  
- **Audio**: Summarizes conversations and main topics

### Language Support

Supports 10 languages - just mention the bot with your preferred language:
- `@bskyscribe.bsky.social` (English, default)
- `@bskyscribe.bsky.social spanish` or `es`
- `@bskyscribe.bsky.social french` or `fr` 
- `@bskyscribe.bsky.social 中文` or `zh`
- `@bskyscribe.bsky.social 日本語` or `ja`
- Plus German, Portuguese, Italian, Korean, Arabic

### Technical Features
- **Multi-Format Support**: Handles images, videos, and audio files 
- **Smart Processing**: Auto-detects media type and applies appropriate processing
- **Multi-Language Support**: Responds in user's preferred language (10 languages supported)
- **Memory Efficient**: Uses in-memory processing (BytesIO) for cloud deployment compatibility

### Deployment 
- **Scheduled Monitoring**: Checks for mentions every 10 minutes via GitHub Actions
- **Free Hosting**: Runs on GitHub Actions public repo free tier (no server costs)
- **State Persistence**: Uses `state.json` committed to the repo to track processed mentions between runs
- **Robust Error Handling**: Graceful fallbacks and comprehensive logging
- **Environment Driven**: All configuration through GitHub Secrets

## File Structure

```
bskyScribe/
├── .github/
│   └── workflows/
│       └── bot.yml        # GitHub Actions workflow (runs every 10 min)
├── clients/
│   ├── bluesky.py         # Bluesky AT Protocol client for posts and notifications
│   └── gemini.py          # Google Gemini AI client for media processing
├── bots/
│   └── transcriptionBot.py # Main media processing bot logic
├── prompt/
│   └── prompt.txt         # Media processing prompt for summarization
├── check_mentions.py      # Single-run mention checker (stateless)
├── state.json             # Persisted state (last check + processed URIs)
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables for local dev
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bskyScribe
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Setup

1. **Get API Keys:**
   - Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Bluesky app password from [Bluesky Settings](https://bsky.app/settings/app-passwords)

2. **Create environment file (for local development):**
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```

3. **Configure your `.env` file:**
   ```bash
   GEMINI_API_KEY=your_gemini_api_key_here
   BLUESKY_USERNAME=bskyscribe.bsky.social
   BLUESKY_PASSWORD=your_app_password_here
   ```

4. **Add GitHub Secrets (for live deployment):**
   Go to **Settings → Secrets and variables → Actions** and add:
   - `GEMINI_API_KEY`
   - `BLUESKY_USERNAME`
   - `BLUESKY_PASSWORD`

## Usage


### Basic Example

```python
from bots.transcriptionBot import MediaProcessingBot

# Initialize the media processing bot (reads from .env automatically)
bot = MediaProcessingBot()

# Process media from a specific post (English)
post_url = "https://bsky.app/profile/user/post/123"
result = bot.transcribe_post(post_url)

# Process with specific language
result = bot.transcribe_post(post_url, language="Spanish")

# Get formatted response for Bluesky
reply_text = bot.format_transcription_reply(result)
print(reply_text)

# Or do the complete workflow (process + reply with language detection)
mention_text = "@bskyscribe.bsky.social español"
success = bot.post_transcription_reply(post_url, mention_text)
```

### Automated Monitoring (GitHub Actions)

The bot runs automatically via GitHub Actions every **10 minutes**.

To trigger a manual run:
1. Go to **Actions → Bluesky Scribe Bot**
2. Click **Run workflow**

To run locally (one-off check):
```python
from check_mentions import main

# Single run: checks mentions, processes them, saves state
main()
```

### Response Format

The bot returns structured JSON responses:

```json
{
    "thinking": "Analysis of the media content and processing approach",
    "request_type": "SUMMARIZE|DESCRIBE|READ_TEXT",
    "media_type": "AUDIO|VIDEO|IMAGE",
    "response_character_count": 245,
    "response": "Concise summary or description under 250 characters"
}
```




## Contributing

Please feel free to contribute to this project. 

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

