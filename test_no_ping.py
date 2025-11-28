#!/usr/bin/env python3
"""
Test script to simulate missing ping command
This helps verify the error handling works correctly
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Mock subprocess to simulate missing ping
import subprocess
original_run = subprocess.run

def mock_run(command, *args, **kwargs):
    """Mock subprocess.run to simulate missing ping"""
    if command[0] == 'ping':
        raise FileNotFoundError(f"[Errno 2] No such file or directory: 'ping'")
    return original_run(command, *args, **kwargs)

# Replace subprocess.run with our mock
subprocess.run = mock_run

# Now import and run the stratum test
import stratum_test

# Test single server
print("Testing with simulated missing ping command...")
print("=" * 80)
stratum_test.test_single_server('solo.atlaspool.io', 3333, runs=1)
