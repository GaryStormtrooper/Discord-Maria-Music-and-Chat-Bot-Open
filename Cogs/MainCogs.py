import random
from os import environ
from discord.ext import commands
from dotenv import load_dotenv
import discord
import asyncio


load_dotenv(".env")
TOKEN = environ["TOKEN"]
logChannel : int = 1350540890027851806
GUILD = environ["DISCORD_GUILD"]
PREFIX = environ["PREFIX"]
OWNER = environ["OWNER"]

# List of initial commands to get a feel for using the Discord API
class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Print to display that everything is ready
    @commands.Cog.listener()
    async def on_ready(self):
        """Print to display that everything is ready"""
        print("Maria is ready to go!")

    # Shutdown the bot only if the OWNER issues the command
    @commands.command(name="shutdown", aliases=["off", "logoff"], help="Tell Maria to logoff Discord")
    async def shutdown(self, ctx):
        """Shutdown the bot only if the OWNER issues the command"""
        if str(ctx.message.author.id) == OWNER:
            print('Shutting down.  Goodbye, Gary.')
            await ctx.send('Shutting down.  Goodbye, Gary.')
            await ctx.bot.close()
            exit(0)
        else:
            print('Someone is trying to shut me down.  How rude.')
            async with ctx.typing():
                await ctx.send('Only Gary can tell me to do that.')
                await ctx.send('If there is a problem with my A.I. then please do tell him.')
                await ctx.send(f'If not, then nice try, {ctx.message.author}.')


    # Ping command returns pong
    @commands.command(name="ping", help="Returns 'pong' for testing connection")
    async def ping(self, ctx):
        """Ping command returns pong"""
        try:
            await ctx.send("pong")
        except Exception:
            print('Failed to send ctx?')


    # Roll a simulated die in NdN format
    @commands.command(name="roll", aliases=["rolldice", "roll dice"], help="Rolls N number of dice with sides N")
    async def roll(self, ctx, dice: str):
        """Roll a simulated die in NdN format"""
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await ctx.send('Format has to be in NdN!')
            return

        result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
        await ctx.send(result)

    # Flip a coin for heads or tails
    @commands.command(name="flipcoin", aliases=["coin", "flip a coin", "flipacoin"], help="Flips a coin to heads or tails")
    async def flipcoin(self, ctx):
        """Flip a coin for heads or tails"""
        try:
            result = random.choice(['Heads', 'Tails'])
            await ctx.send(result)
        except Exception:
            print('Where did I leave my coin?')
            return

    # Member update that needs to be logged (nickname in this case)
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Member update that needs to be logged (nickname in this case)"""
        if before.nick != after.nick:
            print(before.nick, after.nick)
            channel = self.bot.get_channel(logChannel)
            await channel.send(f"{before.nick} has been name changed to {after.nick}")

    # Status of a member has changed and needs to be logged
    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        """Status of a member has changed and needs to be logged"""
        if before.status != after.status:
            print(before.status, after.status)
            channel = self.bot.get_channel(logChannel)
            #await channel.send(f"{before.status} has status changed to {after.status}")

    # Get the audit logs for the server and display them
    @commands.command(name="get_audit_log", aliases=["auditlog", "audit"], help="Fetch the recent entries in the audit log")
    async def get_audit_log(self, ctx):
        """Get the audit logs for the server and display them"""
        try:
            async for entry in ctx.guild.audit_logs(limit=10):  # Limit the number of entries
                print(f'{entry.user} did {entry.action} to {entry.target}')
                await ctx.send(f'{entry.user} did {entry.action} to {entry.target}')
        except Exception:
            print(f'I am having trouble retrieving the audit logs.')
            await ctx.send('I am having trouble retrieving the audit logs.')

# setup Cog for the bot to use
async def setup(bot):
    await bot.add_cog(MainCog(bot))