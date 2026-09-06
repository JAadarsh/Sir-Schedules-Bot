import asyncio

from discord import app_commands
from discord.ext import commands
import discord

from backend.openrouterpy import OpenRouterRequests


class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say_something", description="Get an AI generated response")
    @app_commands.describe(prompt="Prompt for the AI")
    async def say_something(self, interaction: discord.Interaction, *, prompt: str):
        if len(prompt) > 500:
            return await interaction.response.send_message("Prompt is too long. Please keep it under 500 characters.", ephemeral=True)
        await interaction.response.defer(thinking=True)
        try:
            response = await asyncio.to_thread(OpenRouterRequests.response, prompt, True)
        except Exception as error:
            return await interaction.followup.send(f"Error {error}. Please contact the developer.", ephemeral=True)
        if not response or not response.strip():
            return await interaction.followup.send("AI returned an empty response. Please try again.", ephemeral=True)
        await interaction.followup.send(response)
