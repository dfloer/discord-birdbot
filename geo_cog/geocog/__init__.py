from .geocog import GeoCog
from . import geo_utils
import sys
import os

sys.path.append(os.getcwd())
from ebird_lookup import ebird_lookup


def setup(bot):
    bot.add_cog(GeoCog(bot))
