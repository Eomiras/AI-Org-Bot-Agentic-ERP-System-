import discord
from discord.ext import commands
from discord import option
import asyncio
import os
from bot.core.logger import logger

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="join", description="Joins your voice channel.")
    async def join(self, ctx: discord.ApplicationContext):
        if not ctx.author.voice:
            await ctx.respond("❌ You are not in a voice channel.", ephemeral=True)
            return

        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

        await ctx.respond(f"✅ Joined **{channel.name}**.")

    @discord.slash_command(name="leave", description="Leaves the voice channel.")
    async def leave(self, ctx: discord.ApplicationContext):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.respond("👋 Disconnected.")
        else:
            await ctx.respond("I am not in a voice channel.", ephemeral=True)

    @discord.slash_command(name="announce", description="Announces a message via TTS.")
    @option("text", description="The text to speak")
    async def announce(self, ctx: discord.ApplicationContext, text: str):
        if not ctx.voice_client:
            await ctx.respond("❌ I am not in a voice channel. Use `/join` first.", ephemeral=True)
            return

        await ctx.defer()

        # 1. Enqueue Job
        output_filename = f"tts_{ctx.interaction.id}.wav"
        output_path = f"data/audio/{output_filename}"

        try:
            # We enqueue the job and wait for the result path
            # In Arq, enqueue_job returns a Job instance.
            # We can use job.result() to wait, but that blocks async flow if not careful?
            # Arq's job.result() is an async polling method.

            job = await self.bot.arq.enqueue_job("generate_tts", text, output_path=output_path)

            # Wait for result (with timeout)
            # This is "Enterprise" - we wait for the worker to finish.
            result = await job.result(timeout=10, poll_delay=0.5)

            if not os.path.exists(result):
                await ctx.respond("❌ Worker finished but file was not found.")
                return

            # 2. Play Audio
            # FFmpegPCMAudio requires ffmpeg installed.
            source = discord.FFmpegPCMAudio(result)

            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            ctx.voice_client.play(source, after=lambda e: logger.info(f"Finished playing {result}"))

            await ctx.respond(f"📣 **Announcement:** {text}")

        except asyncio.TimeoutError:
            await ctx.respond("❌ TTS Generation timed out.")
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            await ctx.respond("❌ An error occurred while generating audio.")

def setup(bot):
    bot.add_cog(VoiceCog(bot))
