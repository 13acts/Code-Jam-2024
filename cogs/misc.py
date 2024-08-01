import random

import discord
from discord import app_commands
from discord.ext import commands


class MiscCommand(commands.Cog):
    """Misc commands cog.

    Parameters
    ----------
    bot
        A `commands.Bot` instance.
        Should hold the bot that this cog is associted with,
        i.e. the bot that loads this extension.

    Attributes
    ----------
    bot
        A `commands.Bot` instance.
        Should hold the bot that this cog is associted with,
        i.e. the bot that loads this extension.

    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Ping the bot.

        Parameters
        ----------
        interaction
            The interaction that represents this command invocation.

        """
        await interaction.response.send_message(f"Pong! Latency: **{round(self.bot.latency * 1000)}ms**")

    @app_commands.command(name="randomize")
    async def randomize(self, interaction: discord.Interaction) -> None:
        """Tag a random user.

        Parameters
        ----------
        interaction
            The interaction that represents this command invocation.

        """
        phrase = random.choice(["You've been chosen,", "I choose you,", "And the chosen one is"])  # noqa: S311
        user = random.choice(interaction.channel.guild.members)  # noqa: S311
        await interaction.response.send_message(f"{phrase} {user.mention}")


async def setup(bot: commands.Bot) -> None:
    """Setups the misc command."""
    await bot.add_cog(MiscCommand(bot))
