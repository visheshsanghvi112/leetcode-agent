"""
Login Setup Script for LeetCode Agent.

LeetCode marks `LEETCODE_SESSION` as HttpOnly, so it cannot be read via document.cookie.
You can get it directly from Chrome DevTools Application tab in 10 seconds.
"""
import json
import re
import urllib.request
import urllib.error

SESSION_FILE = "leetcode_session.json"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


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


def parse_raw_input(raw_text):
    """Intelligently parses cookies whether pasted as key=value pairs, raw session value, or JSON."""
    raw_text = raw_text.strip()
    # Remove quotes
    if (raw_text.startswith('"') and raw_text.endswith('"')) or (raw_text.startswith("'") and raw_text.endswith("'")):
        raw_text = raw_text[1:-1].strip()

    cookies = {}

    # Check if user pasted JSON
    if raw_text.startswith("{"):
        try:
            data = json.loads(raw_text)
            if "cookies" in data:
                for c in data["cookies"]:
                    cookies[c["name"]] = c["value"]
            elif isinstance(data, dict):
                cookies.update(data)
            return cookies
        except Exception:
            pass

    # Check if user pasted key=value pairs (e.g. from document.cookie or headers)
    if "=" in raw_text:
        for pair in raw_text.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, val = pair.split("=", 1)
                cookies[name.strip()] = val.strip()

    # If it's a standalone session string (starts with eyJ or similar long base64 string)
    if not cookies.get("LEETCODE_SESSION") and len(raw_text) > 40 and " " not in raw_text:
        cookies["LEETCODE_SESSION"] = raw_text

    return cookies


def main():
    print("=" * 65)
    print("           LeetCode Session Setup (Fast & Easy)")
    print("=" * 65)
    print()
    print("  Because LEETCODE_SESSION is HttpOnly, Chrome hides it from 'document.cookie'.")
    print("  Here is how to get it in 10 seconds from DevTools:")
    print()
    print("  1. Open Chrome and go to: https://leetcode.com (make sure you are LOGGED IN)")
    print("  2. Press F12 (or right-click anywhere -> Inspect)")
    print("  3. In the top bar of DevTools, click 'Application' (click '>>' if hidden)")
    print("  4. In the left sidebar: Expand 'Storage' -> Expand 'Cookies' -> click 'https://leetcode.com'")
    print("  5. In the table, find 'LEETCODE_SESSION' and double-click its 'Value' column -> Copy it!")
    print()
    print("=" * 65)
    print()

    session_input = input("Paste your LEETCODE_SESSION value (or full cookie string) here:\n> ").strip()

    cookies = parse_raw_input(session_input)
    leetcode_session = cookies.get("LEETCODE_SESSION")

    # If user only pasted the session value, ask for csrftoken or use placeholder
    if not leetcode_session and len(session_input) > 20:
        leetcode_session = session_input
        cookies["LEETCODE_SESSION"] = leetcode_session

    if not leetcode_session:
        print()
        print("❌ ERROR: Could not find LEETCODE_SESSION.")
        print("Please follow steps 1-5 above to copy the 'LEETCODE_SESSION' value from DevTools -> Application -> Cookies.")
        return

    csrf_token = cookies.get("csrftoken")
    if not csrf_token:
        print()
        csrf_input = input("Paste your 'csrftoken' value (optional, press Enter to skip):\n> ").strip()
        if csrf_input:
            csrf_cookies = parse_raw_input(csrf_input)
            csrf_token = csrf_cookies.get("csrftoken", csrf_input)
            if csrf_token:
                cookies["csrftoken"] = csrf_token

    # Verify session with LeetCode GraphQL
    print("\nVerifying session credentials with LeetCode...")
    auth_status = verify_leetcode_cookies(cookies)
    if auth_status.get("is_signed_in"):
        print(f"✅ SUCCESS: Verified logged-in account: '{auth_status.get('username')}'")
    else:
        print("⚠️ WARNING: LeetCode API could not confirm login status.")
        print("Please verify you copied the full value while actively logged in on leetcode.com.")

    # Build Playwright storage state format
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
    print("=" * 65)
    print(f"  🎉 SUCCESS! Session saved to: {SESSION_FILE}")
    print("=" * 65)
    print()
    print(f"  • LEETCODE_SESSION: {leetcode_session[:18]}...{leetcode_session[-10:]}")
    if csrf_token:
        print(f"  • csrftoken:        {csrf_token[:18]}...")
    print()
    print("  Next steps for GitHub Actions:")
    print("  1. Open leetcode_session.json in your editor and copy ALL its contents")
    print("  2. Go to your GitHub repo -> Settings -> Secrets and variables -> Actions")
    print("  3. Update/Create the secret: LEETCODE_SESSION_JSON")
    print("  4. Paste the JSON contents and click Save")
    print()
    print("=" * 65)


if __name__ == "__main__":
    main()



