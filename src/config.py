import os
from dotenv import load_dotenv

# Find the root directory and load the .env file
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(root_dir, '.env'))

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    DB_URL = os.getenv("DB_URL")

config = Config()
