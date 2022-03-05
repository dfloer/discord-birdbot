import os
import sys

import discord
from redbot.core import commands

sys.path.append(os.getcwd())

from ebird_lookup import ebird_lookup as ebl
from ebird_stuff.ml import api as mlp
from ebird_stuff import transcode

from loguru import logger

class LookupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.typesense = ebl.TypeSenseSearch(api_key="changeMe!")
        self.typesense.connect()
        self.meili = ebl.MeilisearchSearch(api_key="changeMe!")
        self.meili.connect()
        self.ml_search = mlp.Search()
        self.transcoder = transcode.AudioTranscoder()
        self.max_transcode_factor = 4
        self.file_safety_factor = 0.95
        self.file_limits = {0: 8E6, 1: 50E6, 2: 50E6, 3: 100E6}

    def find_name(self, arg, backend):
        res = "No mapping found."
        if len(arg) <= 4 and arg not in ["Emu", "Kea", "Tui", "Mao", "Ou"]:
            res = f"{arg} is not valid (too short)."
        elif len(arg) > 4:
            res = f"{arg} is not valid (too long)."
        try:
            r = backend.code_to_names(arg)
            print("r:", r)
            if r["names"]:
                res = f"{arg.upper()} -> {', '.join(r['names'])}"
        except Exception:
            res = "Error: lookup failed."
        logger.info(f"lookupcog: find_name: arg: {arg}, backend: {backend}, result: {res}")
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
        logger.info(f"lookupcog: find_codes: arg: {arg}, backend: {backend}, result: {res}")
        return res

    def audio_transcoder(self, audio):
        output = self.transcoder.transcode_audio_meta(audio)
        return output

    def ml_asset_preview(self, url):
        logger.info(f"lookupcog: ml_asset_preview: input url: {url}")
        base_url = "https://cdn.download.ams.birds.cornell.edu/api/v1/asset/"
        # res = mlp.ml_assets_url_meta_filtered(url)
        # print(res)
        asset_id = mlp.get_asset_id(url)
        if asset_id is None:
            return discord.Embed(title="Error:", description="ML lookup failed, mis-formed URL?", color=0xFF0000), None, None
        try:
            res = self.ml_search.search_asset(asset_id=asset_id)
        except mlp.Search.NoResults:
            return discord.Embed(title="Error:", description=f"ML{asset_id} lookup failed. Are you sure it exists?", color=0xFF0000), None, None
        if res is None:
            return discord.Embed(title="Error:", description=f"ML{asset_id} lookup failed.", color=0xFF0000), None, None
        media_url = res.metadata["mediaUrl"]
        obs_ts = res.observation_timestamp
        prev = res.preview_url
        media_type = res.media_type
        media_extra = ''
        colour = 0xFF0000
        video_url = None
        ml_url = f"https://macaulaylibrary.org/asset/{res.asset_id}"

        audio_file = None
        if media_type == "Photo":
            colour = 0x007F00
        elif media_type == "Audio":
            media_url = res.media_url
            media_size = res.media_size
            max_size = int(self.file_limits[0] * self.file_safety_factor)
            if media_size > max_size and not self.transcoder:
                return discord.Embed(title=f"ML{res.asset_id}", url=ml_url, description="**Error:**\nMedia over maximum upload size.\n{media_url}", color=0xFF0000), None, None
            elif media_size > max_size * self.max_transcode_factor:
                ratio = round(media_size / max_size, 1)
                return discord.Embed(title=f"ML{res.asset_id}", url=ml_url, description=f"**Error:**\nQuality too low at {ratio}x reduction.\n{media_url}", color=0xFF0000), None, None
            try:
                source_file = res.media
            except mlp.APIBase.MediaStillProcessing:
                return discord.Embed(title="Error:", description="Media still processing. Try again later.", color=0xFF0000), None, None
            in_size = len(source_file.getvalue())
            output = self.audio_transcoder(source_file)
            audio_file = discord.File(output.data, filename=f"ML{asset_id}.mp3")
            media_extra = f"debug: {output.elapsed}s, in: {in_size}B, out: {output.size}B."
            colour = 0x007F7F
        elif media_type == "Video":
            # ML currently says file extensions can be MOV, MP4 and M4V.
            # This has not been tested with MOV of M4V files, but it should work.
            ext = [x for x in ('mov', "mp4", "m4v") if x in media_url.lower()]
            if ext:
                video_url = f"{media_url}/1280.{ext[0]}"
                print(f"Video url: {video_url}")
            colour = 0x7F7F00
        else:
            media_extra = f"{media_type} not supported yet."
            colour = 0x7f0000

        species_info = f"{res.common_name} (_{res.sci_name}_)"
        ml_id = f"ML{res.asset_id}"
        media_metadata = f"**{res.user_name}** at **{res.location[1]}** on **{obs_ts}**."
        desc = f"{species_info}\n{media_metadata}\n{media_extra}"
        embed = discord.Embed(title=ml_id, url=ml_url, description=desc, color=colour)
        if media_type == "Photo":
            embed.set_image(url=prev)
        elif media_type == "Audio":
            embed.set_image(url=prev)
        elif media_type == "Video":
            pass
        return embed, video_url, audio_file

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

    @commands.command(
        brief="Returns a ML image link from an asset link.",
        help="Returns a ML image link from an asset link.",
        usage="https://macaulaylibrary.org/asset/xxxxxxxxx",
    )
    async def ml(self, ctx, *, arg):
        # res = mlp.rewrite_url(arg)
        # if res:
        #     await ctx.send(res)
        # else:
        #     await ctx.send(f"Failed to parse: {arg}")
        embed, video_url, file = self.ml_asset_preview(arg)
        if embed:
            await ctx.send(embed=embed)
        if file:
            await ctx.send(file=file)
        if video_url:
            await ctx.send(video_url)
