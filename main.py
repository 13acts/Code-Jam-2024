import logging.config
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
server = os.getenv("SERVER")
MY_GUILD = discord.Object(id=server)

intents = discord.Intents.all()
allowed_installs = discord.app_commands.AppInstallationType(guild=True)

if not Path.exists(Path("logs")):
    Path.mkdir(Path("logs"))

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("bot")


class Bot(commands.Bot):
    """Bot class."""

    def __init__(self) -> None:
        """Bot Initialization."""
        super().__init__(
            command_prefix="!",
            case_insensitive=True,
            strip_after_prefix=True,
            intents=intents,
            allowed_installs=allowed_installs,
        )

    async def setup_hook(self) -> None:
        """Setups hook for the bot."""
        # This copies the global commands over to your guild.
        await self.load_extensions()
        self.tree._guild_commands[MY_GUILD.id] = self.tree._global_commands
        self.tree._global_commands = {}
        await self.tree.sync(guild=MY_GUILD)

    async def on_ready(self) -> None:
        """Call when bot is logged in."""
        await bot.change_presence(activity=discord.Game(name="/help"))
        logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)

    async def load_extensions(self) -> None:
        """Load all extensions in the cogs directory."""
        extension_path = "cogs"
        excluded_files = ["__init__.py", "database.py"]
        for filename in os.listdir(extension_path):
            if filename.endswith(".py") and filename not in excluded_files:
                await bot.load_extension(f"{extension_path}.{filename[:-3]}")
                logger.info("extension %s loaded.", filename)


bot = Bot()


@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction) -> None:
    """Say hello!."""
    await interaction.response.send_message(
        f"Hi, {interaction.user.mention}.. Whatcha doin?",
    )


try:
    bot.run(BOT_TOKEN)
except KeyboardInterrupt:
    print("\nKeyboardInterrupt is raised. Exiting.".upper())
