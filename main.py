import logging.config
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
server = os.getenv("SERVER")
MY_GUILD = discord.Object(id=server)

intents = discord.Intents.all()
allowed_installs = discord.app_commands.AppInstallationType(guild=MY_GUILD)

if not os.path.exists('logs'):
    os.makedirs('logs')

logging.config.fileConfig('logging.conf')
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
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    async def load_extensions(self) -> None:
        """Load all extensions in the cogs directory."""
        extension_path = "cogs"
        for filename in os.listdir(extension_path):
            if filename.endswith(".py") and filename != "__init__.py":
                await bot.load_extension(f"{extension_path}.{filename[:-3]}")
                logger.info(f"extension {filename} loaded.")


bot = Bot()


@bot.tree.command(name="hello3")
async def hello(interaction: discord.Interaction) -> None:
    """Say hello!."""
    await interaction.response.send_message(
        f"Hi, {interaction.user.mention}.. Whatcha doin?",
    )


try:
    bot.run(BOT_TOKEN)
except KeyboardInterrupt:
    print("\nKeyboardInterrupt is raised. Exiting.".upper())
