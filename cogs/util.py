import math

from discord.ext import commands, tasks
from random import randint

from helpers import constants, logic, moderationUtils, utils
from helpers.constants import Skyblock
from helpers.utils import min_level, get_user, RoleConverter
import json
import asyncio
import discord
import aiohttp
import requests
import random
from discord.ext.commands.cooldowns import BucketType
import time
import datetime
from api_key import moderationColl, hypixel_api_key
from helpers.utils import Embed, strfdelta
import mathterpreter

from helpers.events import Emitter


class util(commands.Cog, name="Other"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.autotogglestatus.start()
        self.autoSuggestions.start()
        self.update_member_counter.start()
        self.last_update = 0
        self.tags = utils.getFileJson("config/tags")
        self.updateSubCount()

    def updateSubCount(self):
        if time.time() - self.last_update > 600:
            self.sub_count = requests.get(
                "https://www.googleapis.com/youtube/v3/channels?part=statistics&id=UCvltzrCoxXIlmqG2VUvV1WA&key=YT_API_KEY").json()[
                "items"][0]["statistics"]
            self.last_update = time.time()

    @commands.command()
    async def subcount(self, ctx):
        '''View Nullzee's YouTube stats'''
        await ctx.send(embed=discord.Embed(title="Nullzee's YouTube stats",
                                           description=f"Subscribers: {int(self.sub_count['subscriberCount']):,}\nTotal Views: {int(self.sub_count['viewCount']):,}\nVideo count: {int(self.sub_count['videoCount']):,}",
                                           color=0x00FF00, url="https://youtube.com/nullzee").set_thumbnail(
            url="https://cdn.discordapp.com/avatars/165629105541349376/2d7ff05116b8930a2fa2bf22bdb119c7.webp?size=1024"))
        self.updateSubCount()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        before_ids = [z.id for z in before.roles]
        after_ids = [z.id for z in after.roles]
        if (668736363297898506 in before_ids and 668736363297898506 not in after_ids) or (
                668724083718094869 in before_ids and 668724083718094869 not in after_ids):
            await after.add_roles(after.guild.get_role(706285767898431500))

    @commands.command()
    async def rolelist(self, ctx: commands.Context, *, text: str):

        special_tokens = "&|!()"
        tokens = []
        builder = ""
        for char in text:
            if char in special_tokens:
                tokens.append(builder)
                tokens.append(char)
                builder = ""
            else:
                builder += char
        tokens.append(builder)
        empty = []
        for i, item in enumerate(tokens):
            if item == "" or item.isspace():
                empty.append(item)
        for i in empty:
            tokens.remove(i)
        for i, item in enumerate(tokens):
            if item not in special_tokens:
                tokens[i] = await RoleConverter().convert(ctx, item.strip())
        count = 0
        tree = logic.BooleanLogic.OperationBuilder(tokens, lambda item, items: item in items).build()
        async with ctx.typing():
            for member in ctx.guild.members:
                if tree.evaluate(member.roles):
                    count += 1
        embed = discord.Embed(title="Role list search",
                              colour=discord.Colour.blurple()).add_field(name="Query",
                                                                         value=tree.pprint(lambda x: x.mention),
                                                                         inline=False) \
            .add_field(name="Member count", value=f"{count:,}", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def roleColour(self, ctx, *, role: RoleConverter):
        await ctx.send(embed=discord.Embed(title=str(role.colour), description=f"Colour for {role.mention}", colour=role.colour).set_thumbnail(url=f"https://singlecolorimage.com/get/{role.colour}/400x300"))

    @commands.command(aliases=["calc", "math", "m"])
    async def maths(self, ctx, *, expr: str):
        '''Get the bot to do your maths homework for you'''
        try:
            await ctx.send(f"{ctx.author.mention}: ```\n{mathterpreter.interpret(expr)}\n```")
        except (mathterpreter.MathSyntaxError, OverflowError) as e:
            if isinstance(e, OverflowError):
                return await ctx.send(f"{ctx.author.mention}, an error occurred! Result too large")
            await ctx.send(f"{ctx.author.mention}, an error occurred! ```\n{e.reason}\n``` ```\n{e.visualisation}\n```",
                           allowed_mentions=discord.AllowedMentions(roles=False, users=True, everyone=False))

    #    @commands.command(aliases=["color"])
    #    async def colour(self, ctx, colour):
    #        embed = discord.Embed(description=colour, colour=colour)
    #        try:
    #            await ctx.send(embed=embed)
    #        except TypeError:
    #            raise commands.BadArgument()

    @commands.command()
    async def serverinfo(self, ctx):
        embed = await Embed(ctx.author).user_colour()
        embed.add_field(name="Owner:", value=f"{ctx.guild.owner}", inline=False)
        embed.add_field(name="Members:", value=len(ctx.guild.members), inline=True)
        embed.add_field(name="Roles:", value=len(ctx.guild.roles) - 1, inline=True)
        bots = 0
        moderators = 0
        for member in ctx.guild.members:
            if member.bot:
                bots += 1
            if member.guild_permissions.manage_messages:
                moderators += 1
        embed.add_field(name="Moderators:", value=moderators, inline=True)
        embed.add_field(name="Bots:", value=bots, inline=True)
        embed.add_field(name="Boosts:", value=len(ctx.guild.premium_subscribers), inline=True)
        embed.add_field(name="Region:", value=str(ctx.guild.region).capitalize(), inline=True)
        creation_date = ctx.guild.created_at
        current_date = datetime.datetime.now()
        time_since_creation = current_date - creation_date
        embed.add_field(name="Server Age:",
                        value=strfdelta(time_since_creation,
                                        f"{f'%Y years, ' if int(strfdelta(time_since_creation, '%Y')) > 1 else (f'%Y year, ' if int(strfdelta(time_since_creation, '%Y')) == 1 else '')}%D days, %H hours and %M minutes"),
                        inline=False)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.set_footer(text=f"ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def whois(self, ctx, user: discord.Member = None):
        '''View your user info (account creation date, join date, roles, etc)'''
        user = user or ctx.author
        user_data = await get_user(user)
        embed_colour = user_data["embed_colour"]
        embed = await Embed(user) \
            .add_field(name="Joined", value=user.joined_at.strftime("%d/%m/%y %H:%M"), inline=True) \
            .add_field(name="Registered", value=user.created_at.strftime("%d/%m/%y %H:%M"), inline=True) \
            .add_field(name=f"{len(user.roles) - 1} roles",
                       value=" ".join([z.mention for z in reversed(user.roles) if not z.is_default()]) if len(
                           user.roles) - 1 <= 42 else "Too many to display", inline=False) \
            .add_field(name="Embed colour",
                       value=f"#{embed_colour}" if not embed_colour.startswith('#') else embed_colour, inline=False) \
            .set_footer(text=user.id) \
            .set_thumbnail(url=user.avatar_url) \
            .auto_author() \
            .timestamp_now() \
            .user_colour()
        extra = []
        if user.id == ctx.guild.owner.id:
            extra.append("owner")
        if user.guild_permissions.administrator:
            extra.append("administrator")
        if user.guild_permissions.manage_messages:
            extra.append("moderator")
        if extra:
            embed.add_field(name="Extra", value=", ".join(extra), inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["av"])
    async def avatar(self, ctx, user: discord.Member = None):
        '''View a user's avatar'''
        user = user or ctx.author
        await ctx.send(
            embed=await Embed(user, title="Avatar").set_image(url=user.avatar_url).auto_author().user_colour())

    @commands.command()
    async def appeal(self, ctx, _id: str, *, reason: str = None):
        '''Appeal a punishment'''
        punishment = await moderationColl.find_one({"id": _id})
        if not punishment:
            return await ctx.send("Could not find a punishment with that ID")
        if punishment["offender_id"] != ctx.author.id:
            return await ctx.send("You can only appeal your own punishments")
        location = punishment["message"].split('-')
        msg = f"https://discord.com/channels/{location[0]}/{location[1]}/{location[2]}"
        embed = discord.Embed(title="Punishment appeal", url=msg, description=reason, colour=discord.Colour.orange())
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await self.bot.get_guild(int(location[0])).get_channel(771061232642949150).send(embed=embed)
        await ctx.send("Punishment appeal submitted.")

    @commands.command()
    @commands.cooldown(1, 900, BucketType.guild)
    @commands.check(min_level(20))
    async def suggest(self, ctx, *, answer: str):
        """Log a suggestion for the server"""
        with open('suggestions.json') as f:
            suggestions = json.load(f)
        suggestion = await Embed(ctx.author, description=answer, color=0x00FF00).user_colour()
        suggestion.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        sugChannel = self.bot.get_guild(667953033929293855).get_channel(667959037265969171)
        sugmsg = await sugChannel.send("<@&738691450417709077>", embed=suggestion)
        suggestions.append(sugmsg.id)
        with open('suggestions.json', 'w') as f:
            json.dump(suggestions, f)
        await sugmsg.add_reaction(u"\u2705")
        await sugmsg.add_reaction(u"\u274E")
        await ctx.send(ctx.author.mention + ", suggestion logged, check <#667959037265969171> to see its progress",
                       delete_after=5)
        await ctx.message.delete()

    @tasks.loop(minutes=20)
    async def update_member_counter(self):
        channel: discord.VoiceChannel = self.bot.get_guild(667953033929293855).get_channel(
            constants.Channel.MEMBER_COUNT_VC)
        member_count = len(channel.guild.members)
        if channel.name != f"Members: {member_count}":
            await channel.edit(name=f"Members: {member_count}")

    @tasks.loop(minutes=2)
    async def autoSuggestions(self):
        with open('suggestions.json') as f:
            suggestions = json.load(f)

        killList = []
        for i in suggestions:
            try:
                msg = await self.bot.get_guild(667953033929293855).get_channel(667959037265969171).fetch_message(i)
                upvotes = [z.count for z in msg.reactions if str(z.emoji) == '✅']
                downvotes = [z.count for z in msg.reactions if str(z.emoji) == '❎']
                karma = upvotes[0] - downvotes[0]
                if karma > 15:
                    try:
                        ctx = await self.bot.get_context(msg)
                        ctx.author = await commands.MemberConverter().convert(ctx, msg.embeds[0].author.name)
                        await Emitter().emit("suggestion_stage_2", ctx)
                    except commands.BadArgument:
                        pass
                    killList.append(i)
                elif downvotes[0] > 14:
                    ctx = await self.bot.get_context(msg)
                    ctx.author = await commands.MemberConverter().convert(ctx, msg.embeds[0].author.name)
                    await Emitter().emit("bad_suggestion", ctx)
                elif downvotes[0] > 8:
                    killList.append(i)
            except:
                killList.append(i)
        for i in killList:
            suggestions.remove(i)
        with open('suggestions.json', 'w') as f:
            json.dump(suggestions, f)

    @commands.command()
    async def members(self, ctx):
        """Displays the number of members in the server"""
        await ctx.send(str(len(ctx.guild.members)))

    @commands.command()
    async def ping(self, ctx):
        """Pings the bot to show latency"""
        embed = discord.Embed(title="Pong!", description=f"That took {round(100 * self.bot.latency)} ms",
                              color=0x00FF00)
        # await ctx.send(f"Pong!\n~{self.bot.latency} (seconds)")
        embed.set_thumbnail(url="https://i.gifer.com/fyMe.gif")
        # await ctx.send(f"Pong! :ping_pong: \nThat took {round(100*self.bot.latency)}ms :wind_blowing_face:")
        await ctx.send(embed=embed)
        # await ctx.message.delete()

    @commands.command(aliases=['commands'])
    async def help(self, ctx, cog: str = None):
        """Displays the help command
        Anything in angled brackets <> is a required argument. Square brackets [] mark an optional argument"""
        prefix = "-"
        if not cog:
            embed = discord.Embed(title="Help", description=f"use `{prefix}help [category|command]` for more info",
                                  color=0x00FF00)
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
                    # title="Help", description=f"**Category {cog[0]}:** {self.bot.cogs[cog[0]].__doc__}",
                    embed = discord.Embed(title="Help", color=0x00FF00)
                    scog_info = ''
                    for c in self.bot.get_cog(x).get_commands():
                        if not c.hidden:
                            scog_info += f"\n`{prefix}{c.name}`: {c.help}\n"
                    embed.add_field(name=f"\n{cog} Category:\n{self.bot.cogs[cog].__doc__}\n ",
                                    value=f"\n{scog_info}\n", inline=False)
                    found = True

            if not found:
                for x in self.bot.cogs:
                    for c in self.bot.get_cog(x).get_commands():
                        if c.name.lower() == cog:
                            embed = discord.Embed(color=0x00FF00)
                            embed.add_field(name=f"{c.name}: {c.help}",
                                            value=f"Usage:\n `{prefix}{c.qualified_name} {c.signature}`")
                            found = True
            if not found:
                embed = discord.Embed(
                    description="Command not found. Check that you have spelt it correctly and used capitals where appropriate")
            await ctx.author.send(embed=embed)
            if not isinstance(ctx.channel, discord.channel.DMChannel):
                await ctx.send("**:mailbox_with_mail: You've got mail**")

    @commands.command(aliases=['boost'])
    async def nitro(self, ctx):
        '''View the perks you can get for being a server booster'''
        embed = discord.Embed(title="Considering boosting the server?", color=0xfb00fd)
        embed.add_field(name="`For Nitro Boosting You Can Get`", value="""- Access to <#674311689738649600>
- A message posted in <#714073835791712267>
- The Nitro Booster (rich) role
- Access to all level restricted commands
- The ability to use commands in all channels
- All other level restricted perks from <#667966078596546580>
""", inline=False)
        embed.set_thumbnail(
            url="https://images-ext-1.discordapp.net/external/PbC_AHw6x6OR_5a6hpvuLTP6nBEnpc5e-ftbgOx9oks/https/i.ytimg.com/vi/ZyX7U78keu0/maxresdefault.jpg?width=960&height=540")
        await ctx.send(embed=embed)
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 667953033929293855:
            channel = member.guild.get_channel(667955504651304999)
            await channel.send(
                f"Welcome to Nullzee's Cave, {member.mention}, Make sure to read <#667966078596546580> carefully and ensure you understand them. We hope you enjoy your time here! :heart: :wave:")

    @tasks.loop(minutes=30)
    async def autotogglestatus(self):
        rand = randint(0, 10)
        watching = ["discord.gg/nullzee", "twitch.tv/nullzeelive"]
        playing = ["with -help", "with Nullzee", "Hypixel Skyblock"]
        rand = randint(1, 2)
        if rand == 1:
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watching)))
        elif rand == 2:
            await self.bot.change_presence(activity=discord.Game(name=random.choice(playing)))

    @commands.command()
    async def report(self, ctx, message: discord.Message, *, reason: str = None):
        '''Report a message a user has sent'''
        try:
            await ctx.message.delete()
        except:
            pass
        await moderationUtils.send_report(ctx, message, reason)
        try:
            await ctx.author.send(
                "Your report has been submitted. For any further concerns, do not hesitate to contact a staff member")
        except:
            pass

    @commands.command(hidden=True)
    @commands.has_guild_permissions(administrator=True)
    async def manualtogglestatus(self, ctx):
        '''Toggle the bot's status manually'''
        rand = randint(0, 10)
        watching = ["discord.gg/nullzee", "twitch.tv/nullzeelive"]
        playing = ["with -help", "with Nullzee", "Hypixel Skyblock"]
        rand = randint(1, 2)
        if rand == 1:
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watching)))
        elif rand == 2:
            await self.bot.change_presence(activity=discord.Game(name=random.choice(playing)))

    @commands.command()
    @commands.cooldown(2, 60, BucketType.user)
    async def claimroles(self, ctx, ign: str):
        """Claim roles for in-game achievement"""
        if ctx.channel.id != 853294481825726475:
            return await ctx.send("go to <#853294481825726475> for that!")
        await ctx.trigger_typing()
        key = hypixel_api_key
        try:
            # noinspection SpellCheckingInspection
            mojang = await utils.fetch_json_api(f"https://api.mojang.com/users/profiles/minecraft/{ign}")
            uuid = mojang["id"]
        except (aiohttp.ContentTypeError, KeyError):
            return await ctx.send(f"{ctx.author.mention}, that username could not be found")
        player_data = await utils.fetch_json_api(f"https://api.hypixel.net/player?uuid={uuid}&key={key}")
        fail_responses = [f"{str(ctx.author)} doesn't know how to claim roles smh",
                          f"{str(ctx.author)} messed up somehow ¯\_(ツ)_/¯",
                          "blame pjones123#6025 if something messes up"]

        async def send_fail():
            try:
                embed = discord.Embed(title=":no_entry_sign: Error!", description="""In order to automatically claim your roles, you must first link your discord account to your hypixel profile. If you do not know how to do this, refer to the gif below for instructions

                                    Additionally, you must turn on your skyblock api, which can be accessed in the Skyblock Menu ⇒ Settings ⇒ API Settings.

                                    Make sure you check every option. This includes the Bank API which can be turned on in Settings ⇒ Island Settings ⇒ Bank API""",
                                      color=0xff0000)
                embed.set_thumbnail(
                    url="https://yt3.ggpht.com/-G0UwZhD1hRI/AAAAAAAAAAI/AAAAAAAAAAA/Q5bg4hzv6C0/s900-c-k-no/photo.jpg")
                await ctx.author.send(embed=embed)
                await ctx.author.send("https://gfycat.com/dentaltemptingleonberger")
                await ctx.message.delete()
                return await ctx.send(embed=discord.Embed(title=":no_entry_sign: Error!",
                                                          description="Could not verify your identity. I've DMed you info",
                                                          color=0xff0000).set_footer(
                    text=random.choice(fail_responses), icon_url=ctx.author.avatar_url))
            except discord.Forbidden:
                await ctx.send(
                    "Could not verify your identity. Please allow DMs from members of this server then try again",
                    delete_after=5)
                return await ctx.message.delete()

        try:
            if player_data["player"]["socialMedia"]["links"]["DISCORD"] != str(ctx.author):
                return await send_fail()
        except KeyError:
            return await send_fail()
        player = await utils.fetch_json_api(f"https://api.hypixel.net/skyblock/profiles?key={key}&uuid={uuid}")
        souls = []
        slayers = []
        slots = {}
        pets = []
        bank = 0
        skills = ("combat", "farming", "fishing", "foraging", "alchemy", "enchanting", "mining", "taming")
        skill_averages = [0]
        for profile in player["profiles"]:
            slots[profile["profile_id"]] = 0
            for user in profile["members"]:
                if user != uuid:
                    continue
                try:
                    souls.append(profile["members"][user]["fairy_souls_collected"])
                    skill_averages.append(math.trunc(sum([Skyblock.SKILL_XP_REQUIREMENTS.index(
                        utils.level_from_table(profile["members"][user][f"experience_skill_{skill}"],
                                               Skyblock.SKILL_XP_REQUIREMENTS[:50] if skill in Skyblock.MAX_LEVEL_50_SKILLS else Skyblock.SKILL_XP_REQUIREMENTS)
                    )+1 for skill in skills]) / len(skills)))
                    if "slayer_bosses" in profile["members"][user]:
                        slayer_bosses = profile["members"][user]["slayer_bosses"]
                        for slayer in slayer_bosses:
                            try:
                                if "level_7" in slayer_bosses[slayer]["claimed_levels"]:
                                    slayers.append(7)
                                if "level_9" in slayer_bosses[slayer]["claimed_levels"]:
                                    slayers.append(9)
                            except KeyError:
                                pass
                    if "pets" in profile["members"][user]:
                        for pet in profile["members"][user]["pets"]:
                            if pet["type"] not in pets:
                                pets.append(pet["type"])
                    if "coin_purse" in profile["members"][user]:
                        bank += profile["members"][user]["coin_purse"]
                    slots[profile["profile_id"]] += len(profile["members"][user]["crafted_generators"])
                except KeyError:
                    pass
        for profile in player["profiles"]:
            try:
                bank += (profile["banking"]["balance"])
            except KeyError:
                pass
            try:
                minion_slot_requirements = [0, 0, 0, 0, 0, 5, 15, 30, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275,
                                            300,
                                            350, 400, 450, 500, 550, 600, 650]
                extra_slots = len(
                    [z for z in profile["community_upgrades"]["upgrade_states"] if z["upgrade"] == "minion_slots"])
                slots[profile["profile_id"]] = minion_slot_requirements.index(utils.level_from_table(
                    slots[profile["profile_id"]] + extra_slots, minion_slot_requirements))
            except KeyError:
                pass

        money_roles = {676694080830439425: 50_000_000, 676694161541300225: 150_000_000}
        roles = []
        if max(skill_averages) >= 20:
            roles.append(853259525406195762)
        if max(skill_averages) >= 35:
            roles.append(853259618645835776)
        if max(skill_averages) >= 50:
            roles.append(853259716531978251)
        if max(souls) >= 210:
            roles.append(676694230382411777)
        for i in money_roles:
            if bank > money_roles[i]:
                roles.append(i)
        if slayers:
            roles.append(694957553079287860)
            if 9 in slayers:
                roles.append(694957649703337995)
        if max(slots.values()) >= 25:
            roles.append(678152501295448074)
        if len(pets) >= 25:
            roles.append(703135943653326899)
        embed = discord.Embed(title="Roles added :scroll:", color=0xfb00fd)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=f"https://mc-heads.net/head/{ign}")
        string = ''
        roles = [ctx.guild.get_role(role) for role in roles]
        for role in roles:
            string += f'\n{role.mention} {"[+]" if role not in ctx.author.roles else ""}'
        await ctx.author.add_roles(*roles)
        if not string:
            return await ctx.send(
                embed=discord.Embed(title=":hear_no_evil: Oh no!", description="You don't qualify for any roles ):",
                                    color=0xff0000).set_footer(
                    text="Think you deserve some roles? Make sure all API settings are enabled").set_author(
                    name=ctx.author, icon_url=ctx.author.avatar_url))
        embed.add_field(
            name=f"Added {len(roles)} roles for {ctx.author.display_name} as {ign}",
            value=string, inline=False)
        embed.set_footer(text="Inaccurate? Make sure all API settings are enabled",
                         icon_url="https://cdn.discordapp.com/icons/667953033929293855/a_76e58197f9e2e51b8280aa70e31fbbe5.gif?size=1024")
        await ctx.send(embed=embed)
        # noinspection SpellCheckingInspection
        await Emitter().emit("hypixel_link", ctx)

    @commands.command(name="tag")
    async def tag_command(self, ctx: commands.Context, *, tag: str):
        for tag_object in self.tags:
            if tag.lower() == tag_object["name"].lower() or tag.lower() in [z.lower() for z in tag_object["aliases"]]:
                return await ctx.send(tag_object["response"])
        await ctx.send(f"Could not find a tag with that name.")

