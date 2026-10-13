"""
FinSight launcher.

Run from this folder with:  py app.py
Then open http://127.0.0.1:5000 - the Login page opens first, and
the Dashboard is reached only after signing in.
"""

import os
import sys

# The Flask app (API + page serving) lives in Transactions/Transactions
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_APP_DIR = os.path.join(PROJECT_ROOT, "Transactions", "Transactions")

sys.path.insert(0, FLASK_APP_DIR)

from app import app  # noqa: E402  (Transactions/Transactions/app.py)


if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )
