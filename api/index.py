from http.server import BaseHTTPRequestHandler
import json
import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"

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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"LeetCode Telegram Agent API is running!")
        return

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            
            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"]
                
                # Send typing action
                requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                # Ask Gemini and send Telegram response
                response_text = ask_gemini(user_text)
                url = f"{TELEGRAM_API_URL}/sendMessage"
                requests.post(url, json={"chat_id": chat_id, "text": response_text, "parse_mode": "Markdown"})
                
        except Exception as e:
            print("Webhook Error:", e)

        # Acknowledge Telegram Webhook success
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")
        return
