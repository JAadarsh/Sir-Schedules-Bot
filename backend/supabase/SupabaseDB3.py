"""
Access object for scheduling role-based repeated messages in Supabase.
Credit: SUPABASE PTE. LTD. 2026
---------------------------------------------
Aadarsh Joshi 2026
"""

import datetime
from supabase import AsyncClient, acreate_client


class Database3:
    """Helper for DB3_Group_Repeated_Messages.

    This table stores role-based recipient groups for repeating messages.
    In this version, recipient_list is intended to hold Discord role IDs,
    not user IDs. When the bot runs, it resolves each role to its members and
    sends a direct message to each member individually.
    """

    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client: AsyncClient = None

    async def connect(self):
        """Establish async Supabase client using URL and key."""
        self.client = await acreate_client(self.url, self.key)

    async def create_entry(
        self,
        user_id: int,
        guild_id: int,
        recipients: list[int] | None = None,
        message: str = "",
        timestamp: datetime.datetime | None = None,
        days_repeated: int = 0,
        times_sent: int = 0,
        entry_id: int | None = None,
    ):
        """Upsert a role-based repeated-message row with its schedule and send count."""

        if recipients is None:
            recipients = []
        self._validate_days_repeated(days_repeated)
        self._validate_times_sent(times_sent)

        ts = None
        if isinstance(timestamp, datetime.datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
            ts = timestamp.isoformat()

        payload = {
            "user_id": user_id,
            "guild_id": guild_id,
            "recipient_list": recipients,
            "universal_message": message or "",
            "timestamp": ts,
            "days_repeated": days_repeated,
            "times_sent": times_sent,
        }

        if entry_id is not None:
            payload["id"] = entry_id

        await self.client.table("DB3_Group_Repeated_Messages").upsert(payload).execute()

    @staticmethod
    def _validate_days_repeated(days_repeated: int):
        if not isinstance(days_repeated, int) or not 0 <= days_repeated <= 127:
            raise ValueError("days_repeated must be an integer between 0 and 127")

    @staticmethod
    def _validate_times_sent(times_sent: int):
        if not isinstance(times_sent, int) or not -(2**63) <= times_sent <= 2**63 - 1:
            raise ValueError("times_sent must fit in a PostgreSQL int8")

    async def get_entry(self, user_id: int, guild_id: int) -> dict | None:
        """Return all stored repeated-message data for a user in a guild."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("*").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        return response.data[0] if response.data else None

    async def set_universal_message(self, user_id: int, guild_id: int, message: str):
        """Update or insert universal text for a user+guild, preserving role recipients."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("recipient_list").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if response.data:
            recipient_list = response.data[0].get("recipient_list") or []
        else:
            recipient_list = []

        await self.client.table("DB3_Group_Repeated_Messages").upsert({
            "user_id": user_id,
            "guild_id": guild_id,
            "recipient_list": recipient_list,
            "universal_message": message or ""
        }).execute()

    async def get_universal_message(self, user_id: int, guild_id: int) -> str:
        """Return stored universal message for a user+guild, default empty."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("universal_message").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if not response.data:
            return ""
        return response.data[0].get("universal_message") or ""

    async def add_recipient(self, user_id: int, guild_id: int, recipient_id: int):
        """Append a role ID to the recipient_list array if missing."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if not response.data:
            recipient_list = []
            universal_message = ""
        else:
            recipient_list = response.data[0].get("recipient_list") or []
            universal_message = response.data[0].get("universal_message") or ""

        if recipient_id not in recipient_list:
            recipient_list.append(recipient_id)
            await self.client.table("DB3_Group_Repeated_Messages").upsert({
                "user_id": user_id,
                "guild_id": guild_id,
                "recipient_list": recipient_list,
                "universal_message": universal_message,
            }).execute()

    async def remove_recipient(self, user_id: int, guild_id: int, recipient_id: int):
        """Remove a role ID from the recipient_list array if present."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if not response.data:
            return

        row = response.data[0]
        recipient_list = row.get("recipient_list") or []
        universal_message = row.get("universal_message") or ""
        if recipient_id in recipient_list:
            recipient_list.remove(recipient_id)
            await self.client.table("DB3_Group_Repeated_Messages").upsert({
                "user_id": user_id,
                "guild_id": guild_id,
                "recipient_list": recipient_list,
                "universal_message": universal_message,
            }).execute()

    async def get_recipients(self, user_id: int, guild_id: int) -> list:
        """Retrieve the role recipient_list for a user+guild; returns empty list if none."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("recipient_list").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if not response.data:
            return []
        return response.data[0].get("recipient_list") or []

    async def set_days_repeated(self, user_id: int, guild_id: int, days_repeated: int):
        """Set the Sunday-to-Saturday repeated-day bitmask."""
        self._validate_days_repeated(days_repeated)
        await self.client.table("DB3_Group_Repeated_Messages").upsert({
            "user_id": user_id,
            "guild_id": guild_id,
            "days_repeated": days_repeated,
        }).execute()

    async def get_days_repeated(self, user_id: int, guild_id: int) -> int:
        """Return the repeated-day bitmask, defaulting to no repeated days."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("days_repeated").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if not response.data:
            return 0
        return response.data[0].get("days_repeated") or 0

    async def increment_times_sent(self, user_id: int, guild_id: int) -> int:
        """Increment and return the stored send count for a row."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("times_sent").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        current_count = response.data[0].get("times_sent") if response.data else 0
        current_count = current_count or 0
        self._validate_times_sent(current_count)
        new_count = current_count + 1
        self._validate_times_sent(new_count)
        await self.client.table("DB3_Group_Repeated_Messages").upsert({
            "user_id": user_id,
            "guild_id": guild_id,
            "times_sent": new_count,
        }).execute()
        return new_count

    async def set_times_sent(self, user_id: int, guild_id: int, times_sent: int):
        """Set the stored send count for a row."""
        self._validate_times_sent(times_sent)
        await self.client.table("DB3_Group_Repeated_Messages").upsert({
            "user_id": user_id,
            "guild_id": guild_id,
            "times_sent": times_sent,
        }).execute()

    async def clear_recipients(self, user_id: int, guild_id: int):
        """Clear the role recipient list while preserving the stored message and schedule."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select("universal_message,timestamp").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if response.data:
            row = response.data[0]
            message = row.get("universal_message") or ""
            timestamp = row.get("timestamp")
        else:
            message = ""
            timestamp = None

        await self.client.table("DB3_Group_Repeated_Messages").upsert({
            "user_id": user_id,
            "guild_id": guild_id,
            "recipient_list": [],
            "universal_message": message,
            "timestamp": timestamp,
        }).execute()

    async def set_timestamp(self, user_id: int, guild_id: int, scheduled_time: datetime.datetime):
        """Store a persistent timestamptz for the user's guild schedule."""
        if isinstance(scheduled_time, datetime.datetime):
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone.utc)
            scheduled_time = scheduled_time.isoformat()

        response = await self.client.table("DB3_Group_Repeated_Messages").select("recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id).execute()
        if response.data:
            row = response.data[0]
            recipient_list = row.get("recipient_list") or []
            universal_message = row.get("universal_message") or ""
        else:
            recipient_list = []
            universal_message = ""

        await self.client.table("DB3_Group_Repeated_Messages").upsert({
            "user_id": user_id,
            "guild_id": guild_id,
            "recipient_list": recipient_list,
            "universal_message": universal_message,
            "timestamp": scheduled_time
        }).execute()

    async def get_scheduled_messages(self, now: datetime.datetime | None = None) -> list:
        """Return rows where stored timestamp hour/minute equals now's hour/minute (UTC default)."""
        response = await self.client.table("DB3_Group_Repeated_Messages").select(
            "user_id,guild_id,timestamp,universal_message,recipient_list,days_repeated,times_sent"
        ).execute()

        if not response.data:
            return []

        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        if not isinstance(now, datetime.datetime):
            raise TypeError("now must be a datetime")

        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)

        due = []
        for row in response.data:
            scheduled_time = row.get("timestamp")
            if not scheduled_time:
                continue

            if isinstance(scheduled_time, str):
                try:
                    scheduled_time = datetime.datetime.fromisoformat(scheduled_time)
                except ValueError:
                    continue

            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone.utc)

            scheduled_in_now_tz = scheduled_time.astimezone(now.tzinfo)
            now_in_same_tz = now.astimezone(now.tzinfo)

            if (
                scheduled_in_now_tz.hour == now_in_same_tz.hour
                and scheduled_in_now_tz.minute == now_in_same_tz.minute
                and (row.get("days_repeated") or 0) & (1 << ((now_in_same_tz.weekday() + 1) % 7))
            ):
                due.append(row)

        return due

    async def delete_entry(self, user_id: int, guild_id: int):
        """Removes an entry for a user+guild entirely."""
        await self.client.table("DB3_Group_Repeated_Messages").delete().eq("user_id", user_id).eq("guild_id", guild_id).execute()

    async def delete_user_data(self, user_id: int):
        """Remove a user's group-message rows across all guilds."""
        await self.client.table("DB3_Group_Repeated_Messages").delete().eq("user_id", user_id).execute()
