#!/usr/bin/env python3
"""
Interactive LeetCode Browser Login.
Launches a real Chromium window so you can log in directly once.
Saves the persistent browser profile to './.leetcode_browser_data' and exports 'leetcode_session.json'.
"""

import os
import json
import time
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PROFILE_DIR = os.path.abspath("./.leetcode_browser_data")
SESSION_FILE = os.path.abspath("./leetcode_session.json")


def interactive_login():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    print("=" * 65)
    print("      LeetCode 1-Time Interactive Browser Login")
    print("=" * 65)
    print("\nOpening a Chromium browser window...")
    print("1. Log in to LeetCode in the browser window that appears.")
    print("2. Once you are logged in and see your dashboard/profile,")
    print("   this script will automatically detect your login and save it!\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://leetcode.com/accounts/login/", wait_until="domcontentloaded")

        logging.info("Waiting for you to log in to LeetCode in the open browser...")

        authenticated = False

        # Poll until user is logged in (up to 10 minutes)
        for i in range(300):
            time.sleep(2)
            try:
                cookies = context.cookies(["https://leetcode.com"])
                session_cookie = next((c for c in cookies if c["name"] == "LEETCODE_SESSION"), None)
                csrf_cookie = next((c for c in cookies if c["name"] == "csrftoken"), None)

                if session_cookie and session_cookie.get("value") and len(session_cookie["value"]) > 30:
                    # Check if not on login page or avatar is present
                    curr_url = page.url
                    if "/accounts/login" not in curr_url:
                        authenticated = True
                        break
                    # Even on login page, check if GraphQL or avatar shows logged in
                    user_status = page.evaluate("""
                        () => {
                            try {
                                const nav = document.querySelector('[data-avatar-url], [data-cypress="UserAvatar"], img[alt*="avatar"]');
                                if (nav) return true;
                            } catch (e) {}
                            return false;
                        }
                    """)
                    if user_status:
                        authenticated = True
                        break
            except Exception:
                pass

        if authenticated:
            logging.info("🎉 Login detected successfully!")
            # Wait 2 seconds for all auth cookies to settle
            time.sleep(2)
            storage_state = context.storage_state()
            
            # Ensure cookies have expires timestamp
            for c in storage_state.get("cookies", []):
                c["expires"] = 2147483647
                c["domain"] = ".leetcode.com"
                c["path"] = "/"
                c["secure"] = True
                c["sameSite"] = "Lax"

            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(storage_state, f, indent=2)
            logging.info(f"Saved session to '{SESSION_FILE}' and persistent profile to '{PROFILE_DIR}'.")
            
            # Update GitHub Secrets as well if gh CLI is installed
            try:
                import subprocess
                subprocess.run(["gh", "secret", "set", "LEETCODE_SESSION_JSON", "--env", "leetcode"], input=json.dumps(storage_state).encode(), check=False)
                subprocess.run(["gh", "secret", "set", "LEETCODE_SESSION_JSON"], input=json.dumps(storage_state).encode(), check=False)
                logging.info("Synced session to GitHub Secrets.")
            except Exception as e:
                logging.debug(f"GitHub secret sync note: {e}")

            context.close()
            print("\n" + "=" * 65)
            print("  SUCCESS! You are now logged in permanently.")
            print("  Submitting today's problem now...")
            print("=" * 65 + "\n")
            return True
        else:
            logging.warning("Login timeout reached. Please run the script again.")
            context.close()
            return False



if __name__ == "__main__":
    success = interactive_login()
    if success:
        import subprocess
        subprocess.run(["python3", "main.py"])
