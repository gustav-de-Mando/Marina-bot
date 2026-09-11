import os,time,platform,discord
from discord.ext import commands
from core.storage import query,get_guild_settings

class InfoPlus(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.started=time.time()
    @commands.hybrid_command(name='help',description='Zeigt Hilfe und Command-Kategorien.')
    async def help(self,ctx,command_name:str|None=None):
        if command_name:
            c=self.bot.get_command(command_name)
            if not c:return await ctx.send('❌ Command nicht gefunden.')
            return await ctx.send(embed=discord.Embed(title=f'/{c.qualified_name}',description=c.help or c.description or 'Keine Beschreibung.').add_field(name='Nutzung',value=f'`{get_guild_settings(ctx.guild.id).get("prefix","!")}{c.qualified_name} {c.signature}`'))
        cats={}
        for c in self.bot.commands:
            if c.hidden: continue
            cats.setdefault(c.cog_name or 'Sonstiges',[]).append(c.name)
        e=discord.Embed(title='🤖 Bot Hilfe',description='Alle neuen Kerncommands funktionieren als Slash- und Prefix-Command.',color=discord.Color.blurple())
        for k,v in list(cats.items())[:20]: e.add_field(name=k,value=', '.join(f'`{x}`' for x in sorted(v))[:1000],inline=False)
        await ctx.send(embed=e)
    @commands.hybrid_command(name='info')
    async def info(self,ctx):
        e=discord.Embed(title=str(self.bot.user),description='All-in-One Discord Bot mit Moderation, Automod, Levels, Economy, Tickets, Musik, Rollen, Tags, Giveaways und Dashboard.',color=discord.Color.blurple()); e.set_thumbnail(url=self.bot.user.display_avatar.url); await ctx.send(embed=e)
    @commands.hybrid_command(name='stats')
    async def stats(self,ctx):
        users=sum(g.member_count or 0 for g in self.bot.guilds); await ctx.send(f'📊 **{len(self.bot.guilds)}** Server • **{users:,}** Mitglieder • **{len(self.bot.commands)}** Prefix/Hybrid Commands • **{len(self.bot.tree.get_commands())}** App Commands')
    @commands.hybrid_command(name='uptime')
    async def uptime(self,ctx):
        s=int(time.time()-self.started); d,s=divmod(s,86400); h,s=divmod(s,3600); m,s=divmod(s,60); await ctx.send(f'⏱️ {d}d {h}h {m}m {s}s')
    @commands.hybrid_command(name='premium')
    async def premium(self,ctx): await ctx.send('✨ Bei diesem Bot sind die eingebauten Funktionen nicht künstlich hinter Dyno-Premium gesperrt.')

async def setup(bot): await bot.add_cog(InfoPlus(bot))
