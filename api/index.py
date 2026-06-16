import sys
import os

# Resolve the absolute path of the backend directory
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
# Add it to Python's system search path so internal imports like 'import db' work
sys.path.append(backend_dir)

from app import app
