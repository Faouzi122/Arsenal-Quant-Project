#!/usr/bin/env python3
# © 2026 Arsenal Decision Engine — Decision Intelligence Layer
# File: test_smeltor_integration.py — Deprecated. Redirecting to test_execution_integration.py

import os
import sys

print("⚠️  This test file is DEPRECATED as we have pivoted away from Smeltor.")
print("➡️  Redirecting to the new direct aggregator execution integration test...")

script_dir = os.path.dirname(os.path.abspath(__file__))
new_test_path = os.path.join(script_dir, "test_execution_integration.py")

os.execv(sys.executable, [sys.executable, new_test_path])
