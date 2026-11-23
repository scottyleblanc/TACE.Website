import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))

sys.path.insert(0, os.path.join(_REPO, "app", "train", "lambda"))

# tracker_auth.py reads these at import time; tests never call the real Cognito.
os.environ.setdefault("COGNITO_DOMAIN", "https://auth.example.test")
os.environ.setdefault("CLIENT_ID", "test-client-id")
os.environ.setdefault("REDIRECT_URI", "https://app.example.test/auth/callback")
os.environ.setdefault("POST_LOGIN_REDIRECT", "https://app.example.test/")
os.environ.setdefault("POST_LOGOUT_REDIRECT", "https://app.example.test/")
