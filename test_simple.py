#!/usr/bin/env python3
"""Simple test without threading to isolate the crash"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the functions
from stratum_test import ping_host, test_stratum_connection

print("Testing ping_host function...")
try:
    result = ping_host("solo.atlaspool.io", timeout=2)
    print(f"Ping result: {result}")
    if result is None:
        print("❌ Ping returned None (BLOCKED)")
    else:
        print(f"✅ Ping successful: {result} ms")
except Exception as e:
    print(f"❌ Exception in ping_host: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting test_stratum_connection function...")
try:
    result = test_stratum_connection("solo.atlaspool.io", 3333, timeout=5)
    print(f"Stratum result: {result}")
    if result is None:
        print("❌ Stratum returned None")
    else:
        print(f"✅ Stratum successful: {result} ms")
except Exception as e:
    print(f"❌ Exception in test_stratum_connection: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\nDone - no crash!")
