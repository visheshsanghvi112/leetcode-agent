"""
Scraper module — Fetches the top community solutions for a given LeetCode problem.

Uses a robust multi-layered approach:
  1. Modern LeetCode Solutions GraphQL API (questionSolutions) — fastest & official
  2. Legacy LeetCode Discuss GraphQL API (questionTopicsList)
  3. Playwright browser fallback for dynamic pages
"""
import logging
import re
import time
import json
import requests as http_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"



def load_cookies_from_session(session_file=SESSION_FILE):
    """Loads cookies from the Playwright session file into a requests-compatible dict."""
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = {}
        for cookie in data.get("cookies", []):
            cookies[cookie["name"]] = cookie["value"]
        return cookies
    except Exception as e:
        logging.debug(f"Could not load cookies from {session_file}: {e}")
        return {}


def get_top_solution(question_slug, session_file=SESSION_FILE):
    """
    Fetches the top community solution across supported languages.
    Returns (code, language) tuple or (None, None) if not found.
    """
    languages_to_try = [
        ("python3", ["python3", "python"]),
        ("python", ["python3", "python"]),
        ("javascript", ["javascript"]),
        ("mysql", ["mysql"]),
        ("pandas", ["pandas"]),
    ]

    for search_query, lang_tags in languages_to_try:
        logging.info(f"Attempting to fetch {search_query} community solution for '{question_slug}'...")

        # Strategy 1: Official modern Solutions GraphQL endpoint
        code = try_question_solutions_api(question_slug, search_query, lang_tags, session_file)
        if code:
            return code, search_query

        # Strategy 2: Legacy Discuss GraphQL API
        code = try_discuss_api(question_slug, search_query, search_query, session_file)
        if code:
            return code, search_query

        # Strategy 3: Playwright scrape fallback
        code = try_playwright_scrape(question_slug, search_query, search_query, session_file)
        if code:
            return code, search_query

    logging.warning(f"No community solutions found via scraping for '{question_slug}'.")
    return None, None


