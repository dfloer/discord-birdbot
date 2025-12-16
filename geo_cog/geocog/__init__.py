from .geocog import GeoCog


async def setup(bot):
    await bot.add_cog(GeoCog(bot))
