from .cog import Compliance

async def setup(bot):
    await bot.add_cog(Compliance(bot))
