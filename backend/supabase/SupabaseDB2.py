"""
Access object for scheduling requests in Supabase.
Credit: SUPABASE PTE. LTD. 2026
---------------------------------------------
Aadarsh Joshi 2026
"""

import datetime
from supabase import AsyncClient, acreate_client


"""Helper for DB2_Repeated_Messages; stores repeating daily messages."""
class Database2:
	def __init__(self, url: str, key: str):
		self.url = url
		self.key = key
		self.client: AsyncClient = None

	async def connect(self):
		"""Establish async Supabase client using URL and key."""
		self.client = await acreate_client(self.url, self.key)

	async def create_entry(self, guild_id: int, recipients: list[int] | None = None, message: str = "", timestamp: datetime.datetime | None = None, entry_id: int | None = None):
		"""Upsert a repeated-message row with recipients, message, and optional timestamp or id."""

		if recipients is None:
			recipients = []

		ts = None
		if isinstance(timestamp, datetime.datetime):
			if timestamp.tzinfo is None:
				timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
			ts = timestamp.isoformat()

		payload = {
			"guild_id": guild_id,
			"recipient_list": recipients,
			"universal_message": message or "",
			"timestamp": ts,
		}

		if entry_id is not None:
			payload["id"] = entry_id

		await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def set_universal_message(self, guild_id: int, message: str):
		"""Update or insert universal text for a guild, preserving recipients."""
		response = await self.client.table("DB2_Repeated_Messages").select("recipient_list").eq("guild_id", guild_id).execute()
		if response.data:
			recipient_list = response.data[0].get("recipient_list") or []
		else:
			recipient_list = []

		await self.client.table("DB2_Repeated_Messages").upsert({
			"guild_id": guild_id,
			"recipient_list": recipient_list,
			"universal_message": message or ""
		}).execute()

	async def get_universal_message(self, guild_id: int) -> str:
		"""Return stored universal message for a guild, default empty."""
		response = await self.client.table("DB2_Repeated_Messages").select("universal_message").eq("guild_id", guild_id).execute()
		if not response.data:
			return ""
		return response.data[0].get("universal_message") or ""

	async def add_recipient(self, guild_id: int, recipient_id: int):
		"""Append a recipient id to the recipient_list array if missing."""
		response = await self.client.table("DB2_Repeated_Messages").select("recipient_list").eq("guild_id", guild_id).execute()
		if not response.data:
			recipient_list = []
		else:
			recipient_list = response.data[0].get("recipient_list") or []

		if recipient_id not in recipient_list:
			recipient_list.append(recipient_id)
			await self.client.table("DB2_Repeated_Messages").upsert({
				"guild_id": guild_id,
				"recipient_list": recipient_list
			}).execute()

	async def remove_recipient(self, guild_id: int, recipient_id: int):
		"""Remove a recipient id from the recipient_list array if present."""
		response = await self.client.table("DB2_Repeated_Messages").select("recipient_list").eq("guild_id", guild_id).execute()
		if not response.data:
			return

		recipient_list = response.data[0].get("recipient_list") or []
		if recipient_id in recipient_list:
			recipient_list.remove(recipient_id)
			await self.client.table("DB2_Repeated_Messages").upsert({
				"guild_id": guild_id,
				"recipient_list": recipient_list
			}).execute()

	async def get_recipients(self, guild_id: int) -> list:
		"""Retrieve the recipient_list for a guild; returns empty list if none."""
		response = await self.client.table("DB2_Repeated_Messages").select("recipient_list").eq("guild_id", guild_id).execute()
		if not response.data:
			return []
		return response.data[0].get("recipient_list") or []

	async def set_timestamp(self, guild_id: int, scheduled_time: datetime.datetime):
		"""Store a persistent timestamptz for the guild's daily schedule."""
		if isinstance(scheduled_time, datetime.datetime):
			if scheduled_time.tzinfo is None:
				scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone.utc)
			scheduled_time = scheduled_time.isoformat()

		response = await self.client.table("DB2_Repeated_Messages").select("recipient_list,universal_message").eq("guild_id", guild_id).execute()
		if response.data:
			row = response.data[0]
			recipient_list = row.get("recipient_list") or []
			universal_message = row.get("universal_message") or ""
		else:
			recipient_list = []
			universal_message = ""

		await self.client.table("DB2_Repeated_Messages").upsert({
			"guild_id": guild_id,
			"recipient_list": recipient_list,
			"universal_message": universal_message,
			"timestamp": scheduled_time
		}).execute()

	async def get_scheduled_messages(self, now: datetime.datetime | None = None) -> list:
		"""Return rows where stored timestamp hour/minute equals now's hour/minute (UTC default)."""
		response = await self.client.table("DB2_Repeated_Messages").select(
			"id,guild_id,timestamp,universal_message,recipient_list"
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

			# Compare hour and minute in `now` timezone.
			scheduled_in_now_tz = scheduled_time.astimezone(now.tzinfo)
			now_in_same_tz = now.astimezone(now.tzinfo)

			if (
				scheduled_in_now_tz.hour == now_in_same_tz.hour
				and scheduled_in_now_tz.minute == now_in_same_tz.minute
			):
				due.append(row)

		return due

	async def delete_entry(self, guild_id: int):
		"""Removes an entry for a guild entirely."""
		await self.client.table("DB2_Repeated_Messages").delete().eq("guild_id", guild_id).execute()