#     @commands.check(min_level(15))
#     @commands.cooldown(600, 1, BucketType.user)
#     @commands.guild_only()
#     @commands.command()
#     async def apply(self, ctx):
#         '''Apply for staff'''
#         answers = {}
#         # questions = ["What level are you in Nullzee's Cave + state your time zone?",
#         #              "How long will you spend in the server + how old are you? (can reply with N/A)",
#         #              "Do you have any prior staffing experiences? How would you respond to someone 1. Spamming, 2. DM advertising, 3. Abusing power?",
#         #              "Why do you want to be a staff member?"
#         #              ]
#         questions = [
#             "What level are you in Nullzee's Cave and how many times have you been warned?",
#             "What timezone are you and how old are you?",
#             "How did you find Nullzee?",
#             "How many hours are you active a day?",
#             "Why do you want to be staff?",
#             "Have you had any previous experience as staff or own your own server? If so, please provide an invite link",
#             "If someone is spamming in general, how would you punish them?",
#             "If another staff member has done something you think is wrong, what would you do?",
#             "Someone has reported a DM Advertiser, what would you do?",
#             "What would you say your biggest weakness is when talking with people? (eg: staying interested, being formal, etc...)"

#         ]
#         try:
#             first_message = await ctx.author.send("Welcome to the staff application process!")
#         except discord.Forbidden:
#             ctx.command.reset_cooldown(ctx)
#             return await ctx.send("I can't DM you! make sure you allow DMs for server members and that you haven't blocked me")
#         await ctx.send(f"{ctx.author.mention}, application started in DM!")
#         message_check = lambda message: message.channel == first_message.channel and message.author.id == ctx.author.id
#         for question in questions:
#             await ctx.author.send(question)
#             try:
#                 answers[question] = (await self.bot.wait_for('message', check=message_check, timeout=600.0)).content
#             except asyncio.TimeoutError:
#                 ctx.command.reset_cooldown(ctx)
#                 return await ctx.author.send("application timed out")
#         confirmation_message = await ctx.author.send("Please confirm that the above information is correct and that you wish for this to be submitted as your staff application in Nullzee's cave discord server.")
#         await confirmation_message.add_reaction("✅")
#         await confirmation_message.add_reaction("❎")
#         try:
#             reaction, user = await self.bot.wait_for('reaction_add', check=lambda reaction, user: user.id == ctx.author.id and reaction.message.id == confirmation_message.id)
#         except asyncio.TimeoutError:
#             ctx.command.reset_cooldown(ctx)
#             return await ctx.author.send("application timed out")
#         if reaction.emoji == "❎":
#             ctx.command.reset_cooldown(ctx)
#             return await ctx.author.send("Application cancelled")
#         elif reaction.emoji == "✅":
#             embed = discord.Embed(title="Staff application", color=discord.Color.green()).set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
#             embed.timestamp = datetime.datetime.now()
#             for answer in answers:
#                 embed.add_field(name=answer, value=answers[answer], inline=False)
#             await ctx.guild.get_channel(700267342482898965).send(embed=embed)
#             await ctx.author.send("Application submitted, good luck!")


def setup(bot):
    bot.add_cog(util(bot, False))
