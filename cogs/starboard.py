import discord
from discord.ext import commands
from core.storage import get_guild_settings,update_guild_settings,execute,one

class Starboard(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.hybrid_command(name='starboard')
    @commands.has_permissions(manage_guild=True)
    async def starboard(self,ctx,channel:discord.TextChannel,threshold:commands.Range[int,1,50]=3):
        update_guild_settings(ctx.guild.id,starboard_enabled=True,starboard_channel=channel.id,starboard_threshold=threshold); await ctx.send(f'⭐ Starboard → {channel.mention}, ab {threshold} ⭐')
    @commands.hybrid_command(name='star')
    async def star(self,ctx,message_id:str):
        try:m=await ctx.channel.fetch_message(int(message_id))
        except:return await ctx.send('❌ Nachricht im aktuellen Channel nicht gefunden.')
        r=discord.utils.get(m.reactions,emoji='⭐'); await ctx.send(f'⭐ **{r.count if r else 0}** Sterne')
    @commands.Cog.listener()
    async def on_raw_reaction_add(self,p):
        if str(p.emoji)!='⭐' or not p.guild_id:return
        g=self.bot.get_guild(p.guild_id); s=get_guild_settings(p.guild_id)
        if not g or not s.get('starboard_enabled'):return
        src=g.get_channel(p.channel_id); dst=g.get_channel(int(s.get('starboard_channel') or 0))
        if not src or not dst:return
        try:m=await src.fetch_message(p.message_id)
        except:return
        r=discord.utils.get(m.reactions,emoji='⭐'); threshold=int(s.get('starboard_threshold',3))
        if not r or r.count<threshold:return
        key=f'starboard_{m.id}'; existing=s.get(key)
        e=discord.Embed(description=m.content or '*Kein Text*',color=discord.Color.gold(),timestamp=m.created_at); e.set_author(name=str(m.author),icon_url=m.author.display_avatar.url); e.add_field(name='Quelle',value=f'[Zur Nachricht]({m.jump_url})');
        if m.attachments:e.set_image(url=m.attachments[0].url)
        if existing:
            try:sm=await dst.fetch_message(int(existing)); return await sm.edit(content=f'⭐ **{r.count}**',embed=e)
            except:pass
        sm=await dst.send(content=f'⭐ **{r.count}**',embed=e); update_guild_settings(g.id,**{key:sm.id})
async def setup(bot): await bot.add_cog(Starboard(bot))
