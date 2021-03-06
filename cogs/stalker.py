import discord
from discord.ext import commands

from core import check, rubbercog, utils
from core.config import config
from core.text import text
from repository import user_repo

repository = user_repo.UserRepository()


class Stalker(rubbercog.Rubbercog):
    """A cog for database lookups"""

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    def dbobj2email(self, dbobj):
        if dbobj is not None:
            if dbobj.group == "FEKT":
                email = (
                    dbobj.login + "@stud.feec.vutbr.cz" if "@" not in dbobj.login else dbobj.login
                )
            elif dbobj.group == "VUT":
                email = dbobj.login + "@vutbr.cz" if "@" not in dbobj.login else dbobj.login
            else:
                email = dbobj.login
            return email
        return

    @commands.check(check.is_verified)
    @commands.group(name="whois", aliases=["gdo"])
    async def whois(self, ctx: commands.Context):
        """Get information about user"""
        await utils.send_help(ctx)

    @whois.command(name="member", aliases=["tag", "user", "id"])
    async def whois_member(
        self, ctx: commands.Context, member: discord.Member = None, log: bool = True
    ):
        """Get information about guild member

        member: A guild member
        pin: A "pin" string that will prevent the embed from disappearing
        """
        if member is None:
            return await utils.send_help(ctx)

        # get user from database
        try:
            dbobj = repository.filterId(discord_id=member.id)[0]
        except IndexError:
            dbobj = None

        embed = self.embed(ctx=ctx, description=member.mention)

        ni = discord.utils.escape_markdown(member.nick) if member.nick else None
        na = discord.utils.escape_markdown(member.name)
        n = f"**{na}** (nick **{ni}**)" if ni else f"**{na}**"
        embed.add_field(
            name="Discord user data",
            value="{name}\n{d_id}\nMember since {date}".format(
                name=n, d_id=member.id, date=member.joined_at.strftime("%Y-%m-%d")
            ),
        )

        # do not display sensitive information in public channels
        if dbobj is not None and ctx.channel.id == config.channel_mods:
            # private channel, found in database
            email = self.dbobj2email(dbobj)
            if dbobj.changed and len(dbobj.changed) == 8:
                d = dbobj.changed
                date = d[:4] + "-" + d[4:6] + "-" + d[6:]
            elif dbobj.changed:
                date = dbobj.changed
            else:
                date = "_none_"
            embed.add_field(name="E-mail", value=email if email else "_none_", inline=False)
            embed.add_field(name="Verification code", value=dbobj.code if dbobj.code else "_none_")
            embed.add_field(name="Status", value=dbobj.status if dbobj.status else "_none_")
            embed.add_field(name="Last changed", value=date)
            if dbobj.comment is not None and len(dbobj.comment) > 0:
                embed.add_field(name="Comment", value=dbobj.comment, inline=False)

        elif not dbobj and ctx.channel.id == config.channel_mods:
            # private channel, not found
            embed.add_field(name="Not in database", value="Server only", inline=False)

        elif dbobj is not None and ctx.channel.id != config.channel_mods:
            # public channel
            embed.add_field(
                inline=False, name="Status", value=dbobj.status if dbobj.status else "_none_"
            )
            if dbobj.comment is not None and len(dbobj.comment) > 0:
                embed.add_field(name="Comment", value=dbobj.comment, inline=False)

        role_list = ", ".join(list((m.name) for m in member.roles[::-1])[:-1])
        embed.add_field(
            inline=False, name="Roles", value=role_list if len(role_list) > 0 else "_none_"
        )

        await ctx.send(embed=embed, delete_after=config.delay_embed)
        await self.event.user(ctx.author, ctx.channel, f"Database lookup for {member}")

        await utils.delete(ctx)

    @whois.command(name="login", aliases=["xlogin", "vutlogin"])
    @commands.check(check.is_elevated)
    async def whois_login(self, ctx: commands.Context, login: str = None, log: bool = True):
        """Get information about xlogin

        login: A xlogin
        """
        if login is None:
            return await utils.send_help(ctx)

        # get user from database
        try:
            dbobj = repository.filterLogin(login=login)[0]
            member = self.getGuild().get_member(dbobj.discord_id)
        except IndexError:
            member = None

        if member:
            await self.whois_member(ctx, member, log=True)
            return

        embed = discord.embed(ctx=ctx)
        embed.add_field(name="Action unsuccessful", value="No user **{}** found.".format(login))

        await ctx.send(embed=embed, delete_after=config.delay_embed)
        await self.event.user(ctx.author, ctx.channel, f"Database lookup for {member}")

        await utils.delete(ctx)

    @whois.command(name="logins", aliases=["emails"])
    @commands.check(check.is_elevated)
    async def whois_logins(self, ctx, login_prefix: str):
        """Filter database by login"""
        users = repository.getByPrefix(prefix=login_prefix)

        # parse data
        items = []
        template = "`{name:<10}` … {email}"
        for user in users:
            member = self.bot.get_user(user.discord_id)
            name = member.name if member is not None else ""
            if user.group == "FEKT" and "@" not in user.login:
                email = user.login + "@stud.feec.vutbr.cz"
            elif user.group == "VUT" and "@" not in user.login:
                email = user.login + "@vutbr.cz"
            else:
                email = user.login
            items.append(template.format(name=name, email=email))

        # construct embed fields
        fields = []
        field = ""
        for item in items:
            if len(field + item) > 1000:
                fields.append(field)
                field = ""
            field = field + "\n" + item
        fields.append(field)

        # create embed
        embed = self.embed(ctx=ctx, description=f"{len(users)} result(s)")
        for field in fields[:5]:  # there is a limit of 6000 characters in total
            embed.add_field(name="\u200b", value=field)
        if len(fields) > 5:
            embed.add_field(name="Too many results", value="Some results were omitted")

        await ctx.send(embed=embed, delete_after=config.delay_embed)
        await self.event.sudo(ctx.author, ctx.channel, f"E-mail lookup: `{login_prefix}`")

        await utils.delete(ctx)

    @commands.guild_only()
    @commands.group(aliases=["db"])
    @commands.check(check.is_elevated)
    async def database(self, ctx: commands.Context):
        """Manage users"""
        await utils.send_help(ctx)

    @database.command(name="add")
    async def database_add(
        self,
        ctx: commands.Context,
        member: discord.Member = None,
        login: str = None,
        group: discord.Role = None,
    ):
        """Add user to database

        member: A server member
        login: xlogin (FEKT, VUT) or e-mail
        group: A role from `roles_native` or `roles_guest` in config file
        """
        if member is None or login is None or group is None:
            return await utils.send_help(ctx)

        # define variables
        guild = self.bot.get_guild(config.guild_id)
        verify = discord.utils.get(guild.roles, name="VERIFY")

        # try to write to database
        try:
            repository.filterId(discord_id=member.id)[0]
            return await self.output.error(ctx, text.get("db", "duplicate"))
        except IndexError:
            # no result is good, we won't have collision
            pass

        try:
            repository.add_user(
                discord_id=member.id,
                login=login,
                group=group.name,
                status="verified",
                code="MANUAL",
            )
        except Exception as e:
            return await self.output.error(ctx, text.get("db", "write"), e)

        # assign roles, if neccesary
        if verify not in member.roles:
            await member.add_roles(verify)
        if group not in member.roles:
            await member.add_roles(group)

        # display the result
        await self.whois_member(ctx, member, log=False)

        await self.event.sudo(ctx.author, ctx.channel, f"New user {member} ({group.name})")

    @database.command(name="remove", aliases=["delete"])
    async def database_remove(
        self, ctx: commands.Context, member: discord.Member = None, force: str = None
    ):
        """Remove user from database

        member: A server member
        force: "force" string. If omitted, show what will be deleted
        """
        if member is None:
            return await utils.send_help(ctx)

        # define variables
        guild = self.bot.get_guild(config.guild_id)
        force = self.parseArg(force)

        try:
            if force:
                result = repository.deleteId(discord_id=member.id)
            else:
                result = repository.filterId(discord_id=member.id)
        except Exception as e:
            return await self.output.error(ctx, text.get("db", "read"), e)

        d = "Result" if force else "Simulation, run with `force` to apply"
        if force:
            embed = self.embed(description=d, color=config.color_success)
            # delete
            if result is None or result < 1:
                return await self.output.error(ctx, text.get("db", "delete error"))
            embed.add_field(
                inline=False, name="Success", value=text.fill("db", "delete success", num=result)
            )
            embed.add_field(name="Warning", value="Roles and channel access haven't been removed")
            await self.event.sudo(
                ctx.author, ctx.channel, "User removed from database: " + member.name
            )
            # TODO remove all roles
        else:
            # simulate
            embed = discord.Embed(color=config.color_notify, description=d)
            for r in result:
                embed.add_field(
                    inline=False,
                    name=self.dbobj2email(r),
                    value=discord.utils.get(guild.members, id=int(r.discord_id)).mention,
                )
            if len(result) < 1:
                embed.add_field(name="No entry", value=text.get("db", "not found"), inline=False)
        await ctx.send(embed=embed, delete_after=config.delay_embed)

        await utils.delete(ctx)

    @database.command(name="update")
    async def database_update(self, ctx, member: discord.Member, key: str, *, value):
        """Update user entry in database

        key: value
        - login: e-mail
        - group: one of the groups defined in gatekeeper mapping
        - status: [unknown, pending, verified, kicked, banned, quarantined]
        - comment: commentary on user
        """
        if key not in ("login", "group", "status", "comment"):
            raise commands.BadArgument("Invalid key.")

        if key == "login":
            repository.update(member.id, login=value)
        elif key == "group":
            # get list of role names, defined in
            role_ids = config.get("roles", "native") + config.get("roles", "guests")
            role_names = [
                x.name for x in [self.bot.get_role(x) for x in role_ids] if hasattr(x, "name")
            ]
            value = value.upper()
            if value not in role_names:
                raise commands.BadArgument("Invalid value.")
            repository.update(member.id, group=value)
        elif key == "status":
            if value not in ("unknown", "pending", "verified", "kicked", "banned", "quarantined"):
                raise commands.BadArgument("Invalid value.")
        elif key == "comment":
            repository.update(member.id, comment=value)

        self.event.sudo(ctx.author, ctx.channel, f"Updated {member}: {key} = {value}.")

    @database.command(name="show")
    async def database_show(self, ctx, param: str):
        """Filter users by parameter

        param: [unverified, pending, kicked, banned]
        """
        if param not in ("unverified", "pending", "kicked", "banned"):
            return await utils.send_help(ctx)

        await self._database_show_filter(ctx, param)

    @commands.guild_only()
    @commands.command(name="guild", aliases=["server"])
    async def guild(self, ctx: commands.Context):
        """Display general about guild"""
        embed = self.embed(ctx=ctx)
        g = self.getGuild()

        # guild
        embed.add_field(
            name=f"Guild **{g.name}**",
            inline=False,
            value=f"Created {g.created_at.strftime('%Y-%m-%d')}," f" owned by **{g.owner.name}**",
        )

        # verification
        states = ", ".join(
            "**{}** {}".format(repository.countStatus(state), state) for state in config.db_states
        )
        embed.add_field(name="Verification states", value=states, inline=False)

        # roles
        role_ids = config.get("roles", "native") + config.get("roles", "guests")
        roles = []
        for role_id in role_ids:
            role = self.getGuild().get_role(role_id)
            if role is not None:
                roles.append(f"**{role}** {repository.countGroup(role.name)}")
            else:
                roles.append(f"**{role_id}** {repository.countGroup(role_id)}")
        roles = ", ".join(roles)
        embed.add_field(name="Roles", value=f"Total count {len(g.roles)}\n{roles}", inline=False)

        # channels
        embed.add_field(
            name=f"{len(g.categories)} categories",
            value=f"{len(g.text_channels)} text channels, {len(g.voice_channels)} voice channels",
        )

        # users
        embed.add_field(
            name="Users",
            value=f"Total count **{g.member_count}**, {g.premium_subscription_count} boosters",
        )

        await ctx.send(embed=embed, delete_after=config.delay_embed)
        await utils.delete(ctx)

    async def _database_show_filter(self, ctx: commands.Context, status: str = None, pin=False):
        """Helper function for all databas_show_* functions"""
        if status is None or status not in config.db_states:
            return await utils.send_help(ctx)

        users = repository.filterStatus(status=status)

        embed = self.embed(ctx=ctx)
        embed.add_field(name="Result", value="{} users found".format(len(users)), inline=False)
        if users:
            embed.add_field(name="-" * 60, value="LIST:", inline=False)
        for user in users:
            member = discord.utils.get(self.getGuild().members, id=user.discord_id)
            if member:
                name = "**{}**, {}".format(member.name, member.id)
            else:
                name = "**{}**, {} _(not on server)_".format(user.discord_id, user.group)
            d = user.changed
            date = (d[:4] + "-" + d[4:6] + "-" + d[6:]) if (d and len(d) == 8) else "_(none)_"
            embed.add_field(
                name=name, value="{}\nLast action on {}".format(self.dbobj2email(user), date)
            )

        await ctx.send(embed=embed, delete_after=config.delay_embed)

        await utils.delete(ctx)


def setup(bot):
    bot.add_cog(Stalker(bot))
