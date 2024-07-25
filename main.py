import wikipedia
import random

import google.generativeai as genai

import discord
from discord.ext import commands
from discord import app_commands

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN") #os.environmen['TOKEN']
GEMINI_KEY = os.getenv("GEMINI_KEY")

bot = commands.Bot(command_prefix='.', intents=discord.Intents.default())

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class FactsDropdown(discord.ui.Select):
    def __init__(self, facts: list, embed: discord.Embed, false_index: int):
        self.embed = embed
        self.false_index = false_index
        
        options = []
        for i in range(len(facts)):
            options.append(discord.SelectOption(label=f"Fact no. {i+1}", value=i))
        
        super().__init__(placeholder="Which one is the wrong fact?", options=options, min_values=1, max_values=1)
        
        self.rightEmbed = discord.Embed(
            title="Correct!",
            color=discord.Color.green()
        )
        self.wrongEmbed = discord.Embed(
            title=f"Wrong! The False Fact was Fact no. {false_index+1}: {facts[false_index]}",
        )
        
    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        embeds = [self.embed]
        
        if self.values[0] == self.false_index:
            embeds.append(self.rightEmbed)
        else:
            embeds.append(self.wrongEmbed)
        await interaction.response.edit_message(view=None, embeds=embeds, content=f"You selected {self.values[0]}")

class FactsView(discord.ui.View):
    def __init__(self, *, timeout: float = 60, embed: discord.Embed, facts: list, false_index: int):
        super().__init__(timeout=timeout)
        self.add_item(FactsDropdown(embed=embed, facts=facts, false_index=false_index))

def getWikiResults(prompt: str, number: int = 5):
    page_list = [str(i) for i in wikipedia.summary(prompt, auto_suggest=False).split('.') if len(i) in range(50, 500)] #splitting the summary into sentences. Checks for garbage sentences
    facts = [] #list of facts
    for i in range(number):
        randomFact = random.choice(page_list)
        while randomFact in facts:
            randomFact = random.choice(page_list)
        facts.append(randomFact)
            
    return facts

def getFalseFact(prompt: str):
    response = model.generate_content("Create false fact about: " + prompt + "in one line")
    
    return response.text + "**False**"
    

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        await bot.change_presence(activity=discord.Game(name="/help"))
    except Exception as e:
        print(e)

@bot.tree.command(name="search", description="returns a number of random facts based on the prompt")
async def search(interaction: discord.Interaction, entry: str, number: int = 5):
    
    await interaction.response.defer()
    
    try:
        results = getWikiResults(entry, number=number)
        
        falseIndex = random.randint(0, number-1)
        results[falseIndex] = getFalseFact(entry)
        
        factEmbed = discord.Embed(
            title="Random Wikipedia Facts",
            description=f"List of random wikipedia facts on the topic **{entry}**",
            colour=discord.Colour.random()
        )
        for i in range(len(results)):
            factEmbed.add_field(name=f"Fact no. {i+1}",
                            value=results[i],
                            inline=False)
            
        questionEmbed = discord.Embed(
            title="Choose the fact that is wrong!",
            color=discord.Color.gold()
        )
            
        await interaction.followup.send(embeds=[factEmbed, questionEmbed], view=FactsView(embed=factEmbed, facts=results, false_index=falseIndex))
    except wikipedia.DisambiguationError:
        await interaction.followup.send(f"The prompt **{entry}** can refer to many different things, please be more specific!")
    except wikipedia.PageError:
        await interaction.followup.send(f"The prompt **{entry}** did not match any of our searches. Please try again with a differently worded prompt / query.")
    
@bot.tree.command(name="help", description="returns a list of commands and their functions")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help",
        description="List of commands and their functions",
        color=discord.Color.from_str("#bb8b3b") #Color of the embed, change to whatever you like
    )
    commands = bot.tree.get_commands()
    for command in commands:
        if command.name != "help":
            parameters = ", ".join([app_commands.Parameter.name for app_commands.Parameter in command.parameters])
            
            embed.add_field(name=f"/{command.name}", 
                            value=f"**`Description:`**\n*{command.description}*\n**`Parameters`**: *{parameters}*", inline=True) #How each command is displayed
            
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
