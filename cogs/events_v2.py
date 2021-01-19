from discord.ext import commands
import discord
import aiohttp
from api_key import userColl

LOG_CHANNEL = 760898316405571615


class Events(commands.Cog, name="events"):

    def __init__(self, bot):
        self.bot = bot
        self.hidden = False

    @commands.command()
    @commands.guild_only()
    async def participate(self, ctx, uname: str, timezone:str):
        if not timezone in ['1', '2']:
            raise commands.UserInputError
        timezone = timezone.upper()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.slothpixel.me/api/players/{uname}") as resp:
                if resp.status == 404:
                    return await ctx.send("That username does not exist in Minecraft.")
                data = await resp.json()
        if data["links"]["DISCORD"] != str(ctx.author):
            return await ctx.send(embed=discord.Embed(title=":x: Error :x:",
                                                      description="Account not linked. Click [here](https://gfycat.com/dentaltemptingleonberger) to see how to link your account",
                                                      colour=discord.Colour.red()))
        await userColl.update_one({"_id": str(ctx.author.id)}, {"$set": {"uname": uname, "timezone": timezone}})
        await ctx.guild.get_channel(LOG_CHANNEL).send(f"{ctx.author.mention} [{timezone}] - `{uname}`")
        await ctx.send(f"You have signed up as {uname} for event {timezone}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def getParticipants(self, ctx, k=None, v=None):
        query = {"uname": {"$exists": True}, k: v} if k and v else {"uname": {"$exists": True}}
        await ctx.send(embed=discord.Embed(description="\n".join(
            [f"<@{z['_id']}> [{z['timezone']}] - `{z['uname']}`" async for z in userColl.find(query)]),
                                           colour=discord.Colour.green()))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def clearParticipants(self, ctx):
        await userColl.update_many({}, {"$unset": {"uname": "", "timezone": ""}})
        await ctx.send("Successfully cleared all participants")


def setup(bot):
    bot.add_cog(Events(bot))
