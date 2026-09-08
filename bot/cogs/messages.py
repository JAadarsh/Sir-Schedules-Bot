from discord import app_commands
from discord.ext import commands
import discord

from backend.timezones import COMMON_TIMEZONES, get_local_scheduled_datetime, normalize_timezone_name


async def timezone_autocomplete(interaction: discord.Interaction, current: str):
    current_value = current.lower()
    matches = []
    for timezone_name in COMMON_TIMEZONES:
        label = timezone_name.replace("/", " / ").replace("_", " ")
        if current_value in label.lower() or current_value in timezone_name.lower():
            matches.append(app_commands.Choice(name=label, value=timezone_name))
    return matches[:25]


class OneTimeMessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="schedule_message", description="Create or update a scheduled message")
    @app_commands.describe(
        message_type="Send once or repeat daily",
        text="The message to send",
        hour="Hour (0-23)",
        minute="Minute (0-59)",
        days_repeated="DB3 bitmask: Sunday=1, Monday=2, through Saturday=64",
        timezone="Timezone, for example Los Angeles",
    )
    @app_commands.choices(message_type=[
        app_commands.Choice(name="One time", value="one_time"),
        app_commands.Choice(name="Daily", value="daily"),
        app_commands.Choice(name="Group repeated", value="group_repeated"),
    ])
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def schedule_message(
        self,
        interaction: discord.Interaction,
        message_type: app_commands.Choice[str],
        text: str,
        hour: int,
        minute: int,
        days_repeated: int = 127,
        timezone: str | None = None,
    ):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        if len(text) > 1500:
            return await interaction.response.send_message("Message is too long. Please keep it under 1500 characters.", ephemeral=True)
        if not text.strip():
            return await interaction.response.send_message("Message cannot be empty.", ephemeral=True)
        if not (0 <= hour < 24) or not (0 <= minute < 60):
            return await interaction.response.send_message("Invalid time format. Please use HH:MM in 24-hour format.", ephemeral=True)
        if not 0 <= days_repeated <= 127:
            return await interaction.response.send_message("Invalid repeated-day mask. Use a value from 0 to 127.", ephemeral=True)

        normalized_timezone = normalize_timezone_name(timezone) if timezone else None
        if timezone and normalized_timezone not in COMMON_TIMEZONES:
            return await interaction.response.send_message("Timezone not recognized. Try something like 'Los Angeles' or 'America/Los_Angeles'.", ephemeral=True)

        scheduled_time = get_local_scheduled_datetime(hour, minute, timezone_name=normalized_timezone)
        user_id = interaction.user.id
        guild_id = interaction.guild_id

        if message_type.value == "daily":
            await self.bot.db2.set_universal_message(user_id, guild_id, text)
            await self.bot.db2.set_timestamp(user_id, guild_id, scheduled_time)
            schedule_label = "daily"
        elif message_type.value == "group_repeated":
            await self.bot.db3.set_universal_message(user_id, guild_id, text)
            await self.bot.db3.set_timestamp(user_id, guild_id, scheduled_time)
            await self.bot.db3.set_days_repeated(user_id, guild_id, days_repeated)
            schedule_label = "group repeated"
        else:
            await self.bot.db.set_universal_message(user_id, guild_id, text)
            await self.bot.db.set_hours(user_id, guild_id, scheduled_time)
            schedule_label = "one-time"

        timezone_label = normalized_timezone or scheduled_time.tzname() or "local timezone"
        await interaction.response.send_message(
            f"Your {schedule_label} message was scheduled for {hour:02d}:{minute:02d} in {timezone_label}."
        )

    @app_commands.command(name="view_message", description="View current message")
    async def view_message(self, interaction: discord.Interaction):
        entry = await self.bot.db.get_entry(interaction.user.id, interaction.guild_id)
        if not entry:
            return await interaction.response.send_message("No scheduled message is saved. Use /schedule_message to create one.", ephemeral=True)
        await interaction.response.send_message(
            "Scheduled message information:\n"
            f"User ID: {entry.get('user_id')}\n"
            f"Guild ID: {entry.get('guild_id')}\n"
            f"Message: {entry.get('universal_message') or '(none)'}\n"
            f"Recipients: {entry.get('recipient_list') or '(none)'}\n"
            f"Scheduled time: {entry.get('timestamp') or '(not scheduled)' }",
            ephemeral=True,
        )

    @app_commands.command(name="add_recipient", description="Add someone to the mailing list")
    @app_commands.describe(recipient="User to add to recipient list")
    async def add_recipient(self, interaction: discord.Interaction, recipient: discord.User):
        await self.bot.db.add_recipient(interaction.user.id, interaction.guild_id, recipient.id)
        await interaction.response.send_message(f"{recipient.name} has been added to your recipient list.")

    @app_commands.command(name="remove_recipient", description="Remove someone from the mailing list")
    @app_commands.describe(recipient="User to remove from recipient list")
    async def remove_recipient(self, interaction: discord.Interaction, recipient: discord.User):
        await self.bot.db.remove_recipient(interaction.user.id, interaction.guild_id, recipient.id)
        await interaction.response.send_message(f"{recipient.name} has been removed from your recipient list.")

    @app_commands.command(name="clear_recipients", description="Clear the recipient list")
    async def clear_recipients(self, interaction: discord.Interaction):
        await self.bot.db.clear_recipients(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message("Recipient list cleared.")

class DailyMessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="view_daily_message", description="View the recurring daily message for this server")
    async def view_daily_message(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        entry = await self.bot.db2.get_entry(interaction.user.id, interaction.guild_id)
        if not entry:
            return await interaction.response.send_message("No daily message is saved. Use /schedule_message with Daily selected to create one.", ephemeral=True)
        await interaction.response.send_message(
            "Daily message information:\n"
            f"User ID: {entry.get('user_id')}\n"
            f"Guild ID: {entry.get('guild_id')}\n"
            f"Message: {entry.get('universal_message') or '(none)'}\n"
            f"Recipients: {entry.get('recipient_list') or '(none)'}\n"
            f"Scheduled time: {entry.get('timestamp') or '(not scheduled)' }",
            ephemeral=True,
        )

    @app_commands.command(name="add_daily_recipient", description="Add someone to this server's daily mailing list")
    @app_commands.describe(recipient="User to receive the daily message")
    async def add_daily_recipient(self, interaction: discord.Interaction, recipient: discord.User):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db2.add_recipient(interaction.user.id, interaction.guild_id, recipient.id)
        await interaction.response.send_message(f"{recipient.name} has been added to the server's daily recipient list.")

    @app_commands.command(name="remove_daily_recipient", description="Remove someone from this server's daily mailing list")
    @app_commands.describe(recipient="User to remove from the server's daily message list")
    async def remove_daily_recipient(self, interaction: discord.Interaction, recipient: discord.User):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db2.remove_recipient(interaction.user.id, interaction.guild_id, recipient.id)
        await interaction.response.send_message(f"{recipient.name} has been removed from the server's daily recipient list.")

    @app_commands.command(name="clear_daily_recipients", description="Clear the server's daily recipient list")
    async def clear_daily_recipients(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db2.clear_recipients(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message("Server daily recipient list cleared.")


class GroupMessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_group_recipient", description="Add a role to a group message recipient list")
    @app_commands.describe(recipient="Role whose members should receive the group message")
    async def add_group_recipient(self, interaction: discord.Interaction, recipient: discord.Role):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db3.add_recipient(interaction.user.id, interaction.guild_id, recipient.id)
        await interaction.response.send_message(f"The {recipient.name} role has been added to the group recipient list.")

    @app_commands.command(name="remove_group_recipient", description="Remove a role from a group message recipient list")
    @app_commands.describe(recipient="Role to remove from the group message recipient list")
    async def remove_group_recipient(self, interaction: discord.Interaction, recipient: discord.Role):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db3.remove_recipient(interaction.user.id, interaction.guild_id, recipient.id)
        await interaction.response.send_message(f"The {recipient.name} role has been removed from the group recipient list.")

    @app_commands.command(name="clear_group_recipients", description="Clear the group message recipient list")
    async def clear_group_recipients(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db3.clear_recipients(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message("Group recipient list cleared.")
