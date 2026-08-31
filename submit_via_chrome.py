#!/usr/bin/env python3
"""
Automated LeetCode Solver & Submitter via Real Google Chrome.
Controls your authenticated Google Chrome browser directly via AppleScript.
Zero manual login, zero cookie copying, 100% automated!
"""

import subprocess
import time
import json
import base64
import logging
from solver import solve_daily
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_applescript(script):
    p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return p.stdout.strip(), p.stderr.strip()


def execute_chrome_js(tab_url_match, js_code):
    """Executes a JS string inside the Chrome tab matching tab_url_match using base64 encoding."""
    b64_js = base64.b64encode(js_code.encode("utf-8")).decode("utf-8")
    script = f'''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "{tab_url_match}" then
                    try
                        return (execute t javascript "eval(atob('{b64_js}'))")
                    on error err
                        return "ERR:" & err
                    end try
                end if
            end repeat
        end repeat
        return "NOT_FOUND"
    end tell
    '''
    out, _ = run_applescript(script)
    return out


def open_or_focus_tab(url):
    script = f'''
    tell application "Google Chrome"
        activate
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "leetcode.com" then
                    set URL of t to "{url}"
                    set active tab index of w to (index of t)
                    return "FOCUSED"
                end if
            end repeat
        end repeat
        make new tab at end of tabs of window 1 with properties {{URL:"{url}"}}
        return "OPENED"
    end tell
    '''
    out, _ = run_applescript(script)
    return out


def solve_and_submit():
    print("=" * 65)
    print("      LeetCode Automated Solution Submitter (Chrome)")
    print("=" * 65)

    # 1. Fetch daily problem and AI-refactored solution
    problem_info = solve_daily()
    if not problem_info:
        logging.error("Failed to solve daily problem.")
        return False

    frontend_id = problem_info.get("frontend_id")
    title = problem_info.get("title")
    slug = problem_info.get("slug")
    question_id = problem_info.get("question_id")
    code = problem_info.get("code")
    language = problem_info.get("language", "python3")
    problem_url = f"https://leetcode.com/problems/{slug}/description/"

    logging.info(f"Submitting #{frontend_id} {title} via Google Chrome...")

    # 2. Open / Focus Problem in Google Chrome
    open_or_focus_tab(problem_url)
    time.sleep(3)

    # 3. Dispatch Submission via in-tab authenticated fetch
    logging.info("Dispatching authenticated submission inside Chrome...")
    code_json = json.dumps(code)
    submit_js = f"""
    (() => {{
        window.__sub_id = 'PENDING';
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        const csrf = match ? match[1] : '';
        fetch('/problems/{slug}/submit/', {{
            method: 'POST',
            credentials: 'include',
            headers: {{
                'Content-Type': 'application/json',
                'x-csrftoken': csrf,
                'x-requested-with': 'XMLHttpRequest'
            }},
            body: JSON.stringify({{
                lang: '{language}',
                question_id: '{question_id}',
                typed_code: {code_json}
            }})
        }})
        .then(r => r.json())
        .then(d => {{
            window.__sub_id = d.submission_id ? String(d.submission_id) : JSON.stringify(d);
        }})
        .catch(e => {{
            window.__sub_id = 'ERR: ' + e.toString();
        }});
        return 'DISPATCHED_OK';
    }})()
    """

    execute_chrome_js("leetcode.com", submit_js)

    # 4. Poll for submission ID
    sub_id = None
    for _ in range(12):
        time.sleep(1)
        res = execute_chrome_js("leetcode.com", "window.__sub_id || 'NONE'")
        if res and res not in ["PENDING", "NONE", "NOT_FOUND"]:
            sub_id = res
            logging.info(f"Received submission ID: #{sub_id}")
            break

    verdict = "Submitted"
    if sub_id and sub_id.isdigit():
        logging.info(f"Polling verdict for submission #{sub_id}...")
        for _ in range(15):
            time.sleep(2)
            check_js = f"""
            (() => {{
                window.__verdict = 'PENDING';
                fetch('/submissions/detail/{sub_id}/check/')
                .then(r => r.json())
                .then(d => {{ window.__verdict = JSON.stringify(d); }})
                .catch(e => {{ window.__verdict = 'ERR'; }});
                return 'CHECKING';
            }})()
            """
            execute_chrome_js("leetcode.com", check_js)
            time.sleep(1)

            res_v = execute_chrome_js("leetcode.com", "window.__verdict || ''")
            if res_v and "SUCCESS" in res_v:
                try:
                    d = json.loads(res_v)
                    status = d.get("status_display", "Accepted")
                    runtime = d.get("status_runtime", "")
                    memory = d.get("status_memory", "")
                    parts = [status]
                    if runtime and runtime != "N/A":
                        parts.append(f"Runtime: {runtime}")
                    if memory and memory != "N/A":
                        parts.append(f"Memory: {memory}")
                    verdict = " | ".join(parts)
                    break
                except Exception:
                    pass

    logging.info(f"🎉 Final Verdict: {verdict}")

    # 5. Save solution file locally
    from main import save_solution
    date_str = datetime.now().strftime("%Y-%m-%d")
    save_solution(date_str, title, frontend_id, code, verdict, language=language)

    print("\n" + "=" * 65)
    print(f"  RESULT: #{frontend_id} {title}")
    print(f"  VERDICT: {verdict}")
    print("=" * 65 + "\n")
    return "Accepted" in verdict


if __name__ == "__main__":
    solve_and_submit()
