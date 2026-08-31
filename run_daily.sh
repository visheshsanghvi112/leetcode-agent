#!/bin/bash
# LeetCode Agent Daily Automatic Runner
export PATH="/Users/vishesh/.pyenv/shims:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd /Users/vishesh/Downloads/leetcode-agent || exit 1

echo "==================================================" >> agent.log
echo "Running LeetCode Daily Solver: $(date)" >> agent.log
echo "==================================================" >> agent.log

# Run solver via Google Chrome session
/Users/vishesh/.pyenv/shims/python3 submit_via_chrome.py >> agent.log 2>&1

# Git sync
git add solutions/ >> agent.log 2>&1
git commit -m "Auto-solve daily challenge: $(date +'%Y-%m-%d')" >> agent.log 2>&1
git push origin main >> agent.log 2>&1

echo "Finished at $(date)" >> agent.log
