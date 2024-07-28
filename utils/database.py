import logging
import os
from typing import Any

import motor.motor_asyncio

logger = logging.getLogger("db")


class Database:
    """Database class."""

    def __init__(self, database: str) -> None:
        """Form Database Connection."""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(database)
        self.db = self.client["bot-data"]

        self.scores = self.db["scores"]
        self.commands_cache = self.db["commands_cache"]
        self.quiz_tokens = self.db["quiz_tokens"]
        self.shortify_cache = self.db["shortify_cache"]

        logger.info("Connected to MongoDB database.")

    async def get_score(self, user_id: int, server_id: int) -> int:
        """Get the score of a user."""
        score = await self.scores.find_one({"user_id": user_id, "server_id": server_id})
        return score["score"] if score else 0

    async def set_score(self, user_id: int, server_id: int, score: int) -> None:
        """Set the score of a user."""
        await self.scores.update_one(
            {"user_id": user_id, "server_id": server_id},
            {"$set": {"score": score}},
            upsert=True,
        )

    async def get_leaderboard(self, server_id: int, limit: int = 5) -> dict:
        """Return the highest scoring users in server."""
        top_users = self.scores.find({"server_id": server_id}).sort("score", -1).limit(limit)
        leaderboard = {}
        async for document in top_users:
            user_id = document.get("user_id")
            score = document.get("score")
            leaderboard[user_id] = score
        return leaderboard

    async def command_is_active(self, command_name: str, channel_id: int) -> bool:
        """Check if a command is active."""
        command = await self.commands_cache.find_one(
            {"command_name": command_name, "channel_id": channel_id},
        )
        return command["active"] if command else False

    async def set_command_active(self, command_name: str, channel_id: int) -> None:
        """Set a command as active."""
        await self.commands_cache.update_one(
            {"command_name": command_name, "channel_id": channel_id},
            {"$set": {"active": True}},
            upsert=True,
        )

    async def set_command_inactive(self, command_name: str, channel_id: int) -> None:
        """Set a command as inactive."""
        await self.commands_cache.update_one(
            {"command_name": command_name, "channel_id": channel_id},
            {"$set": {"active": False}},
            upsert=True,
        )

    async def clear_command_cache(self) -> None:
        """Clear the command cache."""
        await self.commands_cache.delete_many({})

    async def get_token(self, server_id: int) -> dict:
        """Return all currently tokens."""
        if result := await self.quiz_tokens.find_one({"server_id": server_id}):
            return result.get("token")
        return False

    async def change_token(self, server_id: int, token: str) -> None:
        """Change the token of a channel."""
        await self.quiz_tokens.update_one(
            {"server_id": server_id},
            {"$set": {"token": token}},
            upsert=True,
        )

    async def get_shortify_cache(self, user_id: int, channel_id: int) -> dict:
        """Get shortify cache."""
        return await self.shortify_cache.find_one({"user_id": user_id, "channel_id": channel_id})

    async def set_shortify_cache(self, user_id: int, channel_id: int, message_id: int) -> list[int | Any]:
        """Set shortify cache."""
        old_cache = await self.get_shortify_cache(user_id, channel_id)
        if old_cache:
            await self.shortify_cache.delete_one({"user_id": user_id, "channel_id": channel_id})
            return sorted([old_cache["message_id"], message_id])

        await self.shortify_cache.insert_one(
            {"user_id": user_id, "channel_id": channel_id, "message_id": message_id},
        )
        return None

    async def close(self) -> None:
        """Close the database connection."""
        self.client.close()


db = Database(os.getenv("DATABASE"))
