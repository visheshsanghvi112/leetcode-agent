"""
Submit module — Submits a solution to LeetCode using Playwright.
Implements a multi-layered submission engine:
  1. In-browser evaluated fetch submission with real-time check polling (Fastest, avoids DOM layout issues)
  2. Monaco Editor direct JavaScript model manipulation + DOM submit button click
  3. Keyboard simulated selection and paste fallback
"""
import os
import json
import time
import random
import logging
from leetcode_api import get_question_details

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def load_session_data(session_file=SESSION_FILE):
    """Loads session cookies and csrf token from session file."""
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = {}
        for c in data.get("cookies", []):
            cookies[c["name"]] = c["value"]
        return cookies, data
    except Exception as e:
        logging.error(f"Error loading session file {session_file}: {e}")
        return {}, None


def select_language_in_ui(page, language="python3"):
    """Switches the Monaco editor language in the LeetCode UI."""
    import re
    lang_labels = {
        "python3": ["Python3", "Python 3", "python3"],
        "python": ["Python", "python"],
        "javascript": ["JavaScript", "javascript", "JS"],
        "typescript": ["TypeScript", "typescript", "TS"],
        "mysql": ["MySQL", "MySQL"],
        "pandas": ["Pandas", "pandas"],
    }
    targets = lang_labels.get(language.lower(), ["Python3", "Python"])

    try:
        # Check current language button
        lang_btn = page.locator("button:has-text('C++'), button:has-text('Java'), button:has-text('Python'), button:has-text('JavaScript'), button:has-text('TypeScript'), button:has-text('C#'), button:has-text('Go'), button:has-text('Rust'), button:has-text('MySQL'), button:has-text('Pandas')").first
        if lang_btn.is_visible():
            current_lang = lang_btn.inner_text().strip()
            logging.info(f"Current editor language: '{current_lang}'")
            if any(t.lower() in current_lang.lower() for t in targets):
                logging.info(f"Language is already set to {current_lang}.")
                return True
            lang_btn.click()
            page.wait_for_timeout(800)

            # Click target language option in dropdown
            for target in targets:
                opt = page.locator(f"[role='option']:has-text('{target}'), li:has-text('{target}'), div:has-text('{target}')").filter(has_text=re.compile(rf"^{target}$", re.I)).first
                if opt.is_visible():
                    opt.click()
                    page.wait_for_timeout(800)
                    logging.info(f"Switched editor language to '{target}'.")
                    return True
                # Broader locator fallback
                opt = page.locator(f"text={target}").first
                if opt.is_visible():
                    opt.click()
                    page.wait_for_timeout(800)
                    logging.info(f"Switched editor language to '{target}'.")
                    return True
    except Exception as e:
        logging.warning(f"Could not switch language via UI: {e}")
    return False



