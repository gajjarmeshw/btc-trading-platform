import sys
import os

print("--- DIAGNOSTIC START ---")
print(f"Python Version: {sys.version}")
print(f"Current Directory: {os.getcwd()}")

# 1. Check Flask
try:
    import flask
    print(f"Flask installed: Yes ({flask.__version__})")
except ImportError:
    print("FATAL: Flask is NOT installed. Run: pip3 install flask")

# 2. Check Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"Adding Project Root to Path: {BASE_DIR}")
sys.path.append(BASE_DIR)

# 3. Check App Imports
try:
    import app
    print("Import 'app' package: Success")
except ImportError as e:
    print(f"Import 'app' package: FAILED ({e})")

try:
    from app.config.dynamic_config import load_config
    print("Import 'app.config.dynamic_config': Success")
except ImportError as e:
    print(f"Import 'app.config.dynamic_config': FAILED ({e})")

# 4. Read Log File
log_path = os.path.join(BASE_DIR, 'dashboard.log')
print(f"\n--- DASHBOARD LOG ({log_path}) ---")
if os.path.exists(log_path):
    with open(log_path, 'r') as f:
        print(f.read())
else:
    print("(Log file not found)")

print("--- DIAGNOSTIC END ---")
