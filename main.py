"""
Version 0.2.3
Copyright Aadarsh Joshi 2026 all rights reserved.
"""

import asyncio
import discord
from backend.openrouterpy import OpenRouterRequests as OpenRouterRequests
import os
import logging
import datetime
from dotenv import load_dotenv
from backend.supabase.SupabaseDB1 import Database
from backend.supabase.SupabaseDB2 import Database2
from backend.timezones import COMMON_TIMEZONES, get_local_scheduled_datetime, normalize_timezone_name
from discord import app_commands
from discord.ext import tasks, commands

"""
Notice:
Bot is incomplete, but can be deployed.
"""

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.all()

# command prefix is !, change later because its popular
bot = commands.Bot(command_prefix='!', intents=intents)
daily_messages_sent: set[tuple[int, str, datetime.date]] = set()


# -------------------------------------------------
# ^ This is the setup for bot & creating a server 
# v This is the actual bot stuff
# --------------------------------

# looping tasks


async def direct_message(user_id: int, message: str) -> bool:
    """
    Helper method to send a dm to a user.
    """
    if not message or not message.strip():
        return False
    
    user = bot.get_user(user_id)
    if user is None:
        user = await bot.fetch_user(user_id)
    await user.send(message)
    return True


@tasks.loop(seconds=60)
async def refresh_daily_message_cache():
    """Forget daily messages from previous UTC dates."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    daily_messages_sent.intersection_update(
        cache_key for cache_key in daily_messages_sent if cache_key[2] == today
    )



@tasks.loop(seconds=10)
async def check_scheduled_messages():
    """
    checks scheduled messages every 10s
    """

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        response = await bot.db.get_scheduled_messages(now)
    except Exception as e:
        print(f"Error fetching scheduled messages: {e}")
        return
    
    for entry in response:
        user_id = entry["user_id"]
        guild_id = entry["guild_id"]
        message = entry["universal_message"]
        recipient_list = entry["recipient_list"]

        # Skip if message is empty
        if not message or not message.strip():
            continue

        # Send the message to each recipient
        try:
            for recipient_id in recipient_list or []:
                await direct_message(recipient_id, message)
            await bot.db.mark_scheduled_message_sent(user_id, guild_id)
        except Exception as e:
            print(f"Error sending one-time message for user {user_id}: {e}")


@tasks.loop(seconds=10)
async def check_daily_scheduled_messages():
    """Checks the repeating daily schedule and sends it once per local day per guild."""
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        response = await bot.db2.get_scheduled_messages(now)
    except Exception as e:
        print(f"Error fetching daily scheduled messages: {e}")
        return

    for entry in response:
        user_id = entry["user_id"]
        guild_id = entry["guild_id"]
        message = entry["universal_message"]
        recipient_list = entry.get("recipient_list") or []

        if not message or not message.strip():
            continue

        cache_key = (guild_id, message, now.date())
        if cache_key in daily_messages_sent:
            continue

        daily_messages_sent.add(cache_key)
        for recipient_id in recipient_list:
            try:
                await direct_message(recipient_id, message)
            except discord.Forbidden as e:
                print(f"Could not send daily message to user {recipient_id}: {e}")
                try:
                    await bot.db2.remove_recipient(user_id, guild_id, recipient_id)
                except Exception as remove_error:
                    print(f"Could not remove user {recipient_id} from the daily recipient list: {remove_error}")
            except Exception as e:
                print(f"Error sending daily message to user {recipient_id}: {e}")


def looping_tasks():
    """
    helper method to start all looping tasks
    """
    if not check_scheduled_messages.is_running():
        check_scheduled_messages.start()
    if not check_daily_scheduled_messages.is_running():
        check_daily_scheduled_messages.start()
    if not refresh_daily_message_cache.is_running():
        refresh_daily_message_cache.start()


async def clear_all_data(user_id: int, guild_id: int):
    """Remove all stored bot data for a user in a guild."""
    await bot.db.delete_entry(user_id, guild_id)
    await bot.db2.delete_entry(user_id, guild_id)

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="We are open source! Check the github!"))
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')

    # database connection
    bot.db = Database(supabase_url, supabase_key)
    bot.db2 = Database2(supabase_url, supabase_key)
    try:
        await bot.db.connect()
        print("Database connected.")
    except Exception as e:
        print(f"Error connecting to database: {e}")

    try:
        await bot.db2.connect()
        print("Daily schedule database connected.")
    except Exception as e:
        print(f"Error connecting to daily schedule database: {e}")

    # / cmds
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global slash commands.")

        registered = [command.name for command in bot.tree.walk_commands()]
        print(f"Registered slash command names: {registered}")
    except Exception as e:
        print(f"Command sync error: {e}")

    # looping tasks
    looping_tasks()

# slash commands
@bot.tree.command(name="set_message", description="Set your own custom greeting message!")
@app_commands.describe(text="The custom sentence or phrase you want to save")
async def set_message(interaction: discord.Interaction, *, text: str):
    if len(text) > 1500:
        return await interaction.response.send_message("Message is too long. Please keep it under 1500 characters.", ephemeral=True)

    await bot.db.set_universal_message(interaction.user.id, interaction.guild_id, text)
    await interaction.response.send_message("Universal message updated.")

@bot.tree.command(name="view_message", description="View current message")
async def view_message(interaction: discord.Interaction):
    entry = await bot.db.get_entry(interaction.user.id, interaction.guild_id)
    if not entry:
        return await interaction.response.send_message("No scheduled message is saved. Use /set_message or /set_time to create one.", ephemeral=True)

    await interaction.response.send_message(
        "Scheduled message information:\n"
        f"User ID: {entry.get('user_id')}\n"
        f"Guild ID: {entry.get('guild_id')}\n"
        f"Message: {entry.get('universal_message') or '(none)'}\n"
        f"Recipients: {entry.get('recipient_list') or '(none)'}\n"
        f"Scheduled time: {entry.get('timestamp') or '(not scheduled)'}",
        ephemeral=True,
    )


@bot.tree.command(name="set_daily_message", description="Set the recurring daily greeting for this server")
@app_commands.describe(text="The recurring message to send every day")
async def set_daily_message(interaction: discord.Interaction, *, text: str):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
    if len(text) > 1500:
        return await interaction.response.send_message("Message is too long. Please keep it under 1500 characters.", ephemeral=True)

    await bot.db2.set_universal_message(interaction.user.id, interaction.guild_id, text)
    await interaction.response.send_message("Daily server message updated.")


async def timezone_autocomplete(interaction: discord.Interaction, current: str):
    current_value = current.lower()
    matches = []
    for timezone_name in COMMON_TIMEZONES:
        label = timezone_name.replace("/", " / ").replace("_", " ")
        if current_value in label.lower() or current_value in timezone_name.lower():
            matches.append(app_commands.Choice(name=label, value=timezone_name))
    return matches[:25]


@bot.tree.command(name="set_daily_time", description="Set the time for the recurring daily message")
@app_commands.describe(hour="Hour (0-23)", minute="Minute (0-59)", timezone="Timezone, for example Los Angeles")
@app_commands.autocomplete(timezone=timezone_autocomplete)
async def set_daily_time(interaction: discord.Interaction, hour: int, minute: int, timezone: str | None = None):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
    if not (0 <= hour < 24) or not (0 <= minute < 60):
        return await interaction.response.send_message("Invalid time format. Please use HH:MM in 24-hour format.", ephemeral=True)

    normalized_timezone = normalize_timezone_name(timezone) if timezone else None
    if timezone and normalized_timezone not in COMMON_TIMEZONES:
        return await interaction.response.send_message("Timezone not recognized. Try something like 'Los Angeles' or 'America/Los_Angeles'.", ephemeral=True)

    scheduled_time = get_local_scheduled_datetime(hour, minute, timezone_name=normalized_timezone)
    await bot.db2.set_timestamp(interaction.user.id, interaction.guild_id, scheduled_time)
    await interaction.response.send_message(f"Daily message time set to {hour:02d}:{minute:02d}.")


@bot.tree.command(name="clear_daily_time", description="Clear the recurring daily message time")
async def clear_daily_time(interaction: discord.Interaction):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    await bot.db2.clear_timestamp(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message("Daily message time cleared.")


@bot.tree.command(name="view_daily_message", description="View the recurring daily message for this server")
async def view_daily_message(interaction: discord.Interaction):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    entry = await bot.db2.get_entry(interaction.user.id, interaction.guild_id)
    if not entry:
        return await interaction.response.send_message("No daily message is saved. Use /set_daily_message or /set_daily_time to create one.", ephemeral=True)

    await interaction.response.send_message(
        "Daily message information:\n"
        f"User ID: {entry.get('user_id')}\n"
        f"Guild ID: {entry.get('guild_id')}\n"
        f"Message: {entry.get('universal_message') or '(none)'}\n"
        f"Recipients: {entry.get('recipient_list') or '(none)'}\n"
        f"Scheduled time: {entry.get('timestamp') or '(not scheduled)'}",
        ephemeral=True,
    )


@bot.tree.command(name="add_daily_recipient", description="Add someone to this server's daily mailing list")
@app_commands.describe(recipient="User to receive the daily message")
async def add_daily_recipient(interaction: discord.Interaction, recipient: discord.User):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    await bot.db2.add_recipient(interaction.user.id, interaction.guild_id, recipient.id)
    await interaction.response.send_message(f"{recipient.name} has been added to the server's daily recipient list.")


@bot.tree.command(name="remove_daily_recipient", description="Remove someone from this server's daily mailing list")
@app_commands.describe(recipient="User to remove from the server's daily message list")
async def remove_daily_recipient(interaction: discord.Interaction, recipient: discord.User):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    await bot.db2.remove_recipient(interaction.user.id, interaction.guild_id, recipient.id)
    await interaction.response.send_message(f"{recipient.name} has been removed from the server's daily recipient list.")


@bot.tree.command(name="clear_daily_recipients", description="Clear the server's daily recipient list")
async def clear_daily_recipients(interaction: discord.Interaction):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    await bot.db2.clear_recipients(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message("Server daily recipient list cleared.")


@bot.tree.command(name="add_recipient", description="Add someone to the mailing list")
@app_commands.describe(recipient="User to add to recipient list")
async def add_recipient(interaction: discord.Interaction, recipient: discord.User):
    await bot.db.add_recipient(interaction.user.id, interaction.guild_id, recipient.id)
    await interaction.response.send_message(f"{recipient.name} has been added to your recipient list.")

@bot.tree.command(name="remove_recipient", description="Remove someone from the mailing list")
@app_commands.describe(recipient="User to remove from recipient list")
async def remove_recipient(interaction: discord.Interaction, recipient: discord.User):
    await bot.db.remove_recipient(interaction.user.id, interaction.guild_id, recipient.id)
    await interaction.response.send_message(f"{recipient.name} has been removed from your recipient list.")

@bot.tree.command(name="clear_recipients", description="Clear the recipient list")
async def clear_recipients(interaction: discord.Interaction):
    await bot.db.clear_recipients(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message("Recipient list cleared.")


@bot.tree.command(name="clear_all_data", description="Delete all of your saved data in this server")
async def clear_all_data_command(interaction: discord.Interaction):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    await clear_all_data(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message("All of your saved data for this server has been deleted.", ephemeral=True)

@bot.tree.command(name="say_something", description="Get an AI generated response")
@app_commands.describe(prompt="Prompt for the AI")
async def say_something(interaction: discord.Interaction, *, prompt: str):
    """
    This method is mainly to make sure that the bot works, will likely stay a feature or become a helper function soon. 
    """
    if len(prompt) > 500:
        return await interaction.response.send_message("Prompt is too long. Please keep it under 500 characters.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    try:
        response = await asyncio.to_thread(OpenRouterRequests.response, prompt, True)
    except Exception as e:
        return await interaction.followup.send(f"Error {e}. Please contact the developer.", ephemeral=True)

    if not response or not response.strip():
        return await interaction.followup.send("AI returned an empty response. Please try again.", ephemeral=True)

    await interaction.followup.send(response)

@bot.tree.command(name="set_time", description="Set a time for the bot to send a message")
@app_commands.describe(hour="Hour (0-23)", minute="Minute (0-59)", timezone="Timezone, for example Los Angeles")
@app_commands.autocomplete(timezone=timezone_autocomplete)
async def set_time(interaction: discord.Interaction, hour: int, minute: int, timezone: str | None = None):
    """
    This method is to set a time for the bot to send a message. 
    """
    
    try: 
        if not (0 <= hour < 24) or not (0 <= minute < 60):
            raise ValueError("Invalid time format. Please use HH:MM in 24-hour format.")
    except ValueError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_timezone = normalize_timezone_name(timezone) if timezone else None
    if timezone and normalized_timezone not in COMMON_TIMEZONES:
        return await interaction.response.send_message("Timezone not recognized. Try something like 'Los Angeles' or 'America/Los_Angeles'.", ephemeral=True)

    scheduled_time = get_local_scheduled_datetime(hour, minute, timezone_name=normalized_timezone)
    await bot.db.set_hours(interaction.user.id, interaction.guild_id, scheduled_time)
    timezone_label = normalized_timezone or scheduled_time.tzname() or "local timezone"
    await interaction.response.send_message(f"Time set to {hour:02d}:{minute:02d} in {timezone_label} for your messages.")


@bot.tree.command(name="clear_time", description="Clear the scheduled one-time message time")
async def clear_time(interaction: discord.Interaction):
    if interaction.guild_id is None:
        return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

    await bot.db.clear_timestamp(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message("Scheduled one-time message time cleared.")


bot.run(token)