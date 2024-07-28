import io
from pathlib import Path

import aiohttp
import discord
import PIL
from PIL import Image

BASE_PATH = Path(__file__).parent.parent
ASSETS_PATH = BASE_PATH / "assets"
FONTS_PATH = ASSETS_PATH / "fonts"
LEADERBOARD_PATH = ASSETS_PATH / "leaderboard"
CACHE_PATH = BASE_PATH / ".cache"
# create a cache path if it doesn't exist
CACHE_PATH.mkdir(exist_ok=True)


async def generate_quiz_leaderboard_image(
    leaderboard_data: list[tuple[discord.Member, int, int]],
) -> Image.Image | None:
    """Generate a quiz leaderboard image."""
    base_font_path = FONTS_PATH / "Montserrat-Medium.ttf"
    font = PIL.ImageFont.truetype(base_font_path, 24)
    bg_path = LEADERBOARD_PATH / "quiz-leaderboard.png"
    title_text = "Quiz Leaderboard"
    with PIL.Image.open(bg_path) as base_img:
        draw = PIL.ImageDraw.Draw(base_img)
        # Adjust font size and path
        for rank, user_data in enumerate(leaderboard_data, start=1):
            user, score = user_data
            text = f"{rank}. {user}: {score}"
            avatar_url = str(user.guild_avatar or user.display_avatar)
            avatar = await load_image(avatar_url)
            text_width = draw.textlength(text, font=font)
            rank_1 = 1
            rank_2 = 2
            rank_3 = 3

            if rank == rank_1:
                score_x = base_img.width / 2
                img_x = score_x - (avatar.width / 2)
                text_x = score_x - (text_width / 2)
                img_y = 150

            elif rank == rank_2:
                score_x = base_img.width / 4
                img_x = score_x - (avatar.width / 2)
                text_x = score_x - (text_width / 2)
                img_y = 250
            elif rank == rank_3:
                score_x = (3 * base_img.width) / 4
                img_x = score_x - (avatar.width / 2)
                text_x = score_x - (text_width / 2)
                img_y = 250
            text_y = img_y + avatar.height + 10
            base_img.paste(avatar, (int(img_x), img_y))
            draw.text(
                (int(text_x), int(text_y)),
                text,
                fill=(255, 255, 255),
                font=font,
            )
        draw.text(
            (10, 80),
            title_text,
            fill=(255, 255, 255),
            font=font,
        )

        return base_img


async def load_image(url: str, size: int = 50) -> Image.Image | None:
    """Load an image from a URL and resize it."""
    status_ok = 200
    async with aiohttp.ClientSession().get(url) as resp:
        if resp.status != status_ok:
            return None
        data = io.BytesIO(await resp.read())
        return Image.open(data).resize((size, size))
