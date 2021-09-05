from .lookupcog import LookupCog


def setup(bot):
    bot.add_cog(LookupCog(bot))