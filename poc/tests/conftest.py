"""
poc/tests/conftest.py – pytest configuration for the PoC test suite.
"""
import sys
from pathlib import Path

# Ensure poc/ is on the path so all sibling packages are importable.
sys.path.insert(0, str(Path(__file__).parent.parent))
