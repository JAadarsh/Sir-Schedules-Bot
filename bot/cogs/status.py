from discord import app_commands
from discord.ext import commands
import discord


class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="database_status", description="Show the latest database health status")
    async def database_status(self, interaction: discord.Interaction):
        status_lines = []
        for label, key in (("One-time messages", "db1"), ("Daily messages", "db2"), ("Group repeated messages", "db3")):
            state = self.bot.state.database_health[key]
            if state["healthy"]:
                status_lines.append(f"{label}: healthy")
            else:
                status_lines.append(f"{label}: unavailable or not verified\nIssue: {state['error']}")
        await interaction.response.send_message("\n".join(status_lines), ephemeral=True)
