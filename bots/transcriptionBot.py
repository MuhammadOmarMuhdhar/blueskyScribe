import json
import logging
import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from clients.gemini import Client as GeminiClient
from clients.bluesky import Client as BlueskyClient

# Load environment variables
load_dotenv(override=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediaProcessingBot:
    """Bluesky media processing bot that summarizes audio/video and describes/reads images from posts"""
    
    def __init__(self, gemini_api_key: str = None, bluesky_username: str = None, bluesky_password: str = None, prompt_file: str = "prompt/prompt.txt"):
        """Initialize media processing bot with API credentials (loads from .env if not provided)"""
        # Load from environment variables if not provided
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.bluesky_username = bluesky_username or os.getenv('BLUESKY_USERNAME')
        self.bluesky_password = bluesky_password or os.getenv('BLUESKY_PASSWORD')
        self.prompt_file = prompt_file  
        
        # Validate required credentials
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or parameters")
        if not self.bluesky_username:
            raise ValueError("BLUESKY_USERNAME not found in environment variables or parameters")
        if not self.bluesky_password:
            raise ValueError("BLUESKY_PASSWORD not found in environment variables or parameters")
        
        # Initialize clients
        self.gemini_client = GeminiClient(api_key=self.gemini_api_key)
        self.bluesky_client = BlueskyClient(username=self.bluesky_username, password=self.bluesky_password)
    
    def extract_language_from_mention(self, mention_text: str) -> str:
        """Extract requested language from mention text - PROXIMITY-BASED detection only"""
        if not mention_text:
            return "English"
        
        import re
        
        # Language mappings
        language_map = {
            # Full names
            'spanish': 'Spanish', 'español': 'Spanish',
            'french': 'French', 'français': 'French', 
            'german': 'German', 'deutsch': 'German',
            'chinese': 'Chinese', '中文': 'Chinese',
            'japanese': 'Japanese', '日本語': 'Japanese',
            'portuguese': 'Portuguese', 'português': 'Portuguese',
            'italian': 'Italian', 'italiano': 'Italian',
            'korean': 'Korean', '한국어': 'Korean',
            'arabic': 'Arabic', 'العربية': 'Arabic',
            
            # ISO codes
            'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'zh': 'Chinese', 'ja': 'Japanese', 'pt': 'Portuguese', 
            'it': 'Italian', 'ko': 'Korean', 'ar': 'Arabic'
        }
        
        text_lower = mention_text.lower().strip()
        
        # 1. HIGHEST PRIORITY: Explicit structured syntax (anywhere in text)
        explicit_patterns = [
            r'lang(?:uage)?[:\s]+([a-z]{2,})',  # lang:es, language: spanish
            r'\[([a-z]{2,})\]',                 # [spanish]
            r'\{([a-z]{2,})\}',                 # {es}
        ]
        
        for pattern in explicit_patterns:
            match = re.search(pattern, text_lower)
            if match:
                lang_key = match.group(1).lower()
                if lang_key in language_map:
                    return language_map[lang_key]
        
        # 2. PROXIMITY-BASED DETECTION: Language must be within 1-2 words of @mention
        # Find bot mention position
        bot_mention_patterns = [
            r'@bskyscribe\.bsky\.social',
            r'@bskyscribe',
            r'@bot'
        ]
        
        mention_positions = []
        for pattern in bot_mention_patterns:
            for match in re.finditer(pattern, text_lower):
                mention_positions.append(match.start())
        
        if not mention_positions:
            # No bot mention found, default to English
            return "English"
        
        # Extract words and their positions
        words_with_positions = []
        for match in re.finditer(r'\b\w+\b', text_lower):
            words_with_positions.append((match.group(), match.start(), match.end()))
        
        # For each mention, check words within strict proximity window
        for mention_pos in mention_positions:
            # Find the word index that represents the end of the mention
            mention_end = mention_pos + len("@bskyscribe.bsky.social")  # Calculate mention end position
            mention_word_index = None
            
            for i, (word, start_pos, end_pos) in enumerate(words_with_positions):
                # Find the last word that overlaps with or is part of the mention
                if start_pos <= mention_end and end_pos >= mention_pos:
                    mention_word_index = i
            
            if mention_word_index is None:
                continue
            
            # Check ONLY 1-2 words AFTER the mention (safer, more natural)
            proximity_range = 2
            start_idx = mention_word_index + 1  # Start after mention
            end_idx = min(len(words_with_positions), mention_word_index + proximity_range + 1)
            
            nearby_words = []
            for i in range(start_idx, end_idx):
                nearby_words.append(words_with_positions[i][0])
            
            # Check if any nearby words are language keywords
            for word in nearby_words:
                if word in language_map:
                    # Additional validation for short ISO codes
                    if len(word) <= 3:
                        # For ISO codes, ensure it's not part of common English words
                        if word in ['it', 'is', 'in', 'to', 'be', 'we', 'he', 'me', 'no', 'so', 'go', 'do']:
                            continue
                    return language_map[word]
        
        # 3. NATURAL LANGUAGE PATTERNS (with proximity)
        natural_patterns = [
            r'in\s+([a-z]{2,})(?:\s|$|[.,!?])',    # "in spanish"
            r'to\s+([a-z]{2,})(?:\s|$|[.,!?])',    # "to french"
            r'as\s+([a-z]{2,})(?:\s|$|[.,!?])',    # "as german"
        ]
        
        for mention_pos in mention_positions:
            # Check natural patterns within proximity of mentions
            for pattern in natural_patterns:
                for match in re.finditer(pattern, text_lower):
                    if abs(match.start() - mention_pos) <= 20:  # Strict proximity
                        lang_key = match.group(1).lower()
                        if lang_key in language_map:
                            return language_map[lang_key]
        
        # Default: No language detected near bot mentions
        return "English"
    
    def transcribe_post(self, post_url: str, language: str = "English", max_retries: int = 3) -> Dict[str, Any]:
        """
        Transcribe media content from a Bluesky post
        """
        logger.info(f"Starting transcription in {language} (max {max_retries} attempts)")
        
        for attempt in range(max_retries):
            logger.debug(f"Transcription attempt {attempt + 1}/{max_retries}")
            
            try:
                result = self._transcription_attempt(post_url, language)
                
                if "error" in result:
                    logger.warning(f"Attempt {attempt + 1} failed with error: {result['error']}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        return result  # Return error after final attempt
                
                # Success - return result
                logger.info(f"Transcription successful on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                logger.error(f"Transcription attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return {"error": f"Transcription failed after {max_retries} attempts: {str(e)}"}
    
    def _transcription_attempt(self, post_url: str, language: str = "English") -> Dict[str, Any]:
        """
        Single transcription attempt
        """
        start_time = time.time()
        
        # Get parent post with media
        post_data = self.bluesky_client.get_parent_post_with_media(post_url)
        if not post_data:
            return {"error": "Could not retrieve post data"}
        
        # Check for error (no media found)
        if "error" in post_data:
            return post_data  # Return the error directly
        
        # Check if media is present
        media_items = post_data.get("media", [])
        if not media_items:
            return {"error": "No media found in post"}
        
        # Load prompt template from file
        with open(self.prompt_file, 'r') as f:
            prompt_template = f.read()
        
        # Format prompt with language
        formatted_prompt = prompt_template.format(language=language)
        
        # Process first media item (for now)
        media_item = media_items[0]
        media_url = media_item["url"]
        
        # Call Gemini media processing with structured output
        gemini_response = self.gemini_client.process_media(media_url, formatted_prompt)
        
        # Parse JSON response
        try:
            result = json.loads(gemini_response)
            logger.info(f"Transcription completed in {time.time() - start_time:.2f}s")
            return result
            
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON response: {str(e)}"}
    
    def format_transcription_reply(self, transcription_result: Dict[str, Any]) -> str:
        """
        Format the JSON transcription result into a readable Bluesky reply
        
        Args:
            transcription_result: The parsed JSON result from transcription
            
        Returns:
            Formatted string for Bluesky reply
        """
        if "error" in transcription_result:
            return f"{transcription_result['error']}"
            
        # Use the response from the structured JSON output
        response = transcription_result.get("response", "Unable to process media content")
        
        # Clean up any unwanted characters but keep the response natural
        response = response.strip()
        
        return response
    
    def post_transcription_reply(self, original_post_url: str, mention_text: str = "") -> bool:
        """
        Complete workflow: transcribe media from a post and reply with results
        
        Args:
            original_post_url: URL of the post to transcribe
            mention_text: Text of the mention (for language detection)
            
        Returns:
            True if successful, False otherwise
        """
        # Extract language from mention
        language = self.extract_language_from_mention(mention_text)
        logger.info(f"Processing transcription request in {language}")
        
        # Perform transcription with language
        result = self.transcribe_post(original_post_url, language)
        
        # Format reply
        reply_text = self.format_transcription_reply(result)
        
        # Post reply
        reply_result = self.bluesky_client.post_reply(original_post_url, reply_text)
        
        if reply_result:
            logger.info(f"Posted transcription reply in {language}")
            return True
        else:
            logger.error(f"Failed to post reply")
            return False
