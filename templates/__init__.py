# templates/__init__.py

import sys
import os

# Dynamically adjust the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Expose BOOKING_EMAIL_TEMPLATE for external imports
from .email_template import BOOKING_EMAIL_TEMPLATE
