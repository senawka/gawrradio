import discord
import asyncio
import random
from discord.ext import commands
from yt_dlp import YoutubeDL

ITEMS_PER_PAGE = 10

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.playing = False
        self.loop = False
        self.current_song = None
        self.voice_channel = None
        self.YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}
        self.YDL_OPTIONS_PLAYLIST_LENGTH = {"flatplaylist": "True", "playlistend": 1}
        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }
        self.LINK_LIST = (
            "www.youtube.com",
            "youtube.com",
            "youtu.be",
            "m.youtube.com",
            "www.soundcloud.com",
            "soundcloud.com",
        )
        self.now_playing_image = "https://cdn.discordapp.com/emojis/996611634904703118.gif?size=64&quality=lossless"

    async def search(self, video, ctx):
        check = video.split("/")
        link = False
        playlist = False
        for i in self.LINK_LIST:
            if i in check:
                link = True
                break
        if link and check[-1].split("?")[0] == "playlist":
            playlist = True
        if playlist:
            asyncio.create_task(self.load_playlist(ctx, video))
        elif link:
            results = await self.bot.loop.run_in_executor(
                None, self.get_info, self.YDL_OPTIONS, video
            )
            song = {"source": results["url"], "title": results["title"]}
            self.queue.append(song)
            await self.send_queue(ctx, [song])
        else:
            source = await self.bot.loop.run_in_executor(
                None, self.get_info, self.YDL_OPTIONS, f"ytsearch:{video}"
            )
            results = source["entries"][0]
            song = {"source": results["url"], "title": results["title"]}
            self.queue.append(song)
            await self.send_queue(ctx, [song])

    async def play_music(self, ctx):
        if await self.user_is_connected_to_same_vc(ctx):
            if len(self.queue) > 0 or self.loop:
                self.playing = True
                if not self.loop:
                    self.current_song = self.queue[0]
                    await self.send_title(ctx)
                    self.queue.pop(0)
                self.voice_channel.play(
                    discord.FFmpegPCMAudio(
                        self.current_song["source"], **self.FFMPEG_OPTIONS
                    ),
                    after=lambda x: self.bot.loop.create_task(self.play_music(ctx)),
                )
        elif len(self.queue) == 0 or not self.voice_channel.is_playing():
            self.playing = False

    async def load_playlist(self, ctx, link):
        songs = []
        source = await self.bot.loop.run_in_executor(
            None, self.get_info, self.YDL_OPTIONS_PLAYLIST_LENGTH, link
        )
        playlist_length = source["playlist_count"]
        for i in range(playlist_length):
            source = await self.bot.loop.run_in_executor(
                None,
                self.get_info,
                {
                    "format": "bestaudio",
                    "noplaylist": "False",
                    "playliststart": i + 1,
                    "playlistend": i + 1,
                },
                link,
            )
            results = source["entries"][0]
            song = {"source": results["url"], "title": results["title"]}
            self.queue.append(song)
            songs.append(song)
            if not self.playing:
                await self.play_music(ctx)
        await self.send_queue(ctx, songs)

    async def delete_messages(self, ctx, amount):
        await ctx.channel.purge(
            limit=amount, check=lambda message: message.author == self.bot.user
        )

    async def send_title(self, ctx):
        if self.current_song:
            title = self.current_song["title"]
            embed = discord.Embed(title="Now playing", description=title)
            embed.set_thumbnail(url=self.now_playing_image)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No song is currently playing.")

    @staticmethod
    def get_info(parameters, link):
        return YoutubeDL(parameters).extract_info(link, download=False)

    @staticmethod
    async def send_queue(ctx, songs):
        message = ""
        for i in songs:
            title = i["title"]
            message += title + "\n"
        if message != "":
            output = str(f"```Queued up:\n{message}```")
            await ctx.send(output)

    async def user_is_connected_to_same_vc(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("```Must join a VC!```")
            return False

        if self.voice_channel is None:
            return False

        return ctx.author.voice.channel == self.voice_channel.channel

    async def join_voice_channel(self, ctx):
        if self.voice_channel is None:
            if ctx.author.voice is None:
                await ctx.send("```Must join a VC!```")
                return
            self.voice_channel = await ctx.author.voice.channel.connect()

    @commands.command(pass_context=True, aliases=["p"])
    async def play(self, ctx, *args):
        query = " ".join(args)

        if not self.voice_channel:
            if ctx.author.voice:
                self.voice_channel = await ctx.author.voice.channel.connect()
            else:
                await ctx.send("```Must join a VC!```")
                return

        if not await self.user_is_connected_to_same_vc(ctx):
            await ctx.send(
                f"```Must join the same VC as the bot! ({self.voice_channel.channel})```"
            )
            return

        await self.search(query, ctx)

        if not self.playing:
            await self.play_music(ctx)

    @commands.command(pass_context=True, aliases=["s"])
    async def skip(self, ctx):
        if await self.user_is_connected_to_same_vc(ctx) and self.playing:
            await ctx.send("```Skipping...```")
            self.loop = False
            self.voice_channel.stop()

    @commands.command(pass_context=True)
    async def pause(self, ctx):
        if (
            await self.user_is_connected_to_same_vc(ctx)
            and self.playing
            and self.voice_channel.is_playing()
        ):
            await ctx.send("```Pausing.```")
            self.voice_channel.pause()

    @commands.command(pass_context=True)
    async def resume(self, ctx):
        if (
            await self.user_is_connected_to_same_vc(ctx)
            and self.playing
            and self.voice_channel.is_paused()
        ):
            await ctx.send("```Resuming playback.```")
            self.voice_channel.resume()

    @commands.command(pass_context=True, aliases=["skipall"])
    async def clear(self, ctx):
        if await self.user_is_connected_to_same_vc(ctx) and self.playing:
            await ctx.send("```Skipping...```")
            self.queue = []
            self.loop = False
            self.voice_channel.stop()

    @commands.command(pass_context=True, aliases=["leave"])
    async def disconnect(self, ctx):
        if (
            await self.user_is_connected_to_same_vc(ctx)
            and self.voice_channel.is_connected()
        ):
            await ctx.send("```Cya!```")
            self.queue = []
            self.loop = False
            self.voice_channel.stop()
            await self.voice_channel.disconnect()
            self.voice_channel = None

    @commands.command(pass_context=True, aliases=["delete"])
    async def purge(self, ctx, amount=10):
        await self.delete_messages(ctx, int(amount))

    @commands.command(pass_context=True, aliases=["r"])
    async def remove(self, ctx, number):
        if await self.user_is_connected_to_same_vc(ctx):
            title = self.queue[int(number) - 1]["title"]
            message = str(f"```Removed from queue:\n{title}```")
            self.queue.pop(int(number) - 1)
            await ctx.send(message)

    @commands.command(pass_context=True, aliases=["q"])
    async def queue(self, ctx, page=1):
        if page < 1:
            await ctx.send("```Invalid page number.```")
            return

        total_pages = (len(self.queue) - 1) // ITEMS_PER_PAGE + 1
        if page > total_pages:
            await ctx.send("```Invalid page number.```")
            return

        start_index = (page - 1) * ITEMS_PER_PAGE
        end_index = start_index + ITEMS_PER_PAGE

        queue_page = self.queue[start_index:end_index]
        queue_list = [
            f"{start_index + i + 1}) {item['title']}"
            for i, item in enumerate(queue_page)
        ]
        queue_output = "\n".join(queue_list)

        output = f"```Queue (Page {page}/{total_pages}):\n{queue_output}```"
        message = await ctx.send(output)

        if total_pages > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"]

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", timeout=60.0, check=check
                    )
                except asyncio.TimeoutError:
                    break

                if str(reaction.emoji) == "⬅️":
                    page -= 1
                elif str(reaction.emoji) == "➡️":
                    page += 1

                await message.remove_reaction(reaction, user)

                if page < 1 or page > total_pages:
                    break

                start_index = (page - 1) * ITEMS_PER_PAGE
                end_index = start_index + ITEMS_PER_PAGE

                queue_page = self.queue[start_index:end_index]
                queue_list = [
                    f"{start_index + i + 1}) {item['title']}"
                    for i, item in enumerate(queue_page)
                ]
                queue_output = "\n".join(queue_list)

                output = f"```Queue (Page {page}/{total_pages}):\n{queue_output}```"
                await message.edit(content=output)

    @commands.command(pass_context=True)
    async def loop(self, ctx):
        if await self.user_is_connected_to_same_vc(ctx):
            self.loop = not self.loop
            if self.loop:
                title = self.current_song["title"]
                message = str(f"```Looping:\n{title}```")
            else:
                message = "```Unlooping.```"
            await ctx.send(message)

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Latency: {latency}ms")

    @commands.command(pass_context=True)
    async def shuffle(self, ctx):
        if await self.user_is_connected_to_same_vc(ctx):
            if len(self.queue) > 0:
                random.shuffle(self.queue)
                await ctx.send("```Queue shuffled!```")
            else:
                await ctx.send("```The queue is empty. Cannot shuffle.```")

    @commands.command(pass_context=True, aliases=["np"])
    async def now_playing(self, ctx):
        if self.current_song:
            await self.send_title(ctx)
        else:
            await ctx.send("No song is currently playing.")

async def setup(bot):
    await bot.add_cog(Music(bot))
