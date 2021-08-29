from redbot.core import commands
import sys
import os
sys.path.append(os.getcwd())

from ebird_lookup import ebird_lookup as ebl

class LookupCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.typesense = ebl.TypeSenseSearch(api_key="changeMe!")
        self.typesense.connect()
        self.meili = ebl.MeilisearchSearch(api_key="changeMe!")
        self.meili.connect()

    def find_name(self, arg, backend):
        res = "No mapping found."
        if len(arg) != 4 and arg not in ['Emu', 'Kea', 'Tui', 'Mao', 'Ou']:
            res = f"{arg} is not valid (too short)."
        try:
            r = backend.code_to_names(arg)
            print("r:", r)
            if r["names"]:
                res = f"{arg} -> {', '.join(r['names'])}"
        except Exception:
            res = "Error: lookup failed."
        return res

    def find_codes(self, arg, backend):
        res = "No mapping found."
        try:
            r = backend.name_to_codes(arg, "all")
            print(r)
            if r["short_codes"]:
                res = f"{r['name']} -> {', '.join(r['short_codes'])}"
        except Exception:
            res = "Error: lookup failed."
        return res

    @commands.command(
        brief="Gets the 4-letter code for a bird's name. Typesense version.",
        help="Gets the 4-letter code for a bird's name. Typesense version.",
        usage="[common name]",
    )
    async def code(self, ctx, *, arg):
        res = self.find_codes(arg, self.typesense)
        await ctx.send(res)

    @commands.command(
        brief="Gets the name for a bird from its 4-letter code. Typesense version.",
        help="Gets the name for a bird from its 4-letter code. Typesense version.",
        usage="[code]",
    )
    async def name(self, ctx, *, arg):
        res = self.find_name(arg, self.typesense)
        await ctx.send(res)

    @commands.command(
        brief="Gets the 4-letter code for a bird's name. Meilisearch version.",
        help="Gets the 4-letter code for a bird's name. Meilisearch version.",
        usage="[common name]",
    )
    async def code2(self, ctx, *, arg):
        res = self.find_codes(arg, self.meili)
        await ctx.send(res)

    @commands.command(
        brief="Gets the name for a bird from its 4-letter code. Meilisearch version.",
        help="Gets the name for a bird from its 4-letter code. Meilisearch version.",
        usage="[code]",
    )
    async def name2(self, ctx, *, arg):
        res = self.find_name(arg, self.meili)
        await ctx.send(res)

    @commands.command()
    async def echo(self, ctx, *, arg):
        await ctx.send(f"echo: {arg}")
