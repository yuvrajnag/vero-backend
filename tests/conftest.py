"""
Pytest configuration for the vector layer test suite.
Adds the backend root to sys.path so `app.*` imports resolve correctly
when running `pytest` from the backend/ directory.
"""
import sys
import os

# Ensure the backend root is on the path
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
