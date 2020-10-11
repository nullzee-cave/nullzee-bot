import discord 
from discord.ext import commands
from discord.utils import get
#from helpers.colour import color
import traceback
import difflib
import sys
#from api_key import token, prefix
from datetime import datetime
import time
import asyncio
import os
import pymongo
import aiohttp
import json

class events(commands.Cog, name="events"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def newEvent(self, ctx, name:str, limit:int, level:int=0, whitelist:bool=False):
        with open('events.json') as f:
            events = json.load(f)
        events = {"name": name, "limit": limit, "whitelist": whitelist, "level": level, "host": ctx.author.id, "signups": {}, "in": {}, "out": {}, "winner": None, "blacklist": []}
        with open('events.json', 'w') as f:
            json.dump(events, f)
        await ctx.send("event set up")


    @commands.command()
    async def signup(self, ctx, IGN:str):
        with open('events.json') as f:
            events = json.load(f)
        with open('users.json') as f:
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
        events["signups"][str(ctx.author.id)] = IGN
        events["in"][str(ctx.author.id)] = IGN
        with open('events.json', 'w') as f:
            json.dump(events, f)
        channel = self.bot.get_guild(722421169311187037).get_channel(733621113829064735)
        await channel.send(IGN)
        await ctx.send(f"{ctx.author.mention}, you have signed up as {IGN}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def out(self, ctx, IGN:str):
        with open('events.json') as f:
            events = json.load(f)
        dc = (list(events["signups"].keys())[list(events["signups"].values()).index(IGN)])
        events["out"][dc] = IGN
        events["in"].pop(dc)
        await ctx.guild.get_channel(706920230089392260).send(f"{IGN} is out! {len(events['in'])} players left!")
        print(events["in"])
        if len(events["in"]) == 1:
            winner = list(events["in"].values())[0]
            dcwinner = ctx.guild.get_member(int(list(events["in"].keys())[0]))
            await ctx.guild.get_channel(706920230089392260).send(f"{dcwinner.mention} won as {winner}!!")
        with open('events.json','w') as f:
            json.dump(events, f)

    @commands.command()
    async def listPlayers(self, ctx):
        with open('events.json') as f:
            events = json.load(f)
        embed = discord.Embed(color=discord.Color.green())
        string = ''
        for player in events["signups"]:
            string += f"{events['signups'][player]}\n"
        embed.add_field(name="signups", value=string)
        await ctx.send(embed=embed)
            
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def remove(self, ctx, IGN:str):
        with open('events.json') as f:
            events = json.load(f)
        dc = (list(events["signups"].keys())[list(events["signups"].values()).index(IGN)])
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
        with open('events.json', 'w') as f:
            json.dump(events, f)
        await ctx.send(f"removed {IGN}")
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def delEvent(self, ctx):
        events = {}
        with open('events.json', 'w') as f:
            json.dump(events, f)
        await ctx.send("event deleted")
    
    @commands.command
    @commands.has_guild_permissions(manage_messages=True)
    async def blacklist(self, ctx, user:discord.Member):
        with open('events.json') as f:
            events = json.load(f)
        events["blacklist"].append(user.id)
        await ctx.send(f"Blacklisted {user.mention} from this event")
        with open('events.json', 'w') as f:
            json.dump(events, f)

def setup(bot):
    bot.add_cog(events(bot, False))