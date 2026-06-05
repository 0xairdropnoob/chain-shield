"""
Chain Sentinel — Vercel Serverless Function Entry Point
"""

import sys
import os

# Add the parent directory to the path so we can import app and scanner
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects the app to be named 'app'
# The app is already defined in app.py
