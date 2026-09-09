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

	async def create_entry(self, user_id: int, guild_id: int, recipients: list[int] | None = None, message: str = "", timestamp: datetime.datetime | None = None, entry_id: int | None = None, message_index: int | None = None):
		"""Insert a repeated-message row; the database generates its int8 index when omitted."""

		if recipients is None:
			recipients = []

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
		}

		if message_index is not None:
			payload["index"] = message_index
		elif entry_id is not None:
			payload["index"] = entry_id

		response = await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()
		if response.data:
			return response.data[0].get("index")
		return message_index

	async def get_entries(self, user_id: int, guild_id: int) -> list[dict]:
		"""Return every repeated-message row owned by a user in a guild."""
		response = await self.client.table("DB2_Repeated_Messages").select("*").eq("user_id", user_id).eq("guild_id", guild_id).execute()
		return response.data or []

	async def get_entry(self, user_id: int, guild_id: int, message_index: int | None = None) -> dict | None:
		"""Return all stored daily message data for a user in a guild."""
		query = self.client.table("DB2_Repeated_Messages").select("*").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		return response.data[0] if response.data else None

	async def set_universal_message(self, user_id: int, guild_id: int, message: str, message_index: int | None = None):
		"""Update or insert universal text for a user+guild, preserving recipients."""
		query = self.client.table("DB2_Repeated_Messages").select("index,recipient_list").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if response.data:
			message_index = response.data[0].get("index")
			recipient_list = response.data[0].get("recipient_list") or []
		else:
			recipient_list = []

		payload = {
			"user_id": user_id,
			"guild_id": guild_id,
			"recipient_list": recipient_list,
			"universal_message": message or "",
		}
		if message_index is not None:
			payload["index"] = message_index
		await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def get_universal_message(self, user_id: int, guild_id: int) -> str:
		"""Return stored universal message for a user+guild, default empty."""
		response = await self.client.table("DB2_Repeated_Messages").select("universal_message").eq("user_id", user_id).eq("guild_id", guild_id).execute()
		if not response.data:
			return ""
		return response.data[0].get("universal_message") or ""

	async def add_recipient(self, user_id: int, guild_id: int, recipient_id: int, message_index: int | None = None):
		"""Append a recipient id to the recipient_list array if missing."""
		query = self.client.table("DB2_Repeated_Messages").select("index,recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if not response.data:
			recipient_list = []
			universal_message = ""
		else:
			message_index = response.data[0].get("index")
			recipient_list = response.data[0].get("recipient_list") or []
			universal_message = response.data[0].get("universal_message") or ""

		if recipient_id not in recipient_list:
			recipient_list.append(recipient_id)
			payload = {
				"user_id": user_id,
				"guild_id": guild_id,
				"recipient_list": recipient_list,
				"universal_message": universal_message,
			}
			if message_index is not None:
				payload["index"] = message_index
			await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def remove_recipient(self, user_id: int, guild_id: int, recipient_id: int, message_index: int | None = None):
		"""Remove a recipient id from the recipient_list array if present."""
		query = self.client.table("DB2_Repeated_Messages").select("index,recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if not response.data:
			return

		row = response.data[0]
		message_index = row.get("index")
		recipient_list = row.get("recipient_list") or []
		universal_message = row.get("universal_message") or ""
		if recipient_id in recipient_list:
			recipient_list.remove(recipient_id)
			payload = {
				"user_id": user_id,
				"guild_id": guild_id,
				"recipient_list": recipient_list,
				"universal_message": universal_message,
			}
			if message_index is not None:
				payload["index"] = message_index
			await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def get_recipients(self, user_id: int, guild_id: int, message_index: int | None = None) -> list:
		"""Retrieve the recipient_list for a user+guild; returns empty list if none."""
		query = self.client.table("DB2_Repeated_Messages").select("recipient_list").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if not response.data:
			return []
		return response.data[0].get("recipient_list") or []

	async def clear_recipients(self, user_id: int, guild_id: int, message_index: int | None = None):
		"""Clear the recipient list while preserving the stored message and schedule."""
		query = self.client.table("DB2_Repeated_Messages").select("index,universal_message,timestamp").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if response.data:
			row = response.data[0]
			message_index = row.get("index")
			message = row.get("universal_message") or ""
			timestamp = row.get("timestamp")
		else:
			message = ""
			timestamp = None

		payload = {
			"user_id": user_id,
			"guild_id": guild_id,
			"recipient_list": [],
			"universal_message": message,
			"timestamp": timestamp,
		}
		if message_index is not None:
			payload["index"] = message_index
		await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def set_timestamp(self, user_id: int, guild_id: int, scheduled_time: datetime.datetime, message_index: int | None = None):
		"""Store a persistent timestamptz for the user's guild schedule."""
		if isinstance(scheduled_time, datetime.datetime):
			if scheduled_time.tzinfo is None:
				scheduled_time = scheduled_time.replace(tzinfo=datetime.timezone.utc)
			scheduled_time = scheduled_time.isoformat()

		query = self.client.table("DB2_Repeated_Messages").select("index,recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if response.data:
			row = response.data[0]
			message_index = row.get("index")
			recipient_list = row.get("recipient_list") or []
			universal_message = row.get("universal_message") or ""
		else:
			recipient_list = []
			universal_message = ""

		payload = {
			"user_id": user_id,
			"guild_id": guild_id,
			"recipient_list": recipient_list,
			"universal_message": universal_message,
			"timestamp": scheduled_time,
		}
		if message_index is not None:
			payload["index"] = message_index
		await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def clear_timestamp(self, user_id: int, guild_id: int, message_index: int | None = None):
		"""Clear the scheduled timestamp while preserving the stored recipient list and message."""
		query = self.client.table("DB2_Repeated_Messages").select("index,recipient_list,universal_message").eq("user_id", user_id).eq("guild_id", guild_id)
		if message_index is not None:
			query = query.eq("index", message_index)
		response = await query.execute()
		if not response.data:
			return

		row = response.data[0]
		payload = {
			"user_id": user_id,
			"guild_id": guild_id,
			"recipient_list": row.get("recipient_list") or [],
			"universal_message": row.get("universal_message") or "",
			"timestamp": None,
			"index": row.get("index"),
		}
		await self.client.table("DB2_Repeated_Messages").upsert(payload).execute()

	async def get_scheduled_messages(self, now: datetime.datetime | None = None) -> list:
		"""Return rows where stored timestamp hour/minute equals now's hour/minute (UTC default)."""
		response = await self.client.table("DB2_Repeated_Messages").select(
			"index,user_id,guild_id,timestamp,universal_message,recipient_list"
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

	async def delete_entry(self, user_id: int, guild_id: int):
		"""Removes an entry for a user+guild entirely."""
		await self.client.table("DB2_Repeated_Messages").delete().eq("user_id", user_id).eq("guild_id", guild_id).execute()

	async def delete_user_data(self, user_id: int):
		"""Remove a user's rows across all guilds and recipient-list references."""
		response = await self.client.table("DB2_Repeated_Messages").select(
			"user_id,guild_id,recipient_list"
		).execute()

		for row in response.data or []:
			recipient_list = row.get("recipient_list") or []
			if row.get("user_id") != user_id and user_id in recipient_list:
				await self.client.table("DB2_Repeated_Messages").update({
					"recipient_list": [recipient_id for recipient_id in recipient_list if recipient_id != user_id]
				}).eq("user_id", row["user_id"]).eq("guild_id", row["guild_id"]).execute()

		await self.client.table("DB2_Repeated_Messages").delete().eq("user_id", user_id).execute()
