import discord
from discord.ext import commands
from discord import option
from bot.core.knowledge.ingest import add_document
from bot.core.knowledge.vector_db import get_retriever

class KnowledgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @commands.slash_command(name="ask", description="Search the knowledge base.")
    @option("question", description="The question or topic to search for")
    async def ask(self, ctx: discord.ApplicationContext, question: str):
        await ctx.defer()
        try:
            retriever = get_retriever()
            # LangChain retrievers return list of Document objects
            results = retriever.invoke(question)

            if not results:
                await ctx.respond("No relevant records found in the knowledge base.")
                return

            response_lines = ["Found these relevant records:"]
            for i, doc in enumerate(results[:3], 1):
                # Clean up newlines for cleaner display, or keep as is.
                # Keeping as is but limiting length might be wise if chunks are huge,
                # but chunks are ~1000 chars, which fits in Discord msg (2000 chars total limit might be hit).
                # We'll truncate if necessary or send multiple messages.
                # For now, let's assume 3 chunks of 1000 chars might exceed one message.
                # However, usually top 3 won't be full 1000 chars each.
                # Let's format it carefully.

                content = doc.page_content.strip()
                # Simple truncation for display safety if needed,
                # but user asked for "raw text found".
                # Let's hope it fits or Discord handles it (it won't handle >2000 automatically).
                # We will truncate each chunk to ~600 chars to be safe for 3 items.
                if len(content) > 600:
                    content = content[:600] + "..."

                response_lines.append(f"{i}. {content}")

            final_response = "\n".join(response_lines)

            if len(final_response) > 2000:
                # If still too long, send as file or truncate further.
                # Fallback: just send the first one or split.
                # For simplicity, we truncate the whole message.
                final_response = final_response[:1997] + "..."

            await ctx.respond(final_response)

        except Exception as e:
            await ctx.respond(f"❌ Error searching knowledge base: {str(e)}")

def setup(bot):
    bot.add_cog(KnowledgeCog(bot))
