import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from bots.transcriptionBot import MediaProcessingBot

STATE_FILE = "state.json"
MAX_PROCESSED_URIS = 500
MAX_AGE_SECONDS = 3600  # Skip mentions older than 1 hour

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_state():
    """Load persisted state from state.json"""
    if not os.path.exists(STATE_FILE):
        return {"last_processed_timestamp": None, "processed_mentions": []}
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load state: {e}. Starting fresh.")
        return {"last_processed_timestamp": None, "processed_mentions": []}


def save_state(state):
    """Save state to state.json"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def is_too_old(notification_time_str, max_age_seconds=MAX_AGE_SECONDS):
    """Check if a notification is older than max_age_seconds"""
    if not notification_time_str:
        return False
    try:
        notification_time = datetime.fromisoformat(notification_time_str.replace('Z', '+00:00'))
        current_time = datetime.now(timezone.utc)
        return (current_time - notification_time).total_seconds() > max_age_seconds
    except Exception:
        return False


def main():
    state = load_state()
    bot = MediaProcessingBot()

    last_ts = state.get("last_processed_timestamp")
    processed_uris = set(state.get("processed_mentions", []))
    newest_ts = last_ts
    newly_processed = []

    logger.info(f"Starting mention check. Last processed: {last_ts or 'N/A'}. Known URIs: {len(processed_uris)}")

    try:
        notifications = bot.bluesky_client.get_notifications(limit=50)
        logger.info(f"Fetched {len(notifications)} notifications")

        mention_count = 0
        for notification in notifications:
            if getattr(notification, 'reason', None) != 'mention':
                continue

            mention_count += 1
            mention_uri = notification.uri
            indexed_at = getattr(notification, 'indexedAt', None)

            # Skip already processed
            if mention_uri in processed_uris:
                continue

            # Skip too old
            if indexed_at and is_too_old(indexed_at):
                logger.debug(f"Skipping old mention: {mention_uri}")
                continue

            # Skip if bot already replied (network-side duplicate guard)
            try:
                if bot.bluesky_client.has_bot_already_replied(mention_uri, bot.bluesky_username):
                    logger.info(f"Already replied to {mention_uri}, marking as processed")
                    processed_uris.add(mention_uri)
                    newly_processed.append(mention_uri)
                    if indexed_at and (not newest_ts or indexed_at > newest_ts):
                        newest_ts = indexed_at
                    continue
            except Exception as e:
                logger.warning(f"Failed to check existing replies for {mention_uri}: {e}")

            # Process the mention
            try:
                mention_text = bot.bluesky_client.get_post_text(mention_uri)
                logger.info(f"Processing mention: {mention_uri}")
                result = bot.post_transcription_reply(mention_uri, mention_text or "")

                if result:
                    logger.info(f"Successfully replied to {mention_uri}")
                else:
                    logger.error(f"Failed to reply to {mention_uri}")

                processed_uris.add(mention_uri)
                newly_processed.append(mention_uri)

                if indexed_at and (not newest_ts or indexed_at > newest_ts):
                    newest_ts = indexed_at

            except Exception as e:
                logger.error(f"Error processing mention {mention_uri}: {e}")
                # Mark as processed to avoid infinite retry loops
                processed_uris.add(mention_uri)
                newly_processed.append(mention_uri)

        logger.info(f"Found {mention_count} mentions, processed {len(newly_processed)} new ones")

    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        sys.exit(1)

    # Save updated state
    all_processed = list(processed_uris)
    if len(all_processed) > MAX_PROCESSED_URIS:
        all_processed = all_processed[-MAX_PROCESSED_URIS:]

    state["processed_mentions"] = all_processed
    if newest_ts:
        state["last_processed_timestamp"] = newest_ts

    save_state(state)
    logger.info("Run complete. State saved.")


if __name__ == "__main__":
    main()
