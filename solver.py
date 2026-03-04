"""
Solver module — Orchestrates fetching the daily problem and retrieving a solution.
Uses LeetCode GraphQL for the daily problem and the scraper (Playwright) for the solution.
"""
import logging
from leetcode_api import get_daily_problem
from scraper import get_top_solution
from ai_refactor import refactor_code

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"


def solve_daily(session_file=SESSION_FILE):
    """
    Main solver function:
    1. Fetches today's daily problem via GraphQL
    2. Scrapes the top community solution using the logged-in session
    3. Uses AI to mildly refactor the code (if key provided) to prevent ban triggers
    Returns a dict with problem info and solution code, or None on failure.
    """
    logging.info("Fetching today's daily problem...")
    daily = get_daily_problem()

    if not daily:
        logging.error("Could not fetch the daily problem.")
        return None

    question = daily["question"]
    title = question["title"]
    slug = question["titleSlug"]
    difficulty = question["difficulty"]
    date = daily["date"]
    link = daily["link"]

    logging.info(f"Daily Problem: {title} ({difficulty}) — {slug}")

    logging.info("Fetching top community solution (logged-in session)...")
    code, language = get_top_solution(slug, session_file=session_file)

    if not code:
        logging.error("Could not fetch or extract a community solution.")
        return None

    logging.info(f"Successfully extracted solution code ({len(code)} chars) in {language}.")
    
    # Send through the AI auto-refactor bypass
    code = refactor_code(code, language)

    return {
        "title": title,
        "slug": slug,
        "difficulty": difficulty,
        "date": date,
        "link": link,
        "code": code,
        "language": language,
    }


if __name__ == "__main__":
    result = solve_daily()
    if result:
        print(f"\n{'='*60}")
        print(f"Problem: {result['title']} ({result['difficulty']})")
        print(f"Date: {result['date']}")
        print(f"{'='*60}")
        print(result["code"])
    else:
        print("Failed to solve the daily problem.")
