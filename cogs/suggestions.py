import discord
from discord.ext import commands
from core.storage import get_guild_settings
class Suggestions(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.hybrid_command(name='suggest',description='Sendet einen Vorschlag.')
    async def suggest(self,ctx,*,text:str):
        s=get_guild_settings(ctx.guild.id); cid=s.get('suggestions_channel'); ch=ctx.guild.get_channel(int(cid)) if cid else ctx.channel
        e=discord.Embed(title='💡 Neuer Vorschlag',description=text,color=discord.Color.blurple(),timestamp=discord.utils.utcnow()); e.set_author(name=ctx.author.display_name,icon_url=ctx.author.display_avatar.url)
        msg=await ch.send(embed=e); await msg.add_reaction('👍'); await msg.add_reaction('👎')
        if ch!=ctx.channel: await ctx.send(f'✅ Vorschlag gesendet: {msg.jump_url}',ephemeral=True if ctx.interaction else False)
async def setup(bot): await bot.add_cog(Suggestions(bot))
