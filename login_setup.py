"""
Login Setup Script for LeetCode Agent.

Simplest approach: copy the raw cookie string from Chrome Console.

Steps:
  1. Open Chrome and go to https://leetcode.com (make sure you're logged in)
  2. Press F12 to open DevTools
  3. Click the "Console" tab
  4. Type:  document.cookie
  5. Press Enter
  6. Right-click the output string → Copy string contents
  7. Run this script and paste it when asked
"""
import json
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"


def parse_cookie_string(cookie_string):
    """Parses a raw document.cookie string into individual cookie dicts."""
    cookies = {}
    for pair in cookie_string.split(";"):
        pair = pair.strip()
        if "=" in pair:
            name, value = pair.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies


def main():
    print("=" * 60)
    print("  LeetCode Session Setup")
    print("=" * 60)
    print()
    print("  Step 1: Open Chrome -> go to https://leetcode.com")
    print("          (make sure you are LOGGED IN)")
    print()
    print("  Step 2: Press F12 to open DevTools")
    print()
    print("  Step 3: Click the 'Console' tab")
    print()
    print("  Step 4: Click in the console area, type this and press Enter:")
    print()
    print("          document.cookie")
    print()
    print("  Step 5: You'll see a long string starting with quotes.")
    print("          Right-click on it -> 'Copy string contents'")
    print()
    print("  Step 6: Paste it below when prompted.")
    print()
    print("=" * 60)
    print()

    raw_cookies = input("Paste the cookie string here: ").strip()

    # Remove surrounding quotes if user copied with them
    if raw_cookies.startswith('"') and raw_cookies.endswith('"'):
        raw_cookies = raw_cookies[1:-1]
    if raw_cookies.startswith("'") and raw_cookies.endswith("'"):
        raw_cookies = raw_cookies[1:-1]

    if not raw_cookies:
        print("ERROR: Cookie string cannot be empty.")
        return

    cookies = parse_cookie_string(raw_cookies)

    leetcode_session = cookies.get("LEETCODE_SESSION")
    csrf_token = cookies.get("csrftoken")

    if not leetcode_session:
        print()
        print("ERROR: Could not find LEETCODE_SESSION in the cookie string.")
        print("Make sure you are logged in to LeetCode before copying cookies.")
        return

    if not csrf_token:
        print()
        print("WARNING: csrftoken not found. Will try without it.")
        csrf_token = ""

    # Build Playwright storage state
    cookie_list = [
        {
            "name": "LEETCODE_SESSION",
            "value": leetcode_session,
            "domain": ".leetcode.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        },
    ]

    if csrf_token:
        cookie_list.append({
            "name": "csrftoken",
            "value": csrf_token,
            "domain": ".leetcode.com",
            "path": "/",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
        })

    storage_state = {
        "cookies": cookie_list,
        "origins": [],
    }

    with open(SESSION_FILE, "w") as f:
        json.dump(storage_state, f, indent=2)

    print()
    print("=" * 60)
    print(f"  SUCCESS! Session saved to: {SESSION_FILE}")
    print()
    print("  Found cookies:")
    print(f"    LEETCODE_SESSION: {leetcode_session[:20]}...{leetcode_session[-10:]}")
    if csrf_token:
        print(f"    csrftoken:        {csrf_token[:20]}...")
    print()
    print("  For GitHub Actions setup:")
    print("  1. Open leetcode_session.json and copy ALL its contents")
    print("  2. GitHub repo -> Settings -> Secrets -> Actions")
    print("  3. Create secret: LEETCODE_SESSION_JSON")
    print("  4. Paste the file contents and save")
    print()
    print("  NOTE: Cookies expire periodically (~2 weeks).")
    print("  Re-run this script if the bot stops working.")
    print("=" * 60)


if __name__ == "__main__":
    main()
