import discord 
from discord.ext import commands
import json


class Events(commands.Cog, name="Events"):
    """The original events cog"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def new_event(self, ctx, name: str, limit: int, level: int = 0, whitelist: bool = False):
        # with open("events.json") as f:
        #     events = json.load(f)
        events = {
            "name": name,
            "limit": limit,
            "whitelist": whitelist,
            "level": level,
            "host": ctx.author.id,
            "signups": {},
            "in": {},
            "out": {},
            "winner": None,
            "blacklist": []
        }
        with open("events.json", "w") as f:
            json.dump(events, f)
        await ctx.send("event set up")

    @commands.command(name="signup")
    async def sign_up(self, ctx, ign: str):
        with open("events.json") as f:
            events = json.load(f)
        with open("users.json") as f:
            levels = json.load(f)
        if not events:
            return await ctx.send("There is currently no event.")
        if str(ctx.author.id) in events["signups"]:
            return await ctx.send("You have already signed up!")
        if len(events["signups"]) > events["limit"]:
            return await ctx.send("This event is full")
        if ctx.author.id in events["blacklist"]:
            return await ctx.send("You are not allowed to join this event")
        if events["whitelist"]:
            return await ctx.send("This event is private")
        if events["level"] > 0:
            try:
                if levels[str(ctx.author.id)]["level"] < events["level"]:
                    return await ctx.send("You are not a high enough level to participate in this event")
            except KeyError:
                return await ctx.send("You are not a high enough level to participate in this event")
        events["signups"][str(ctx.author.id)] = ign
        events["in"][str(ctx.author.id)] = ign
        with open("events.json", "w") as f:
            json.dump(events, f)
        channel = self.bot.get_guild(722421169311187037).get_channel(733621113829064735)
        await channel.send(ign)
        await ctx.send(f"{ctx.author.mention}, you have signed up as {ign}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def out(self, ctx, ign: str):
        with open("events.json") as f:
            events = json.load(f)
        dc = (list(events["signups"].keys())[list(events["signups"].values()).index(ign)])
        events["out"][dc] = ign
        events["in"].pop(dc)
        await ctx.guild.get_channel(706920230089392260).send(f"{ign} is out! {len(events['in'])} players left!")
        print(events["in"])
        if len(events["in"]) == 1:
            winner = list(events["in"].values())[0]
            dc_winner = ctx.guild.get_member(int(list(events["in"].keys())[0]))
            await ctx.guild.get_channel(706920230089392260).send(f"{dc_winner.mention} won as {winner}!!")
        with open("events.json", "w") as f:
            json.dump(events, f)

    @commands.command(name="listplayers")
    async def list_players(self, ctx):
        with open("events.json") as f:
            events = json.load(f)
        embed = discord.Embed(color=discord.Color.green())
        string = ""
        for player in events["signups"]:
            string += f"{events['signups'][player]}\n"
        embed.add_field(name="signups", value=string)
        await ctx.send(embed=embed)
            
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def remove(self, ctx, ign: str):
        with open("events.json") as f:
            events = json.load(f)
        dc = (list(events["signups"].keys())[list(events["signups"].values()).index(ign)])
        try:
            events["signups"].pop(dc)
        except:
            pass
        try:
            events["out"].pop(dc)
        except:
            pass
        try:
            events["in"].pop(dc)
        except:
            pass
        with open("events.json", "w") as f:
            json.dump(events, f)
        await ctx.send(f"removed {ign}")

    @commands.command(name="delevent")
    @commands.has_guild_permissions(manage_messages=True)
    async def del_event(self, ctx):
        events = {}
        with open("events.json", "w") as f:
            json.dump(events, f)
        await ctx.send("event deleted")
    
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def blacklist(self, ctx, user: discord.Member):
        with open("events.json") as f:
            events = json.load(f)
        events["blacklist"].append(user.id)
        await ctx.send(f"Blacklisted {user.mention} from this event")
        with open("events.json", "w") as f:
            json.dump(events, f)


def setup(bot):
    bot.add_cog(Events(bot, False))
