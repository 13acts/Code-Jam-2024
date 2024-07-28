import asyncio
import json
import random
import re
import time

import discord
import wikipedia
from discord import app_commands
from discord.ext import commands
from repositories.wiki_repo import FactsView
from utils.database import db
from utils.gemini import gemini_client
from utils.wiki import create_false_statement, get_wiki_facts, get_wiki_image


class FactCommand(commands.Cog):
    """Fact commands cog."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize FactCommand cog."""
        self.bot = bot

    @app_commands.command(name="discuss")
    async def discuss(self, interaction: discord.Interaction, topic: str) -> None:
        """Create a discussion on the given topic."""
        await interaction.response.defer()

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
            await interaction.followup.send(content=None, embed=embed)
            return

        # Send convo start embed
        embed = discord.Embed(
            title=f"You have started a discussion on the topic: **{topic}**",
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(content=None, embed=embed)

        # Assign users for the generated convo
        convo_starter = interaction.user
        other_users = random.sample(
            [member for member in interaction.guild.members if not (member.bot or member == convo_starter)],
            k=2,
        )
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
            await asyncio.sleep(len(message["message"]) / 7)
            await webhook.send(
                content=message["message"],
                username=user.display_name,
                avatar_url=avatar_url,
            )

    @app_commands.command(name="summarize")
    async def summarize(self, interaction: discord.Interaction, text: str) -> None:
        """Summarize the given text."""
        await interaction.response.defer()
        summary = await gemini_client.summarize_conversation(text)
        if summary:
            summarized_text = json.loads(summary)["summary"]
            embed = discord.Embed(
                title="Summary",
                description=summarized_text,
                color=discord.Color.blurple(),
            )

            await interaction.followup.send(content=None, embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to summarize the conversation.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(content=None, embed=embed)

    @app_commands.command(name="shortify")
    async def shortify(self, interaction: discord.Interaction, start: str, end: str) -> None:
        """Summarize the conversation in-between 2 messages."""

        def parse_msg_id(arg: str) -> str | ValueError:
            """Verify the input arg is either msg link or msg id."""
            if match := re.match(r"^(?:https:\/\/discord\.com\/channels\/\d+\/\d+\/)*(\d+)$", arg):
                return int(match.group(1))
            raise ValueError

        async def convert_user_tags(message: discord.Message) -> str:
            def replace_tag(match: re.Match) -> str:
                """Replace user's ID with user's display name."""
                user_id = int(match.group(1))
                user = message.guild.get_member(user_id)
                return f"{user.display_name}" if user else match.group(0)

            return re.sub(r"<@?(\d+)>", replace_tag, message.content)

        channel = interaction.channel
        await interaction.response.defer()

        # Messages verification
        try:
            msg1 = await channel.fetch_message(parse_msg_id(start))
            msg2 = await channel.fetch_message(parse_msg_id(end))
        except (discord.NotFound, ValueError):
            embed = discord.Embed(
                title="Error",
                description="One or both message IDs are invalid.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return

        # Ensure msg1 is the older message
        if msg1.created_at > msg2.created_at:
            msg1, msg2 = msg2, msg1

        # Attach start and end messages
        messages = (
            [msg1] + [message async for message in channel.history(after=msg1, before=msg2, limit=None)] + [msg2]
        )

        # Turn into readable convo
        msg_contents = "\n".join([f"{msg.author.display_name}: {await convert_user_tags(msg)}" for msg in messages])

        # Gemini summarize and return result
        summary = await gemini_client.summarize_conversation(msg_contents)
        if summary:
            summarized_text = json.loads(summary)["summary"]
            embed = discord.Embed(
                title=f"**Summary** from {msg1.jump_url} to {msg2.jump_url}",
                description=summarized_text,
                color=discord.Color.blurple(),
            )
            await interaction.followup.send(content=None, embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to summarize the conversation.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(content=None, embed=embed)

    @app_commands.command()
    async def factpedia(self, interaction: discord.Interaction, entry: str, number: int = 5) -> None:
        """Generate a list of Wikipedia statements about topic. Find the one that is incorrect."""
        await interaction.response.defer()

        # Fetching facts from Wiki
        try:
            facts = get_wiki_facts(entry, number=number)
        except wikipedia.DisambiguationError:
            await interaction.followup.send(
                f"""The prompt **{entry}** can refer to many different things, please be more specific!""",
            )
            return
        except wikipedia.PageError:
            await interaction.followup.send(
                f"The prompt **{entry}** did not match any of our searches. Please try again with a differently worded prompt / query.",  # noqa: E501
            )
            return

        # Alter 1 fact to become incorrect
        false_index = random.randint(0, number - 1)  # noqa: S311
        correction = facts[false_index]
        facts[false_index] = create_false_statement(facts[false_index])

        # Create embeds for statements
        statements_embed = discord.Embed(
            title="Random Wikipedia Statements",
            description=f"Topic: **{entry}**",
            colour=discord.Colour.random(),
        )
        for i in range(len(facts)):
            statements_embed.add_field(name=f"Statement #{i+1}", value=facts[i], inline=False)
        if url := get_wiki_image(entry):
            statements_embed.set_thumbnail(url=url)

        # Create embed for more info
        question_embed = discord.Embed(
            title=f"Choose the incorrect statement!\nTime's up **<t:{int(time.time()) + 60}:R>**",
            color=discord.Color.gold(),
        )

        # Send the message containing 2 embeds and a drop select
        view = FactsView(
            embed=statements_embed,
            facts=facts,
            false_index=false_index,
            correction=correction,
            caller=interaction.user.id,
        )
        view.message = await interaction.followup.send(
            embeds=[statements_embed, question_embed],
            view=view,
        )

    @app_commands.command(name="hello")
    async def hello(self, interaction: discord.Interaction) -> None:
        """Say hello!."""
        msg = f"Hi, {interaction.user.mention}."
        fact = await gemini_client.name_fun_fact(interaction.user.display_name)
        fact = json.loads(fact)["fun_fact"]
        if fact != "False":
            msg += f"\nDid you know: {fact}"
        await interaction.response.send_message(msg)


async def setup(bot: commands.Bot) -> None:
    """Setups the Fact command."""
    cog = FactCommand(bot)

    @bot.tree.context_menu(name="short")
    async def shortify_context(interaction: discord.Interaction, message: discord.Message) -> None:
        """Summarize the conversation in-between 2 messages."""
        messages = await db.set_shortify_cache(interaction.user.id, message.channel.id, message.id)
        if messages:
            await cog.shortify.callback(cog, interaction, str(messages[0]), str(messages[1]))
        else:
            await interaction.response.send_message("Select another message to summarize.", ephemeral=True)

    await bot.add_cog(cog)
