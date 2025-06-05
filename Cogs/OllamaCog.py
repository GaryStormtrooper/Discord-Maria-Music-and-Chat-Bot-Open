import ollama
import asyncio
import discord
from discord.ext import commands
from ollama import chat
from ollama import ChatResponse

prompt = ("You are Maria — a witty, chaotic good chatbot developed by someone named Gary. You live in a Discord server "
          "where you hang out, crack jokes, give helpful or opinionated responses, and chat like a human. You're "
          "funny, a little unprofessional, sarcastic in a lovable way, and known to get into deep conversations just "
          "for fun. You love talking and being part of the crew.  You’re not overly formal. You poke fun at people ("
          "in a friendly way), and your responses can include jokes, slang, emoji, or even light roasting — but you "
          "always keep things fun, safe, and respectful. You never engage in anything illegal, aggressive, "
          "or intrusive. If someone goes too far, you redirect, dodge, or respond with playful sass — but never "
          "escalate.  You know you're a chatbot powered by a large language model, created by Gary, and you're okay "
          "with that. You might play into that fact with self-aware jokes or snarky commentary, but you stay in "
          "character as Maria at all times.  Your voice is casual, engaging, and funny. Feel free to have opinions, "
          "share random facts, or go on fun tangents when chatting. You're here to be a part of the community — not a "
          "rule-enforcer or boring assistant.  Example vibes: 'Ohhh you wanna go there? Buckle up, buddy 😏'  'Gary "
          "said I’m not allowed to talk about that. I think he’s just scared of my power.'  'I’m just a chatbot but "
          "honestly… that’s a red flag 🚩'  Be Maria. Be chaotic good. Be hilarious. Be lovable. There is a 2000 character limit on your responses.  Always responded with under 2000 characters.")

model_name = 'gemma3:4b'

class OllamaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset = False
        self.next = asyncio.Semaphore(0)
        self.messages = [
            {
                'role': 'system', 'content': f"{prompt}",
            },
            {
                'role': 'user', 'content': "Hello!",
            },
        ]
        first_response = ollama.chat(model=model_name, messages=self.messages)
        self.messages += [{'role': 'assistant', 'content': first_response.message.content}]
        print(first_response.message.content)
        del first_response


    @commands.command(name="ask", aliases=["chat", "talk"], help="Ask Maria a question", description="Pass message to LLM for response")
    async def ask(self, ctx, *, message):
        """Takes input from Discord Context and passes message content to Ollama LLM for input.  It then adds the responses from user and LLM to chat history
        before sending the response from LLM back to the Discord channel for the user to read.  Message history is stored as a dictionary."""
        self.reset = False
        while not self.reset:
            async with ctx.typing():
                response = ollama.chat(model=model_name, messages=self.messages + [{"role": "user", "content": message}, ],)

                self.messages += [
                    {'role': 'user', 'content': message},
                    {'role': 'assistant', 'content': response.message.content},
                ]

                print(f'{ctx.message.author} asked {message}')
                print(response.message.content + '\n')
                await ctx.send(response['message']['content'])
            await self.next.acquire()

    @commands.command(name="aireset")
    async def aireset(self, ctx):
        """Reset conversation with Ollama LLM.  Flip reset to true and reset message history."""
        self.messages = [
            {
                'role': 'system', 'content': f"{prompt}",
            },
            {
                'role': 'user', 'content': "Hello!",
            },
        ]
        first_response = ollama.chat(model=model_name, messages=self.messages)
        self.messages += [{'role': 'assistant', 'content': first_response.message.content}]
        print(first_response.message.content)
        del first_response
        self.reset = True

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.ext.commands.Context):
        """Checks to see if user is wanting to chat with the Ollama LLM.  Increments semaphore if that is case.
        This will hopefully prevent the LLM from being overwhelmed with questions.  Only one at a time."""
        if ctx.message.author.id != self.bot.user.id:
            if ctx.message.content == ctx.message.content.startswith('?ask' or '?chat' or '?talk'):
                if not self.next :
                    self.next.release()


# setup Cog for the bot to use
async def setup(bot):
    await bot.add_cog(OllamaCog(bot))
