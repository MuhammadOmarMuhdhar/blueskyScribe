import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

from bots.transcriptionBot import MediaProcessingBot


def main():
    if len(sys.argv) < 2:
        print("Usage: python process_link.py <bluesky-post-url>")
        print("Example: python process_link.py https://bsky.app/profile/username.bsky.social/post/3lkb5jq2zts2o")
        sys.exit(1)

    post_url = sys.argv[1]

    if not post_url.startswith("https://bsky.app/"):
        print("Error: URL must be a Bluesky post URL (https://bsky.app/...)")
        sys.exit(1)

    bot = MediaProcessingBot()
    print(f"Processing post: {post_url}")
    print("---")

    success = bot.post_transcription_reply(post_url)

    if success:
        print("---")
        print("Reply posted successfully!")
    else:
        print("---")
        print("Failed to process or reply.")
        sys.exit(1)


if __name__ == "__main__":
    main()
