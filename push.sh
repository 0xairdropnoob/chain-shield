#!/bin/bash
# Push chain-shield to GitHub
# Token is provided by the user
cd /home/ubuntu/sentinel/chain-shield

# Use token from environment
export GIT_ASKPASS=echo
git remote set-url origin "https://0xairdropnoob:${GITHUB_TOKEN}@github.com/0xairdropnoob/chain-shield.git"
git push -u origin master 2>&1
