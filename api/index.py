import os
import requests
from flask import Flask, request, jsonify

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"

app = Flask(__name__)

def ask_gemini(user_text):
    if not GEMINI_KEY:
        return "System offline: Missing GEMINI_API_KEY config."
        
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
        return f"Neural error processing query: {str(e)}"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if request.method == 'GET':
        return "LeetCode Telegram Agent API is running on Vercel using Flask!", 200
        
    if request.method == 'POST':
        update = request.get_json(silent=True)
        if update and "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            # Send typing action
            requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
            
            # Ask Gemini and send Telegram response
            response_text = ask_gemini(user_text)
            url = f"{TELEGRAM_API_URL}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": response_text, "parse_mode": "Markdown"})
            
        return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
