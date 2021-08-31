from redbot.core import commands
import discord
import sys
import os
import requests
import re
from io import BytesIO

sys.path.append(os.getcwd())
from .geo_utils import MapBox, GBIF, Tile, eBirdMap, get_token


class GeoCog(commands.Cog):
    def __init__(self, bot):
        self.mapbox_token = get_token()
        self.mapbox = MapBox(self.mapbox_token)
        self.gbif = GBIF()
        self.ebird = eBirdMap()

    @commands.command(
        brief="Gets a lat/lon from an address, or vice versa.",
        help="Gets a lat/lon from an address, or vice versa. Mapbox version",
        usage="[query]",
    )
    async def geocode(self, ctx, *, arg):
        res = self.mapbox.geocode(arg)
        await ctx.send(res)

    @commands.command(
        brief="Gets a test range map.",
        help="Gets a test range map. Just Bushtits from GBIF.",
        usage="[query]",
    )
    async def gimmeamap(self, ctx, *, arg):
        z = 0
        x = 0
        y = 0
        fmt = "jpg90"
        style = "satellite"
        high_res = True
        print("gimmeamap: ", arg)
        scientific_name, taxon_id = self.gbif.lookup_species(arg)
        if all((scientific_name, taxon_id)):

            print(scientific_name, taxon_id)
            mb = self.mapbox.get_tile(z, x, y, fmt, style, high_res)
            gb = self.gbif.get_hex_map(z, x, y, taxon_id, high_res=False)
            t1 = mb.composite(gb)
            desc = f"Source: GBIF, Mapbox. GBIF taxon id: {taxon_id}."
            embed = discord.Embed(
                title=scientific_name, description=desc, color=0x007F00
            )
            file = discord.File(t1.asbytes, filename=f"{taxon_id}.png")
            embed.set_image(url="attachment://image.png")
            await ctx.send(file=file, embed=embed)
        else:
            await ctx.send(f"Lookup of {arg} failed.")

    @commands.command(
        brief="Test GBIF species lookup.",
        help="Test GBIF species lookup.",
        usage="[query]",
    )
    async def glookup(self, ctx, *, arg):
        scientific_name, taxon_id = self.gbif.lookup_species(arg)
        if all((scientific_name, taxon_id)):
            await ctx.send(f"{arg} -> {scientific_name}, id: {taxon_id}.")
        else:
            await ctx.send("Lookup failed.")

    @commands.command(
        brief="Gets a lat/lon from an address, or vice versa.",
        help="Gets a lat/lon from an address, or vice versa. Mapbox version",
        usage="[query]",
    )
    async def ebirdmap(self, ctx, *, arg):
        species_code = "bushti"
        common_name = "Bushtit"
        scientific_name = "Psaltriparus minimus"
        res_img = self.ebird.get_range_map(species_code, 3)
        title = f"eBird range map for: Bushtit (_{scientific_name}_)."
        desc = "Any bird you want, as long as it's a Bushtit."

        d = BytesIO()
        res_img.save(d, "png")
        img = BytesIO(d.getvalue())

        embed = discord.Embed(title=title, description=desc, color=0x007F00)
        file = discord.File(img, filename=f"{species_code}.png")
        if res_img:
            await ctx.send(file=file, embed=embed)
        else:
            await ctx.send(f"Lookup of {arg} failed.")
