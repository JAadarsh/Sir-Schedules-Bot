import hmac
import secrets
import string
import time

from discord import app_commands
from discord.ext import commands
import discord

from bot.services.data import DataService


class PrivacyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = DataService(bot)

    @app_commands.command(name="clear_all_data", description="Delete all of your saved data in this server")
    async def clear_all_data(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.data.clear_guild_data(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message("All of your saved data for this server has been deleted.", ephemeral=True)

    @app_commands.command(name="begin_full_deletion", description="Generate a code to delete all of your saved bot data")
    async def begin_full_deletion(self, interaction: discord.Interaction):
        code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        async with self.bot.state.full_deletion_lock:
            self.bot.state.pending_full_deletions[interaction.user.id] = (code, time.monotonic() + 120)
        await interaction.response.send_message(
            f"This code expires in 2 minutes: `{code}`\n"
            "Run `/confirm_full_deletion` with this code to permanently delete all of your saved bot data across every guild.",
            ephemeral=True,
        )

    @app_commands.command(name="confirm_full_deletion", description="Confirm deletion of all your saved bot data")
    @app_commands.describe(code="The 8-character code from /begin_full_deletion")
    async def confirm_full_deletion(self, interaction: discord.Interaction, code: str):
        user_id = interaction.user.id
        normalized_code = code.strip().upper()
        async with self.bot.state.full_deletion_lock:
            pending = self.bot.state.pending_full_deletions.get(user_id)
            if pending is None or time.monotonic() >= pending[1]:
                self.bot.state.pending_full_deletions.pop(user_id, None)
                return await interaction.response.send_message("No active deletion request exists. Run `/begin_full_deletion` to generate a new code.", ephemeral=True)
            if not hmac.compare_digest(normalized_code, pending[0]):
                return await interaction.response.send_message("That code is incorrect. Your current code is still active.", ephemeral=True)
            self.bot.state.pending_full_deletions.pop(user_id, None)
        try:
            await self.data.delete_user_data(user_id)
        except Exception:
            await interaction.response.send_message("Deletion could not be completed. Please start again with `/begin_full_deletion`.", ephemeral=True)
            raise
        await interaction.response.send_message("All of your saved bot data across every guild has been deleted.", ephemeral=True)
