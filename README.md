# LeetCode Daily Automation Agent

This repository contains an automated Python agent that fetches the daily LeetCode problem, retrieves the most upvoted Python3 community solution, and submits it using Playwright browser automation.

The entire process runs automatically every day using GitHub Actions.

## Setup Instructions

### 1. Local Setup
You need to generate a Playwright session file locally first so the bot can authenticate without dealing with Google or GitHub sign-ins.

1. Clone this repository locally.
2. Install Python 3.11+ and the required dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Run the setup script:
   ```bash
   python login_setup.py
   ```
4. A browser window will open. Navigate to LeetCode and log in manually using your preferred method (Google, GitHub, etc.).
5. Once logged in and you see the LeetCode homepage, return to the terminal and press `Enter`.
6. The script will save your session cookies into a file named `leetcode_session.json`.

### 2. GitHub Actions Setup
Now, you need to provide this session to GitHub Actions securely.

1. Open `leetcode_session.json` and copy its entire contents.
2. Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret**.
4. Name the secret `LEETCODE_SESSION_JSON`.
5. Paste the contents of `leetcode_session.json` into the value field and click **Add secret**.
6. Note: Make sure **Workflow permissions** (Settings -> Actions -> General) is set to **Read and write permissions** so the bot can commit the daily solutions back to the repository.

### 3. Usage
- The bot is scheduled to run daily via GitHub Actions.
- You can also trigger it manually by going to the **Actions** tab, selecting **Daily LeetCode Solver**, and clicking **Run workflow**.
- Each successful run will save the solution to the `solutions/` folder and commit it to the repository.
