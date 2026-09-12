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


DAY_OPTIONS = (
    ("Sunday", "0", 1),
    ("Monday", "1", 2),
    ("Tuesday", "2", 4),
    ("Wednesday", "3", 8),
    ("Thursday", "4", 16),
    ("Friday", "5", 32),
    ("Saturday", "6", 64),
)


class GroupDaysView(discord.ui.View):
    def __init__(self, owner_id: int, db3, user_id: int, guild_id: int, text: str, scheduled_time):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.db3 = db3
        self.user_id = user_id
        self.guild_id = guild_id
        self.text = text
        self.scheduled_time = scheduled_time

        self.day_select = discord.ui.Select(
            placeholder="Select one or more days",
            min_values=1,
            max_values=len(DAY_OPTIONS),
            options=[discord.SelectOption(label=label, value=value) for label, value, _ in DAY_OPTIONS],
        )
        self.day_select.callback = self.select_days
        self.add_item(self.day_select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the person who started this command can use this menu.", ephemeral=True)
            return False
        return True

    async def select_days(self, interaction: discord.Interaction):
        await interaction.response.defer()

    @discord.ui.button(label="Save schedule", style=discord.ButtonStyle.primary)
    async def save_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_values = set(self.day_select.values)
        days_repeated = sum(bit for _, value, bit in DAY_OPTIONS if value in selected_values)
        await self.db3.set_universal_message(self.user_id, self.guild_id, self.text)
        await self.db3.set_timestamp(self.user_id, self.guild_id, self.scheduled_time)
        await self.db3.set_days_repeated(self.user_id, self.guild_id, days_repeated)

        selected_days = [label for label, value, _ in DAY_OPTIONS if value in selected_values]
        self.stop()
        await interaction.response.edit_message(
            content=f"Your group repeated message was scheduled for {', '.join(selected_days)}.",
            view=None,
        )


class OneTimeMessagesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="schedule_message", description="Create or update a scheduled message")
    @app_commands.describe(
        message_type="Send once or repeat daily",
        text="The message to send",
        hour="Hour (0-23)",
        minute="Minute (0-59)",
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
        normalized_timezone = normalize_timezone_name(timezone) if timezone else None
        if timezone and normalized_timezone not in COMMON_TIMEZONES:
            return await interaction.response.send_message("Timezone not recognized. Try something like 'Los Angeles' or 'America/Los_Angeles'.", ephemeral=True)

        scheduled_time = get_local_scheduled_datetime(hour, minute, timezone_name=normalized_timezone)
        user_id = interaction.user.id
        guild_id = interaction.guild_id

        if message_type.value == "daily":
            message_index = await self.bot.db2.create_entry(
                user_id,
                guild_id,
                message=text,
                timestamp=scheduled_time,
            )
            schedule_label = "daily"
        elif message_type.value == "group_repeated":
            await interaction.response.send_message(
                "Select the days for this group repeated message, then press Save schedule.",
                view=GroupDaysView(interaction.user.id, self.bot.db3, user_id, guild_id, text, scheduled_time),
                ephemeral=True,
            )
            return
        else:
            await self.bot.db.set_universal_message(user_id, guild_id, text)
            await self.bot.db.set_hours(user_id, guild_id, scheduled_time)
            schedule_label = "one-time"

        timezone_label = normalized_timezone or scheduled_time.tzname() or "local timezone"
        await interaction.response.send_message(
            f"Your {schedule_label} message was scheduled for {hour:02d}:{minute:02d} in {timezone_label}."
            + (f" Message index: {message_index}." if message_type.value == "daily" and message_index is not None else "")
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
        entries = await self.bot.db2.get_entries(interaction.user.id, interaction.guild_id)
        if not entries:
            return await interaction.response.send_message("No daily message is saved. Use /schedule_message with Daily selected to create one.", ephemeral=True)
        await interaction.response.send_message(
            "Daily messages:\n" + "\n\n".join(
                f"Index: {entry.get('index')}\n"
                f"Message: {entry.get('universal_message') or '(none)'}\n"
                f"Recipients: {entry.get('recipient_list') or '(none)'}\n"
                f"Scheduled time: {entry.get('timestamp') or '(not scheduled)'}"
                for entry in entries
            ),
            ephemeral=True,
        )

    @app_commands.command(name="add_daily_recipient", description="Add someone to this server's daily mailing list")
    @app_commands.describe(recipient="User to receive the daily message", message_index="Index of the daily message")
    async def add_daily_recipient(self, interaction: discord.Interaction, recipient: discord.User, message_index: int):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db2.add_recipient(interaction.user.id, interaction.guild_id, recipient.id, message_index)
        await interaction.response.send_message(f"{recipient.name} has been added to the server's daily recipient list.")

    @app_commands.command(name="remove_daily_recipient", description="Remove someone from this server's daily mailing list")
    @app_commands.describe(recipient="User to remove from the server's daily message list", message_index="Index of the daily message")
    async def remove_daily_recipient(self, interaction: discord.Interaction, recipient: discord.User, message_index: int):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db2.remove_recipient(interaction.user.id, interaction.guild_id, recipient.id, message_index)
        await interaction.response.send_message(f"{recipient.name} has been removed from the server's daily recipient list.")

    @app_commands.command(name="clear_daily_recipients", description="Clear a daily message recipient list")
    @app_commands.describe(message_index="Index of the daily message")
    async def clear_daily_recipients(self, interaction: discord.Interaction, message_index: int):
        if interaction.guild_id is None:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        await self.bot.db2.clear_recipients(interaction.user.id, interaction.guild_id, message_index)
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
