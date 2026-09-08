import asyncio


class DataService:
    def __init__(self, bot):
        self.bot = bot

    async def clear_guild_data(self, user_id: int, guild_id: int):
        await self.bot.db.delete_entry(user_id, guild_id)
        await self.bot.db2.delete_entry(user_id, guild_id)
        await self.bot.db3.delete_entry(user_id, guild_id)

    async def delete_user_data(self, user_id: int):
        await asyncio.gather(
            self.bot.db.delete_user_data(user_id),
            self.bot.db2.delete_user_data(user_id),
            self.bot.db3.delete_user_data(user_id),
        )
