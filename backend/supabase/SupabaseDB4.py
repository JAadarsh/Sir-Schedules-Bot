"""
Access object for user data in Supabase.
Acknowledgement: SUPABASE PTE. LTD. 2026
---------------------------------------------
Aadarsh Joshi 2026
"""

import datetime

from supabase import AsyncClient, acreate_client


class Database4:
	"""Access universal user data stored in DB4_User_Data."""

	TABLE_NAME = "DB4_User_Data"

	def __init__(self, url: str, key: str):
		self.url = url
		self.key = key
		self.client: AsyncClient = None

	async def connect(self):
		"""Establish the asynchronous Supabase client."""
		self.client = await acreate_client(self.url, self.key)

	@staticmethod
	def _validate_user_id(user_id: int):
		if (
			isinstance(user_id, bool)
			or not isinstance(user_id, int)
			or not -(2**63) <= user_id <= 2**63 - 1
		):
			raise ValueError("user_id must fit in a PostgreSQL int8")

	@staticmethod
	def _validate_premium_status(premium_status: bool):
		if not isinstance(premium_status, bool):
			raise TypeError("premium_status must be a boolean")

	@staticmethod
	def _serialize_default_time(default_time: datetime.datetime | None) -> str | None:
		if default_time is None:
			return None
		if not isinstance(default_time, datetime.datetime):
			raise TypeError("default_time must be a datetime or None")
		if default_time.tzinfo is None:
			default_time = default_time.replace(tzinfo=datetime.timezone.utc)
		return default_time.isoformat()

	async def create_entry(
		self,
		user_id: int,
		premium_status: bool = False,
		default_time: datetime.datetime | None = None,
	):
		"""Create or replace a user's universal data row."""
		self._validate_user_id(user_id)
		self._validate_premium_status(premium_status)

		await self.client.table(self.TABLE_NAME).upsert({
			"user_id": user_id,
			"premium_status": premium_status,
			"default_time": self._serialize_default_time(default_time),
		}).execute()

	async def get_entry(self, user_id: int) -> dict | None:
		"""Return a user's universal data row, or None when absent."""
		self._validate_user_id(user_id)
		response = await self.client.table(self.TABLE_NAME).select("*").eq("user_id", user_id).execute()
		return response.data[0] if response.data else None

	async def set_premium_status(self, user_id: int, premium_status: bool):
		"""Set whether a user has premium access."""
		self._validate_user_id(user_id)
		self._validate_premium_status(premium_status)
		await self.client.table(self.TABLE_NAME).upsert({
			"user_id": user_id,
			"premium_status": premium_status,
		}).execute()

	async def get_premium_status(self, user_id: int) -> bool:
		"""Return a user's premium status, defaulting to False when absent."""
		entry = await self.get_entry(user_id)
		return bool(entry.get("premium_status")) if entry else False

	async def set_default_time(self, user_id: int, default_time: datetime.datetime | None):
		"""Set or clear a user's default timestamptz value."""
		self._validate_user_id(user_id)
		await self.client.table(self.TABLE_NAME).upsert({
			"user_id": user_id,
			"default_time": self._serialize_default_time(default_time),
		}).execute()

	async def get_default_time(self, user_id: int) -> str | None:
		"""Return a user's default time as provided by Supabase, or None."""
		self._validate_user_id(user_id)
		response = await self.client.table(self.TABLE_NAME).select("default_time").eq("user_id", user_id).execute()
		if not response.data:
			return None
		return response.data[0].get("default_time")

	async def delete_entry(self, user_id: int):
		"""Delete a user's universal data row."""
		self._validate_user_id(user_id)
		await self.client.table(self.TABLE_NAME).delete().eq("user_id", user_id).execute()