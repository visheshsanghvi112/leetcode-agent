<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/1/19/LeetCode_logo_black.png" width="200" alt="LeetCode Logo">
  
  # LeetCode Auto-Agent 🤖
  
  **A completely autonomous, stealthy Python agent that solves the daily LeetCode challenge using the community's most-upvoted Python3 solution.**

  [![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com/visheshsanghvi112/leetcode-agent/actions)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![Playwright](https://img.shields.io/badge/Playwright-Browser_Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/python/)

</div>

---

## ✨ Features
- **100% Autonomous:** Runs automatically in the cloud every day via GitHub Actions.
- **Stealth & Anti-Bot Detection:** Bypasses Cloudflare using Playwright. Includes randomized cursor wait times, keystroke delays, and execution times to mimic true human behavior so your LeetCode account remains completely safe.
- **Self-Documenting:** Captures, formats, and commits exactly what it submitted directly to the `solutions/` folder to naturally build your GitHub activity.
- **Guaranteed Solutions:** Leverages the authenticated LeetCode Discuss API to scrape the highest-voted, most optimal `Python3` community solutions.

---

## 🚀 Setup Instructions

### 1. Generate Local Session (Only do once!)
The agent needs your LeetCode session cookie so it can authenticate without triggering manual Google/GitHub OAuth captchas.

1. Clone this repository locally.
2. Install Python 3.11+ and dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Run the setup script:
   ```bash
   python login_setup.py
   ```
4. A browser window will open. Navigate to LeetCode and log in manually.
5. Once logged in, return to the terminal and press `Enter`. The script will generate a file named `leetcode_session.json` which contains your authentication tokens.

### 2. Configure GitHub Actions
Pass the generated tokens to the cloud so GitHub Actions can impersonate your logged-in browser securely.

1. Open `leetcode_session.json` and **copy its entire contents**.
2. Go to your GitHub repository: **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret**.
4. Name the secret exactly: `LEETCODE_SESSION_JSON`.
5. Paste the JSON contents and click **Add secret**.

> **Note:** Make sure **Workflow permissions** (Settings -> Actions -> General) is set to **Read and write permissions** so the bot can commit your daily `.py` solutions to your repository!

---

## 🛡️ Anti-Ban & Humanization Measures
To ensure your account is protected from being flagged as automated:
- **Randomized Cron Job:** The GitHub Action is programmed to trigger at a slightly randomized time between `7:00 AM` and `10:00 AM IST` rather than precisely on the hour.
- **Dynamic Interactions:** All DOM element waits, keystrokes, clearing logic, clipboard usage, and clicking behaviors utilize `random.randint()` millisecond sleep gaps.
- **Headed Emulation:** Injects headless evasion properties (e.g. bypassing `navigator.webdriver`).

---

## ⚖️ Disclaimer
This project is intended strictly for educational purposes and personal archival of algorithmic problems. Over-reliance on automation defeats the purpose of learning data structures and algorithms. Use responsibly!
