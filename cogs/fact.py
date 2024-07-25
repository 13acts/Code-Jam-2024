import random

import discord
from discord import app_commands
from discord.ext import commands
from utils.gemini import gemini_client


class FactCommand(commands.Cog):
    """Fact commands cog."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize FactCommand cog."""
        self.bot = bot

    @app_commands.command(name="discuss")
    async def discuss(self, interaction: discord.Interaction, topic: str) -> None:
        """Create a discussion on the given topic."""
        await interaction.response.send_message("Loading conversation...")

        # Generate convo from gemini
        conversation = await gemini_client.generate_conversation(topic)
        data = json.loads(conversation)

        # Verify data structure
        if isinstance(data, dict):
            message = data.get("summary", "Failed to generate a conversation on given topic.")
            embed = discord.Embed(
                title="Error",
                description=message,
                color=discord.Color.red(),
            )
            await interaction.edit_original_response(content=None, embed=embed)
            return

        # Send convo start embed
        embed = discord.Embed(
            title=f"You have started a discussion on the topic: **{topic}**",
            color=discord.Color.blurple(),
        )
        await interaction.edit_original_response(content=None, embed=embed)

        # Assign users for the generated convo
        convo_starter = interaction.user
        other_users = random.sample(
            [member for member in interaction.guild.members if not (member.bot or member==convo_starter)],
            k=2)
        users = [convo_starter, *other_users]

        # Set up webhooks with server
        webhooks = await interaction.channel.webhooks()
        if not webhooks:
            webhook = await interaction.channel.create_webhook(name="Discussion")
        else:
            for webhook in webhooks:
                if webhook.token:
                    break
            else:
                webhook = await interaction.channel.create_webhook(name="Discussion")

        # Send messages
        for message in data:
            user = users[message["userid"] % len(users)]
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            await webhook.send(
                content=message["message"],
                username=user.display_name,
                avatar_url=avatar_url,
            )

    @app_commands.command(name="summarize")
    async def summarize(self, interaction: discord.Interaction, text: str) -> None:
        """Summarize the given text."""
        await interaction.response.send_message("Summarizing the conversation...", ephemeral=True)
        summary = await gemini_client.summarize_conversation(text)
        if summary:
            summarized_text = json.loads(summary)["summary"]
            embed = discord.Embed(
                title="Summary",
                description=summarized_text,
                color=discord.Color.blurple(),
            )

            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to summarize the conversation.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Setups the Fact command."""
    await bot.add_cog(FactCommand(bot))
