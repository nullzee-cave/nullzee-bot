import math

from discord import app_commands
from discord.ext import commands, tasks
from random import randint

from helpers import constants, logic, moderation_utils, utils
from helpers.constants import Skyblock, Role, Channel, Misc
from helpers.modals import ShortTextInputModal
from helpers.utils import min_level, get_user, RoleConverter, staff_check, MemberUserConverter
import json
import asyncio
import discord
import aiohttp
import requests
import random
from discord.ext.commands.cooldowns import BucketType
import time
from api_key import HYPIXEL_API_KEY, DEV_ID
from helpers.utils import Embed, strfdelta, staff_only, HelpConverter
import mathterpreter

from helpers.events import Emitter


class Util(commands.Cog, name="Other"):
    """Other useful commands"""

    # and listeners

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot
        self.auto_toggle_status.start()
        self.auto_suggestions.start()
        self.update_member_counter.start()
        self.last_update = 0
        self.tags = utils.get_file_json("config/tags")
        self.sub_count = {}
        self.update_sub_count()

        self.report_context_menu = discord.app_commands.ContextMenu(
            name="Report Message",
            callback=self.report_context_menu_callback,
        )
        self.bot.tree.add_command(self.report_context_menu)

    async def toggle_bot_status(self):
        watching = ["discord.gg/nullzee", "twitch.tv/nullzeelive"]
        playing = ["with -help", "with Nullzee", "Hypixel Skyblock"]
        rand = randint(1, 2)
        if rand == 1:
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watching)))
        elif rand == 2:
            await self.bot.change_presence(activity=discord.Game(name=random.choice(playing)))

    def update_sub_count(self):
        if time.time() - self.last_update > 600:
            self.sub_count = requests.get(
                "https://www.googleapis.com/youtube/v3/channels?part=statistics&id=UCvltzrCoxXIlmqG2VUvV1WA&key=YT_API_KEY"
            ).json()["items"][0]["statistics"]
            self.last_update = time.time()

    @commands.command(name="subcount")
    async def sub_count(self, ctx):
        """View Nullzee's YouTube stats"""
        embed = discord.Embed(title="Nullzee's YouTube stats",
                              description=f"Subscribers: {int(self.sub_count['subscriberCount']):,}\n"
                                          f"Total Views: {int(self.sub_count['viewCount']):,}\n"
                                          f"Video count: {int(self.sub_count['videoCount']):,}",
                              color=0x00FF00, url="https://youtube.com/nullzee")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/avatars/165629105541349376/2d7ff05116b8930a2fa2bf22bdb119c7.webp?size=1024")
        await ctx.send(embed=embed)
        self.update_sub_count()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        before_ids = [z.id for z in before.roles]
        after_ids = [z.id for z in after.roles]
        if ((Role.TWITCH_SUB in before_ids and Role.TWITCH_SUB not in after_ids) or (
             Role.BOOSTER in before_ids and Role.BOOSTER not in after_ids)) and (
             Role.RETIRED_SUPPORTER not in after_ids):
            await after.add_roles(after.guild.get_role(Role.RETIRED_SUPPORTER))

    @commands.command(name="rolelist")
    async def role_list(self, ctx: commands.Context, *, text: str):
        """
        Check how many users have a specific role (or combination of roles).
        Usable characters:
        `role & role` - users with both roles
        `role | role` - users with either role
        `!role` - users without that role
        `()` - can be used to format the query
        """
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
        embed = discord.Embed(title="Role List Search", colour=discord.Colour.og_blurple())
        embed.add_field(name="Query", value=tree.pprint(lambda x: x.mention), inline=False)
        embed.add_field(name="Member count", value=f"{count:,}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="rolecolour")
    async def role_colour(self, ctx, *, role: RoleConverter):
        """View the colour of a role"""
        embed = discord.Embed(title=str(role.colour), description=f"Colour for {role.mention}", colour=role.colour)
        embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{str(role.colour)[1:]}/400x300")
        await ctx.send(embed=embed)

    @commands.command(aliases=["calc", "math", "m"])
    async def maths(self, ctx, *, expr: str):
        """Get the bot to do your maths homework for you"""
        try:
            await ctx.send(f"{ctx.author.mention}: ```\n{mathterpreter.interpret(expr)}\n```")
        except (mathterpreter.MathSyntaxError, OverflowError) as e:
            if isinstance(e, OverflowError):
                return await ctx.send(f"{ctx.author.mention}, an error occurred! Result too large")
            await ctx.send(f"{ctx.author.mention}, an error occurred! ```\n{e.text}\n``` ```\n{e.visualisation}\n```",
                           allowed_mentions=discord.AllowedMentions(roles=False, users=True, everyone=False))

    #    @commands.command(aliases=["color"])
    #    async def colour(self, ctx, colour):
    #        embed = discord.Embed(description=colour, colour=colour)
    #        try:
    #            await ctx.send(embed=embed)
    #        except TypeError:
    #            raise commands.BadArgument()

    @commands.command(name="serverinfo")
    async def server_info(self, ctx):
        """View some information about the server"""
        embed = await Embed(ctx.author).user_colour(self.bot)
        embed.add_field(name="Owner:", value=f"{ctx.guild.owner}", inline=False)
        embed.add_field(name="Members:", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="Roles:", value=len(ctx.guild.roles) - 1, inline=True)
        bots = 0
        moderators = 0
        for member in ctx.guild.members:
            if member.bot:
                bots += 1
            elif member.guild_permissions.manage_messages:
                moderators += 1
        embed.add_field(name="Moderators:", value=moderators, inline=True)
        embed.add_field(name="Bots:", value=bots, inline=True)
        embed.add_field(name="Boosts:", value=len(ctx.guild.premium_subscribers), inline=True)
        embed.add_field(name="Emojis:", value=len(ctx.guild.emojis), inline=True)
        time_since_creation = discord.utils.utcnow() - ctx.guild.created_at
        template = ""
        if int(strfdelta(time_since_creation, "%Y")) > 1:
            template += f"%Y years, "
        elif int(strfdelta(time_since_creation, "%Y")) == 1:
            template += f"%Y year, "
        template += "%D days, %H hours and %M minutes"
        age_string = strfdelta(time_since_creation, template)
        embed.add_field(name="Server Age:", value=age_string, inline=False)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.set_footer(text=f"ID: {ctx.guild.id} | Created")
        embed.timestamp = ctx.guild.created_at
        await ctx.send(embed=embed)

    @commands.command(name="userinfo", aliases=["whois"])
    @commands.guild_only()
    async def user_info(self, ctx, user: MemberUserConverter = None):
        """View your user info (account creation date, join date, roles, etc.) or that of the mentioned user"""
        user = user or ctx.author
        is_member = isinstance(user, discord.Member)
        embed = Embed(user)
        embed.add_field(name="Joined", value=user.joined_at.strftime("%d/%m/%y %H:%M") if is_member else "N/A",
                        inline=True)
        embed.add_field(name="Registered", value=user.created_at.strftime("%d/%m/%y %H:%M"), inline=True)
        if is_member:
            user_data = await get_user(self.bot, user)
            embed_colour = user_data["embed_colour"]
            embed.add_field(name=f"{len(user.roles) - 1} roles",
                            value=" ".join([z.mention for z in reversed(user.roles) if not z.is_default()]) if len(
                                user.roles) - 1 <= 42 else "Too many to display", inline=False)
            embed.add_field(name="Embed Colour",
                            value=f"#{embed_colour}" if not embed_colour.startswith("#") else embed_colour,
                            inline=False)
        else:
            user_data = await self.bot.user_coll.find_one({"_id": str(user.id)})
            embed_colour = f"#{user_data['embed_colour']}" if user_data else "N/A"
            embed.add_field(name="0 Roles", value="N/A", inline=False)
            embed.add_field(name="Embed Colour", value=embed_colour)
            if user_data:
                embed.colour = discord.Colour(int(user_data["embed_colour"], base=16))
        embed.set_footer(text=user.id)
        embed.set_thumbnail(url=user.avatar)
        embed.auto_author()
        embed.timestamp_now()
        if is_member:
            await embed.user_colour(self.bot)

            extra = []
            if user.id == ctx.guild.owner.id:
                extra.append("Owner")
            if user.guild_permissions.administrator:
                extra.append("Administrator")
            if user.guild_permissions.manage_messages:
                extra.append("Moderator")
            if extra:
                embed.add_field(name="Extra", value=", ".join(extra), inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["av", "pfp"])
    async def avatar(self, ctx, user: discord.Member = None):
        """View a user's avatar"""
        user = user or ctx.author
        embed = Embed(user, title="Avatar")
        embed.set_image(url=user.avatar)
        embed.auto_author()
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)

    @commands.command()
    async def appeal(self, ctx, _id: str, *, reason: str = None):
        """Appeal a punishment"""
        punishment = await self.bot.moderation_coll.find_one({"id": _id})
        if not punishment:
            return await ctx.send("Could not find a punishment with that ID")
        if punishment["offender_id"] != ctx.author.id:
            return await ctx.send("You can only appeal your own punishments")
        location = punishment["message"].split("-")
        msg = f"https://discord.com/channels/{location[0]}/{location[1]}/{location[2]}"
        embed = discord.Embed(title="Punishment appeal", url=msg, description=reason, colour=discord.Colour.orange())
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar)
        await self.bot.get_guild(int(location[0])).get_channel(Channel.REPORTS_APPEALS).send(embed=embed)
        await ctx.send("Punishment appeal submitted.")

    @commands.command()
    @commands.check(min_level(20))
    @commands.cooldown(1, 900, BucketType.guild)
    async def suggest(self, ctx, *, answer: str):
        """Log a suggestion for the server"""
        with open("suggestions.json") as f:
            suggestions = json.load(f)
        suggestion = await Embed(ctx.author, description=answer, color=0x00FF00).user_colour(self.bot)
        suggestion.set_author(name=ctx.author, icon_url=ctx.author.avatar)
        suggestion_channel = self.bot.get_guild(Misc.GUILD).get_channel(Channel.POLLS)
        suggestion_msg = await suggestion_channel.send(f"<@&{Role.POLL_PING}>", embed=suggestion)
        suggestions.append(suggestion_msg.id)
        with open("suggestions.json", "w") as f:
            json.dump(suggestions, f)
        await suggestion_msg.add_reaction(u"\u2705")
        await suggestion_msg.add_reaction(u"\u274E")
        await ctx.send(ctx.author.mention + f", suggestion logged, check <#{Channel.POLLS}> to see its progress",
                       delete_after=5)
        await ctx.message.delete()

    @tasks.loop(minutes=20)
    async def update_member_counter(self):
        channel: discord.VoiceChannel = self.bot.get_guild(Misc.GUILD).get_channel(
            constants.Channel.MEMBER_COUNT_VC)
        member_count = channel.guild.member_count
        if channel.name != f"Members: {member_count}":
            await channel.edit(name=f"Members: {member_count}")

    @update_member_counter.before_loop
    async def before_update_member_counter(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def auto_suggestions(self):
        with open("suggestions.json") as f:
            suggestions = json.load(f)

        kill_list = []
        for i in suggestions:
            try:
                msg = await self.bot.get_guild(Misc.GUILD).get_channel(Channel.POLLS).fetch_message(i)
                upvotes = [z.count for z in msg.reactions if str(z.emoji) == "✅"]
                downvotes = [z.count for z in msg.reactions if str(z.emoji) == "❎"]
                karma = upvotes[0] - downvotes[0]
                if karma > 15:
                    try:
                        ctx = await self.bot.get_context(msg)
                        ctx.author = await commands.MemberConverter().convert(ctx, msg.embeds[0].author.name)
                        await Emitter().emit("suggestion_stage_2", ctx)
                    except commands.BadArgument:
                        pass
                    kill_list.append(i)
                elif downvotes[0] > 8:
                    kill_list.append(i)
            except:
                kill_list.append(i)
        for i in kill_list:
            suggestions.remove(i)
        with open("suggestions.json", "w") as f:
            json.dump(suggestions, f)

    @auto_suggestions.before_loop
    async def before_auto_suggestions(self):
        await self.bot.wait_until_ready()

    @commands.command(name="membercount", aliases=["members"])
    async def member_count(self, ctx):
        """Displays the number of members in the server"""
        await ctx.send(str(ctx.guild.member_count))

    @commands.command()
    async def ping(self, ctx):
        """Pings the bot to show latency"""
        embed = discord.Embed(title="Pong!", description=f"That took {round(100 * self.bot.latency)} ms",
                              color=0x00FF00)
        embed.set_thumbnail(url="https://i.gifer.com/fyMe.gif")
        await ctx.send(embed=embed)
        # await ctx.message.delete()

    @commands.command(aliases=["commands"])
    async def help(self, ctx, *, arg: HelpConverter = None):
        """Displays the help command
        Anything in angled brackets `<>` is a required argument. Square brackets `[]` mark an optional argument"""
        ctx.guild = self.bot.get_guild(Misc.GUILD)
        ctx.author = ctx.guild.get_member(ctx.author.id)
        ctx.is_help_command = True
        help_embed = None
        if isinstance(arg, commands.Cog):
            help_embed = discord.Embed(title=arg.qualified_name.title(), description=arg.__doc__, colour=0x00FF00)
            cog_commands = []
            for command in arg.get_commands():
                try:
                    if not await command.can_run(ctx):
                        continue
                    cog_commands.append(command.name)
                except commands.CheckFailure:
                    continue
            help_embed.add_field(name="Commands:", value=(", ".join(sorted(cog_commands))) if cog_commands else None)
        elif isinstance(arg, commands.Command):
            help_embed = discord.Embed(title=arg.name.capitalize(),
                                       description=arg.help if arg.help is not None else "No Information",
                                       colour=0x00FF00)
            help_embed.add_field(name="Usage:",
                                 value=f"`{ctx.prefix}{arg.qualified_name} {arg.signature}"
                                       f"`\n\n`<>` represents required arguments\n`[]` represents optional arguments")
        elif arg is None:
            help_embed = discord.Embed(title="Help",
                                       description=f"Use `{ctx.prefix}help [category|command]` for more information",
                                       colour=0x00FF00)
            for cog in [ctx.bot.get_cog(z) for z in ctx.bot.cogs]:
                if (cog.hidden and not staff_check(ctx)) or cog.get_commands() == []:
                    continue
                help_embed.add_field(name=f"__{cog.qualified_name.title()}:__", value=cog.__doc__, inline=False)
            help_embed.set_footer(text="Created by pjones123#6025, maintained and continued by Septikai#1676")
        try:
            await ctx.author.send(embed=help_embed)
            if not isinstance(ctx.channel, discord.DMChannel):
                await ctx.message.add_reaction("✅")
        except discord.Forbidden:
            await ctx.send("Please enable DMs from server members then try again")

    @commands.command(name="nitro", aliases=["nitroinfo", "boost", "boostinfo"])
    async def nitro_info(self, ctx):
        """View the perks you can get for being a server booster"""
        embed = discord.Embed(title="Considering boosting the server?", color=0xfb00fd)
        embed.add_field(name="`For Nitro Boosting You Can Get`",
                        value=f"""
                        - Access to <#{Channel.COOL_KID_CLUB}>
                        - A message posted in <#{Channel.NITRO_BOOSTERS}>
                        - The <@&{Role.BOOSTER}> role
                        - Access to all level restricted commands
                        - The ability to use commands in all channels
                        - All other level restricted perks from <#{Channel.RULES_AND_INFO}>
                        """, inline=False)
        embed.set_thumbnail(
            url="https://images-ext-1.discordapp.net/external/PbC_AHw6x6OR_5a6hpvuLTP6nBEnpc5e-ftbgOx9oks/https/i.ytimg.com/vi/ZyX7U78keu0/maxresdefault.jpg?width=960&height=540")
        await ctx.send(embed=embed)
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == Misc.GUILD:
            channel = member.guild.get_channel(Channel.WELCOME)
            await channel.send(
                f"Welcome to Nullzee's Cave, {member.mention}, make sure to read <#{Channel.RULES_AND_INFO}> carefully and ensure you understand them. We hope you enjoy your time here! :heart: :wave:")

    @tasks.loop(minutes=30)
    async def auto_toggle_status(self):
        await self.toggle_bot_status()

    @auto_toggle_status.before_loop
    async def before_auto_toggle_status(self):
        await self.bot.wait_until_ready()

    @commands.command(name="manualtogglestatus", aliases=["togglestatus"], hidden=True)
    @commands.has_role(Role.ADMIN)
    async def manual_toggle_status(self, ctx):
        """Toggle the bot's status manually"""
        await self.toggle_bot_status()

    @commands.command()
    async def report(self, ctx, message: discord.Message, *, reason: str = None):
        """Report a message a user has sent"""
        try:
            await ctx.message.delete()
        except:
            pass
        await moderation_utils.send_report(ctx, message, reason)
        try:
            await ctx.author.send(
                "Your report has been submitted. For any further concerns, do not hesitate to contact a staff member")
        except:
            pass

    @app_commands.guild_only
    async def report_context_menu_callback(self, interaction: discord.Interaction, message: discord.Message):
        """Report a message a user has sent via context menu"""
        modal = ShortTextInputModal(title="Report", label="Reason", placeholder="Reason")
        await interaction.response.send_modal(modal)
        await modal.wait()
        await moderation_utils.send_report(interaction, message, modal.text)
        await modal.response.send_message(
            "Your report has been submitted. For any further concerns, do not hesitate to contact a staff member",
            ephemeral=True
        )

    @commands.command(name="claimroles")
    @commands.cooldown(2, 60, BucketType.user)
    async def claim_roles(self, ctx, ign: str):
        """Claim roles for in-game achievement"""
        if ctx.channel.id != Channel.ROLE_COMMANDS:
            return await ctx.send(f"Go to <#{Channel.ROLE_COMMANDS}> for that!")
        async with ctx.channel.typing():
            key = HYPIXEL_API_KEY
            try:
                mojang = await utils.fetch_json_api(f"https://api.mojang.com/users/profiles/minecraft/{ign}")
                uuid = mojang["id"]
            except (aiohttp.ContentTypeError, KeyError):
                return await ctx.send(f"{ctx.author.mention}, that username could not be found")
            player_data = await utils.fetch_json_api(f"https://api.hypixel.net/player?uuid={uuid}&key={key}")
            fail_responses = [f"{str(ctx.author)} doesn't know how to claim roles smh",
                              f"{str(ctx.author)} messed up somehow ¯\_(ツ)_/¯",
                              "Blame Septikai#1676 if something messes up"]

            async def send_fail():
                try:
                    embed = discord.Embed(title=":no_entry_sign: Error!",
                                          description="""In order to automatically claim your roles, you must first link your discord account to your hypixel profile. If you do not know how to do this, refer to the gif below for instructions
                                          
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
                                                              color=0xff0000)
                                          .set_footer(text=random.choice(fail_responses), icon_url=ctx.author.avatar))
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
            skills = ("combat", "farming", "fishing", "foraging", "alchemy", "enchanting", "mining", "taming")
            skill_averages = [0]
            catacombs_xp = 0
            catacombs_level = 0
            pet_score = 0
            for profile in player["profiles"]:
                for user in profile["members"]:
                    if user != uuid:
                        continue
                    try:
                        souls.append(profile["members"][user]["fairy_souls_collected"])

                        skill_averages.append(math.trunc(sum([Skyblock.SKILL_XP_REQUIREMENTS.index(
                            utils.level_from_table(profile["members"][user][f"experience_skill_{skill}"],
                                                   Skyblock.SKILL_XP_REQUIREMENTS[
                                                   :50] if skill in Skyblock.MAX_LEVEL_50_SKILLS else Skyblock.SKILL_XP_REQUIREMENTS)
                        ) + 1 for skill in skills]) / len(skills)))

                        if "slayer_bosses" in profile["members"][user]:
                            slayer_bosses = profile["members"][user]["slayer_bosses"]
                            for slayer in slayer_bosses:
                                try:
                                    if "level_7" in slayer_bosses[slayer]["claimed_levels"] or \
                                       "level_7_special" in slayer_bosses[slayer]["claimed_levels"]:
                                        slayers.append(7)
                                    if "level_9" in slayer_bosses[slayer]["claimed_levels"] or \
                                       "level_9_special" in slayer_bosses[slayer]["claimed_levels"]:
                                        slayers.append(9)
                                except KeyError:
                                    pass

                        pets = {}
                        if "pets" in profile["members"][user]:
                            for pet in profile["members"][user]["pets"]:
                                if pet["tier"] in Skyblock.PET_TIERS:
                                    if pet["type"] not in pets:
                                        if pet["heldItem"] in ["PET_ITEM_TOY_JERRY"]:
                                            pets[pet["type"]] = Skyblock.PET_TIERS[
                                                Skyblock.PET_TIERS.index(pet["tier"]) + 1]
                                        else:
                                            pets[pet["type"]] = pet["tier"]
                                    else:
                                        if Skyblock.PET_TIERS.index(pet["tier"]) > Skyblock.PET_TIERS.index(
                                                pets[pet["type"]]):
                                            # TODO: find the id for tier boosts and add it to the following line
                                            if pet["heldItem"] in ["PET_ITEM_TOY_JERRY"]:
                                                pets[pet["type"]] = Skyblock.PET_TIERS[
                                                    Skyblock.PET_TIERS.index(pet["tier"]) + 1]
                                            else:
                                                pets[pet["type"]] = pet["tier"]
                                else:
                                    await ctx.guild.get_member(DEV_ID) \
                                        .send(f"Invalid pet tier: `{pet['tier']}`")
                        profile_pet_score = 0
                        for _pet in pets:
                            profile_pet_score += Skyblock.PET_TIERS.index(pets[_pet]) + 1
                        if profile_pet_score > pet_score:
                            pet_score = profile_pet_score

                        if "experience" in profile["members"][user]["dungeons"]["dungeon_types"]["catacombs"]:
                            if profile["members"][user]["dungeons"]["dungeon_types"]["catacombs"]["experience"] > catacombs_xp:
                                catacombs_xp = profile["members"][user]["dungeons"]["dungeon_types"]["catacombs"][
                                    "experience"]
                                catacombs_level = Skyblock.CATACOMBS_XP_REQUIREMENTS.index(
                                    utils.level_from_table(catacombs_xp, Skyblock.CATACOMBS_XP_REQUIREMENTS)) + 1
                    except KeyError:
                        pass
            roles = []
            if max(skill_averages) >= 20:
                roles.append(Role.SkyblockRole.NOVICE_SKILLER)
            if max(skill_averages) >= 35:
                roles.append(Role.SkyblockRole.EXPERIENCED_SKILLER)
            if max(skill_averages) >= 50:
                roles.append(Role.SkyblockRole.MASTER_SKILLER)
            if max(souls) >= 210:
                roles.append(Role.SkyblockRole.FAIRY)
            if slayers:
                roles.append(Role.SkyblockRole.EXPERIENCED_SLAYER)
                if 9 in slayers:
                    roles.append(Role.SkyblockRole.SEASONED_SLAYER)
            if pet_score > 100:
                roles.append(Role.SkyblockRole.MENAGERIST)
            if catacombs_level >= 20:
                roles.append(Role.SkyblockRole.CATA_20)
                if catacombs_level >= 30:
                    roles.append(Role.SkyblockRole.CATA_30)
                    if catacombs_level >= 40:
                        roles.append(Role.SkyblockRole.CATA_40)
            embed = discord.Embed(title="Roles added :scroll:", color=0xfb00fd)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar)
            embed.set_thumbnail(url=f"https://mc-heads.net/head/{ign}")
            string = ""
            roles = [ctx.guild.get_role(role) for role in roles]
            for role in roles:
                string += f"\n{role.mention} {'[+]' if role not in ctx.author.roles else ''}"
            await ctx.author.add_roles(*roles)
            if not string:
                return await ctx.send(
                    embed=discord.Embed(title=":hear_no_evil: Oh no!",
                                        description="You don't qualify for any roles ):",
                                        color=0xff0000)
                        .set_footer(text="Think you deserve some roles? Make sure all API settings are enabled")
                        .set_author(name=ctx.author, icon_url=ctx.author.avatar))
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
        """View a tag"""
        for tag_object in self.tags:
            if tag.lower() == tag_object["name"].lower() or tag.lower() in [z.lower() for z in tag_object["aliases"]]:
                return await ctx.send(tag_object["response"],
                                      allowed_mentions=discord.AllowedMentions(roles=False, everyone=False))
        await ctx.send(f"Could not find a tag with that name.")

    @commands.command(name="tags")
    async def tags_command(self, ctx: commands.Context):
        """View a list of all saved tags"""
        tags = "\n".join([f"+ {z['name']} : {', '.join(z['aliases'])}" for z in self.tags])
        await ctx.send(f"All available tags: ```diff\n{tags}\n```",
                       allowed_mentions=discord.AllowedMentions(roles=False, everyone=False))

    @commands.command(hidden=True)
    @staff_only
    async def add_tag(self, ctx: commands.Context, name: str):
        """Add a new tag"""

        def check(message: discord.Message):
            return message.channel.id == ctx.channel.id and message.author.id == ctx.author.id

        await ctx.send("Send a comma-delimited list of aliases for this tag")
        try:
            aliases = [
                *map(str.strip, (await self.bot.wait_for("message", check=check, timeout=120.0)).content.split(","))]
            await ctx.send("Send the response for this tag")
            response = (await self.bot.wait_for("message", check=check, timeout=300)).content
        except asyncio.TimeoutError:
            return await ctx.send("Timed out")
        self.tags.append({"name": name, "aliases": aliases, "response": response})
        utils.save_file_json(self.tags, "config/tags")
        await ctx.send(f"Added tag `{name}`")

    @commands.command(hidden=True)
    @staff_only
    async def del_tag(self, ctx: commands.Context, *, tag: str):
        """Delete an unwanted tag"""
        for i, tag_object in enumerate(self.tags):
            if tag.lower() == tag_object["name"] or tag.lower() in [z.lower() for z in tag_object["aliases"]]:
                self.tags.pop(i)
                break
        utils.save_file_json(self.tags, "config/tags")
        await ctx.send(f"Deleted tag `{tag}`")


#     @commands.check(min_level(15))
#     @commands.cooldown(600, 1, BucketType.user)
#     @commands.guild_only()
#     @commands.command()
#     async def apply(self, ctx):
#         """Apply for staff"""
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
#                 answers[question] = (await self.bot.wait_for("message", check=message_check, timeout=600.0)).content
#             except asyncio.TimeoutError:
#                 ctx.command.reset_cooldown(ctx)
#                 return await ctx.author.send("application timed out")
#         confirmation_message = await ctx.author.send("Please confirm that the above information is correct and that you wish for this to be submitted as your staff application in Nullzee's cave discord server.")
#         await confirmation_message.add_reaction("✅")
#         await confirmation_message.add_reaction("❎")
#         try:
#             reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user.id == ctx.author.id and reaction.message.id == confirmation_message.id)
#         except asyncio.TimeoutError:
#             ctx.command.reset_cooldown(ctx)
#             return await ctx.author.send("application timed out")
#         if reaction.emoji == "❎":
#             ctx.command.reset_cooldown(ctx)
#             return await ctx.author.send("Application cancelled")
#         elif reaction.emoji == "✅":
#             embed = discord.Embed(title="Staff application", color=discord.Color.green()).set_author(name=ctx.author, icon_url=ctx.author.avatar)
#             embed.timestamp = datetime.datetime.now()
#             for answer in answers:
#                 embed.add_field(name=answer, value=answers[answer], inline=False)
#             await ctx.guild.get_channel(700267342482898965).send(embed=embed)
#             await ctx.author.send("Application submitted, good luck!")


async def setup(bot):
    await bot.add_cog(Util(bot, False))
