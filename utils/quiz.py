import asyncio
import html
import random
from collections import defaultdict

import aiohttp
import discord
import requests
from bs4 import BeautifulSoup

from utils.database import db


def fetch_categories() -> dict:
    """Create structured categories."""
    response = requests.get("https://opentdb.com/api_category.php", timeout=(3, 5))
    raw_categories = response.json()["trivia_categories"]

    structured_categories = defaultdict(dict)

    for category in raw_categories:
        topic: str = category["name"]
        id = category["id"]

        if ":" in topic:
            topic, subtopic = topic.split(": ")
            structured_categories[topic][subtopic] = id
        else:
            structured_categories[topic] = id

    return structured_categories


# defaultdict(<class 'dict'>, {'General Knowledge': 9, 'Entertainment': {'Books': 10, 'Film': 11, 'Music': 12, 'Musicals & Theatres': 13, 'Television': 14, 'Video Games': 15, 'Board Games': 16, 'Comics': 29, 'Japanese Anime & Manga': 31, 'Cartoon & Animations': 32}, 'Science & Nature': 17, 'Science': {'Computers': 18, 'Mathematics': 19, 'Gadgets': 30}, 'Mythology': 20, 'Sports': 21, 'Geography': 22, 'History': 23, 'Politics': 24, 'Art': 25, 'Celebrities': 26, 'Animals': 27, 'Vehicles': 28})  # noqa: E501

TOPICS_POOL = fetch_categories()


def has_sub_topic(topic: str) -> bool:
    """Determine if the topic name has subtopics or not."""
    return not isinstance(TOPICS_POOL[topic], int)


def get_topic_id(topic: str) -> int:
    """Return opentdb's root topic id from name."""
    return TOPICS_POOL[topic]


def get_sub_topic_id(topic: str, topic_id_correct_count: dict) -> int:
    """Return subtopic id from name and possibly count of how many times the topic is correct."""
    all_topic_ids = list(TOPICS_POOL[topic].values())
    if not topic_id_correct_count:
        return random.choice(all_topic_ids)  # noqa: S311

    sorted_correct_count = [
        x[0]
        for x in sorted(
            topic_id_correct_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]
    return weighted_selection(all_topic_ids, sorted_correct_count)


def weighted_selection(all_ids: list, ordered_correct_count: list) -> int:
    """Assign weights algorithm. The higher the order of correct_count, the lower the weight."""
    weights = [len(all_ids)] * len(all_ids)

    max_weight = len(ordered_correct_count)
    for weight, element in enumerate(ordered_correct_count, start=1):
        if element in all_ids:
            weights[all_ids.index(element)] -= max_weight - weight + 1

    return random.choices(all_ids, weights=weights)[0]  # noqa: S311


def create_api_call(
    number_of_q: int,
    category: int | None = None,
    difficulty: str | None = None,
    type: str | None = None,
) -> str:
    """Create API call. Could've used params but it'll interfere with token."""
    url = f"https://opentdb.com/api.php?amount={number_of_q}"
    if category:
        url += f"&category={category}"
    if difficulty:
        url += f"&difficulty={difficulty}"
    if type:
        url += f"&type={type}"
    return url


def fetch_json(url: str) -> list:
    """Fetch API from opentdb. Return False if bad response code."""
    try:
        response = requests.get(url, timeout=(3, 5))
    except requests.exceptions.Timeout:
        print("Timed out")

    if response.json()["response_code"] != 0:
        return False

    return response.json()["results"]


def fetch_quizzes(json: list) -> list:
    """Return list of quizzes based on json."""
    quizzes = []
    for quiz in json:
        quiz["question"] = html.unescape(quiz["question"])
        quiz["correct_answer"] = html.unescape(quiz["correct_answer"])
        quiz["incorrect_answers"] = [html.unescape(answer) for answer in quiz["incorrect_answers"]]

        quizzes.append(quiz)

    return quizzes


async def fetch_token() -> str:
    """Fetch a token from the API."""
    url = "https://opentdb.com/api_token.php?command=request"
    async with aiohttp.ClientSession().get(url, timeout=3) as response:
        return (await response.json())["token"]


async def get_quizzes_with_token(server_id: int, api_url: str) -> list:
    """Return list of quizzes with token check."""
    # If token exists
    if current_token := await db.get_token(server_id):
        # Current token works
        if json := fetch_json(api_url + f"&token={current_token}"):
            return fetch_quizzes(json)

        # Current token no longer works
        await asyncio.sleep(5)
        new_token = await fetch_token()
        await db.change_token(server_id, new_token)

        return fetch_quizzes(fetch_json(api_url + f"&token={new_token}"))

    # No token yet
    new_token = await fetch_token()
    await db.change_token(server_id, new_token)
    return fetch_quizzes(fetch_json(api_url + f"&token={new_token}"))


def learn_more_url(question: str) -> str:
    """Return the first Wikipedia Google search result URL for the question."""
    query = question + " site:en.wikipedia.org"
    url = "https://www.google.com/search"

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82",  # noqa: E501
    }
    parameters = {"q": query}

    response = requests.get(url, headers=headers, params=parameters, timeout=3)
    response.raise_for_status()  # Raise an exception for HTTP errors
    content = response.text

    soup = BeautifulSoup(content, "html.parser")
    search_results = soup.find_all("a")

    # Find the first Wikipedia link
    for link in search_results:
        href: str = link.get("href")
        if href and "en.wikipedia.org/wiki/" in href:
            return href

    # Default return
    return "https://en.wikipedia.org"


async def get_top_participants(
    interaction: discord.Interaction,
    participants: dict,
    limit: int = 3,
) -> list:
    """Return top 3 participants."""
    top_participants = sorted(
        participants.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:limit]

    top_users = []
    for user_id, score in top_participants:
        user = await interaction.guild.fetch_member(user_id)
        top_users.append((user, score))
    return top_users
    


async def result_embed(
    interaction: discord.Interaction,
    participants: dict,
    limit: int = 3,
) -> discord.Embed:
    """Return embed for quiz results with top 3."""
    top_users = await get_top_participants(interaction, participants, limit)

    if top_users:
        result_message = ""
        for rank, (user, score) in enumerate(top_users, start=1):
            result_message += f"{rank}. **{user.display_name}** - {score} points\n"
        embed = discord.Embed(
            title=f"Top {limit} players",
            description=result_message,
            color=discord.Color.blurple(),
        )
    else:
        embed = discord.Embed(
            title="No participants.",
            color=discord.Color.red(),
        )
    return embed
