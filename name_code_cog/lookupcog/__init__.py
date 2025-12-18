from .lookupcog import LookupCog


async def setup(bot):
    await bot.add_cog(LookupCog(bot))