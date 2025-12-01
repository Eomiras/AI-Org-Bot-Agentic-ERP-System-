import discord
from discord.ext import commands, tasks
from discord import option
import os
import shutil
import json
import redis.asyncio as redis
import asyncio
from bot.core.knowledge.ingest import add_document
from bot.core.knowledge.vector_db import get_retriever
from bot.core.logger import logger
from bot.core.config import settings

class KnowledgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis_listener.start()

    def cog_unload(self):
        self.redis_listener.cancel()

    @tasks.loop(seconds=1.0)
    async def redis_listener(self):
        # We listen to Redis events to report back to Discord
        try:
            r = redis.Redis.from_url(settings.redis_url)
            pubsub = r.pubsub()
            await pubsub.subscribe("ingestion_events")

            # This loop blocks until message arrives or connection breaks
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await self.handle_ingestion_event(data)
                    except Exception as json_err:
                        logger.error(f"Redis JSON Error: {json_err}")

        except Exception as e:
            logger.error(f"Redis Listener Connection Error: {e}")
            await asyncio.sleep(5)

    @redis_listener.before_loop
    async def before_redis_listener(self):
        await self.bot.wait_until_ready()

    async def handle_ingestion_event(self, data):
        channel_id = data.get("channel_id")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.warning(f"Could not find channel {channel_id} to report ingestion.")
            return

        filename = data.get("filename", "Unknown Asset")

        if data["status"] == "SUCCESS":
            chunks = data.get("chunks", 0)
            msg = (
                f"🛡️ **SHIELD OPERATOR REPORT**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ **PROTOCOL UPDATE COMPLETE**\n"
                f"**Asset:** `{filename}`\n"
                f"**Status:** `INTEGRITY_VERIFIED`\n"
                f"**Vector Injection:** {chunks} segments grounded in Hive Mind.\n"
                f"*The Oracle is now updated.*"
            )
            await channel.send(msg)

        elif data["status"] == "PII_CONTAMINATION":
            hits = data.get("pii_redacted", 0)
            msg = (
                f"🛡️ **SHIELD OPERATOR ALERT**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🛑 **COMPLIANCE MANDATE ENFORCED**\n"
                f"**Asset:** `{filename}`\n"
                f"**Status:** `INGESTION_ABORTED`\n"
                f"**Reason:** PII Contamination Detected ({hits} instances).\n"
                f"*Audit Trail logged. Admin notification sent.*"
            )
            await channel.send(msg)

        else:
            reason = data.get("reason", "Unknown Error")
            await channel.send(f"❌ **Ingestion Failed:** {reason}")

    @commands.slash_command(name="learn", description="Add text to the bot's knowledge base (Admin only).")
    @commands.has_permissions(administrator=True)
    @option("text", description="The text to learn")
    async def learn(self, ctx: discord.ApplicationContext, text: str):
        await ctx.defer(ephemeral=True)
        try:
            num_chunks = add_document(text, metadata={"source": "manual_entry", "author_id": ctx.author.id})
            await ctx.respond(f"✅ Successfully ingested {num_chunks} chunks into the knowledge base.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Failed to ingest text: {str(e)}", ephemeral=True)

    @commands.slash_command(name="ingest", description="Upload a document (PDF/TXT) for the Shield Operator to analyze (Admin only).")
    @commands.has_permissions(administrator=True)
    @option("file", description="The document file")
    @option("type", description="Document type (e.g., lore, protocol)", default="general")
    async def ingest(self, ctx: discord.ApplicationContext, file: discord.Attachment, type: str):
        """
        Uploads a file, saves it to temp, and queues it for the Ingestion Worker.
        """
        if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
            await ctx.respond("❌ Only PDF or TXT files are supported.", ephemeral=True)
            return

        await ctx.defer()

        # 1. Save File
        temp_dir = "data/temp/ingestion"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{ctx.interaction.id}_{file.filename}")

        try:
            await file.save(file_path)

            # 2. Enqueue Job
            metadata = {
                "source": file.filename,
                "author_id": ctx.author.id,
                "channel_id": ctx.channel_id,
                "type": type,
                "upload_timestamp": ctx.interaction.created_at.isoformat()
            }

            # Note: We must ensure self.bot.arq exists (set up in main.py)
            await self.bot.arq.enqueue_job("ingest_task", file_path, metadata)

            await ctx.respond(f"🛡️ **SHIELD OPERATOR:** Asset `{file.filename}` received. Ingestion Protocol initiated. PII Scan pending.")

        except Exception as e:
            logger.error(f"Ingestion Queue Error: {e}")
            await ctx.respond("❌ Failed to queue ingestion job.")

    @discord.slash_command(name="ask", description="Search the knowledge base.")
    @option("question", description="The question or topic to search for")
    async def ask(self, ctx: discord.ApplicationContext, question: str):
        await ctx.defer()
        try:
            retriever = get_retriever()
            results = retriever.invoke(question)

            if not results:
                await ctx.respond("No relevant records found in the knowledge base.")
                return

            response_lines = ["Found these relevant records:"]
            for i, doc in enumerate(results[:3], 1):
                content = doc.page_content.strip()
                if len(content) > 600:
                    content = content[:600] + "..."

                response_lines.append(f"{i}. {content}")

            final_response = "\n".join(response_lines)

            if len(final_response) > 2000:
                final_response = final_response[:1997] + "..."

            await ctx.respond(final_response)

        except Exception as e:
            await ctx.respond(f"❌ Error searching knowledge base: {str(e)}")

def setup(bot):
    bot.add_cog(KnowledgeCog(bot))
