import asyncio
import io
import time
from collections import defaultdict

import discord
from discord.ext import commands
from repositories import quiz_repo
from utils.database import db
from utils.leaderboard import generate_quiz_leaderboard_image
from utils.quiz import (
    create_api_call,
    get_quizzes_with_token,
    get_sub_topic_id,
    get_top_participants,
    get_topic_id,
    has_sub_topic,
    result_embed,
)

VOTING_TIME = quiz_repo.voting_time()


class QuizCommand(commands.Cog):
    """Quiz commands cog."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize QuizCommand cog."""
        self.bot = bot

    @discord.app_commands.command(name="score")
    async def score(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
    ) -> None:
        """Get the score of a user."""
        await interaction.response.defer()
        user = user or interaction.user
        score = await db.get_score(user.id, interaction.guild_id)
        if score:
            embed = discord.Embed(
                description=f"{user.mention}'s Score: {score}",
                color=discord.Color.blurple(),
            )
            await interaction.followup.send(
                embed=embed,
                allowed_mentions=None,
                ephemeral=True,
            )
        else:
            embed = discord.Embed(
                description=f"{user.mention} has not attempted the quiz yet.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(
                embed=embed,
                allowed_mentions=None,
                ephemeral=True,
            )

    @discord.app_commands.command()
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        """Return the server's leaderboabrd."""
        await interaction.response.defer()
        leaderboard = await db.get_leaderboard(interaction.guild_id)
        embed = await result_embed(interaction, leaderboard, 5)
        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name="quiz")
    async def quiz(self, interaction: discord.Interaction) -> None:
        """Start new quiz."""
        await interaction.response.defer()
        channel_id = interaction.channel_id
        server_id = interaction.guild_id

        # Check if there's already an active quiz in this channel
        if await db.command_is_active("quiz", channel_id):
            embed = discord.Embed(
                title="Quiz",
                description="**A quiz is already running in this channel.**",
                color=discord.Color.red(),
            )
            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
            return

        # Mark quiz started
        await db.set_command_active("quiz", channel_id)

        # Voting phase =====================================================================
        voting_view = quiz_repo.VotingView()
        await interaction.followup.send(
            f"Choose your topic! Ends **<t:{int(time.time()) + 11}:R>**",
            view=voting_view,
        )
        voting_view.message = await interaction.original_response()  # Store the original message in the view

        await asyncio.sleep(VOTING_TIME)
        if timeout := await voting_view.on_timeout():
            number, topic = timeout

        # Quiz is cancelled
        else:
            embed = discord.Embed(
                title="Quiz is cancelled.",
                color=discord.Color.red(),
            )
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=None,
            )
            await db.set_command_inactive("quiz", channel_id)
            return

        # For dynamic topic
        if has_sub := has_sub_topic(topic):
            topic_id_correct_count = defaultdict(int)

        # Question phase ====================================================================
        participants = defaultdict(int)
        for i in range(1, number + 1):
            async with interaction.channel.typing():
                # Get topic id dynamically based on previous answers
                topic_id = get_sub_topic_id(topic, topic_id_correct_count) if has_sub else get_topic_id(topic)

                # Fetch question
                quiz = await get_quizzes_with_token(
                    server_id,
                    create_api_call(1, topic_id),
                )
                quiz = quiz[0]

                # Send the question and store in view
                content = f"### {i}) {quiz['question']} {'Quiz ends ' if i == number else 'Next '} **<t:{int(time.time()) + 11}:R>**"  # noqa: E501
                question_view = quiz_repo.QuestionView(
                    i,
                    quiz["question"],
                    quiz["correct_answer"],
                    quiz["incorrect_answers"],
                    quiz["type"],
                )
                question_view.message = await interaction.channel.send(
                    content=content,
                    view=question_view,
                    silent=True,
                )

            # Set timer
            await asyncio.sleep(VOTING_TIME - 5)
            correct_users = await question_view.on_timeout()

            # Track correct answers
            for user_id in correct_users:
                participants[user_id] += 1
                score = await db.get_score(user_id, server_id)
                await db.set_score(user_id, server_id, score + 1)

                # Register topic_id is correctly answered (for dynamic topic)
                if has_sub:
                    topic_id_correct_count[topic_id] += 1

        # Results =============================================================================
        embed = await result_embed(interaction, participants, 3)
        await interaction.channel.send(content="## Quiz ended", embed=embed)
        top_participants = await get_top_participants(interaction, participants)
        if top_participants:
            image = await generate_quiz_leaderboard_image(top_participants)
            with io.BytesIO() as image_binary:
                image.save(image_binary, "PNG")
                image_binary.seek(0)
                await interaction.channel.send(
                    file=discord.File(fp=image_binary, filename="leaderboard.png"),
                )

        # Mark quiz ended
        await db.set_command_inactive("quiz", channel_id)


async def setup(bot: commands.Bot) -> None:
    """Setups the Quiz command."""
    await bot.add_cog(QuizCommand(bot))
