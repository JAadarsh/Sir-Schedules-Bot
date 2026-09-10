import datetime

from discord.ext import tasks

from bot.services.delivery import DeliveryService


class Scheduler:
    def __init__(self, bot):
        self.bot = bot
        self.delivery = DeliveryService(bot)

    @tasks.loop(seconds=60)
    async def refresh_daily_message_cache(self):
        today = datetime.datetime.now(datetime.timezone.utc).date()
        self.bot.state.daily_messages_sent.intersection_update(
            cache_key
            for cache_key in self.bot.state.daily_messages_sent
            if cache_key[2] == today
        )
        current_minute = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
        self.bot.state.group_messages_sent.intersection_update(
            cache_key
            for cache_key in self.bot.state.group_messages_sent
            if cache_key[2] == current_minute
        )

    @tasks.loop(seconds=10)
    async def check_scheduled_messages(self):
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            response = await self.bot.db.get_scheduled_messages(now)
        except Exception as error:
            self.bot.state.database_health["db1"] = {"healthy": False, "error": str(error)}
            print(f"Error fetching scheduled messages: {error}")
            return

        self.bot.state.database_health["db1"] = {"healthy": True, "error": None}
        for entry in response:
            message = entry["universal_message"]
            if not message or not message.strip():
                continue

            try:
                for recipient_id in entry.get("recipient_list") or []:
                    await self.delivery.direct_message(recipient_id, message)
                await self.bot.db.mark_scheduled_message_sent(entry["user_id"], entry["guild_id"])
            except Exception as error:
                print(f"Error sending one-time message for user {entry['user_id']}: {error}")

    @tasks.loop(seconds=10)
    async def check_daily_scheduled_messages(self):
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            response = await self.bot.db2.get_scheduled_messages(now)
        except Exception as error:
            self.bot.state.database_health["db2"] = {"healthy": False, "error": str(error)}
            print(f"Error fetching daily scheduled messages: {error}")
            return

        self.bot.state.database_health["db2"] = {"healthy": True, "error": None}
        for entry in response:
            message = entry["universal_message"]
            if not message or not message.strip():
                continue

            cache_key = (entry["guild_id"], message, now.date())
            if cache_key in self.bot.state.daily_messages_sent:
                continue

            self.bot.state.daily_messages_sent.add(cache_key)
            for recipient_id in entry.get("recipient_list") or []:
                await self.delivery.send_daily_message(
                    recipient_id,
                    message,
                    entry["user_id"],
                    entry["guild_id"],
                )

    @tasks.loop(seconds=10)
    async def check_group_scheduled_messages(self):
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            response = await self.bot.db3.get_scheduled_messages(now)
        except Exception as error:
            self.bot.state.database_health["db3"] = {"healthy": False, "error": str(error)}
            print(f"Error fetching group scheduled messages: {error}")
            return

        self.bot.state.database_health["db3"] = {"healthy": True, "error": None}
        current_minute = now.replace(second=0, microsecond=0)
        for entry in response:
            message = entry["universal_message"]
            cache_key = (entry["guild_id"], message, current_minute)
            if not message or not message.strip() or cache_key in self.bot.state.group_messages_sent:
                continue

            guild = self.bot.get_guild(entry["guild_id"])
            if guild is None:
                continue

            self.bot.state.group_messages_sent.add(cache_key)
            for role_id in entry.get("recipient_list") or []:
                role = guild.get_role(role_id)
                if role is None:
                    continue
                for member in role.members:
                    try:
                        await self.delivery.direct_message(member.id, message)
                    except Exception as error:
                        print(f"Error sending group message to user {member.id}: {error}")
            send_count = await self.bot.db3.increment_times_sent(entry["user_id"], entry["guild_id"])
            if send_count > 7:
                await self.bot.db3.delete_entry(entry["user_id"], entry["guild_id"])

    def start(self):
        for loop in (
            self.check_scheduled_messages,
            self.check_daily_scheduled_messages,
            self.check_group_scheduled_messages,
            self.refresh_daily_message_cache,
        ):
            if not loop.is_running():
                loop.start()

    def stop(self):
        for loop in (
            self.check_scheduled_messages,
            self.check_daily_scheduled_messages,
            self.check_group_scheduled_messages,
            self.refresh_daily_message_cache,
        ):
            loop.cancel()
