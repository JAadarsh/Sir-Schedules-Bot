"""Start the Discord bot."""

from bot.app import create_bot
from bot.config import load_config


def main():
    config = load_config()
    bot = create_bot(config)
    bot.run(config.discord_token)

if __name__ == "__main__":
    main()