def submit_solution(question_slug, code, language="python3", question_id=None, session_file=SESSION_FILE):
    """
    Submits the solution to LeetCode using Playwright with multi-tier fallback.
    Returns the submission verdict string (e.g. 'Accepted', 'Wrong Answer', etc.).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logging.error("Playwright is not installed. Cannot submit solution.")
        return "Playwright not installed"

    cookies, storage_state = load_session_data(session_file)
    csrf_token = cookies.get("csrftoken", "")

    # Retrieve question_id if not provided
    if not question_id:
        details = get_question_details(question_slug)
        if details:
            question_id = details.get("questionId")

    problem_url = f"https://leetcode.com/problems/{question_slug}/"
    logging.info(f"Preparing Playwright submission for '{question_slug}' (Question ID: {question_id})...")

    def save_refreshed_session():
        try:
            context.storage_state(path=session_file)
            logging.info("Refreshed and saved updated session state to session file.")
        except Exception as err:
            logging.debug(f"Could not update session file: {err}")

    profile_dir = os.path.abspath("./.leetcode_browser_data")

    with sync_playwright() as p:
        if os.path.exists(profile_dir) and os.path.isdir(profile_dir) and os.listdir(profile_dir):
            logging.info(f"Using persistent browser profile at '{profile_dir}'.")
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=True,
                user_agent=DEFAULT_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                permissions=["clipboard-read", "clipboard-write"],
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            browser = None
        else:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                permissions=["clipboard-read", "clipboard-write"],
            )

        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Explicitly build and register well-formed cookies for Playwright
        if not browser and storage_state and "cookies" in storage_state:
            pass
        elif storage_state and "cookies" in storage_state:
            cookies_to_add = []
            for c in storage_state["cookies"]:
                c_name = c.get("name")
                c_val = c.get("value")
                if c_name and c_val:
                    cookies_to_add.append({
                        "name": c_name,
                        "value": c_val,
                        "domain": ".leetcode.com",
                        "path": "/",
                        "httpOnly": c.get("httpOnly", True if c_name == "LEETCODE_SESSION" else False),
                        "secure": True,
                        "sameSite": "Lax",
                        "expires": 2147483647,
                    })
            if cookies_to_add:
                try:
                    context.add_cookies(cookies_to_add)
                    logging.info(f"Loaded {len(cookies_to_add)} authentication cookies into browser context.")
                except Exception as e:
                    logging.warning(f"Error adding cookies to context: {e}")

        page = context.pages[0] if context.pages else context.new_page()

        def close_all():
            try:
                if browser:
                    browser.close()
                else:
                    context.close()
            except Exception:
                pass

        try:
            logging.info(f"Navigating to problem page: {problem_url}")
            page.goto(problem_url, wait_until="domcontentloaded", timeout=30000)


            # Wait briefly for cloudflare or hydration to complete
            page.wait_for_timeout(3000)

            # Check if redirected to login page or blocked
            current_url = page.url
            if "/accounts/login" in current_url:
                logging.error("LeetCode redirected to login page! Session cookies have expired. Please run login_setup.py.")
                page.screenshot(path="debug_session_expired.png")
                close_all()
                return "Error: Session Expired (Login Required)"

            page_title = page.title()
            if "Just a moment" in page_title or "Cloudflare" in page_title:
                logging.warning("Cloudflare challenge page detected, waiting 5 seconds for clearance...")
                page.wait_for_timeout(5000)

            # Switch language in the UI to match the solution language
            select_language_in_ui(page, language)

            # Setup network response interceptor to capture submission verdicts
            submission_network_result = {"submission_id": None, "verdict": None}

            def handle_response(response):
                try:
                    url = response.url
                    if "/submit/" in url and response.request.method == "POST":
                        try:
                            json_data = response.json()
                            sub_id = json_data.get("submission_id")
                            if sub_id:
                                submission_network_result["submission_id"] = sub_id
                                logging.info(f"Captured submission ID from network: #{sub_id}")
                        except Exception:
                            pass
                    elif "/check/" in url:
                        try:
                            check_data = response.json()
                            if check_data.get("state") == "SUCCESS":
                                status_display = check_data.get("status_display", "Accepted")
                                runtime = check_data.get("status_runtime", "")
                                memory = check_data.get("status_memory", "")
                                verdict_parts = [status_display]
                                if runtime and runtime != "N/A":
                                    verdict_parts.append(f"Runtime: {runtime}")
                                if memory and memory != "N/A":
                                    verdict_parts.append(f"Memory: {memory}")
                                submission_network_result["verdict"] = " | ".join(verdict_parts)
                                logging.info(f"Captured verdict from network: {submission_network_result['verdict']}")
                        except Exception:
                            pass
                except Exception:
                    pass

            page.on("response", handle_response)

            # -------------------------------------------------------------
            # Strategy: Direct Monaco Editor JS API Injection + React Sync + Click Submit
            # -------------------------------------------------------------
            logging.info("Executing Monaco Editor API Injection...")

            monaco_set = page.evaluate(
                """
                ([codeStr]) => {
                    try {
                        if (window.monaco && window.monaco.editor) {
                            const models = window.monaco.editor.getModels();
                            if (models.length > 0) {
                                const model = models[0];
                                model.setValue(codeStr);
                                try {
                                    model.pushEditOperations([], [{
                                        range: model.getFullModelRange(),
                                        text: codeStr
                                    }], () => null);
                                } catch (e) {}
                                return true;
                            }
                        }
                    } catch (e) {}
                    return false;
                }
                """,
                [code],
            )

            if monaco_set:
                logging.info("Successfully set code via Monaco JS API!")
            
            # Click inside the Monaco editor and dispatch a keystroke to force React state sync
            try:
                editor_elem = page.locator(".monaco-editor, [data-track-load='code_editor'], .view-lines").first
                if editor_elem.is_visible():
                    editor_elem.click()
                    page.keyboard.press("End")
                    page.keyboard.type(" ")
                    page.keyboard.press("Backspace")
                    page.wait_for_timeout(800)
            except Exception as e:
                logging.debug(f"Note on typing in editor: {e}")

            # Click the Submit button
            page.wait_for_timeout(1000)
            logging.info("Clicking Submit button...")
            submit_clicked = False
            submit_selectors = [
                'button[data-e2e-locator="console-submit-button"]',
                'button:has-text("Submit")',
                'button[data-cy="submit-code-btn"]',
            ]
            for sel in submit_selectors:
                try:
                    btns = page.locator(sel).all()
                    for btn in btns:
                        if btn.is_visible():
                            # Click with mouse and also dispatch click
                            btn.scroll_into_view_if_needed()
                            btn.click(force=True)
                            btn.dispatch_event("click")
                            submit_clicked = True
                            logging.info(f"Clicked submit button using selector '{sel}'.")
                            break
                    if submit_clicked:
                        break
                except Exception:
                    continue

            if not submit_clicked:
                logging.warning("Could not find visible Submit button in DOM.")

            # Wait for network response or DOM result container
            logging.info("Waiting for submission verdict from network / DOM...")
            for _ in range(15):
                page.wait_for_timeout(2000)
                if submission_network_result.get("verdict"):
                    final_verdict = submission_network_result["verdict"]
                    save_refreshed_session()
                    close_all()
                    return final_verdict
                if submission_network_result.get("submission_id"):
                    sub_id = submission_network_result["submission_id"]
                    verdict = poll_submission_verdict(page, sub_id)
                    save_refreshed_session()
                    close_all()
                    return verdict

            # Check DOM for submission result
            try:
                result_elem = page.locator('[data-e2e-locator="submission-result"], [data-track-load="submission_result"]').first
                if result_elem.is_visible():
                    result_text = result_elem.inner_text().strip()
                    logging.info(f"DOM Submission Result: {result_text}")
                    save_refreshed_session()
                    close_all()
                    return result_text
            except Exception:
                pass

            # Capture screenshot
            page.screenshot(path="debug_submission_failure.png")
            save_refreshed_session()
            close_all()
            return "Submission Sent (Check LeetCode Profile)"



        except Exception as e:
            logging.error(f"Playwright submission encountered exception: {e}")
            try:
                page.screenshot(path="debug_submission_failure.png")
            except Exception:
                pass
            close_all()
            return f"Error: Submission Failed ({e})"



def poll_submission_verdict(page, submission_id, max_attempts=15):
    """Polls LeetCode check endpoint for the submission verdict."""
    logging.info(f"Polling verification for submission #{submission_id}...")
    for attempt in range(1, max_attempts + 1):
        page.wait_for_timeout(2000)
        try:
            check_data = page.evaluate(
                """
                async (subId) => {
                    const res = await fetch(`/submissions/detail/${subId}/check/`);
                    return await res.json();
                }
                """,
                submission_id,
            )

            state = check_data.get("state")
            if state == "SUCCESS":
                status_display = check_data.get("status_display", "Accepted")
                runtime = check_data.get("status_runtime", "")
                memory = check_data.get("status_memory", "")
                total_correct = check_data.get("total_correct", "")
                total_testcases = check_data.get("total_testcases", "")

                verdict_parts = [status_display]
                if runtime and runtime != "N/A":
                    verdict_parts.append(f"Runtime: {runtime}")
                if memory and memory != "N/A":
                    verdict_parts.append(f"Memory: {memory}")
                if total_correct and total_testcases:
                    verdict_parts.append(f"Passed: {total_correct}/{total_testcases}")

                final_verdict = " | ".join(verdict_parts)
                if "Accepted" in status_display:
                    logging.info(f"✅ ACCEPTED: {final_verdict}")
                else:
                    logging.info(f"❌ Result: {final_verdict}")
                return final_verdict
            elif state == "PENDING" or state == "STARTED":
                logging.info(f"Submission status: {state}... (attempt {attempt}/{max_attempts})")
            else:
                logging.info(f"Submission state: {state} (data: {check_data})")
        except Exception as e:
            logging.warning(f"Polling error on attempt {attempt}: {e}")

    return f"Submitted (#{submission_id})"


if __name__ == "__main__":
    slug = "special-positions-in-a-binary-matrix"
    test_code = """class Solution:
    def numSpecial(self, mat: List[List[int]]) -> int:
        rows = [sum(r) for r in mat]; cols = [sum(c) for c in zip(*mat)]
        return sum(mat[i][j] and rows[i] == cols[j] == 1 for i in range(len(mat)) for j in range(len(mat[0])))
"""
    print("Testing Playwright submission engine...")
    res = submit_solution(slug, test_code)
    print(f"Final Result: {res}")

