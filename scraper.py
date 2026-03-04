"""
Scraper module — Fetches the top Python3 community solution for a given problem.

Uses a multi-layered approach:
  1. Authenticated requests to LeetCode's discuss API (fastest, most reliable)
  2. Playwright fallback that scrapes Python code from solution post pages
"""
import logging
import re
import time
import json
import random
import requests as http_requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"


def load_cookies_from_session(session_file):
    """Loads cookies from the Playwright session file into a requests-compatible dict."""
    with open(session_file, "r") as f:
        data = json.load(f)
    cookies = {}
    for cookie in data.get("cookies", []):
        cookies[cookie["name"]] = cookie["value"]
    return cookies


def get_top_python_solution(question_slug, session_file=SESSION_FILE):
    """Fetches the top Python3 community solution using multiple strategies."""
    # Strategy 1: Authenticated discuss API
    code = try_discuss_api(question_slug, session_file)
    if code:
        return code

    # Strategy 2: Playwright scrape
    code = try_playwright_scrape(question_slug, session_file)
    if code:
        return code

    logging.error("All solution fetch strategies failed.")
    return None


def try_discuss_api(question_slug, session_file):
    """Uses the authenticated discuss API to fetch the top solution."""
    try:
        cookies = load_cookies_from_session(session_file)
    except Exception as e:
        logging.warning(f"Could not load cookies: {e}")
        return None

    headers = {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/problems/{question_slug}/",
        "x-csrftoken": cookies.get("csrftoken", ""),
    }

    # Get questionId first
    question_query = """
    query getQuestion($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        title
      }
    }
    """
    resp = http_requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": question_query, "variables": {"titleSlug": question_slug}},
        cookies=cookies,
        headers=headers,
    )
    if resp.status_code != 200:
        logging.warning(f"Failed to fetch questionId. Status: {resp.status_code}")
        return None

    question_data = resp.json().get("data", {}).get("question", {})
    question_id = question_data.get("questionId")
    if not question_id:
        logging.warning("Could not get questionId.")
        return None

    logging.info(f"Got questionId: {question_id} for {question_slug}")

    # Try fetching discuss topics with python filter
    topics_query = """
    query questionTopicsList($questionId: String!, $orderBy: TopicSortingOption, $skip: Int!, $query: String!, $first: Int!, $tags: [String!]) {
      questionTopicsList(questionId: $questionId, orderBy: $orderBy, skip: $skip, query: $query, first: $first, tags: $tags) {
        totalNum
        data {
          id
          title
          post {
            id
            voteCount
            content
          }
        }
      }
    }
    """
    variables = {
        "questionId": question_id,
        "orderBy": "most_votes",
        "skip": 0,
        "query": "python",
        "first": 10,
        "tags": [],
    }

    resp = http_requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": topics_query, "variables": variables},
        cookies=cookies,
        headers=headers,
    )

    if resp.status_code == 200:
        data = resp.json()
        topics = data.get("data", {}).get("questionTopicsList", {}).get("data", [])
        for topic in topics:
            content = topic.get("post", {}).get("content", "")
            if content:
                code = extract_python_from_markdown(content)
                if code:
                    logging.info(f"Found solution via API: '{topic.get('title')}' (votes: {topic['post'].get('voteCount', 0)})")
                    return code
        logging.warning("Discuss API: found topics but no extractable Python code.")
    else:
        logging.warning(f"Discuss API status {resp.status_code}")

    return None


def try_playwright_scrape(question_slug, session_file):
    """
    Fallback: Uses Playwright to open the solutions list,
    iterates through the top solution posts looking for Python code.
    """
    solutions_url = f"https://leetcode.com/problems/{question_slug}/solutions/?languageTags=python3&orderBy=most_votes"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                storage_state=session_file,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
        except Exception as e:
            logging.error(f"Failed to load session: {e}")
            browser.close()
            return None

        page = context.new_page()

        try:
            logging.info(f"[Playwright] Navigating to: {solutions_url}")
            page.goto(solutions_url, wait_until="domcontentloaded")
            time.sleep(5)

            # Collect all solution post links
            solution_links = page.locator(f'a[href*="/problems/{question_slug}/solutions/"]').all()
            hrefs = []
            for link in solution_links:
                href = link.get_attribute("href")
                if href and "/solutions/" in href:
                    parts = href.split("/solutions/")
                    if len(parts) > 1 and parts[1].strip("/"):
                        full = f"https://leetcode.com{href}" if href.startswith("/") else href
                        if full not in hrefs:
                            hrefs.append(full)

            if not hrefs:
                logging.error("[Playwright] No solution links found.")
                browser.close()
                return None

            logging.info(f"[Playwright] Found {len(hrefs)} solution links. Checking top 3...")

            # Try the top 3 solutions to find one with Python code
            for i, url in enumerate(hrefs[:3]):
                logging.info(f"[Playwright] Trying solution {i+1}: {url}")
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(6)

                # Get the full page HTML to search for Python code
                page_content = page.content()

                # Check if there's Python code in the page
                python_code = extract_python_from_html(page_content)
                if python_code:
                    logging.info(f"[Playwright] Found Python solution on attempt {i+1} ({len(python_code)} chars)")
                    browser.close()
                    return python_code

                # Also try extracting from visible text
                code_blocks = []
                for selector in ["pre", "code"]:
                    elements = page.locator(selector).all()
                    for el in elements:
                        try:
                            text = el.inner_text(timeout=3000).strip()
                            if text and len(text) > 20 and is_python_code(text):
                                code_blocks.append(text)
                        except:
                            pass

                if code_blocks:
                    best = max(code_blocks, key=len)
                    cleaned = clean_solution_code(best)
                    if cleaned:
                        logging.info(f"[Playwright] Found Python code on attempt {i+1} ({len(cleaned)} chars)")
                        browser.close()
                        return cleaned

            logging.error("[Playwright] No Python solution found in top 3 posts.")
            browser.close()
            return None

        except Exception as e:
            logging.error(f"[Playwright] Error: {e}")
            browser.close()
            return None


