<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/1/19/LeetCode_logo_black.png" width="180" alt="LeetCode Logo">
  
  # 🚀 LeetCode God-Mode Agent
  
  **The ultimate autonomous agent that solves your daily LeetCode challenges while you sleep.**

  [![GitHub Actions](https://img.shields.io/badge/Auto_Solver-Online-2088FF?style=for-the-badge&logo=github-actions)](https://github.com/visheshsanghvi112/leetcode-agent/actions)
  [![AI Stealth](https://img.shields.io/badge/Gemini_AI-Stealth_Refactoring-FF6F00?style=for-the-badge&logo=google-gemini)](https://aistudio.google.com/)
  [![Notifications](https://img.shields.io/badge/Telegram-24%2F7_Chatbot-26A5E4?style=for-the-badge&logo=telegram)](https://core.telegram.org/bots)

</div>

---

## 🔥 What exactly does this do?
Imagine never losing your LeetCode streak again. This Python agent wakes up automatically every morning, scrapes the absolute best community solution, and submits it for you. 

But it gets better:
- 🧠 **AI Stealth:** It passes the code through **Google Gemini 2.5 Flash** to completely refactor the variables and syntax. Your submissions are **100% uniquely yours**, effortlessly bypassing plagiarism checks.
- 🥷 **Anti-Ban Architecture:** From randomized daily trigger times to organic Playwright DOM interactions (human-like typing & clipboard usage) — detection systems don't stand a chance.
- 📱 **Telegram Chatbot:** The moment your challenge is solved, it texts your phone. You can even interact with a 24/7 AI coding assistant directly via the bot!
- 🌐 **Multi-Language:** Database problem? Panda dataframe? No problem. The agent intelligently switches between `Python3`, `MySQL`, and `JavaScript` as needed.

---

## ⚡ How to turn on God-Mode (Setup)

### 1. The Core Setup
1. Clone the repo and run `pip install -r requirements.txt` and `playwright install chromium`. 
2. Run `python login_setup.py`. A browser will pop up—log into LeetCode normally and hit `Enter` in your terminal.
3. This generates a `leetcode_session.json` file. Copy its entire text box.
4. In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**. 
5. Click **New repository secret**, name it `LEETCODE_SESSION_JSON`, and paste!

*(P.S. Make sure your GitHub Action Workflow permissions are set to "Read and write"!)*

### 2. The Fun Stuff (Optional Secrets)
Want the AI stealth and Telegram texts? Add these three remaining GitHub secrets:
* **`GEMINI_API_KEY`**: Grab a free token from Google AI Studio.
* **`TELEGRAM_BOT_TOKEN`**: Message `@BotFather` on Telegram to get your bot token.
* **`TELEGRAM_CHAT_ID`**: Send your new bot a message, hit the API, and grab your personal Chat ID integer. 

---

## 🚀 That's it.
Sit back, relax, and let the cloud handle the grind. The agent logs everything directly to the `/solutions` folder, naturally building out your GitHub commits history.

**Welcome to the future of streaks. 🥂**

---

<p align="center">
  <i>Made with ❤️ by <a href="https://visheshsanghvi.me">Vishesh Sanghvi</a>. Connect with me on <a href="https://www.linkedin.com/in/vishesh-sanghvi-96b16a237/">LinkedIn</a>!</i>
</p>
