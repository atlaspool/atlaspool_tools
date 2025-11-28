#!/usr/bin/env python3
"""
Test to verify Linux-specific install message
"""

import platform
import os

# Mock platform.system to return 'Linux'
original_system = platform.system
platform.system = lambda: 'Linux'

# Create fake /etc/debian_version to simulate Ubuntu/Debian
os.path.exists_original = os.path.exists
def mock_exists(path):
    if path == '/etc/debian_version':
        return True
    return os.path.exists_original(path)
os.path.exists = mock_exists

# Now test the function
import sys
sys.path.insert(0, os.path.dirname(__file__))
import stratum_test

message = stratum_test.get_ping_install_message()
print(f"Linux (Debian/Ubuntu) message: {message}")

# Test RHEL
def mock_exists_rhel(path):
    if path == '/etc/redhat-release':
        return True
    return False
os.path.exists = mock_exists_rhel

message = stratum_test.get_ping_install_message()
print(f"Linux (RHEL/CentOS) message: {message}")

# Test Alpine
def mock_exists_alpine(path):
    if path == '/etc/alpine-release':
        return True
    return False
os.path.exists = mock_exists_alpine

message = stratum_test.get_ping_install_message()
print(f"Linux (Alpine) message: {message}")

# Test unknown Linux
os.path.exists = lambda path: False

message = stratum_test.get_ping_install_message()
print(f"Linux (Unknown) message: {message}")
