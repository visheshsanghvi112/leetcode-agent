"""
Solver module — Orchestrates fetching the daily problem and retrieving a high-quality solution.
Uses LeetCode GraphQL for problem data, community scraping as primary, and Gemini AI solver as fallback.
"""
import logging
from leetcode_api import get_daily_problem
from scraper import get_top_solution
from ai_refactor import refactor_code, solve_with_ai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SESSION_FILE = "leetcode_session.json"


def solve_daily(session_file=SESSION_FILE):
    """
    Main solver function:
    1. Fetches today's daily problem metadata, description, and starter snippets via GraphQL.
    2. Attempts to scrape the top community solution using modern & legacy APIs.
    3. If community solution exists, stealthily refactors it with Gemini AI.
    4. If no community solution exists (new problems), solves the problem directly using Gemini AI.
    Returns a dict with problem info and solution code, or None on critical failure.
    """
    logging.info("Fetching today's daily problem details...")
    daily = get_daily_problem()

    if not daily or not daily.get("question"):
        logging.error("Could not fetch the daily problem details from LeetCode.")
        return None

    question = daily["question"]
    title = question.get("title", "Daily Problem")
    slug = question.get("titleSlug", "")
    difficulty = question.get("difficulty", "Medium")
    question_id = question.get("questionId", "")
    frontend_id = question.get("questionFrontendId", "")
    date = daily.get("date", "")
    link = daily.get("link", "")
    content = question.get("content", "")
    code_snippets = question.get("codeSnippets", [])

    logging.info(f"Daily Problem: #{frontend_id} {title} ({difficulty}) — {slug}")

    # Extract default python3 starter code snippet
    python_snippet = next((s["code"] for s in code_snippets if s.get("langSlug") == "python3"), "")
    if not python_snippet:
        python_snippet = next((s["code"] for s in code_snippets if s.get("langSlug") == "python"), "class Solution:\n    pass")

    # Step 1: Try community scraping
    logging.info("Searching for top community solutions...")
    code, language = get_top_solution(slug, session_file=session_file)

    if code and language:
        logging.info(f"Successfully retrieved community solution ({len(code)} chars) in {language}.")
        # Refactor scraped community code to ensure uniqueness
        code = refactor_code(code, language)
    else:
        # Step 2: Fallback to direct Gemini AI Problem Solver
        logging.warning("No community solutions available. Activating Gemini AI direct problem solver...")
        ai_code = solve_with_ai(
            title=title,
            difficulty=difficulty,
            content_html=content,
            starter_code=python_snippet,
            language="python3",
        )
        if ai_code:
            code = ai_code
            language = "python3"
            logging.info("Successfully solved problem using Gemini AI fallback.")
        else:
            logging.error("Failed to generate solution via community scraper and AI solver.")
            return None

    return {
        "title": title,
        "slug": slug,
        "question_id": question_id,
        "frontend_id": frontend_id,
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
        print(f"Problem: #{result.get('frontend_id')} {result['title']} ({result['difficulty']})")
        print(f"Date: {result['date']}")
        print(f"Language: {result['language']}")
        print(f"{'='*60}")
        print(result["code"])
    else:
        print("Failed to solve the daily problem.")

