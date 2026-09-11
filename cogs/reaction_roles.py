import discord
from discord.ext import commands
from core.storage import execute,query
class ReactionRoles(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.hybrid_command(name='reactionrole_create')
    @commands.has_permissions(manage_roles=True)
    async def create(self,ctx,*,text:str='Reagiere für deine Rolle!'):
        m=await ctx.send(embed=discord.Embed(title='🎭 Reaction Roles',description=text,color=discord.Color.blurple()));await ctx.send(f'✅ Message-ID: `{m.id}`',ephemeral=True)
    @commands.hybrid_command(name='reactionrole_add')
    @commands.has_permissions(manage_roles=True)
    async def add(self,ctx,message_id:str,emoji:str,role:discord.Role):
        try:m=await ctx.channel.fetch_message(int(message_id));await m.add_reaction(emoji)
        except Exception:return await ctx.send('❌ Nachricht/Emoji ungültig.')
        execute('INSERT OR REPLACE INTO reaction_roles(guild_id,channel_id,message_id,emoji,role_id) VALUES(?,?,?,?,?)',(ctx.guild.id,ctx.channel.id,m.id,emoji,role.id));await ctx.send(f'✅ {emoji} → {role.mention}')
    @commands.hybrid_command(name='reactionrole_remove')
    @commands.has_permissions(manage_roles=True)
    async def remove(self,ctx,message_id:str,emoji:str):
        n=execute('DELETE FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?',(ctx.guild.id,int(message_id),emoji))[0];await ctx.send('✅ Entfernt.' if n else '❌ Nicht gefunden.')
    @commands.hybrid_command(name='reactionrole_list')
    async def list(self,ctx,message_id:str):
        rows=query('SELECT emoji,role_id FROM reaction_roles WHERE guild_id=? AND message_id=?',(ctx.guild.id,int(message_id)));await ctx.send('\n'.join(f"{r['emoji']} → <@&{r['role_id']}>" for r in rows) or 'Keine Reaction Roles.')
    async def change(self,payload,add=True):
        if not payload.guild_id:return
        rows=query('SELECT role_id FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?',(payload.guild_id,payload.message_id,str(payload.emoji)))
        if not rows:return
        g=self.bot.get_guild(payload.guild_id);m=g.get_member(payload.user_id) if g else None;role=g.get_role(rows[0]['role_id']) if g else None
        if not m or m.bot or not role:return
        try:await (m.add_roles(role,reason='Reaction role') if add else m.remove_roles(role,reason='Reaction role'))
        except:pass
    @commands.Cog.listener()
    async def on_raw_reaction_add(self,p):await self.change(p,True)
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self,p):await self.change(p,False)
async def setup(bot):await bot.add_cog(ReactionRoles(bot))
