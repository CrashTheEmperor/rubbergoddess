import datetime

import discord
from discord.ext.commands import Bot

from core.config import config
from config.messages import Messages
from features.base_feature import BaseFeature


class Reaction(BaseFeature):
    def __init__(self, bot: Bot):
        super().__init__(bot)

    async def add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return
        if channel.type is discord.ChannelType.text:
            guild = channel.guild
        else:
            guild = self.bot.get_guild(config.guild_id)
            if guild is None:
                raise Exception("Nemuzu najit guildu podle config.guild_id")
        member = guild.get_member(payload.user_id)

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return

        if member is None or message is None or member.bot:
            return

        if payload.emoji.is_custom_emoji():
            emoji = self.bot.get_emoji(payload.emoji.id)
            if emoji is None:
                emoji = payload.emoji
        else:
            emoji = payload.emoji.name

        # if the message has X or more 'pin' emojis pin the message
        if emoji == "📌":
            for reaction in message.reactions:
                if (
                    reaction.emoji == "📌"
                    and reaction.count >= config.pin_limit
                    and not message.pinned
                ):
                    embed = discord.Embed(title="📌 Auto pin message log", color=config.color)
                    users = await reaction.users().flatten()
                    user_names = ", ".join([user.name for user in users])
                    message_link = (
                        Messages.message_link_prefix
                        + str(message.channel.id)
                        + "/"
                        + str(message.id)
                    )
                    embed.add_field(name="Users", value=user_names)
                    embed.add_field(name="In channel", value=message.channel)
                    embed.add_field(name="Message", value=message_link, inline=False)
                    embed.set_footer(text=datetime.datetime.now().replace(microsecond=0))
                    channel = self.bot.get_channel(config.channel_botlog)
                    await channel.send(embed=embed)
                    try:
                        await message.pin()
                    except discord.HTTPException:
                        break
