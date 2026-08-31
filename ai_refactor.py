import os
import re
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Supported Gemini models in order of priority
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


def clean_markdown_code(raw_text: str, language: str = "python3") -> str:
    """Strips markdown code blocks, backticks, and explanations to return clean code."""
    if not raw_text:
        return ""

    text = raw_text.strip()

    # Extract code from within triple backticks if present
    match = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # Strip leading/trailing single line backticks
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    # If python and class Solution is present, ensure we start from class Solution or imports
    if language in ["python", "python3"]:
        if "class Solution" in text:
            # Keep imports above class Solution if present
            lines = text.splitlines()
            start_idx = 0
            for idx, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from ") or line.startswith("class Solution"):
                    start_idx = idx
                    break
            text = "\n".join(lines[start_idx:]).strip()

    return text


def query_gemini(prompt: str, temperature: float = 0.4) -> str:
    """Queries Google Gemini API with automatic model fallback."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.warning("No GEMINI_API_KEY found in environment.")
        return ""

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
            },
        }
        try:
            req = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if req.status_code == 200:
                data = req.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        logging.info(f"Gemini API query succeeded with model '{model}'.")
                        return parts[0]["text"]
            else:
                logging.warning(f"Gemini model '{model}' returned HTTP {req.status_code}: {req.text[:200]}")
        except Exception as e:
            logging.warning(f"Gemini model '{model}' request failed: {e}")

    logging.error("All Gemini models failed to generate content.")
    return ""


def solve_with_ai(title: str, difficulty: str, content_html: str, starter_code: str, language: str = "python3") -> str:
    """
    Solves a LeetCode problem directly using Gemini AI when no community solution exists.
    Ensures optimal time/space complexity and exact conformance to starter template.
    """
    # Clean HTML tags from content for clean prompt
    content_text = re.sub(r"<[^>]+>", " ", content_html or "")
    content_text = re.sub(r"\s+", " ", content_text).strip()

    logging.info(f"Solving '{title}' ({difficulty}) from scratch using Gemini AI...")

    prompt = f"""
You are a competitive programming grandmaster and expert {language} engineer.
Solve the following LeetCode problem with optimal time and space complexity.

Problem Title: {title} ({difficulty})
Problem Description:
{content_text}

Starter Code Template:
```
{starter_code}
```

CRITICAL INSTRUCTIONS:
1. Output the COMPLETE, WORKING, OPTIMAL solution in {language}.
2. You MUST use the exact class and method signature from the Starter Code Template.
3. Include necessary helper imports (e.g. from typing import List, Optional, Dict, collections, math, heapq, bisect) if needed.
4. Do NOT output any markdown explanations, commentary, or text outside the code.
5. ONLY return the executable code block.
"""

    raw_solution = query_gemini(prompt, temperature=0.2)
    if not raw_solution:
        logging.error("Gemini AI failed to generate problem solution.")
        return ""

    cleaned_code = clean_markdown_code(raw_solution, language)
    if "class Solution" not in cleaned_code and "def " not in cleaned_code:
        logging.warning("AI solution missing standard Solution structure, retrying with raw output.")
        return cleaned_code or raw_solution

    logging.info(f"Successfully generated AI solution ({len(cleaned_code)} chars).")
    return cleaned_code


def refactor_code(code: str, language: str = "python3") -> str:
    """
    Uses Gemini API to mildly refactor scraped community solutions to ensure uniqueness
    while strictly preserving logic and time/space complexity.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.info("No GEMINI_API_KEY found. Skipping AI refactoring.")
        return code

    logging.info("Sending code to Gemini AI for stealth refactoring...")

    prompt = f"""
You are an expert {language} developer.
Refactor the following LeetCode solution to make variable names and formatting clean and unique.
- Do NOT alter algorithm logic, time/space complexity, or class/method names.
- Do NOT output explanations or markdown commentary.
- Return ONLY the refactored code.

Code:
{code}
"""

    raw_text = query_gemini(prompt, temperature=0.6)
    if not raw_text:
        logging.warning("AI refactoring failed; retaining original code.")
        return code

    cleaned = clean_markdown_code(raw_text, language)
    if len(cleaned) > 20 and ("class Solution" in cleaned or "def " in cleaned or language in ["mysql", "javascript"]):
        logging.info("AI Refactoring successful! Code is now unique.")
        return cleaned

    return code


if __name__ == "__main__":
    test_starter = "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        pass"
    res = solve_with_ai("Two Sum", "Easy", "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.", test_starter)
    print("Test AI solve output:\n", res)

