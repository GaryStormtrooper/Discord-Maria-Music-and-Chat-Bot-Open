#.\myenv\Scripts\activate

import asyncio
import os
from os import environ
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv(".env")
TOKEN = environ["TOKEN"]
logChannel : int = <PUT_LOG_CHANNEL_ID_HERE>
GUILD = environ["DISCORD_GUILD"]
PREFIX = environ["PREFIX"]
OWNER = environ["OWNER"]

description = 'Maria'

intents = discord.Intents.all()

# Set up the bot prefix, description, intents.  Then load any cogs we want to use.  Finally, run the bot.
bot = commands.Bot(command_prefix=PREFIX, description=description, intents=intents)

# Custom help command is being used in HelpCog.py
bot.remove_command("help")

# Load in the cogs that are in the Cogs folder
async def load():
    for filename in os.listdir('./Cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'Cogs.{filename[:-3]}')

# Main that starts the bot
async def main():
    await load()
    await bot.start(TOKEN)

asyncio.run(main())
