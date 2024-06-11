import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_PATH = Path(__file__).resolve().parent.parent

load_dotenv()
DONE_MESSAGE = "[done]"
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', None)

API_SPEC_PATH = ROOT_PATH / 'data' / 'openapi_items.json'
