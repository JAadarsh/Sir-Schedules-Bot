"""
v0.3.1
Copyright Aadarsh Joshi 2026
All rights reserved.
"""

from bot.app import create_bot
from bot.config import load_config


def main():
    config = load_config()
    bot = create_bot(config)
    bot.run(config.discord_token)

if __name__ == "__main__":
    main()
