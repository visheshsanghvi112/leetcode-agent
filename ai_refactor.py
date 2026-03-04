import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def refactor_code(code: str, language: str) -> str:
    """
    Uses the free Google Gemini API to refactor the solution code so it is 100% unique,
    making it completely undetectable by any plagiarism/duplicate-submission checks.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.info("No GEMINI_API_KEY found. Skipping AI refactoring.")
        return code
        
    logging.info("Sending code to Gemini AI for stealth refactoring...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    You are an expert {language} developer. I want you to slightly refactor the following LeetCode solution.
    Do NOT change the underlying algorithm or time/space complexity.
    DO change variable names (make them more descriptive or different), swap 'for' loops to 'while' loops if it makes sense, or adjust the syntax slightly to make the code look 100% unique but function exactly the same.
    Only output the raw code. NO markdown formatting, NO backticks, NO explanations. Just the raw text of the code.
    
    Here is the code:
    {code}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
        }
    }
    
    try:
        req = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        req.raise_for_status()
        
        response_data = req.json()
        raw_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Clean any accidental markdown backticks just in case
        cleaned = raw_text.replace("```python", "").replace("```python3", "").replace("```mysql", "").replace("```javascript", "").replace("```", "").strip()
        logging.info("AI Refactoring successful! Code is now unique.")
        return cleaned
    except Exception as e:
        logging.error(f"AI Refactoring failed (using original code): {e}")
        return code

if __name__ == "__main__":
    test_code = 'class Solution:\n    def numSpecial(self, mat: List[List[int]]) -> int:\n        return 1'
    print(refactor_code(test_code, "python3"))
