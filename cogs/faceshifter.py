import discord
from discord.ext import commands

from core import check, rubbercog
from core.config import config
from core.text import text
from repository.subject_repo import SubjectRepository

repo_s = SubjectRepository()


class Faceshifter(rubbercog.Rubbercog):
    """Manage roles and subjects"""

    def __init__(self, bot):
        super().__init__(bot)
        self.limit_programmes = None
        self.limit_interests = None

    ##
    ## Getters
    ##

    def getLimitProgrammes(self, ctx: commands.Context) -> discord.Role:
        if self.limit_programmes is None:
            self.limit_programmes = discord.utils.get(ctx.guild.roles, name="---PROGRAMMES")
        return self.limit_programmes

    def getLimitInterests(self, ctx: commands.Context) -> discord.Role:
        if self.limit_interests is None:
            self.limit_interests = discord.utils.get(ctx.guild.roles, name="---INTERESTS")
        return self.limit_interests

    ##
    ## Commands
    ##

    @commands.guild_only()
    @commands.check(check.is_verified)
    @commands.group(name="subject")
    async def subject(self, ctx):
        """Add or remove subject"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.invoked_with)

    @subject.command(name="add")
    async def subject_add(self, ctx, *, subjects: str):
        """Add subject

        subjects: Space separated subject shortcuts
        """
        subjects = self.sanitise(subjects, limit=200).split(" ")
        for subject in subjects:
            channel = await self._get_subject(ctx, subject)
            if channel is None:
                await ctx.send("předmětovou místnost {subject} tu nemáme.")
            else:
                await self._subject_add(ctx, ctx.author, channel)

        await ctx.send("hotovo ^.^")

    @subject.command(name="remove")
    async def subject_remove(self, ctx, *, subjects: str):
        """Remove subject

        subjects: Space separated subject shortcuts
        """
        subjects = self.sanitise(subjects, limit=200).split(" ")
        for subject in subjects:
            channel = await self._get_subject(ctx, subject)
            if channel is None:
                await ctx.send("předmětovou místnost {subject} tu nemáme.")
            else:
                await self._subject_remove(ctx, ctx.author, channel)

        await ctx.send("hotovo ^.^")

    @commands.guild_only()
    @commands.check(check.is_verified)
    @commands.group(name="role", aliases=["programme"])
    async def role(self, ctx):
        """Add or remove role"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.invoked_with)

    @role.command(name="add")
    async def role_add(self, ctx, *, roles: str):
        """Add role

        roles: Space separated role shortcuts
        """
        roles = self.sanitise(roles, limit=200).split(" ")
        for role in roles:
            guild_role = await self._get_role(ctx, role)
            if guild_role is None:
                await ctx.send("roli {role} tu nemáme")
            else:
                await self._role_add(ctx, ctx.author, guild_role)

        await ctx.send("hotovo ^.^")

    @role.command(name="remove")
    async def role_remove(self, ctx, *, roles: str):
        """Remove role

        roles: Space separated role shortcuts
        """
        roles = self.sanitise(roles, limit=200).split(" ")
        for role in roles:
            guild_role = await self._get_role(ctx, role)
            if guild_role is None:
                await ctx.send("roli {role} tu nemáme")
            else:
                await self._role_remove(ctx, ctx.author, guild_role)

        await ctx.send("hotovo ^.^")

    ##
    ## Listeners
    ##

    @commands.Cog.listener()
    async def on_message(self, message):
        pass

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        pass

    ##
    ## Helper functions
    ##
    async def _get_role(self, ctx, role: str) -> discord.Role:
        return discord.utils.get(ctx.guild.roles, name=role)

    async def _get_subject(self, ctx, shortcut: str) -> discord.TextChannel:
        return discord.utils.get(ctx.guild.text_channels, name=shortcut)

    async def _message_to_tuple(self, message: discord.Message) -> tuple:
        pass

    async def _reaction_payload_to_tuple(self, payload: discord.RawMessageUpdateEvent) -> tuple:
        # _parsePayload()
        pass

    ##
    ## Logic
    ##
    async def _subject_add(self, ctx, member: discord.Member, channel: discord.TextChannel):
        # check permission
        for subject_role in config.get("faceshifter", "subject roles"):
            if subject_role in [r.id for r in member.roles]:
                break
        else:
            # they do not have neccesary role
            await ctx.send("na to nemáš právo, nejsi z VUT ^.^")
            return

        await channel.set_permissions(member, view_channel=True)

    async def _subject_remove(self, ctx, member: discord.Member, channel: discord.TextChannel):
        # we do not need to check for permissions
        await channel.set_permissions(member, overwrite=None)

    async def _role_add(self, ctx, member: discord.Member, role: discord.Role):
        if role < self.getLimitProgrammes(ctx) and role > self.getLimitInterests(ctx):
            # role is programme, check if user has permission
            for programme_role in config.get("faceshifter", "programme roles"):
                if programme_role in [r.id for r in member.roles]:
                    break
            else:
                await ctx.send("na to nemáš právo, nejsi z FEKTu ^.^")
                return
        elif role < self.getLimitInterests(ctx):
            # role is below interests limit, continue
            pass
        else:
            # role is limit itself or something above programmes
            await ctx.send("do takových rolí nesmíš sahat!")
            return

        await member.add_roles(role)

    async def _role_remove(self, ctx, member: discord.Member, role: discord.Role):
        if role < self.getLimitProgrammes(ctx) and role > self.getLimitInterests(ctx):
            # role is programme, check if user has permission
            for programme_role in config.get("faceshifter", "programme roles"):
                if programme_role in [r.id for r in member.roles]:
                    break
            else:
                await ctx.send("na to nemáš právo, nejsi z FEKTu ^.^")
                return
        elif role < self.getLimitInterests(ctx):
            # role is below interests limit, continue
            pass
        else:
            # role is limit itself or something above programmes
            await ctx.send("do takových rolí nesmíš sahat!")
            return

        await member.remove_roles(role)


def setup(bot):
    bot.add_cog(Faceshifter(bot))
