import discord


class DeliveryService:
    def __init__(self, bot):
        self.bot = bot

    async def direct_message(self, user_id: int, message: str) -> bool:
        if not message or not message.strip():
            return False

        user = self.bot.get_user(user_id)
        if user is None:
            user = await self.bot.fetch_user(user_id)
        await user.send(message)
        return True

    async def send_daily_message(self, user_id: int, message: str, owner_id: int, guild_id: int, message_index: int):
        try:
            await self.direct_message(user_id, message)
        except discord.Forbidden as error:
            print(f"Could not send daily message to user {user_id}: {error}")
            try:
                await self.bot.db2.remove_recipient(owner_id, guild_id, user_id, message_index)
            except Exception as remove_error:
                print(f"Could not remove user {user_id} from the daily recipient list: {remove_error}")
        except Exception as error:
            print(f"Error sending daily message to user {user_id}: {error}")
