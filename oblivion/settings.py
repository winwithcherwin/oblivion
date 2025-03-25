import os

from dotenv import load_dotenv

load_dotenv()

# CLI SETTINGS
ENABLE_CLI_COLOR = os.getenv("OBLIVION_CLI_COLOR", "false").lower() in ("1", "true", "yes")
REDIS_URI = os.getenv("REDIS_URI")

