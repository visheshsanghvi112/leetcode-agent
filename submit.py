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

    problem_url = f"https://leetcode.com/problems/{question_slug}/description/"
    logging.info(f"Preparing Playwright submission for '{question_slug}' (Question ID: {question_id})...")

    def save_refreshed_session():
        try:
            context.storage_state(path=session_file)
            logging.info("Refreshed and saved updated session state to session file.")
        except Exception as err:
            logging.debug(f"Could not update session file: {err}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        context_args = {
            "user_agent": DEFAULT_USER_AGENT,
            "viewport": {"width": 1920, "height": 1080},
            "device_scale_factor": 1,
            "permissions": ["clipboard-read", "clipboard-write"],
        }
        if os.path.exists(session_file):
            context_args["storage_state"] = session_file

        context = browser.new_context(**context_args)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page = context.new_page()

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
                browser.close()
                return "Error: Session Expired (Login Required)"

            page_title = page.title()
            if "Just a moment" in page_title or "Cloudflare" in page_title:
                logging.warning("Cloudflare challenge page detected, waiting 5 seconds for clearance...")
                page.wait_for_timeout(5000)

            # -------------------------------------------------------------
            # Strategy 1: In-Browser Evaluated Fetch (Fastest & Most Reliable)
            # -------------------------------------------------------------
            if question_id:
                logging.info("Executing Strategy 1: In-Browser Evaluated API Submission...")
                try:
                    submit_response = page.evaluate(
                        """
                        async ([slug, qId, codeStr, langStr, csrf]) => {
                            // Extract csrf from document.cookie if not passed
                            let token = csrf;
                            if (!token) {
                                const match = document.cookie.match(/csrftoken=([^;]+)/);
                                if (match) token = match[1];
                            }
                            try {
                                const res = await fetch(`/problems/${slug}/submit/`, {
                                    method: "POST",
                                    headers: {
                                        "Content-Type": "application/json",
                                        "x-csrftoken": token,
                                        "x-requested-with": "XMLHttpRequest"
                                    },
                                    body: JSON.stringify({
                                        lang: langStr,
                                        question_id: String(qId),
                                        typed_code: codeStr
                                    })
                                });
                                const json = await res.json();
                                return { status: res.status, data: json };
                            } catch (err) {
                                return { error: err.toString() };
                            }
                        }
                        """,
                        [question_slug, question_id, code, language, csrf_token],
                    )

                    if submit_response and "data" in submit_response:
                        data = submit_response["data"]
                        submission_id = data.get("submission_id")

                        if submission_id:
                            logging.info(f"Submission accepted by LeetCode! Submission ID: {submission_id}")
                            # Poll for verification check
                            verdict = poll_submission_verdict(page, submission_id)
                            save_refreshed_session()
                            if verdict:
                                browser.close()
                                return verdict
                        elif "error" in data:
                            logging.warning(f"Strategy 1 API returned error message: {data['error']}")
                        else:
                            logging.warning(f"Strategy 1 response: {data}")
                except Exception as e:
                    logging.warning(f"Strategy 1 execution failed: {e}")

            # -------------------------------------------------------------
            # Strategy 2: Direct Monaco Editor JS API Injection + Click Submit
            # -------------------------------------------------------------
            logging.info("Executing Strategy 2: Monaco Editor API Injection...")
            monaco_set = page.evaluate(
                """
                ([codeStr]) => {
                    try {
                        if (window.monaco && window.monaco.editor) {
                            const models = window.monaco.editor.getModels();
                            if (models.length > 0) {
                                models[0].setValue(codeStr);
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
            else:
                # -------------------------------------------------------------
                # Strategy 3: Simulated Mouse & Keyboard Paste
                # -------------------------------------------------------------
                logging.info("Executing Strategy 3: DOM Keyboard Selection & Paste...")
                try:
                    editor = page.locator(".monaco-editor, [data-track-load='code_editor']").first
                    editor.wait_for(state="visible", timeout=8000)
                    editor.click()
                    modifier = "Meta" if "Mac" in page.evaluate("navigator.platform") else "Control"
                    page.keyboard.press(f"{modifier}+A")
                    page.keyboard.press("Backspace")
                    page.evaluate("([code]) => navigator.clipboard.writeText(code)", [code])
                    page.keyboard.press(f"{modifier}+V")
                    page.wait_for_timeout(1000)
                except Exception as e:
                    logging.warning(f"Strategy 3 editor interaction failed: {e}")

            # Click the Submit button
            logging.info("Clicking Submit button...")
            submit_clicked = False
            submit_selectors = [
                'button[data-e2e-locator="console-submit-button"]',
                'button:has-text("Submit")',
                'button[data-cy="submit-code-btn"]',
            ]
            for sel in submit_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible():
                        btn.click()
                        submit_clicked = True
                        logging.info(f"Clicked submit button using selector '{sel}'.")
                        break
                except Exception:
                    continue

            if not submit_clicked:
                logging.warning("Could not find visible Submit button in DOM.")

            # Wait for submission result container or response
            logging.info("Waiting for submission verdict element in DOM...")
            try:
                page.locator('[data-e2e-locator="submission-result"], [data-track-load="submission_result"]').first.wait_for(
                    state="visible", timeout=20000
                )
                result_text = page.locator('[data-e2e-locator="submission-result"]').inner_text()
                logging.info(f"DOM Submission Result: {result_text}")
                save_refreshed_session()
                browser.close()
                return result_text.strip()
            except Exception as e:
                logging.warning(f"Timeout waiting for DOM result container: {e}")

            # Capture failure screenshot for debugging
            page.screenshot(path="debug_submission_failure.png")
            save_refreshed_session()
            browser.close()
            return "Submission Sent (Check LeetCode Profile)"

        except Exception as e:
            logging.error(f"Playwright submission encountered exception: {e}")
            try:
                page.screenshot(path="debug_submission_error.png")
            except Exception:
                pass
            save_refreshed_session()
            browser.close()
            return f"Error interacting with browser: {e}"



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

