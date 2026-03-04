import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"

def get_daily_problem():
    """Fetches the current daily active problem from LeetCode."""
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          questionId
          title
          titleSlug
          difficulty
        }
      }
    }
    """
    
    response = requests.post(LEETCODE_GRAPHQL_URL, json={"query": query})
    if response.status_code == 200:
        data = response.json()
        daily = data.get("data", {}).get("activeDailyCodingChallengeQuestion", {})
        if daily and daily.get("question"):
            return daily
        else:
            logging.error("Failed to parse daily problem from response.")
            return None
    else:
        logging.error(f"Failed to fetch daily problem. Status code: {response.status_code}")
        return None

if __name__ == "__main__":
    daily = get_daily_problem()
    if daily:
        print(f"Daily Problem: {daily['question']['title']} ({daily['question']['titleSlug']})")
