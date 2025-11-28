#!/usr/bin/env python3
"""Debug script to test ping behavior on macOS"""

import subprocess
import platform
import sys

hostname = "solo.atlaspool.io"
timeout = 2

print(f"Python version: {sys.version}")
print(f"Platform: {platform.system()} {platform.release()}")
print()

# Test 1: Basic ping
print("=" * 60)
print("Test 1: Basic ping (no timeout flag)")
print("=" * 60)
command = ['ping', '-c', '1', '-t', '255', hostname]
print(f"Command: {' '.join(command)}")
print()

try:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout + 1,
        text=True
    )
    
    print(f"Return code: {result.returncode}")
    print(f"\nSTDOUT:\n{result.stdout}")
    print(f"\nSTDERR:\n{result.stderr}")
    
    # Try to parse
    if 'time=' in result.stdout:
        time_part = result.stdout.split('time=')[1]
        time_str = time_part.split('ms')[0].strip().split()[0]
        print(f"\n✅ Parsed time: {time_str} ms")
    else:
        print("\n❌ Could not find 'time=' in output")
        
except subprocess.TimeoutExpired:
    print("❌ Subprocess timed out")
except Exception as e:
    print(f"❌ Exception: {type(e).__name__}: {e}")

# Test 2: With -W flag (problematic)
print("\n" + "=" * 60)
print("Test 2: Ping with -W flag (known to be problematic)")
print("=" * 60)
command = ['ping', '-c', '1', '-W', str(timeout), hostname]
print(f"Command: {' '.join(command)}")
print()

try:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout + 1,
        text=True
    )
    
    print(f"Return code: {result.returncode}")
    print(f"\nSTDOUT:\n{result.stdout}")
    print(f"\nSTDERR:\n{result.stderr}")
    
    # Try to parse
    if 'time=' in result.stdout:
        time_part = result.stdout.split('time=')[1]
        time_str = time_part.split('ms')[0].strip().split()[0]
        print(f"\n✅ Parsed time: {time_str} ms")
    else:
        print("\n❌ Could not find 'time=' in output")
        
except subprocess.TimeoutExpired:
    print("❌ Subprocess timed out")
except Exception as e:
    print(f"❌ Exception: {type(e).__name__}: {e}")

# Test 3: Direct command line test
print("\n" + "=" * 60)
print("Test 3: What does command line ping show?")
print("=" * 60)
print("Please run this manually and compare:")
print(f"  ping -c 1 -t 255 {hostname}")
print()
