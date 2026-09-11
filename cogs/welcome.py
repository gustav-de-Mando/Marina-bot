import discord
from discord.ext import commands
from core.storage import get_guild_settings,update_guild_settings,query

def render(text,member):
    return (text or 'Willkommen {mention} auf **{server}**!').replace('{mention}',member.mention).replace('{user}',member.display_name).replace('{server}',member.guild.name).replace('{count}',str(member.guild.member_count))
class Welcome(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.Cog.listener()
    async def on_member_join(self,member):
        s=get_guild_settings(member.guild.id);roles=[]
        rid=s.get('autorole_id')
        if rid:
            r=member.guild.get_role(int(rid))
            if r:roles.append(r)
        for row in query('SELECT role_id FROM role_persist WHERE guild_id=? AND user_id=?',(member.guild.id,member.id)):
            r=member.guild.get_role(row['role_id'])
            if r and r not in roles:roles.append(r)
        if roles:
            try:await member.add_roles(*[r for r in roles if r<member.guild.me.top_role],reason='Autorole/Role Persist')
            except:pass
        if s.get('welcome_enabled',True) and s.get('welcome_channel'):
            ch=member.guild.get_channel(int(s['welcome_channel']))
            if ch:
                try:await ch.send(render(s.get('welcome_message'),member))
                except:pass
    @commands.Cog.listener()
    async def on_member_remove(self,member):
        s=get_guild_settings(member.guild.id)
        if s.get('goodbye_enabled',True) and s.get('goodbye_channel'):
            ch=member.guild.get_channel(int(s['goodbye_channel']))
            if ch:
                try:await ch.send(render(s.get('goodbye_message') or '{user} hat **{server}** verlassen.',member))
                except:pass
    @commands.hybrid_command(name='welcomemessage')
    @commands.has_permissions(administrator=True)
    async def welcomemessage(self,ctx,*,message:str):update_guild_settings(ctx.guild.id,welcome_message=message);await ctx.send('✅ Gespeichert. Variablen: `{mention}`, `{user}`, `{server}`, `{count}`')
async def setup(bot):await bot.add_cog(Welcome(bot))