def try_question_solutions_api(question_slug, search_query, lang_tags, session_file):
    """
    Queries LeetCode's modern official Solutions tab GraphQL API (questionSolutions).
    """
    cookies = load_cookies_from_session(session_file)
    headers = {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/problems/{question_slug}/solutions/",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if "csrftoken" in cookies:
        headers["x-csrftoken"] = cookies["csrftoken"]

    query = """
    query communitySolutions($questionSlug: String!, $skip: Int!, $first: Int!, $query: String!, $orderBy: TopicSortingOption, $languageTags: [String!], $topicTags: [String!]) {
      questionSolutions(
        filters: {questionSlug: $questionSlug, skip: $skip, first: $first, query: $query, orderBy: $orderBy, languageTags: $languageTags, topicTags: $topicTags}
      ) {
        totalNum
        solutions {
          id
          title
          post {
            id
            status
            voteCount
            content
          }
        }
      }
    }
    """

    variables = {
        "questionSlug": question_slug,
        "skip": 0,
        "first": 5,
        "query": "",
        "orderBy": "most_votes",
        "languageTags": lang_tags,
        "topicTags": [],
    }

    try:
        resp = http_requests.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            cookies=cookies,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            solutions = data.get("data", {}).get("questionSolutions", {}).get("solutions", [])
            for sol in solutions:
                content = sol.get("post", {}).get("content", "")
                if content:
                    code = extract_code_from_markdown(content, search_query)
                    if code:
                        title = sol.get("title", "")
                        votes = sol.get("post", {}).get("voteCount", 0)
                        logging.info(f"Found solution via modern Solutions API: '{title}' (votes: {votes})")
                        return code
    except Exception as e:
        logging.warning(f"Error querying modern Solutions API: {e}")

    return None


def try_discuss_api(question_slug, search_query, leetcode_lang_id, session_file):
    """Legacy discuss topics GraphQL API."""
    cookies = load_cookies_from_session(session_file)
    headers = {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/problems/{question_slug}/",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if "csrftoken" in cookies:
        headers["x-csrftoken"] = cookies["csrftoken"]

    # Fetch questionId
    question_query = """
    query getQuestion($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        title
      }
    }
    """
    try:
        resp = http_requests.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": question_query, "variables": {"titleSlug": question_slug}},
            cookies=cookies,
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        question_id = resp.json().get("data", {}).get("question", {}).get("questionId")
        if not question_id:
            return None

        topics_query = """
        query questionTopicsList($questionId: String!, $orderBy: TopicSortingOption, $skip: Int!, $query: String!, $first: Int!, $tags: [String!]) {
          questionTopicsList(questionId: $questionId, orderBy: $orderBy, skip: $skip, query: $query, first: $first, tags: $tags) {
            totalNum
            edges {
              node {
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
        }
        """
        variables = {
            "questionId": str(question_id),
            "orderBy": "most_votes",
            "skip": 0,
            "query": search_query,
            "first": 5,
            "tags": [],
        }

        resp = http_requests.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": topics_query, "variables": variables},
            cookies=cookies,
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 200:
            topics_data = resp.json().get("data", {}).get("questionTopicsList", {})
            edges = topics_data.get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                content = node.get("post", {}).get("content", "")
                if content:
                    code = extract_code_from_markdown(content, search_query)
                    if code:
                        logging.info(f"Found solution via Discuss API: '{node.get('title')}'")
                        return code
    except Exception as e:
        logging.warning(f"Error querying Discuss API: {e}")

    return None


def try_playwright_scrape(question_slug, search_query, leetcode_lang_id, session_file):
    """Fallback: Scrapes solution using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logging.debug("Playwright not installed; skipping browser scrape.")
        return None

    solutions_url = f"https://leetcode.com/problems/{question_slug}/solutions/?languageTags={leetcode_lang_id}&orderBy=most_votes"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
            )

            context_opts = {
                "user_agent": DEFAULT_USER_AGENT,
                "viewport": {"width": 1920, "height": 1080},
            }
            try:
                with open(session_file, "r") as f:
                    json.load(f)
                context_opts["storage_state"] = session_file
            except Exception:
                pass

            context = browser.new_context(**context_opts)
            page = context.new_page()

            try:
                page.goto(solutions_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)

                # Find solution links
                solution_links = page.locator('a[href*="/solutions/"]').all()
                hrefs = []
                for link in solution_links:
                    href = link.get_attribute("href")
                    if href and "/solutions/" in href:
                        parts = href.split("/solutions/")
                        if len(parts) > 1 and parts[1].strip("/"):
                            full = f"https://leetcode.com{href}" if href.startswith("/") else href
                            if full not in hrefs:
                                hrefs.append(full)

                for url in hrefs[:3]:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(2000)
                        content = page.content()
                        code = extract_code_from_html(content, search_query)
                        if code:
                            browser.close()
                            return code
                    except Exception:
                        continue

            finally:
                browser.close()
    except Exception as e:
        logging.warning(f"Playwright scrape encountered error: {e}")

    return None


def is_language_code(text, language="python"):
    text_lower = text.lower()

    if language in ["python", "python3"]:
        # Disqualify C++/Java/Rust/Go signatures
        if any(bad in text for bad in ["vector<", "public:", "ListNode*", "TreeNode*", "public int", "public void", "std::", "-> std", "func "]):
            return False
        has_def = "def " in text
        has_class = "class solution" in text_lower
        python_features = ["self", "->", "return", "for ", "while ", "import ", "range(", "len(", "in "]
        feature_count = sum(1 for ind in python_features if ind in text_lower)
        return (has_def and feature_count >= 1) or (has_class and has_def)

    elif language == "mysql":
        sql_indicators = ["select ", "from ", "where ", "group by", "order by", "left join", "join ", "insert ", "update "]
        return sum(1 for ind in sql_indicators if ind in text_lower) >= 2

    elif language == "javascript":
        if "def " in text:
            return False
        js_indicators = ["var ", "let ", "const ", "function", "=>", "console.log", "return "]
        return sum(1 for ind in js_indicators if ind in text_lower) >= 2

    elif language == "pandas":
        pandas_indicators = ["import pandas", "pd.", "def ", ".map", ".apply", ".merge", ".groupby", "dataframe"]
        return sum(1 for ind in pandas_indicators if ind in text_lower) >= 2

    return True


def extract_code_from_markdown(content, language="python"):
    """Extracts code blocks for the requested language from markdown content."""
    if not content:
        return None

    # Specific language fence patterns prioritized first
    if language in ["python", "python3"]:
        lang_patterns = [
            r"```(?:python3?|py)\s*\n(.*?)```",
            r"```\s*\n(class\s+Solution.*?)```",
            r"```\s*\n(.*?)```",
        ]
    elif language == "javascript":
        lang_patterns = [
            r"```(?:javascript|js)\s*\n(.*?)```",
            r"```(?:typescript|ts)\s*\n(.*?)```",
            r"```\s*\n(.*?)```",
        ]
    elif language == "mysql":
        lang_patterns = [
            r"```(?:mysql|sql)\s*\n(.*?)```",
            r"```\s*\n(.*?)```",
        ]
    elif language == "pandas":
        lang_patterns = [
            r"```(?:pandas|python3?|py)\s*\n(.*?)```",
            r"```\s*\n(.*?)```",
        ]
    else:
        lang_patterns = [r"```\s*\n(.*?)```"]

    for pattern in lang_patterns:
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        valid = [m.strip() for m in matches if is_language_code(m, language)]
        if valid:
            best = max(valid, key=len)
            cleaned = clean_solution_code(best, language)
            if cleaned:
                return cleaned

    # Unfenced code containing class Solution
    match = re.search(r"(class\s+Solution.*?)(?:\n\n[^\s]|\Z)", content, re.DOTALL)
    if match and is_language_code(match.group(1), language):
        cleaned = clean_solution_code(match.group(1), language)
        if cleaned:
            return cleaned

    return None



def extract_code_from_html(html_content, language="python"):
    """Extracts code blocks from raw HTML."""
    patterns = [
        r'<code[^>]*>(.*?)</code>',
        r'<pre[^>]*>(.*?)</pre>',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            clean = re.sub(r'<[^>]+>', '', match).strip()
            if clean and len(clean) > 20 and is_language_code(clean, language):
                cleaned = clean_solution_code(clean, language)
                if cleaned:
                    return cleaned
    return None


def clean_solution_code(raw_code, language="python"):
    """Normalizes and extracts a clean Solution block from raw code."""
    if not raw_code:
        return None

    # Decode HTML entities
    raw_code = (
        raw_code.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )

    # Strip trailing markdown fences if included
    if "```" in raw_code:
        raw_code = raw_code.split("```")[0].strip()

    # Remove trailing markdown links or horizontal rules
    lines = raw_code.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("http://") or stripped.startswith("https://") or stripped.startswith("[http"):
            break
        if stripped.startswith("---") or stripped.startswith("___"):
            break
        cleaned_lines.append(line)
    raw_code = "\n".join(cleaned_lines).strip()

    if language not in ["python", "python3"]:
        return raw_code.strip()

    # Extract class Solution if present
    match = re.search(r"(class\s+Solution.*)", raw_code, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If method with self is present, wrap in class Solution
    match = re.search(r"(def\s+\w+\s*\(self.*)", raw_code, re.DOTALL)
    if match:
        method_code = match.group(1).strip()
        indented = "\n".join("    " + line for line in method_code.split("\n"))
        return f"class Solution:\n{indented}"

    # Standalone def
    match = re.search(r"(def\s+\w+.*)", raw_code, re.DOTALL)
    if match:
        return match.group(1).strip()

    return raw_code.strip()



if __name__ == "__main__":
    import sys
    test_slug = sys.argv[1] if len(sys.argv) > 1 else "find-the-minimum-and-maximum-number-of-nodes-between-critical-points"
    print(f"Testing community solution fetch for: {test_slug}")
    code, lang = get_top_solution(test_slug)
    if code:
        print(f"Found {lang} solution ({len(code)} chars):\n{code[:300]}...")
    else:
        print("No community solution found.")

