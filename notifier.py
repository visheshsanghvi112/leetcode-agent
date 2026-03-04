import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_discord_notification(title, difficulty, result):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logging.info("No DISCORD_WEBHOOK_URL found. Skipping notification.")
        return

    # Determine color based on result
    color = 3066993 if "Accepted" in result else 15158332 # Green or Red
    
    embed = {
        "title": f"LeetCode Daily: {title}",
        "description": f"**Difficulty:** {difficulty}\n**Result:** {result}",
        "color": color,
        "author": {
            "name": "LeetCode Auto-Agent 🤖"
        }
    }
    
    data = {"embeds": [embed]}
    
    try:
        req = requests.post(webhook_url, json=data)
        req.raise_for_status()
        logging.info("Discord notification sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Discord notification: {e}")

if __name__ == "__main__":
    send_discord_notification("Test Problem", "Hard", "✅ ACCEPTED!")
