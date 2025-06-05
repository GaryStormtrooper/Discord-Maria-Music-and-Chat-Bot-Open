import asyncio
import functools
import itertools
import math
import random
import os
import discord
from discord.ext import commands
from discord import utils
import utils
import sys
import yt_dlp as youtube_dl
from async_timeout import timeout

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: discord.ext.commands.Context, source: discord.FFmpegPCMAudio, *, data: dict,
                 volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: discord.ext.commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()
        print("Create1")
        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        print("Create2")
        data = await loop.run_in_executor(None, partial)
        print("Create3")

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        print("Create4")
        webpage_url = process_info['webpage_url']
        print("Create5")
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        print("Create6")
        processed_info = await loop.run_in_executor(None, partial)
        print("Create7")

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        try:
            print("Create8")
            new_source = cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)
            print("Create9")
        except discord.ClientException:
            raise YTDLError("FFmpegPCMAudio Subprocess failed to be created. Is one already running?")
        return new_source

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: discord.ext.commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()
        self.NowPlayingMessage = None
        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    async def resume_music(self):
        if self.current and not self.voice.is_playing():
            self.voice.play(self.current.source, after=self.play_next_song)
            # optionally reset other settings hre.

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    async def is_in_channel(self):
        guild = self._ctx.guild
        if guild.voice_client is None:
            await self._ctx.send('Not connected to any voice channel.', ephemeral=True)
            return False
        else:
            return True

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value
        try:
            self.voice_client.source.volume = float(value) / 100.0
        except Exception as e:
            pass

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()
            print('Player1')
            # check if looping or
            if not self.loop or self.current is None:
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(20):  # Wait for a few seconds
                        print('Player2')
                        self.current = await self.songs.get()
                        print('Player3')
                except asyncio.TimeoutError:

                    self.bot.loop.create_task(self.stop())
                    return False
            print('Player4')
            self.current.source.volume = self._volume
            try:
                print('Player5')
                self.voice.play(self.current.source, after=self.play_next_song)
                if self.is_playing:
                    print('Is playing')
                print('Player6')
            except Exception as e:
                print('Error occured when trying to play song {}'.format(e))
                await self.stop()
                return
            print('Player7')
            self.NowPlayingMessage = await self.current.source.channel.send(embed=self.current.create_embed())
            print('Player8')

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))
        #if self.current and not self.is_playing :
        #    print('Setting Next')
        #    self.next.set()
        #    print('Next Set')
        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()
        # proper cleanup
        if self.voice:
            self.voice.stop()
            await self.voice.disconnect()
            self.voice = None
        if self.audio_player:
            self.audio_player.cancel()
            self.audio_player = None


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: discord.ext.commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: discord.ext.commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: discord.ext.commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: discord.ext.commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    # checks for sudden disconnect and reconnects the bot to the voice channel
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id and before.channel is not None and after.channel is None:
            voice_state = self.get_voice_state(before.guild.id)
            if voice_state and voice_state.is_playing:
                successfully_reconnected = await self.reconnect_voice_client(before.guild.id, before.channel)
            if successfully_reconnected:
                await voice_state.resume_music()
            if voice_state and not voice_state.is_playing:
                await voice_state.stop()
                del self.voice_states[before.guild.id]

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: discord.ext.commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()
        await ctx.send("Joining Voice channel", ephemeral=True)

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: discord.ext.commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: discord.ext.commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    async def _volume(self, ctx: discord.ext.commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='restart')
    async def restart(self, ctx: discord.ext.commands.Context):
        # Bandaid fix a long time ago for the player, it is not necessary now, but it is still here.
        await ctx.send('Restarting bot...')
        os.execv(sys.executable, ['python3'] + sys.argv)

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: discord.ext.commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: discord.ext.commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.send("Paused the audio.")
            #await ctx.message.add_reaction('?')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: discord.ext.commands.Context):
        """Resumes a currently paused song."""

        #if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
        if ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.send("Resuming currently paused song")

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: discord.ext.commands.Context):
        """Stops playing song and clears the queue."""
        ctx.voice_state.songs.clear()

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.', ephemeral=True)

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]
        await ctx.send('Stopping bot')

    @commands.command(name='skip')
    async def _skip(self, ctx: discord.ext.commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...', ephemeral=True)

        voter = ctx.author
        if voter == ctx.voice_state.current.requester:
            await ctx.send('Author requested to Skip Song')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.send('Skipping song,currently at **{}/3**'.format(total_votes))
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.', ephemeral=True)

    @commands.command(name='queue')
    async def _queue(self, ctx: discord.ext.commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: discord.ext.commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.send('Shuffled Playlist')

    @commands.command(name='remove')
    async def _remove(self, ctx: discord.ext.commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.send("removing song at index %d" % (index))

    @commands.command(name='loop')
    async def _loop(self, ctx: discord.ext.commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        if (ctx.voice_state.loop == True):
            await ctx.send("looping playlist")
        if (ctx.voice_state.loop == False):
            await ctx.send("unlooping playlist")

    @commands.command(name='play', description='plays a song')
    async def _play(self, ctx: discord.ext.commands.Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """
        print("Play1")
        #if not ctx.voice_state.voice or not ctx.voice_state.is_in_channel():
        if not ctx.voice_state.voice:
            print("Play2")
            await ctx.invoke(self._join)

        if ctx.voice_state.audio_player.done():
            print("Play3")
            ctx.voice_state.audio_player = self.bot.loop.create_task(ctx.voice_state.audio_player_task())
            print("Play4")
            await ctx.send("Restarted player.", ephemeral=True)

        async with ctx.typing():
            try:
                print("Play5")
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                print("Play6")

            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                print("Play7")
                song = Song(source)
                print("Play8")

                await ctx.voice_state.songs.put(song)
                print("Play9")
                await ctx.send('Enqueued {}'.format(str(source)))
                print("Play10")

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: discord.ext.commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

# setup Cog for the bot to use
async def setup(bot):
    await bot.add_cog(MusicCog(bot))