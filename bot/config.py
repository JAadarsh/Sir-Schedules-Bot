from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    discord_token: str
    supabase_url: str
    supabase_key: str


def load_config() -> Config:
    load_dotenv()

    values = {
        "discord_token": os.getenv("DISCORD_TOKEN"),
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_SERVICE_KEY"),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(**values)
