import discord
from discord.ext import commands


def bot_hierarchy_ok(actor: discord.Member, target: discord.Member) -> bool:
    if actor.guild.owner_id == actor.id:
        return True
    return actor.top_role > target.top_role


def target_is_safe(ctx: commands.Context, target: discord.Member) -> bool:
    return target.id not in {ctx.author.id, ctx.guild.owner_id, ctx.bot.user.id}
