# Maria the Discord Chatbot
## Layout
1. main.py - Our main file that creates and runs the bot
2. env - Our environment variables for the bot
3. Cogs - Our folder for keeping cogs all in one place
## Setup
### Preliminary
- In order to get this bot up and running, you will first need at least Python 3.08 or above.<br>
- Get your envirnment established with a directory layout that you like.  For example: a new project repository or folder just for the bot somewhere you can easily access.<br>
- A Discord account is required.  Access to the Discord Developer portal and Discord Developer Settings for the Discord app.
### Dependencies
- Discord.py and the Discord package for Python
- PyNaCl package
- FFMPEG package and executable (open source full and essential should both work)
- Ollama package and executable
- A LLM model of your choice to run locally through Ollama
- YT-DLP package (make sure to get the latest version)
### Discord Portal
If you don't know how to setup an application through Discord, it is super simple: 
1. Head to the portal looking for the "Applications" section.
2. You will need to add a new application.
3. Generate a token if not already given to you.
4. SAVE THE TOKEN.  You will need this for the bot to access Discord.
5. Go to the OAuth2 section to create a link for the bot.  Do this by selecting bot and give it administration privelege.
6. Make sure the bot is private if you do not want others to use the bot.
7. Generate the invite link and invite the bot to your server.
### Installation
For the install, pull this repository into your project folder/directory.  Then, fill in your information in the .env file and maybe some in main.py (if you would like to make changes).  With the envirnment setup, major dependencies installed, and Discord ready, you should not be able to start the bot.  Simply type "python main.py" in the console of your virtual envirnment to run the bot. <br>

If you see errors, it is likely that your virtual envrinment is missing some smaller dependencies.  Make sure the packages being asked for by the imports are actually present in the virtual environment.  Work through the missing packages and errors until you see that the bot has successfully connected to Discord.  Once that happens, you have your very own Discord bot!
## Cogs
### Explanation
Cogs are like sets of functions that the bot can be asked to do or tools added to its belt.  It is done like this to keep the main.py tidy and short, but it also allows for the bot to be fully customizable.  If there is a cog that interests you add it, if not remove it.  You can even add cogs that others have made to provide even more functionality to the bot.
All you need is to setup the cog alongside the others in the folder.  The cogs that are currently available out of the box are:
1. MusicCog - Play, queue, pause, resume, autodisconnect, autoconnect, skip are all functions of this cog.  All also refer to the bots ability to join a voice channel to play YouTube videos and not just music.
2. OllamaCog - This cog is where the bot is able to have a genuine conversation with the server.  It is using Google's Gemini right now but can be swapped out for others by changing the model_name.  Simply type your prefix and ask to chat with the bot.  Response times depend on your machine and chosen model.  Function calling also depends on selected model.
3. MainCog - Basic commands such as flipping a coin, rolling dice, or fetching audit logs.  This file will likely change often and can be filled with many essential commands.
4. HelpCog - This cog contains the information regarding the available commands of the bot.  It is not yet automated and must be changed by hand.  It can also allow for the prefix to be changed during runtime.

## What Broke?
If you find that something is just not working for you or that a step is glossed over/missing, I implore you to notify me of the issue.  I will try to work through the issue with you and get you a cool chatbot to show off to your friends.
