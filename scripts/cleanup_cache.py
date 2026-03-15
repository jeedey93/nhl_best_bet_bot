#!/usr/bin/env python3
"""
Cache cleanup utility for removing old odds cache files.

This script should be run periodically (e.g., daily) to prevent
accumulation of old cache files in data/cache/.

Can be called from GitHub Actions or manually.
"""

import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.odds_cache import clear_old_caches

if __name__ == "__main__":
    print("🧹 Cleaning up old cache files...")
    clear_old_caches(days_to_keep=2)
    print("✓ Cache cleanup complete")
