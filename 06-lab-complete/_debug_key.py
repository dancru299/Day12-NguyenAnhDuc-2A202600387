import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("AGENT_API_KEY", "")
print(f"AGENT_API_KEY from dotenv: [{key}]")
from app.config import settings
print(f"settings.agent_api_key: [{settings.agent_api_key}]")
