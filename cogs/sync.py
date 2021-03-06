import re
import time
import json
import random
import asyncio
import datetime
from operator import itemgetter

import discord
from discord.ext import commands

from core import check, rubbercog, utils
from cogs import creator, errors
from core.text import text
from core.config import config
from repository import user_repo

repository = user_repo.UserRepository()

# flake8: noqa
# TODO: Fix it all


class Sync(rubbercog.Rubbercog):
    """Master-Slave server synchronization"""

    def __init__(self, bot):
        super().__init__(bot)
        self.errors = errors.Errors(bot)
        self.rubbercog = rubbercog.Rubbercog(bot)
        self.creator = creator.Creator(bot)
        self.visible = False

    @commands.group("sync")
    @commands.check(check.is_mod)
    @commands.check(check.is_in_modroom)
    async def sync(self, ctx: commands.Context):
        """Synchronization cog"""
        await utils.send_help(ctx)

    @sync.command(name="roles")
    async def sync_roles(self, ctx: commands.Context):
        """Synchronize roles from master to slave."""
        if ctx.message.guild == self.getGuild():
            guild = self.getGuild()
            slave = self.getSlave()
            channel = ctx.message.channel
            master_roles = await guild.fetch_roles()

            for role in master_roles:
                slave_role = discord.utils.get(slave.roles, name=role.name)
                if slave_role is not None:
                    r = [role.position, role.hoist, role.mentionable, role.permissions, role.colour]
                    a = [
                        slave_role.position,
                        slave_role.hoist,
                        slave_role.mentionable,
                        slave_role.permissions,
                        slave_role.colour,
                    ]
                    if a != r:
                        await asyncio.sleep(0.5)
                        await self.creator.edit_role(
                            ctx,
                            slave,
                            slave_role,
                            position=role.position,
                            hoist=role.hoist,
                            mentionable=role.mentionable,
                            permissions=role.permissions,
                            color=role.colour,
                        )
                else:
                    await asyncio.sleep(0.5)
                    await self.creator.create_role(
                        ctx,
                        slave,
                        name=role.name,
                        hoist=role.hoist,
                        mentionable=role.mentionable,
                        permissions=role.permissions,
                        color=role.colour,
                    )
                    # API is not a fan of creation and quick edit of roles (can't create one at a position tho)
        await channel.send("Synchronizování rolí dokončeno.")
        return

    @sync.command(name="members")
    async def sync_members(self, ctx: commands.Context):
        """Synchronize member roles from master to slave.
        Only use for first time, automatic synchronization is used when cog loaded.
        Potentially slow depending on the number of users in slave."""
        slave = self.getSlave()
        guild = self.getGuild()
        channel = ctx.message.channel
        members = await slave.fetch_members().flatten()

        for member in members:
            main_member = discord.utils.get(guild.members, id=member.id)
            if member is not None:
                after_roles = []
                member_roles = []

                for role in main_member.roles:
                    after_roles.append(role.name)
                    slave_role = discord.utils.get(slave.roles, name=role.name)
                    if slave_role is not None:
                        for r in member.roles:
                            member_roles.append(r.name)
                            if r.name == role.name:
                                break
                        else:
                            if config.debug:
                                print("Adding role: " + slave_role.name + " to " + member.name)
                            try:
                                await member.add_roles(slave_role)
                            except Exception as e:
                                embed = discord.Embed(
                                    title="on_member_update Exception",
                                    description="add_roles() failed",
                                    color=config.color_error,
                                )
                                embed.add_field(name="Role", value=slave_role.name)
                                embed.add_field(name="User", value=member.mention)
                                embed.add_field(name="Exception", value=e)
                                channel = self.bot.get_channel(config.channel_botlog)
                                await channel.send(embed=embed)

                    else:
                        await config.channel_botlog.send(
                            "Slave role {} neexistuje".format(slave_role.name)
                        )

                for name in member_roles:
                    if name not in after_roles:
                        role = discord.utils.get(slave.roles, name=name)
                        if config.debug:
                            print("Removing role: " + role.name + " from " + member.name)
                        try:
                            await member.remove_roles(role)
                        except Exception as e:
                            embed = discord.Embed(
                                title="on_member_update Exception",
                                description="remove_roles() failed",
                                color=config.color_error,
                            )
                            embed.add_field(name="Role", value=role.name)
                            embed.add_field(name="User", value=member.mention)
                            embed.add_field(name="Exception", value=e)
                            channel = self.bot.get_channel(config.channel_botlog)
                            await channel.send(embed=embed)

        if config.debug:
            print("Role sync finished")
        await channel.send("Synchronizování rolí uživatelů dokončeno.")
        return

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        server = role.guild
        if server == self.getGuild() and self.getSlave() != 0:
            guild = self.getSlave()
        else:
            return

        await asyncio.sleep(1)

        r = discord.utils.get(guild.roles, name=role.name)
        if r is None:
            await self.creator.create_role(
                None,
                guild,
                name=role.name,
                hoist=role.hoist,
                mentionable=role.mentionable,
                permissions=role.permissions,
                color=role.colour,
            )
        return

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if self.creator.isRunning() == False:
            server = before.guild
            # DO NOT allow changes from more than 1 server, just stick to master-slaves relationship and save your sanity
            if server == self.getGuild() and self.getSlave() != 0:
                guild = self.getSlave()
            else:
                return

            slave_role = discord.utils.get(guild.roles, name=before.name)

            if slave_role is not None:
                role = None
                now = time.time()
                timeout = 10
                await asyncio.sleep(2)
                while role is None:
                    if time.time() > now + timeout:
                        break
                    role = discord.utils.get(guild.roles, name=before.name)
                r = [role.name, role.hoist, role.mentionable, role.permissions, role.colour]
                a = [after.name, after.hoist, after.mentionable, after.permissions, after.colour]

                # ignoring positional changes of 1 (otherwise brace for a storm)
                if abs(int(before.position) - int(after.position)) > 1 or a != r:
                    await self.creator.edit_role(
                        None,
                        guild,
                        role,
                        name=after.name,
                        position=after.position,
                        hoist=after.hoist,
                        mentionable=after.mentionable,
                        permissions=after.permissions,
                        color=after.colour,
                    )
            else:
                embed = discord.Embed(
                    title="Role does not exist",
                    description="role update failed",
                    color=config.color_error,
                )
                embed.add_field(
                    name="Role",
                    value="Before name: {} After name: {}".format(before.name, after.name),
                )
                embed.add_field(name="Advice", value="Manual role sync recommended")
                channel = self.bot.get_channel(config.channel_guildlog)
                await channel.send(embed=embed)

        return

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        server = role.guild
        if server == self.getGuild() and self.getSlave() != 0:
            guild = self.getSlave()
        else:
            return

        await asyncio.sleep(1)
        role = discord.utils.get(guild.roles, name=role.name)
        if role is not None:
            if config.debug:
                print("Deleting role {} at {}".format(role.name, guild.name))

            try:
                await role.delete()
            except Exception as e:
                embed = discord.Embed(
                    title="on_guild_role_delete Exception",
                    description="role.delete() failed",
                    color=config.color_error,
                )
                embed.add_field(name="Role", value=role.name)
                embed.add_field(name="Exception", value=e)
                channel = self.bot.get_channel(config.channel_botlog)
                await channel.send(embed=embed)
        return

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild == self.getSlave():
            guild = self.getGuild()
            main_member = discord.utils.get(guild.members, id=member.id)
            if main_member is not None:
                for role in main_member.roles:
                    slave_role = discord.utils.get(self.getSlave().roles, name=role.name)
                    if slave_role is not None:
                        for r in member.roles:
                            if r.name == role.name:
                                break
                        else:
                            if config.debug:
                                print("Adding role: " + slave_role.name + " to " + member.name)
                            try:
                                await member.add_roles(slave_role)
                            except Exception as e:
                                embed = discord.Embed(
                                    title="on_member_update Exception",
                                    description="add_roles() failed",
                                    color=config.color_error,
                                )
                                embed.add_field(name="Role", value=slave_role.name)
                                embed.add_field(name="User", value=member.mention)
                                embed.add_field(name="Exception", value=e)
                                channel = self.bot.get_channel(config.channel_botlog)
                                await channel.send(embed=embed)

                    else:
                        embed = discord.Embed(
                            title="Role does not exist",
                            description="Adding role on slave failed",
                            color=config.color_error,
                        )
                        embed.add_field(name="Role", value="Role name: {}".format(role.name))
                        embed.add_field(name="Advice", value="Manual role sync recommended")
                        channel = self.bot.get_channel(config.channel_guildlog)
                        await channel.send(embed=embed)
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild == self.getGuild() and self.getSlave() != 0:

            slave = self.getSlave()
            slave_member = discord.utils.get(slave.members, id=member.id)
            if slave_member is not None:
                if config.debug:
                    print("Removing member " + slave_member.name)
                try:
                    await slave_member.kick()
                except Exception as e:
                    embed = discord.Embed(
                        title="on_member_remove Exception",
                        description="member.kick() failed",
                        color=config.color_error,
                    )
                    embed.add_field(name="User", value=member.mention)
                    embed.add_field(name="Exception", value=e)
                    channel = self.bot.get_channel(config.channel_botlog)
                    await channel.send(embed=embed)
        return

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if guild == self.getGuild() and self.getSlave() != 0:
            server = self.getSlave()
        elif guild == self.getSlave():
            server = self.getGuild()
        else:
            return

        await asyncio.sleep(2)

        try:
            banned = await server.fetch_ban(user)
        except discord.errors.NotFound:
            banned = None
        if banned is None:
            if config.debug:
                print("Banning member " + user.name)
            try:
                await server.ban(user)
                # repository.update_status(discord_id=user.id, status="banned")
            except Exception as e:
                embed = discord.Embed(
                    title="on_member_remove Exception",
                    description="member.kick() failed",
                    color=config.color_error,
                )
                embed.add_field(name="User", value=user.mention)
                embed.add_field(name="Exception", value=e)
                channel = self.bot.get_channel(config.channel_botlog)
                await channel.send(embed=embed)
        return

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if guild == self.getGuild() and self.getSlave() != 0:
            server = self.getSlave()
        elif guild == self.getSlave():
            server = self.getGuild()
        else:
            return

        await asyncio.sleep(2)

        try:
            banned = await server.fetch_ban(user)
        except discord.errors.NotFound:
            banned = None
        if banned is not None:
            if config.debug:
                print("Unbanning member " + user.name)
            try:
                await server.unban(user)
                # repository.update_status(discord_id=user.id, status="reverify")
            except Exception as e:
                embed = discord.Embed(
                    title="on_member_remove Exception",
                    description="member.kick() failed",
                    color=config.color_error,
                )
                embed.add_field(name="User", value=user.mention)
                embed.add_field(name="Exception", value=e)
                channel = self.bot.get_channel(config.channel_botlog)
                await channel.send(embed=embed)
        return

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return
        server = before.guild
        if server == self.getGuild() and self.getSlave() != 0:
            guild = self.getSlave()
        else:
            return

        await asyncio.sleep(1)
        member = discord.utils.get(guild.members, id=before.id)

        if member is not None:
            after_roles = []
            member_roles = []

            for role in after.roles:
                after_roles.append(role.name)
                slave_role = discord.utils.get(guild.roles, name=role.name)
                if slave_role is not None:
                    for r in member.roles:
                        member_roles.append(r.name)
                        if r.name == role.name:
                            break
                    else:
                        if config.debug:
                            print("Adding role: " + slave_role.name + " to " + member.name)
                        try:
                            await member.add_roles(slave_role)
                        except Exception as e:
                            embed = discord.Embed(
                                title="on_member_update Exception",
                                description="add_roles() failed",
                                color=config.color_error,
                            )
                            embed.add_field(name="Role", value=slave_role.name)
                            embed.add_field(name="User", value=member.mention)
                            embed.add_field(name="Exception", value=e)
                            channel = self.bot.get_channel(config.channel_botlog)
                            await channel.send(embed=embed)

                else:
                    embed = discord.Embed(
                        title="Role does not exist",
                        description="Adding role on slave failed",
                        color=config.color_error,
                    )
                    embed.add_field(name="Role", value="Role name: {}".format(role.name))
                    embed.add_field(name="Advice", value="Manual role sync recommended")
                    channel = self.bot.get_channel(config.channel_guildlog)
                    await channel.send(embed=embed)

            for name in member_roles:
                if name not in after_roles:
                    role = discord.utils.get(guild.roles, name=name)
                    if config.debug:
                        print("Removing role: " + role.name + " from " + member.name)
                    try:
                        await member.remove_roles(role)
                    except Exception as e:
                        embed = discord.Embed(
                            title="on_member_update Exception",
                            description="remove_roles() failed",
                            color=config.color_error,
                        )
                        embed.add_field(name="Role", value=role.name)
                        embed.add_field(name="User", value=member.mention)
                        embed.add_field(name="Exception", value=e)
                        channel = self.bot.get_channel(config.channel_botlog)
                        await channel.send(embed=embed)

        return


def setup(bot):
    bot.add_cog(Sync(bot))
