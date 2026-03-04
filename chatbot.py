import os
import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Ensure these secrets are available in your local terminal environment
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
# We will use Gemini 2.5 Flash for the chatbot
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"

def get_updates(offset=None):
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("result", [])
    except Exception as e:
        logging.error(f"Error getting updates: {e}")
        return []

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def ask_gemini(user_text):
    if not GEMINI_KEY:
        return "I'm sorry, my AI brain (Gemini API Key) is currently disconnected! I need my secrets loaded into the environment."
        
    payload = {
        "contents": [{"parts": [{"text": user_text}]}],
        "systemInstruction": {
            "parts": [{"text": "You are Master Vishesh's personal autonomous coding assistant. You live inside Telegram but have access to his LeetCode proxy. Keep answers concise, extremely helpful, and slightly robotic."}]
        }
    }
    
    try:
        req = requests.post(GEMINI_API_URL, json=payload, headers={"Content-Type": "application/json"})
        req.raise_for_status()
        return req.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        return "I encountered a neural error trying to process that."

def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
         logging.error("Missing TELEGRAM_BOT_TOKEN or GEMINI_API_KEY in environment variables.")
         return

    logging.info("Starting Assistant Listener for Master Vishesh...")
    last_update_id = None
    
    # Get the latest update ID ignoring past messages on startup
    updates = get_updates()
    if updates:
        last_update_id = updates[-1]["update_id"] + 1

    while True:
        updates = get_updates(last_update_id)
        for update in updates:
            update_id = update["update_id"]
            last_update_id = update_id + 1
            
            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"]
                username = update["message"]["from"].get("first_name", "User")
                
                logging.info(f"Received message from {username}: {user_text}")
                
                # Show typing indicator
                requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                response_text = ask_gemini(user_text)
                send_message(chat_id, response_text)
                
        time.sleep(1)

if __name__ == "__main__":
    main()
