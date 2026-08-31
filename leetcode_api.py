import time
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}


def post_graphql(query, variables=None, cookies=None, headers=None, max_retries=3):
    """Executes a GraphQL query against LeetCode with retries."""
    combined_headers = {**DEFAULT_HEADERS, **(headers or {})}
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables or {}},
                cookies=cookies or {},
                headers=combined_headers,
                timeout=15,
            )
            if response.status_code == 200:
                return response.json()
            logging.warning(f"GraphQL request returned status {response.status_code} (attempt {attempt}/{max_retries})")
        except Exception as e:
            logging.warning(f"GraphQL request failed (attempt {attempt}/{max_retries}): {e}")
        time.sleep(attempt * 2)
    return None


def get_daily_problem():
    """Fetches the current daily active problem from LeetCode with full details."""
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          questionId
          questionFrontendId
          title
          titleSlug
          difficulty
          content
          codeSnippets {
            lang
            langSlug
            code
          }
        }
      }
    }
    """
    data = post_graphql(query)
    if not data:
        logging.error("Failed to query LeetCode GraphQL for daily problem.")
        return None

    daily = data.get("data", {}).get("activeDailyCodingChallengeQuestion", {})
    question = daily.get("question") if daily else None

    if daily and question:
        # If content or codeSnippets are missing from questionOfToday, fetch separately
        if not question.get("content") or not question.get("codeSnippets"):
            details = get_question_details(question["titleSlug"])
            if details:
                question.update(details)
        return daily
    else:
        logging.error("Failed to parse daily problem from GraphQL response.")
        return None


def get_question_details(title_slug):
    """Fetches complete question description, metadata, and code snippets by slug."""
    query = """
    query getQuestionDetails($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        questionFrontendId
        title
        titleSlug
        difficulty
        content
        codeSnippets {
          lang
          langSlug
          code
        }
      }
    }
    """
    data = post_graphql(query, variables={"titleSlug": title_slug})
    if data:
        return data.get("data", {}).get("question")
    return None


def check_user_session(cookies):
    """Checks whether the provided session cookies represent a logged-in session."""
    query = """
    query userStatus {
      userStatus {
        isSignedIn
        username
        realName
      }
    }
    """
    if isinstance(cookies, list):
        cookie_dict = {c["name"]: c["value"] for c in cookies if isinstance(c, dict) and "name" in c and "value" in c}
    elif isinstance(cookies, dict):
        cookie_dict = cookies
    else:
        cookie_dict = {}

    csrf = cookie_dict.get("csrftoken", "")
    headers = {
        "x-csrftoken": csrf,
        "Referer": "https://leetcode.com/",
        "Origin": "https://leetcode.com"
    }
    data = post_graphql(query, cookies=cookie_dict, headers=headers)
    if data:
        user_status = data.get("data", {}).get("userStatus", {})
        return {
            "is_signed_in": user_status.get("isSignedIn", False),
            "username": user_status.get("username", ""),
            "real_name": user_status.get("realName", ""),
        }
    return {"is_signed_in": False, "username": "", "real_name": ""}




if __name__ == "__main__":
    daily = get_daily_problem()
    if daily:
        q = daily["question"]
        print(f"Daily Problem: #{q.get('questionFrontendId')} {q.get('title')} ({q.get('titleSlug')}) [{q.get('difficulty')}]")
        print(f"Date: {daily.get('date')}")
        snippets = [s['langSlug'] for s in q.get('codeSnippets', [])]
        print(f"Available language snippets: {snippets}")
    else:
        print("Failed to fetch daily problem.")

