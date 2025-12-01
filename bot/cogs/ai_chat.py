import discord
from discord.ext import commands
from bot.core.logger import logger
from bot.core.ai.supervisor import app
from langchain_core.messages import HumanMessage

class AiChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Ignore own messages
        if message.author == self.bot.user:
            return

        # 2. Ignore messages that are commands
        # Use get_context to determine if the message is a valid command.
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # 3. Check Triggers:
        # - Direct Message (DM)
        # - Mentioned (@BotName)
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions

        if not (is_dm or is_mentioned):
            return

        # 4. Invoke LangGraph App
        try:
            user_input = message.clean_content
            # If mentioned, clean_content usually handles stripping the mention,
            # but sometimes we might want to ensure the mention is removed or kept depending on context.
            # For now, passing the full clean content is fine.

            inputs = {"messages": [HumanMessage(content=user_input)]}

            # Run the graph
            # Since LangGraph is sync/async, app.invoke is sync by default?
            # We should check if we need ainvoke. app.compile() returns a CompiledGraph which has ainvoke.
            result = await app.ainvoke(inputs)

            # 5. Reply with the result
            # The result is the final state. We want the content of the LAST message.
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                response_text = last_message.content
                await message.reply(response_text)
            else:
                # Should not happen if agents return messages
                logger.warning("AI Agent returned no messages.")
                await message.reply("Thinking process complete, but I have no response.")

        except Exception as e:
            logger.error("Error in AiChatCog on_message", error=str(e))
            await message.reply("I encountered an error processing your request.")

def setup(bot: commands.Bot):
    bot.add_cog(AiChatCog(bot))
