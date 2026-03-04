"""
Submit module — Submits a solution to LeetCode using Playwright.
Must use Playwright to pass Cloudflare's bot protection on the /submit/ endpoint.
"""
import logging
import random
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"


def submit_solution(question_slug, code, session_file=SESSION_FILE):
    """
    Automates the browser to go to the problem page, paste the code, and click submit.
    """
    problem_url = f"https://leetcode.com/problems/{question_slug}/description/"
    
    with sync_playwright() as p:
        # Use headed mode locally if needed, but headless=True is fine if cookies are valid
        browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
        
        try:
            context = browser.new_context(
                storage_state=session_file,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                permissions=["clipboard-read", "clipboard-write"],
            )
            # Add scripts to mask Playwright
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            # Go to leetcode.com first to set local storage
            page.goto("https://leetcode.com/")
            page.evaluate("window.localStorage.setItem('global_lang', 'python3')")
            
            logging.info(f"Navigating to problem page: {problem_url}")
            page.goto(problem_url, wait_until="domcontentloaded")
            
            # Wait for page to settle
            page.wait_for_timeout(random.randint(5000, 7000))
            
            # 1. Click into the editor to focus it
            logging.info("Looking for code editor...")
            editor = page.locator('.monaco-editor').first
            editor.wait_for(state="visible", timeout=15000)
            editor.click()
            page.wait_for_timeout(random.randint(500, 1000))
            
            # 2. Select all existing code (Ctrl+A or Cmd+A)
            logging.info("Clearing existing code...")
            modifier = "Meta" if "Mac" in page.evaluate("navigator.platform") else "Control"
            page.keyboard.press(f"{modifier}+A")
            page.wait_for_timeout(random.randint(300, 600))
            page.keyboard.press("Backspace")
            page.wait_for_timeout(random.randint(500, 900))
            
            # 3. Paste the new code via Clipboard API
            logging.info("Pasting solution code...")
            page.evaluate("([code]) => navigator.clipboard.writeText(code)", [code])
            page.wait_for_timeout(random.randint(300, 800))
            page.keyboard.press(f"{modifier}+V")
            
            # Wait a chunk so the editor "reads" the paste before clicking submit
            page.wait_for_timeout(random.randint(1500, 2500))
            
            # 4. Click Submit
            logging.info("Clicking Submit button...")
            submit_btn = page.locator('button[data-e2e-locator="console-submit-button"]').first
            submit_btn.click()
            
            # 5. Wait for the submission result
            logging.info("Waiting for result (usually takes 5-15s)...")
            
            try:
                # First wait for the result container to appear
                page.locator('[data-e2e-locator="submission-result"]').wait_for(state="visible", timeout=25000)
                
                # Check what the result is
                result_text = page.locator('[data-e2e-locator="submission-result"]').inner_text()
                if "Accepted" in result_text:
                    logging.info("✅ ACCEPTED!")
                else:
                    logging.info(f"❌ Result: {result_text}")
                
            except Exception as e:
                logging.warning(f"Timeout or error waiting for result element: {e}")
                result_text = "Timeout waiting for result (check browser)"
                    
            browser.close()
            return result_text
            
        except Exception as e:
            logging.error(f"Playwright error during submission: {e}")
            browser.close()
            return "Error interacting with browser"


if __name__ == "__main__":
    slug = "special-positions-in-a-binary-matrix"
    test_code = """class Solution:
    def numSpecial(self, mat: List[List[int]]) -> int:
        rows = [sum(r) for r in mat]; cols = [sum(c) for c in zip(*mat)]
        return sum(mat[i][j] and rows[i] == cols[j] == 1 for i in range(len(mat)) for j in range(len(mat[0])))
"""
    print("Testing Playwright submission...")
    res = submit_solution(slug, test_code)
    print(f"Final Result: {res}")
