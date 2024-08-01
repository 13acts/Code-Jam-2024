# Quizzly Bear - Python Discord Codejam Project
Welcome to the GitHub repository for Quizzly Bear, a Discord bot created for the Python Discord Summer CodeJam 2024! This bot is based on the theme "Information Overload", where its plethora of interactive and informative features fit right in.

Quizzly bot has the following slash commands
- `discuss` to create a discussion on a given topic
- `summarize` to summarize a given body of text
- `shortify` to summarize the conversation in-between two messages
- `factpedia` to start a fact checker minigame
- `hello` to generate a simple greeting :&#41;
- `ping` to ping the bot
- `randomize` to tag a random user
- `score` to fetch the user score
- `leaderboard` to display the server leaderboard
- `quiz` to start a new quiz

Check out this [presentation](https://docs.google.com/presentation/d/e/2PACX-1vQ5dI5UWM8UZZ8NZUfjjBaWK1HaHybkqfwrur6GFR01_-KkRIltL7CU3iqb8rrjBg/pub?start=true&loop=false&delayms=15000&slide=id.p1) for a glimpse of the commands at work!

## Installation and Running
1. Create a [bot account](https://discordpy.readthedocs.io/en/stable/discord.html).

2. Clone the repo.
```sh
git clone https://github.com/13acts/Code-Jam-2024.git
```

3. Enter directory, install [poetry](https://python-poetry.org), and do `poetry install` to install all the project dependencies. Skip step 2 if you already have poetry installed on your system.

```sh
cd Code-Jam-2024
python -m pip install poetry
poetry install
```

4. Activate .venv
```sh
poetry shell
```

5. Create an .env file with environment values set as in the .env.sample file.
- `TOKEN`: Discord Bot Token
- `SERVER`: Discord server ID (used for development only)
- `DATABASE`: Connection to MongoDB
- `GOOGLE_API_KEY`: API Token from Google Gemini

7. Run the bot.
```sh
python main.py
```
