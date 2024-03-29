from discord.ext import commands
import typing

from helpers.constants import Role, Channel
from helpers.utils import Embed, TimeConverter, staff_only, staff_or_trainee, MemberUserConverter, nano_id, \
    get_file_json, save_file_json
import discord
from helpers import payloads, moderation_utils
import datetime
from EZPaginator import Paginator


async def mass_ban_internal(ctx, user: typing.Union[discord.Member, discord.User],
                            _time: int, message: discord.Message, _id):
    if isinstance(user, discord.Member):
        if user.guild_permissions.manage_messages:
            return await ctx.send("You cannot ban a moderator/administrator")
    reason = "Mass Banned"
    # Here it makes the payload that goes into the db, for individual user bans in the mass ban
    payload = payloads.ban_payload(offender_id=user.id, mod_id=ctx.author.id, duration=_time, reason=reason, _id=_id)
    payload = payloads.insert_message(payload, message)
    await ctx.guild.ban(user, reason=f"Mod: {ctx.author} | Reason: {reason}")
    await ctx.bot.moderation_coll.insert_one(payload)


class Moderation(commands.Cog, name="Moderation"):
    """Moderation commands, such as warn, mute, kick, etc"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot

    @commands.command(hidden=True)
    @staff_or_trainee
    async def warn(self, ctx, user: discord.Member, *, reason: str):
        """Give a user a warning"""
        payload = payloads.warn_payload(offender_id=user.id, mod_id=ctx.author.id, reason=reason)
        message = await ctx.send(embed=moderation_utils.chat_embed(ctx, payload))
        payload = payloads.insert_message(payload, message)
        await self.bot.moderation_coll.insert_one(payload)
        await moderation_utils.log(self.bot, payload)
        await moderation_utils.warn_punishments(ctx, user)
        try:
            await user.send(f"You were warned in {ctx.guild.name} for {reason}\nInfraction ID:`{payload['id']}`")
        except discord.Forbidden:
            await ctx.send("I could not dm them!")

    @commands.command(hidden=True, aliases=["shut"])
    @staff_or_trainee
    async def mute(self, ctx, user: discord.Member, _time: typing.Optional[TimeConverter] = None,
                   *, reason: str = "None"):
        """Mute a user"""
        if user.guild_permissions.manage_messages:
            return await ctx.send("You cannot mute a moderator/administrator")
        payload = payloads.mute_payload(offender_id=user.id, mod_id=ctx.author.id, duration=_time, reason=reason)
        message = await ctx.send(embed=moderation_utils.chat_embed(ctx, payload))
        payload = payloads.insert_message(payload, message)
        await user.add_roles(
            ctx.guild.get_role((await moderation_utils.get_config(self.bot))["mutedRole"]),
            reason=f"Mod: {ctx.author} | Reason: {reason[:400]}{'...' if len(reason) > 400 else ''}"
        )
        await self.bot.moderation_coll.insert_one(payload)
        await moderation_utils.log(self.bot, payload)
        time_string = payload["duration_string"]
        try:
            await user.send(
                f"You were muted in {ctx.guild.name} {f'for `{time_string}`' if _time else ''} "
                f"{f'for `{reason}`' if reason else ''}\nInfraction ID:`{payload['id']}`")
        except discord.Forbidden:
            await ctx.send("I could not dm them!")

    @commands.command(hidden=True)
    @staff_or_trainee
    async def unmute(self, ctx, user: discord.Member, *, reason: str = "None"):
        """Unmute a user"""
        await self.bot.moderation_coll.update_many({"offender_id": user.id, "type": "mute"}, {"$set": {"expired": True}})
        await user.remove_roles(
            ctx.guild.get_role((await moderation_utils.get_config(self.bot))["mutedRole"]),
            reason=f"Mod: {ctx.author} | Reason: {reason[:400]}{'...' if len(reason) > 400 else ''}"
        )
        await moderation_utils.end_log(self.bot, {"type": "mute", "offender_id": user.id},
                                       moderator=ctx.author, reason=reason)
        await ctx.send(embed=discord.Embed(description=f"Unmuted {user}", colour=discord.Colour.green()))

    @commands.command(hidden=True, aliases=["yeet"])
    @staff_or_trainee
    async def ban(self, ctx, user: MemberUserConverter, _time: typing.Optional[TimeConverter] = None,
                  *, reason: str = "None"):
        """Ban a user"""
        if isinstance(user, discord.Member):
            if user.guild_permissions.manage_messages:
                return await ctx.send("You cannot ban a moderator/administrator")
        payload = payloads.ban_payload(offender_id=user.id, mod_id=ctx.author.id, duration=_time, reason=reason)
        message = await ctx.send(embed=moderation_utils.chat_embed(ctx, payload))
        payload = payloads.insert_message(payload, message)
        time_string = payload["duration_string"]
        try:
            await user.send(
                f"You were banned from {ctx.guild.name} {f'for `{time_string}`' if _time else ''} "
                f"{f'for `{reason}`' if reason else ''}\nInfraction ID:`{payload['id']}`")
        except discord.Forbidden:
            pass
        await ctx.guild.ban(
            user, reason=f"Mod: {ctx.author} | Reason: {reason[:400]}{'...' if len(reason) > 400 else ''}"
        )
        await self.bot.moderation_coll.insert_one(payload)
        await moderation_utils.log(self.bot, payload)

    @commands.command(name="scamban", aliases=["sban", "syeet"], hidden=True)
    @staff_or_trainee
    async def scam_ban(self, ctx, user: MemberUserConverter, _time: typing.Optional[TimeConverter] = None):
        """
        Ban with a pre-set reason
        For hacked accounts sending scam/IP logger links
        """
        await ctx.invoke(self.bot.get_command("ban"), user, _time,
                         reason="Scam Links. When you regain access to your account, please DM a staff member "
                                "or rejoin and open a ticket on another account to be unbanned.")

    @commands.command(hidden=True, name="massban")
    @staff_only
    async def mass_ban(self, ctx, users: commands.Greedy[int], _time: typing.Optional[TimeConverter] = None):
        """
        Ban multiple users at once via user ID
        Mainly for use during raids with a list of user IDs
        """
        if not users:
            raise commands.UserInputError
        valid = []
        invalid = []
        for user_id in users:
            try:
                user = await MemberUserConverter().convert(ctx, str(user_id))
                valid.append(user)
            except commands.UserInputError:
                invalid.append(user_id)
        if valid:
            _id = nano_id()
            payload = payloads.mass_ban_payload(offenders=valid, mod_id=ctx.author.id, duration=_time,
                                                reason="Mass Ban", _id=_id)
            message = await ctx.send(embed=moderation_utils.mass_ban_chat_embed(ctx, payload))
            payload = payloads.insert_message(payload, message)
            for user in valid:
                await mass_ban_internal(ctx, user, _time, message, _id)
            await moderation_utils.log_mass(self.bot, payload)
        if invalid:
            invalid_users = "\n- ".join([str(z) for z in invalid])
            await ctx.send(f"Could not find the following users:\n```diff\n- {invalid_users}\n```")

    @commands.command(hidden=True)
    @staff_or_trainee
    async def unban(self, ctx, member, *, reason: str = "none"):
        """Unban a user"""
        try:
            await ctx.guild.unban(
                moderation_utils.BannedUser(member),
                reason=f"Mod: {ctx.author} | Reason: {reason[:400]}{'...' if len(reason) > 400 else ''}"
            )
        except (discord.NotFound, discord.HTTPException):
            return await ctx.send("Could not find a ban for that user")
        await moderation_utils.end_log(self.bot, {"type": "ban", "offender_id": member},
                                       moderator=ctx.author, reason=reason)
        await ctx.send(embed=discord.Embed(description=f"**{member} was unbanned**", color=discord.Colour.green()))

    @commands.command(name="delwarn", hidden=True)
    @staff_or_trainee
    async def delete_warn(self, ctx, _id: str):
        """Delete a warning from someone"""
        doc = await self.bot.moderation_coll.find_one({"id": _id})
        if not doc:
            return await ctx.send("Could not find that warning")
        else:
            await self.bot.moderation_coll.update_one(doc, {"$set": {"expired": True}})
            await ctx.send("Successfully deleted warning `{}`".format(_id))

    @commands.command(hidden=True, aliases=["boot"])
    @staff_or_trainee
    async def kick(self, ctx, user: discord.Member, *, reason: str = "none"):
        """Kick a user"""
        if user.guild_permissions.manage_messages:
            embed = discord.Embed(description="You cannot kick a moderator/administrator", color=0xff0000)
            return await ctx.send(embed=embed)
        payload = payloads.kick_payload(offender_id=user.id, mod_id=ctx.author.id, reason=reason)
        message = await ctx.send(embed=moderation_utils.chat_embed(ctx, payload))
        payload = payloads.insert_message(payload, message)
        await self.bot.moderation_coll.insert_one(payload)
        await moderation_utils.log(self.bot, payload)
        try:
            await user.send(
                f"You were kicked from {ctx.guild.name} "
                f"{f'for `{reason}`' if reason else 'No reason given'}\nInfraction ID:`{payload['id']}`"
            )
        except discord.Forbidden:
            pass
        await user.kick(reason=f"Mod: {ctx.author} | Reason: {reason[:400]}{'...' if len(reason) > 400 else ''}")

    @commands.command(hidden=True)
    @staff_or_trainee
    async def punishments(self, ctx, user: MemberUserConverter = None):
        """View a user's punishments"""
        user = user if user else ctx.author
        warnings = [z async for z in self.bot.moderation_coll.find({"offender_id": user.id, "expired": False})]
        embed = discord.Embed(title=f"{len(warnings)} punishments", colour=discord.Colour.green())
        embed.set_author(name=user, icon_url=user.avatar)
        for warning in warnings:
            embed.add_field(
                name=f"ID: {warning['id']} | {self.bot.get_user(warning['mod_id'])}",
                value=f"[{warning['type']}] {warning['reason']} - "
                      f"{datetime.datetime.fromtimestamp(warning['timestamp']).strftime('%d/%m/%Y, %H:%M:%S')}",
                inline=False)
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @staff_or_trainee
    async def warnings(self, ctx, user: MemberUserConverter = None):
        """View a user's warnings"""
        user = user if user else ctx.author
        warnings = [z async for z in self.bot.moderation_coll.find({
                    "offender_id": user.id, "expired": False, "type": "warn"})]
        embed = discord.Embed(title=f"{len(warnings)} warnings", colour=discord.Colour.green())
        embed.set_author(name=user, icon_url=user.avatar)
        for warning in warnings:
            embed.add_field(
                name=f"ID: {warning['id']} | {self.bot.get_user(warning['mod_id'])}",
                value=f"{warning['reason']} - "
                      f"{datetime.datetime.fromtimestamp(warning['timestamp']).strftime('%d/%m/%Y, %H:%M:%S')}",
                inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="modlogs", hidden=True)
    @staff_or_trainee
    async def moderation_logs(self, ctx, user: MemberUserConverter):
        """View all of a user's moderation logs"""
        user = user if user else ctx.author
        infractions = [z async for z in self.bot.moderation_coll.find({"offender_id": user.id})]
        if not infractions:
            return await ctx.send(f"No infractions found for {user}")
        embeds = [discord.Embed(title=f"All infractions for {user}", color=discord.Colour.orange())]
        embed_count = 0
        for i, infraction in enumerate(infractions):
            embeds[embed_count].add_field(
                name=f"{infraction['type']} | ID: {infraction['id']} | {self.bot.get_user(infraction['mod_id'])}",
                value=f"{infraction['reason'][:800]} - "
                      f"{datetime.datetime.fromtimestamp(infraction['timestamp']).strftime('%d/%m/%Y, %H:%M:%S')}",
                inline=False)
            if not i % 5 and i != 0:
                embed_count += 1
                embeds.append(discord.Embed(title=f"All infractions for {user}", color=discord.Colour.orange()))
        msg = await ctx.send(embed=embeds[0])
        if len(embeds) == 1:
            return
        for i, e in enumerate(embeds):
            e.set_footer(text=f"Page {i+1} of {len(embeds)}")
        pages = Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author)
        await pages.start()

    @commands.command(name="whereiswarn", hidden=True)
    @staff_or_trainee
    async def where_is_warn(self, ctx, warn: str):
        """Find where someone was warned"""
        warning = await self.bot.moderation_coll.find_one({"id": warn})
        if not warning:
            return await ctx.send("Could not find a warning with that ID")
        location = warning["message"].split("-")
        await ctx.send(f"https://discord.com/channels/{location[0]}/{location[1]}/{location[2]}")

    @commands.command(hidden=True)
    @staff_only
    async def lockdown(self, ctx, confirmation: bool = None):
        """
        Put the server into lockdown.

        While in lockdown:
        - All public channels are read-only
        - Tickets are disabled
        - All kicks and bans are logged, stored in a .txt file and sent in modlogs when lockdown is ended.
        """
        allowed = {}
        config = get_file_json("config")
        in_lockdown = config["lockdown"]

        default = ctx.guild.default_role
        level_one = ctx.guild.get_role(int(Role.LevelRoles.LEVELS["1"]))

        if confirmation is None or confirmation is False:
            def check(m):
                return m.channel == ctx.channel and m.author == ctx.author

            if in_lockdown:
                msg = await ctx.send(
                    "The server is currently in lockdown. Are you sure you want to lift lockdown? (`Y`/`N`)")
            else:
                msg = await ctx.send(
                    "The server is not currently in lockdown. Are you sure you want to enter lockdown? (`Y`/`N`)")
            message = await self.bot.wait_for("message", timeout=60, check=check)
            await msg.delete()
            await message.delete()
            if message.content.lower() not in ["y", "yes"]:
                return

        for channel_id in Channel.lockdown_channels():
            channel = ctx.guild.get_channel(channel_id)
            overwrites = channel.overwrites

            if not in_lockdown:
                if level_one in overwrites and overwrites[level_one].send_messages is not False:
                    perms = channel.overwrites_for(level_one)
                    perms.send_messages = False
                    await channel.set_permissions(level_one, overwrite=perms, reason="Lockdown")
                    allowed[str(channel.id)] = "level_one"
                if default in overwrites and overwrites[default].send_messages is not False:
                    perms = channel.overwrites_for(default)
                    perms.send_messages = False
                    await channel.set_permissions(default, overwrite=perms, reason="Lockdown")
                    allowed[str(channel.id)] = "default"
            else:
                if str(channel.id) in config["lockdown_channel_perms"] and \
                   config["lockdown_channel_perms"][str(channel.id)] == "default":
                    perms = channel.overwrites_for(default)
                    perms.send_messages = None
                    await channel.set_permissions(default, overwrite=perms, reason="Lockdown Lifted")
                    allowed[str(channel.id)] = "default"
                if str(channel.id) in config["lockdown_channel_perms"] and \
                   config["lockdown_channel_perms"][str(channel.id)] in ["default", "level_one"]:
                    perms = channel.overwrites_for(level_one)
                    perms.send_messages = None
                    await channel.set_permissions(level_one, overwrite=perms, reason="Lockdown Lifted")
                    allowed[str(channel.id)] = "level_one"

        dt = datetime.datetime.now()
        if in_lockdown:
            data = moderation_utils.get_lockdown_log()
            formatted_data = f"--------------------------------------------------" \
                             f"\nLockdown - Ended @ {dt.strftime('%M:%S %d/%m/%Y')}\n"
            if data:
                for user in data:
                    formatted_data += f"\n{user} " \
                                      f"({data[user]['name']}): {data[user]['type'].upper()} - {data[user]['reason']}"
                formatted_data += f"\n\nRaw ID's:\n"
                for user in data:
                    formatted_data += f"\n{user}"
            else:
                formatted_data += "\nNo Data"
            formatted_data += "\n--------------------------------------------------\n\n\n"
            with open(f"lockdown_logs/{dt.strftime('%d-%m-%Y')}.txt", "a+") as f:
                f.write(formatted_data)
            moderation_utils.reset_lockdown_log()

        if not in_lockdown:
            await ctx.send("Entered lockdown.")
            embed = Embed(ctx.author, title="Entered Lockdown", colour=0xFF0000)
            embed.auto_author().timestamp_now()
            await ctx.guild.get_channel(Channel.MOD_LOGS).send(embed=embed)
            config["lockdown_channel_perms"] = allowed
            config["lockdown"] = True
        else:
            await ctx.send("Lifted lockdown.")
            embed = Embed(ctx.author, title="Lifted Lockdown", colour=discord.Colour.green())
            embed.auto_author().timestamp_now()
            log_file = discord.File(f"lockdown_logs/{dt.strftime('%d-%m-%Y')}.txt")
            await ctx.guild.get_channel(Channel.MOD_LOGS).send(embed=embed, file=log_file)
            config["lockdown_channel_perms"] = {}
            config["lockdown"] = False

        save_file_json(config)

    @commands.command(hidden=True)
    @staff_only
    async def lock(self, ctx, channel: discord.TextChannel):
        """Lock a channel"""
        allowed = {}
        default = ctx.guild.default_role
        level_one = ctx.guild.get_role(int(Role.LevelRoles.LEVELS["1"]))

        overwrites = channel.overwrites
        if level_one in overwrites and overwrites[level_one].send_messages is not False:
            perms = channel.overwrites_for(level_one)
            perms.send_messages = False
            await channel.set_permissions(level_one, overwrite=perms, reason="Locked")
            allowed[str(channel.id)] = "level_one"
        if default in overwrites and overwrites[default].send_messages is not False:
            perms = channel.overwrites_for(default)
            perms.send_messages = False
            await channel.set_permissions(default, overwrite=perms, reason="Locked")
            allowed[str(channel.id)] = "default"

        config = get_file_json("config")

        for channel_data in allowed:
            if str(channel_data) in config["lockdown_channel_perms"]:
                if Channel.lockdown_priority() \
                   .index(config["lockdown_channel_perms"][str(channel_data)]) < allowed[str(channel_data)]:
                    continue
                else:
                    config["lockdown_channel_perms"][str(channel_data)] = allowed[str(channel_data)]
            else:
                config["lockdown_channel_perms"][str(channel_data)] = allowed[str(channel_data)]
        save_file_json(config)
        await ctx.send(embed=discord.Embed(description=f"Locked {channel.mention}", colour=0xFF0000))
        await moderation_utils.log_channel_lock(ctx, channel, "lock")

    @commands.command(hidden=True)
    @staff_only
    async def unlock(self, ctx, channel: discord.TextChannel):
        """Unlock a locked channel"""
        allowed = {}
        default = ctx.guild.default_role
        level_one = ctx.guild.get_role(int(Role.LevelRoles.LEVELS["1"]))

        config = get_file_json("config")

        if str(channel.id) in config["lockdown_channel_perms"] and \
           config["lockdown_channel_perms"][str(channel.id)] == "default":
            perms = channel.overwrites_for(default)
            perms.send_messages = None
            await channel.set_permissions(default, overwrite=perms, reason="Unlocked")
            allowed[str(channel.id)] = "default"
        if str(channel.id) in config["lockdown_channel_perms"] and \
           config["lockdown_channel_perms"][str(channel.id)] in ["default", "level_one"]:
            perms = channel.overwrites_for(level_one)
            perms.send_messages = None
            await channel.set_permissions(level_one, overwrite=perms, reason="Unlocked")
            allowed[str(channel.id)] = "level_one"

        for channel_data in allowed:
            if str(channel_data) in config["lockdown_channel_perms"]:
                del config["lockdown_channel_perms"][str(channel_data)]
        save_file_json(config)
        await ctx.send(embed=discord.Embed(description=f"Unlocked {channel.mention}", colour=discord.Colour.green()))
        await moderation_utils.log_channel_lock(ctx, channel, "unlock")

    async def cog_after_invoke(self, ctx):
        await ctx.message.delete()
                

async def setup(bot):
    await bot.add_cog(Moderation(bot, True))
