import os
from dotenv import load_dotenv

# Find the root directory and load the .env file
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(root_dir, '.env'))

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    DB_URL = os.getenv("DB_URL")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", os.path.join(root_dir, "logs"))
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    SLOW_QUERY_WARNING_MS = int(os.getenv("SLOW_QUERY_WARNING_MS", "100"))

config = Config()
