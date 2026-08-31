import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def send_telegram_notification(title, difficulty, result, problem_url=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logging.info("No TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID found. Skipping notification.")
        return

    icon = "✅" if "Accepted" in result or "Submitted" in result else "⚠️"

    message = f"""
{icon} *LeetCode Daily Agent*
*Problem:* {title} ({difficulty})
*Verdict:* `{result}`
"""
    if problem_url:
        message += f"[View Problem]({problem_url})\n"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message.strip(),
        "parse_mode": "Markdown",
    }

    try:
        req = requests.post(url, json=payload, timeout=10)
        req.raise_for_status()
        logging.info("Telegram notification sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram notification: {e}")


def send_session_expired_alert(username=None):
    """Sends an alert to Telegram when LeetCode cookies have expired."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        return

    account_str = f" for `{username}`" if username else ""
    message = f"""
🚨 *LeetCode Session Expired*

Your LeetCode session token{account_str} has expired or is unauthenticated.
The agent is still saving daily solutions, but cannot credit your profile until renewed.

*Action Required:*
1. Run `python login_setup.py` locally.
2. Update `LEETCODE_SESSION_JSON` in your GitHub repository secrets.
"""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message.strip(),
        "parse_mode": "Markdown",
    }

    try:
        requests.post(url, json=payload, timeout=10)
        logging.info("Sent session expiration alert to Telegram.")
    except Exception as e:
        logging.error(f"Failed to send Telegram expiration alert: {e}")


if __name__ == "__main__":
    send_telegram_notification("Test Problem", "Hard", "Accepted | Runtime: 35 ms | Memory: 16.5 MB")

