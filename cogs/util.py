from discord.ext import commands, tasks
from random import randint
from helpers.utils import min_level
import json
import asyncio
import discord
import aiohttp
import requests
import random
from discord.ext.commands.cooldowns import BucketType
import time
import datetime
from api_key import moderationColl
from helpers.utils import Embed

class util(commands.Cog, name="Other"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.autotogglestatus.start()
        self.autoSuggestions.start()
        self.last_update = 0
        self.updateSubCount()

    def updateSubCount(self):
        if time.time() - self.last_update > 600:
            self.sub_count = requests.get("https://www.googleapis.com/youtube/v3/channels?part=statistics&id=UCvltzrCoxXIlmqG2VUvV1WA&key=YT_API_KEY").json()["items"][0]["statistics"]
            self.last_update = time.time()

    @commands.command()
    async def subcount(self, ctx):
        await ctx.send(embed=discord.Embed(title="Nullzee's YouTube stats", description=f"Subscribers: {int(self.sub_count['subscriberCount']):,}\nTotal Views: {int(self.sub_count['viewCount']):,}\nVideo count: {int(self.sub_count['videoCount']):,}", color=0x00FF00, url="https://youtube.com/nullzee").set_thumbnail(url="https://cdn.discordapp.com/avatars/165629105541349376/2d7ff05116b8930a2fa2bf22bdb119c7.webp?size=1024"))
        self.updateSubCount()

    @commands.command()
    async def appeal(self, ctx, _id: str, *, reason:str=None):
        punishment = await moderationColl.find_one({"id": _id})
        if not punishment:
            return await ctx.send("Could not find a punishment with that ID")
        if punishment["offender_id"] != ctx.author.id:
            return await ctx.send("You can only appeal your own punishments")
        location = punishment["message"].split('-')
        print(location)
        msg = await self.bot.get_guild(int(location[0])).get_channel(int(location[1])).fetch_message(int(location[2]))
        embed = discord.Embed(title="Punishment appeal", url=msg.jump_url, description=reason, colour=discord.Colour.orange())
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await self.bot.get_guild(int(location[0])).get_channel(771061232642949150).send(embed=embed)
        await ctx.send("Punishment appeal submitted.")


    @commands.command()
    @commands.cooldown(1, 900, BucketType.guild)
    @commands.check(min_level(20))
    async def suggest(self, ctx, *, answer:str):
        """Log a suggestion for the server"""
        with open('suggestions.json') as f:
            suggestions = json.load(f)
        suggestion = await Embed(ctx.author, description=answer, color=0x00FF00).user_colour()
        suggestion.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        sugChannel = self.bot.get_guild(667953033929293855).get_channel(667959037265969171)
        sugmsg = await sugChannel.send("<@&738691450417709077>", embed=suggestion)
        suggestions[sugmsg.id] = {"stage_two": False}
        with open('suggestions.json', 'w') as f:
            json.dump(suggestions, f)
        await sugmsg.add_reaction(u"\u2705")
        await sugmsg.add_reaction(u"\u274E")
        await ctx.send(ctx.author.mention + ", suggestion logged, check <#667959037265969171> to see its progress", delete_after=5)
        await ctx.message.delete()

    @tasks.loop(minutes=2)
    async def autoSuggestions(self):
        with open('suggestions.json') as f:
            suggestions = json.load(f)

        #for i in [z for z in suggestions if not z["stage_two"]]:
        killList = []
        for i in suggestions:
            if not suggestions[i]["stage_two"]:
                try:
                    msg = await self.bot.get_guild(667953033929293855).get_channel(667959037265969171).fetch_message(i)
                    upvotes = [z.count for z in msg.reactions if str(z.emoji) == '✅']
                    downvotes = [z.count for z in msg.reactions if str(z.emoji) == '❎']
                    karma = upvotes[0] - downvotes[0]
                    if karma > 15:
                        await self.bot.get_guild(667953033929293855).get_channel(738506620098576434).send(embed=msg.embeds[0])
                        suggestions[i]["stage_two"] = True
                except:
                    pass
            else:
                killList.append(i)
        for i in killList:
            del suggestions[i]
        with open('suggestions.json', 'w') as f:
            json.dump(suggestions, f)


    @commands.command()
    async def members(self, ctx):
        """Displays the number of members in the server"""
        await ctx.send(str(len(ctx.guild.members)))
    @commands.command()
    async def ping(self, ctx):
        """Pings the bot to show latency"""
        embed = discord.Embed(title="Pong!", description=f"That took {round(100*self.bot.latency)} ms", color=0x00FF00)
        # await ctx.send(f"Pong!\n~{self.bot.latency} (seconds)")
        embed.set_thumbnail(url="https://i.gifer.com/fyMe.gif")
        # await ctx.send(f"Pong! :ping_pong: \nThat took {round(100*self.bot.latency)}ms :wind_blowing_face:")
        await ctx.send(embed=embed)
        # await ctx.message.delete()




    @commands.command(aliases = ['commands'])
    async def help(self, ctx, cog:str=None):
        """Displays the help command
        Anything in angled brackets <> is a required argument. Square brackets [] mark an optional argument"""
        prefix = "-"
        if not cog:
            embed = discord.Embed(title="Help", description=f"use `{prefix}help [category|command]` for more info", color=0x00FF00)
            embed.set_footer(text=f"Created by pjones123#6025")
            cog_desc = ''
            for x in self.bot.cogs:
                if not self.bot.cogs[x].hidden:
                    cmd = ''
                    cog_desc += f"__**{x}**__: {self.bot.cogs[x].__doc__}\n"
                    for y in self.bot.get_cog(x).get_commands():
                        if not y.hidden:
                            cmd += f"`{prefix}{y}`,  "
                    embed.add_field(name=f"__**{x}**__: {self.bot.cogs[x].__doc__}", value=cmd, inline=False)
            if not isinstance(ctx.channel, discord.channel.DMChannel):
                await ctx.send("**:mailbox_with_mail: You've got mail**")
            await ctx.author.send(embed=embed)
        else:
            found = False
            cog = cog.lower()
            for x in self.bot.cogs:
                if x.lower() == cog:
                    #title="Help", description=f"**Category {cog[0]}:** {self.bot.cogs[cog[0]].__doc__}", 
                    embed = discord.Embed(title="Help", color=0x00FF00)
                    scog_info = ''
                    for c in self.bot.get_cog(x).get_commands():
                        if not c.hidden:
                            scog_info += f"\n`{prefix}{c.name}`: {c.help}\n"
                    embed.add_field(name=f"\n{cog} Category:\n{self.bot.cogs[cog].__doc__}\n ", value=f"\n{scog_info}\n", inline=False)
                    found = True
                            
            if not found:
                for x in self.bot.cogs:
                    for c in self.bot.get_cog(x).get_commands():
                        if c.name.lower() == cog:
                            embed = discord.Embed(color=0x00FF00)
                            embed.add_field(name=f"{c.name}: {c.help}", value=f"Usage:\n `{prefix}{c.qualified_name} {c.signature}`")
                            found = True
            if not found:
                embed = discord.Embed(description="Command not found. Check that you have spelt it correctly and used capitals where appropriate")
            await ctx.author.send(embed=embed)
            if not isinstance(ctx.channel, discord.channel.DMChannel):
                await ctx.send("**:mailbox_with_mail: You've got mail**")

    @commands.command(aliases = ['boost'])
    async def nitro(self, ctx):
        embed = discord.Embed(title="Considering boosting the server?", color=0xfb00fd)
        embed.add_field(name="`For Nitro Boosting You Can Get`", value="""- Access to <#674311689738649600>
- A message posted in <#714073835791712267>
- The Nitro Booster (rich) role
- Role is positioned under @Null
""", inline=False)
        embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/PbC_AHw6x6OR_5a6hpvuLTP6nBEnpc5e-ftbgOx9oks/https/i.ytimg.com/vi/ZyX7U78keu0/maxresdefault.jpg?width=960&height=540")
        await ctx.send(embed=embed)
        await ctx.message.delete()


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 667953033929293855:
            channel = member.guild.get_channel(667955504651304999)
            await member.add_roles(member.guild.get_role(738080587000184923))
            await channel.send(f"Welcome to Nullzee's Cave, {member.mention}, You will be able to talk after 10mins, please use this time to look at the <#667966078596546580> and ensure you understand them. :heart: :wave:")


    @tasks.loop(minutes=30)
    async def autotogglestatus(self):
        rand = randint(0, 10)
        watching = ["discord.gg/nullzee", "twitch.tv/nullzeelive"]
        playing = ["with -help", "with Nullzee", "Hypixel Skyblock"]
        rand = randint(1, 2)
        if rand == 1:
	        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watching)))
        elif rand == 2:
            await self.bot.change_presence(activity=discord.Game(name=random.choice(playing)))

    @commands.command()
    async def report(self, ctx, message_id: int, *, reason:str=None):
        await ctx.message.delete()
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("Could not find that message")
        if not message:
            return await ctx.send("Could not find that message")
        embed = discord.Embed(title="New report", colour=discord.Color.red(), url=message.jump_url, description=f"reason: {reason}" if reason else "").add_field(name="Message Content", value=message.content, inline=False).add_field(name="reported by", value=f"{ctx.author.mention} ({ctx.author})", inline=False).set_author(name=message.author, icon_url=message.author.avatar_url)
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
        await ctx.guild.get_channel(771061232642949150).send(embed=embed)
        await ctx.author.send("Your report has been submitted. For any further concerns, do not hesitate to contact a staff member")

    @commands.command(hidden=True)
    @commands.has_guild_permissions(administrator=True)
    async def manualtogglestatus(self, ctx):
        rand = randint(0, 10)
        watching = ["discord.gg/nullzee", "twitch.tv/nullzeelive"]
        playing = ["with -help", "with Nullzee", "Hypixel Skyblock"]
        rand = randint(1, 2)
        if rand == 1:
	        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watching)))
        elif rand == 2:
            await self.bot.change_presence(activity=discord.Game(name=random.choice(playing)))


    @commands.command()
    @commands.cooldown(2, 60, BucketType.user)
    async def claimroles(self, ctx, ign: str):
        """Claim roles for in-game achievement"""
        if ctx.channel.id != 676693868741263381:
            return await ctx.send("go to <#676693868741263381> for that!")
        await ctx.trigger_typing()
        #key = "c78026a2-8180-49d9-8564-c255fe1b53fb"
        #key = "e2bede711-9481-43d1-81fb-91cc8b7d9d23"
        key = "3a8c518e-7bdc-4745-a9d8-1268cc511c47"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{ign}") as resp:
                    mojang = await resp.json()
            uuid = mojang["id"]
        except (aiohttp.ContentTypeError, KeyError):
            return await ctx.send(f"{ctx.author.mention}, that username could not be found")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/player?uuid={uuid}&key={key}") as resp:
                dc = await resp.json()
        failRepsonses = [f"{str(ctx.author)} doesn't know how to claim roles smh", f"{str(ctx.author)} messed up somehow ¯\_(ツ)_/¯", "blame pjones123#6025 if something messes up"]
        try:
            if dc["player"]["socialMedia"]["links"]["DISCORD"] != str(ctx.author):
                try:
                    embed = discord.Embed(title=":no_entry_sign: Error!", description="""In order to automatically claim your roles, you must first link your discord account to your hypixel profile. If you do not know how to do this, refer to the gif below for instructions

                    Additionally, you must turn on your skyblock api, which can be accessed in the Skyblock Menu ⇒ Settings ⇒ API Settings.

                    Make sure you check every option. This includes the Bank API which can be turned on in Settings ⇒ Island Settings ⇒ Bank API""", color=0xff0000)
                    embed.set_thumbnail(url="https://yt3.ggpht.com/-G0UwZhD1hRI/AAAAAAAAAAI/AAAAAAAAAAA/Q5bg4hzv6C0/s900-c-k-no/photo.jpg")
                    await ctx.author.send(embed=embed)
                    await ctx.author.send("https://gfycat.com/dentaltemptingleonberger")
                    await ctx.message.delete()        
                    return await ctx.send(embed=discord.Embed(title=":no_entry_sign: Error!", description="Could not verify your identity. I've DMed you info", color=0xff0000).set_footer(text=random.choice(failRepsonses), icon_url=ctx.author.avatar_url))    
                except discord.Forbidden:
                    return await ctx.send("Could not verify your identity. Please allow DMs from members of this server then try again", delete_after=5)
                    await ctx.message.delete()
        except KeyError:
                try:
                    embed = discord.Embed(title=":no_entry_sign: Error!", description="""In order to automatically claim your roles, you must first link your discord account to your hypixel profile. If you do not know how to do this, refer to the gif below for instructions

                    Additionally, you must turn on your skyblock api, which can be accessed in the Skyblock Menu ⇒ Settings ⇒ API Settings.

                    Make sure you check every option. This includes the Bank API which can be turned on in Settings ⇒ Island Settings ⇒ Bank API""", color=0xff0000)
                    embed.set_thumbnail(url="https://yt3.ggpht.com/-G0UwZhD1hRI/AAAAAAAAAAI/AAAAAAAAAAA/Q5bg4hzv6C0/s900-c-k-no/photo.jpg")
                    await ctx.author.send(embed=embed)
                    await ctx.author.send("https://gfycat.com/dentaltemptingleonberger")
                    await ctx.message.delete()
                    return await ctx.send(embed=discord.Embed(title=":no_entry_sign: Error!", description="Could not verify your identity. I've DMed you info", color=0xff0000).set_footer(text=random.choice(failRepsonses), icon_url=ctx.author.avatar_url))            
                except discord.Forbidden:
                    await ctx.message.delete()
                    return await ctx.send("Could not verify your identity. Please allow DMs from members of this server then try again", delete_after=5)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/skyblock/profiles?key={key}&uuid={uuid}") as resp:
                player = await resp.json()
        souls = []
        slayers = []
        slots = {}
        pets = []
        skills = {"combat": [0], "farming": [0], "fishing": [0], "foraging": [0], "alchemy": [0], "enchanting": [0], "mining": [0]}
        skillroles = {"combat": 694957008759160862, "farming": 694956649458434111, "fishing": 694956709537513502, "foraging": 694957060907073586, "alchemy": 694956798125408416, "enchanting": 694958166550642838, "mining": 694957334195208274}
        for profile in player["profiles"]:
            slots[profile["profile_id"]] = 0
            for user in profile["members"]:
                if user != uuid:
                    pass
                else:
                    #print(profile["members"][user])
                    try:
                        souls.append(profile["members"][user]["fairy_souls_collected"])
                    except KeyError:
                        pass
                    for skill in skills:
                        try:
                            skills[skill].append(profile["members"][user][f"experience_skill_{skill}"])
                        except KeyError:
                            pass
                    if "slayer_bosses" in profile["members"][user]:
                        slayersbosses = profile["members"][user]["slayer_bosses"]
                        for slayer in slayersbosses:
                            try:
                                if "level_7" in slayersbosses[slayer]["claimed_levels"]:
                                    slayers.append(slayer)
                            except KeyError:
                                pass
                    if "pets" in profile["members"][user]:
                        for pet in profile["members"][user]["pets"]:
                            if pet["type"] not in pets:
                                pets.append(pet["type"])
                try:
                    #print(profile["members"][user][len("crafted_generators")])
                    #print(len(profile["members"][user]["crafted_generators"]))
                    slots[profile["profile_id"]] += len(profile["members"][user]["crafted_generators"])
                except KeyError:
                    pass

        #print(max(souls))
        bank = 0
        for profile in player["profiles"]:
            try:
                bank += (profile["banking"]["balance"])
            except KeyError:
                pass
        money_roles = {676693908788477953: 1000000, 676694080830439425: 10000000, 676694161541300225: 35000000}
        roles = []
        if max(souls) > 180:
            roles.append(676694230382411777)
        for i in money_roles:
            if bank > money_roles[i]:
                roles.append(i)
        if slayers:
            roles.append(694957553079287860)
            if len(slayers) > 2:
                roles.append(694957649703337995)
        if max(slots.values()) > 200:
            roles.append(678152501295448074)
        #print(slots)
        for skill in skills:
            if max(skills[skill]) > 3022425:
                roles.append(skillroles[skill])
        if len(pets) >= 15:
            roles.append(703135943653326899)
            #print(f"{skill} {max(skills[skill]) > 3022425}")
        embed = discord.Embed(title="Roles added :scroll:", color=0xfb00fd)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=f"https://mc-heads.net/head/{ign}")
        string = ''
        for role in roles:
            addrole = ctx.guild.get_role(role)
            if addrole not in ctx.author.roles:
                had = '[+]'
            else:
                had = ''
            await ctx.author.add_roles(addrole)
            await asyncio.sleep(0.5)
            string += f'\n{addrole.mention} {had}'
        if not string:
            #return await ctx.send("You don't qualify for any roles ):\n \n check that all your APIs are turned on")
            return await ctx.send(embed=discord.Embed(title=":hear_no_evil: Oh no!", description="You don't qualify for any roles ):", color=0xff0000).set_footer(text="Think you deserve some roles? Make sure all API settings are enabled").set_author(name=ctx.author, icon_url=ctx.author.avatar_url))
        embed.add_field(name=f"Added {len(roles)} roles for {ctx.author.nick if ctx.author.nick else ctx.author.name} as {ign}", value=string, inline=False)
        embed.set_footer(text="Innacurate? Make sure all API settings are enabled", icon_url="https://cdn.discordapp.com/icons/667953033929293855/a_76e58197f9e2e51b8280aa70e31fbbe5.gif?size=1024")
        await ctx.send(embed=embed)

    @commands.check(min_level(15))
    @commands.cooldown(600, 1, BucketType.user)
    @commands.guild_only()
    @commands.command()
    async def apply(self, ctx):
        answers = {}
        # questions = ["What level are you in Nullzee's Cave + state your time zone?",
        #              "How long will you spend in the server + how old are you? (can reply with N/A)",
        #              "Do you have any prior staffing experiences? How would you respond to someone 1. Spamming, 2. DM advertising, 3. Abusing power?",
        #              "Why do you want to be a staff member?"
        #              ]
        questions = [
            "What level are you in Nullzee's Cave and how many times have you been warned?",
            "What timezone are you and how old are you?",
            "How did you find Nullzee?",
            "How many hours are you active a day?",
            "Why do you want to be staff?",
            "Have you had any previous experience as staff or own your own server? If so, please provide an invite link",
            "If someone is spamming in general, how would you punish them?",
            "If another staff member has done something you think is wrong, what would you do?",
            "Someone has reported a DM Advertiser, what would you do?",
            "What would you say your biggest weakness is when talking with people? (eg: staying interested, being formal, etc...)"

        ]
        try:
            first_message = await ctx.author.send("Welcome to the staff application process!")
        except discord.Forbidden:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("I can't DM you! make sure you allow DMs for server members and that you haven't blocked me")
        await ctx.send(f"{ctx.author.mention}, application started in DM!")
        message_check = lambda message: message.channel == first_message.channel and message.author.id == ctx.author.id
        for question in questions:
            await ctx.author.send(question)
            try:
                answers[question] = (await self.bot.wait_for('message', check=message_check, timeout=600.0)).content
            except asyncio.TimeoutError:
                ctx.command.reset_cooldown(ctx)
                return await ctx.author.send("application timed out")
        confirmation_message = await ctx.author.send("Please confirm that the above information is correct and that you wish for this to be submitted as your staff application in Nullzee's cave discord server.")
        await confirmation_message.add_reaction("✅")
        await confirmation_message.add_reaction("❎")
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=lambda reaction, user: user.id == ctx.author.id and reaction.message.id == confirmation_message.id)
        except asyncio.TimeoutError:
            ctx.command.reset_cooldown(ctx)
            return await ctx.author.send("application timed out")
        if reaction.emoji == "❎":
            ctx.command.reset_cooldown(ctx)
            return await ctx.author.send("Application cancelled")
        elif reaction.emoji == "✅":
            embed = discord.Embed(title="Staff application", color=discord.Color.green()).set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            embed.timestamp = datetime.datetime.now()
            for answer in answers:
                embed.add_field(name=answer, value=answers[answer], inline=False)
            await ctx.guild.get_channel(700267342482898965).send(embed=embed)
            await ctx.author.send("Application submitted, good luck!")





def setup(bot):
    bot.add_cog(util(bot, False))