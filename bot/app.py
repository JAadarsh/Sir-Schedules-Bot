import logging

import discord
from discord.ext import commands

from backend.supabase.SupabaseDB1 import Database
from backend.supabase.SupabaseDB2 import Database2
from bot.cogs.ai import AICog
from bot.cogs.messages import DailyMessagesCog, OneTimeMessagesCog
from bot.cogs.privacy import PrivacyCog
from bot.cogs.status import StatusCog
from bot.config import Config
from bot.state import AppState
from bot.tasks.scheduler import Scheduler


class GreeterBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.all()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.config = config
        self.state = AppState()
        self.db = None
        self.db2 = None
        self.scheduler = None

    async def setup_hook(self):
        self.db = Database(self.config.supabase_url, self.config.supabase_key)
        self.db2 = Database2(self.config.supabase_url, self.config.supabase_key)
        await self._connect_database(self.db, "db1", "Database connected.")
        await self._connect_database(self.db2, "db2", "Daily schedule database connected.")

        for cog in (StatusCog, OneTimeMessagesCog, DailyMessagesCog, PrivacyCog, AICog):
            await self.add_cog(cog(self))

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global slash commands.")
            registered = [command.name for command in self.tree.walk_commands()]
            print(f"Registered slash command names: {registered}")
        except Exception as error:
            print(f"Command sync error: {error}")

        self.scheduler = Scheduler(self)
        self.scheduler.start()

    async def _connect_database(self, database, health_key: str, success_message: str):
        try:
            await database.connect()
            self.state.database_health[health_key] = {
                "healthy": False,
                "error": "Connection client initialized; awaiting a successful query.",
            }
            print(success_message)
        except Exception as error:
            self.state.database_health[health_key] = {"healthy": False, "error": str(error)}
            print(f"Error connecting to {health_key}: {error}")

    async def on_ready(self):
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="We are open source! Check the github!"),
        )
        print(f"Logged in as {self.user.name} (ID: {self.user.id})")


def create_bot(config: Config) -> GreeterBot:
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.FileHandler("discord.log", encoding="utf-8", mode="w")],
    )
    return GreeterBot(config)
