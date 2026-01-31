"""
Configuration settings for EDISON PRO.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Data directories
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "out")

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Azure configuration (loaded from environment variables)
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "transformer-index")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")

# API settings
API_HOST = "0.0.0.0"
API_PORT = 7861
FRONTEND_URL = "http://localhost:5173"

# File upload settings
MAX_FILE_SIZE_MB = 100
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".json"}

print(f"[CONFIG] Upload folder: {UPLOAD_FOLDER}")
print(f"[CONFIG] Output folder: {OUTPUT_FOLDER}")
