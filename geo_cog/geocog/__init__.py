from .geocog import GeoCog

def setup(bot):
    bot.add_cog(GeoCog(bot))
