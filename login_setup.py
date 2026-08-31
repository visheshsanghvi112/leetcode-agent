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
import urllib.request
import urllib.error

SESSION_FILE = "leetcode_session.json"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def parse_cookie_string(cookie_string):
    """Parses a raw document.cookie string into individual cookie dicts."""
    cookies = {}
    for pair in cookie_string.split(";"):
        pair = pair.strip()
        if "=" in pair:
            name, value = pair.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies


def verify_leetcode_cookies(cookies):
    """Verifies cookies against LeetCode GraphQL using pure standard library."""
    query = """
    query userStatus {
      userStatus {
        isSignedIn
        username
      }
    }
    """
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = urllib.request.Request(
        LEETCODE_GRAPHQL_URL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "Cookie": cookie_header,
            "x-csrftoken": cookies.get("csrftoken", ""),
            "Referer": "https://leetcode.com/",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            user_status = data.get("data", {}).get("userStatus", {})
            return {
                "is_signed_in": user_status.get("isSignedIn", False),
                "username": user_status.get("username", ""),
            }
    except Exception as e:
        return {"is_signed_in": False, "username": "", "error": str(e)}


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

    # Verify session with LeetCode GraphQL
    print("\nVerifying session with LeetCode...")
    auth_status = verify_leetcode_cookies(cookies)
    if auth_status.get("is_signed_in"):
        print(f"✅ SUCCESS: Verified logged-in account: '{auth_status.get('username')}'")
    else:
        print("⚠️ WARNING: LeetCode API did not confirm active login. Please verify you copied all cookies while logged in.")

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

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
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
    print("  2. GitHub repo -> Settings -> Secrets and variables -> Actions")
    print("  3. Create/update secret: LEETCODE_SESSION_JSON")
    print("  4. Paste the file contents and save")
    print()
    print("  NOTE: Cookies expire periodically (~2 weeks).")
    print("  Re-run this script if the bot stops working.")
    print("=" * 60)


if __name__ == "__main__":
    main()


