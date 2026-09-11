import discord
from discord.ext import commands
from core.storage import get_guild_settings
class LoggingPlus(commands.Cog):
    def __init__(self,bot):self.bot=bot
    async def log(self,g,e):
        s=get_guild_settings(g.id)
        if not s.get('logs_enabled',True):return
        ch=g.get_channel(int(s.get('modlog_channel') or 0))
        if ch:
            try:await ch.send(embed=e)
            except:pass
    def emb(self,title,desc,color=discord.Color.blurple()):return discord.Embed(title=title,description=desc,color=color,timestamp=discord.utils.utcnow())
    @commands.Cog.listener()
    async def on_message_delete(self,m):
        if m.guild and not m.author.bot:await self.log(m.guild,self.emb('🗑️ Nachricht gelöscht',f'{m.author.mention} in {m.channel.mention}\n{(m.content or "*kein Text*")[:3000]}',discord.Color.red()))
    @commands.Cog.listener()
    async def on_message_edit(self,b,a):
        if b.guild and not b.author.bot and b.content!=a.content:await self.log(b.guild,self.emb('✏️ Nachricht bearbeitet',f'{b.author.mention} in {b.channel.mention}\n**Vorher:** {(b.content or "—")[:1200]}\n**Nachher:** {(a.content or "—")[:1200]}',discord.Color.orange()))
    @commands.Cog.listener()
    async def on_member_join(self,m):await self.log(m.guild,self.emb('📥 Mitglied beigetreten',f'{m.mention} (`{m.id}`)',discord.Color.green()))
    @commands.Cog.listener()
    async def on_member_remove(self,m):await self.log(m.guild,self.emb('📤 Mitglied verlassen',f'{m} (`{m.id}`)',discord.Color.red()))
    @commands.Cog.listener()
    async def on_member_update(self,b,a):
        if b.nick!=a.nick:await self.log(a.guild,self.emb('👤 Nickname geändert',f'{a.mention}: `{b.nick or b.name}` → `{a.nick or a.name}`'))
        br={r.id for r in b.roles};ar={r.id for r in a.roles}
        if br!=ar:
            added=[r.mention for r in a.roles if r.id in ar-br];removed=[r.mention for r in b.roles if r.id in br-ar];await self.log(a.guild,self.emb('🎭 Rollen geändert',f'{a.mention}\n+ {" ".join(added) or "—"}\n- {" ".join(removed) or "—"}'))
    @commands.Cog.listener()
    async def on_guild_channel_create(self,ch):await self.log(ch.guild,self.emb('➕ Channel erstellt',f'{ch.mention} (`{ch.id}`)',discord.Color.green()))
    @commands.Cog.listener()
    async def on_guild_channel_delete(self,ch):await self.log(ch.guild,self.emb('➖ Channel gelöscht',f'`{ch.name}` (`{ch.id}`)',discord.Color.red()))
    @commands.Cog.listener()
    async def on_guild_role_create(self,r):await self.log(r.guild,self.emb('➕ Rolle erstellt',f'{r.mention} (`{r.id}`)',discord.Color.green()))
    @commands.Cog.listener()
    async def on_guild_role_delete(self,r):await self.log(r.guild,self.emb('➖ Rolle gelöscht',f'`{r.name}` (`{r.id}`)',discord.Color.red()))
    @commands.Cog.listener()
    async def on_member_ban(self,g,u):await self.log(g,self.emb('🔨 Ban',f'{u} (`{u.id}`)',discord.Color.red()))
    @commands.Cog.listener()
    async def on_member_unban(self,g,u):await self.log(g,self.emb('✅ Unban',f'{u} (`{u.id}`)',discord.Color.green()))
    @commands.Cog.listener()
    async def on_voice_state_update(self,m,b,a):
        if b.channel!=a.channel:await self.log(m.guild,self.emb('🔊 Voice',f'{m.mention}: **{b.channel or "—"}** → **{a.channel or "—"}**'))
async def setup(bot):await bot.add_cog(LoggingPlus(bot))
