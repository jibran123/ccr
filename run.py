#!/usr/bin/env python3
"""Application entry point."""

import os
import sys
from app import create_app

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)