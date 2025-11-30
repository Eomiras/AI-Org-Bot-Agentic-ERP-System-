from .cog import Media

async def setup(bot):
    await bot.add_cog(Media(bot))
