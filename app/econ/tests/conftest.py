import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))

sys.path.insert(0, os.path.join(_REPO, "app", "econ", "lambda"))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

# indicators.py reads these at import time; tests never call the real services.
os.environ.setdefault("TD_API_KEY", "test")
os.environ.setdefault("FRED_API_KEY", "test")
os.environ.setdefault("S3_BUCKET", "test-bucket")
