import discord
from discord.ext import commands
class Utility(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.hybrid_command(name='ping',description='Zeigt die Bot-Latenz.')
    async def ping(self,ctx): await ctx.send(f'🏓 {round(self.bot.latency*1000)} ms')
    @commands.hybrid_command(name='avatar',description='Zeigt einen Avatar.')
    async def avatar(self,ctx,member:discord.Member|None=None):
        member=member or ctx.author; e=discord.Embed(title=f'Avatar: {member.display_name}'); e.set_image(url=member.display_avatar.url); await ctx.send(embed=e)
    @commands.hybrid_command(name='userinfo',description='Zeigt User-Informationen.')
    async def userinfo(self,ctx,member:discord.Member|None=None):
        m=member or ctx.author; e=discord.Embed(title=f'👤 {m}',color=m.color); e.set_thumbnail(url=m.display_avatar.url); e.add_field(name='ID',value=m.id); e.add_field(name='Erstellt',value=discord.utils.format_dt(m.created_at,'R')); e.add_field(name='Beigetreten',value=discord.utils.format_dt(m.joined_at,'R') if m.joined_at else '—'); e.add_field(name='Rollen',value=str(len(m.roles)-1)); await ctx.send(embed=e)
    @commands.hybrid_command(name='serverinfo',description='Zeigt Server-Informationen.')
    async def serverinfo(self,ctx):
        g=ctx.guild; e=discord.Embed(title=f'🏠 {g.name}'); e.add_field(name='Mitglieder',value=g.member_count); e.add_field(name='Channels',value=len(g.channels)); e.add_field(name='Rollen',value=len(g.roles)); e.add_field(name='Owner',value=g.owner.mention if g.owner else '—'); await ctx.send(embed=e)
    @commands.hybrid_command(name='invite',description='Zeigt den Bot-Einladungslink.')
    async def invite(self,ctx):
        p=discord.Permissions(manage_roles=True,manage_channels=True,kick_members=True,ban_members=True,moderate_members=True,manage_messages=True,view_audit_log=True,send_messages=True,embed_links=True,add_reactions=True,read_message_history=True,connect=True,speak=True)
        await ctx.send(discord.utils.oauth_url(self.bot.user.id,permissions=p,scopes=('bot','applications.commands')))
async def setup(bot): await bot.add_cog(Utility(bot))
