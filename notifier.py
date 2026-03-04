import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(title, difficulty, result):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logging.info("No TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID found. Skipping notification.")
        return

    icon = "✅" if "Accepted" in result else "❌"
    
    message = f"""
{icon} **LeetCode Daily**
**Problem:** {title}
**Difficulty:** {difficulty}
**Result:** {result}
"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        req = requests.post(url, json=payload)
        req.raise_for_status()
        logging.info("Telegram notification sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram notification: {e}")

if __name__ == "__main__":
    send_telegram_notification("Test Problem", "Hard", "✅ ACCEPTED!")
