import logging.config
import os
from pathlib import Path

import discord
from cogwatch import watch
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


class InfoFilter(logging.Filter):
    """Filter to change INFO logs to DEBUG."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Change log level in the record."""
        if record.levelno == logging.INFO:
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return True


cogwatcher = logging.getLogger("cogwatch")
cogwatcher.addFilter(InfoFilter())


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
        await self.tree.sync()

    @watch(path="cogs", default_logger=False)
    async def on_ready(self) -> None:
        """Call when bot is logged in."""
        from utils.database import db

        await db.clear_command_cache()
        await bot.change_presence(activity=discord.Game(name="/help"))
        logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)

    async def load_extensions(self) -> None:
        """Load all extensions in the cogs directory."""
        extension_path = "cogs"
        for filename in os.listdir(extension_path):
            if filename.endswith(".py") and filename != "__init__.py":
                await bot.load_extension(f"{extension_path}.{filename[:-3]}")
                logger.info("extension %s loaded.", filename)


bot = Bot()


@bot.tree.command(name="help", description="List of commands and their functions")
async def help(interaction: discord.Interaction) -> None:
    """Return a list of commands and their functions."""
    embed = discord.Embed(
        title="Help",
        description="List of commands and their functions",
        color=discord.Color.from_str("#bb8b3b"),
    )
    commands = bot.tree.get_commands()
    for command in commands:
        if command.name != "help":
            desc = command.description
            params = ", ".join(
                [parameters.name for parameters in command.parameters],
            )

            embed.add_field(
                name=f"/{command.name}",
                value=f"**Description:**\n*{desc}*{f'\n**Parameters**: *{params}*' if params else ''}",
                inline=True,
            )

    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt is raised. Exiting.".upper())
