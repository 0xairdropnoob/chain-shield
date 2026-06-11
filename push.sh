#!/bin/bash
# Push chain-shield to GitHub
# Token is provided by the user
cd /home/ubuntu/sentinel/chain-shield

# Use token from environment
export GIT_ASKPASS=echo
git remote set-url origin "https://ChainShieldSn:${GITHUB_TOKEN}@github.com/ChainShieldSn/chain-shield.git"
git push -u origin master 2>&1