def is_python_code(text):
    """Heuristic to check if a code block is Python."""
    python_indicators = [
        "class Solution",
        "def ",
        "self.",
        "return ",
        "for ",
        "while ",
        "if ",
        "elif ",
        "import ",
        "range(",
        "len(",
        "print(",
        "# ",
    ]
    non_python_indicators = [
        "public class",
        "public static",
        "System.out",
        "int main(",
        "void ",
        "vector<",
        "#include",
        "cout <<",
        "nullptr",
        "var ",
        "let ",
        "const ",
        "function(",
        "func ",
        "fn ",
    ]

    text_lower = text.lower()
    python_score = sum(1 for ind in python_indicators if ind.lower() in text_lower)
    non_python_score = sum(1 for ind in non_python_indicators if ind.lower() in text_lower)

    return python_score > non_python_score and python_score >= 2


def extract_python_from_html(html_content):
    """Extracts Python code blocks from raw HTML."""
    # Look for code blocks that mention python in their class/lang attributes
    # Pattern: <code class="...python..." ...>...</code> or <pre><code>class Solution...</code></pre>
    patterns = [
        r'<code[^>]*(?:python|py)[^>]*>(.*?)</code>',
        r'<pre[^>]*>(.*?class Solution.*?)</pre>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            # Strip HTML tags from the match
            clean = re.sub(r'<[^>]+>', '', match).strip()
            if clean and len(clean) > 20 and is_python_code(clean):
                return clean_solution_code(clean)

    return None


def extract_python_from_markdown(content):
    """Extracts Python code blocks from markdown content."""
    if not content:
        return None

    # Fenced code blocks with python tag
    patterns = [
        r'```python3?\s*\n(.*?)```',
        r'```py\s*\n(.*?)```',
        r'```\s*\n(class Solution.*?)```',
        r'```\n(.*?class Solution.*?)```',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            # Filter for Python and pick the longest
            python_matches = [m for m in matches if is_python_code(m)]
            if python_matches:
                return max(python_matches, key=len).strip()
            # If no python-specific match, return longest that has class Solution
            for m in matches:
                if "class Solution" in m:
                    return m.strip()

    # Try to find class Solution without code fences
    match = re.search(r'(class Solution.*?)(?:\n\n[^\s]|\Z)', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def clean_solution_code(raw_code):
    """Extracts a clean class Solution block from raw code."""
    if not raw_code:
        return None

    # Decode HTML entities
    raw_code = raw_code.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"')

    # If we already have class Solution, extract it
    match = re.search(r'(class\s+Solution.*)', raw_code, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If we have a bare def with self param (method without class wrapper), wrap it
    match = re.search(r'(def\s+\w+\s*\(self.*)', raw_code, re.DOTALL)
    if match:
        method_code = match.group(1).strip()
        # Indent each line by 4 spaces and wrap with class Solution
        indented = "\n".join("    " + line for line in method_code.split("\n"))
        return f"class Solution:\n{indented}"

    # Bare def without self (standalone function)
    match = re.search(r'(def\s+\w+.*)', raw_code, re.DOTALL)
    if match:
        return match.group(1).strip()

    return raw_code.strip()


if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "special-positions-in-a-binary-matrix"
    print(f"Fetching top Python3 solution for: {slug}")
    code = get_top_python_solution(slug)
    if code:
        print("=" * 60)
        print("Extracted Code:")
        print("=" * 60)
        print(code)
    else:
        print("Failed to extract solution.")
