import os,time,platform,discord
from discord.ext import commands
from core.storage import get_guild_settings

CATEGORY_MAP={
    'Admin':'⚙️ Serververwaltung','DynoManager':'⚙️ Serververwaltung','Welcome':'⚙️ Serververwaltung','Backup':'⚙️ Serververwaltung','Bump':'⚙️ Serververwaltung',
    'Moderation':'🛡️ Moderation','Automod':'🛡️ Moderation','LoggingPlus':'🛡️ Moderation',
    'Levels':'📈 Level & Rollen','RolesTags':'📈 Level & Rollen','ReactionRoles':'📈 Level & Rollen',
    'Tickets':'💬 Community','Suggestions':'💬 Community','Giveaways':'💬 Community','Starboard':'💬 Community','Counting':'💬 Community','CustomCommands':'💬 Community',
    'Music':'🎵 Musik','Economy':'💰 Economy','Fun':'🎉 Spaß','Misc':'🎉 Spaß','Dice':'🎉 Spaß',
    'Utility':'ℹ️ Informationen','InfoPlus':'ℹ️ Informationen'
}

class InfoPlus(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.started=time.time()

    @commands.hybrid_command(name='help',description='Zeigt eine übersichtliche Hilfe mit Command-Kategorien.')
    async def help(self,ctx,command_name:str|None=None):
        prefix=get_guild_settings(ctx.guild.id).get('prefix','-')
        if command_name:
            c=self.bot.get_command(command_name)
            if not c:return await ctx.send('❌ Command nicht gefunden.')
            desc=c.description or c.help or f'Führt den Befehl {c.name} aus.'
            e=discord.Embed(title=f'/{c.qualified_name}',description=desc,color=discord.Color.purple())
            e.add_field(name='Prefix-Nutzung',value=f'`{prefix}{c.qualified_name} {c.signature}`',inline=False)
            e.add_field(name='Slash-Nutzung',value=f'`/{c.qualified_name}`',inline=False)
            return await ctx.send(embed=e)
        groups={}
        for c in self.bot.commands:
            if c.hidden:continue
            group=CATEGORY_MAP.get(c.cog_name or '','🧩 Sonstiges')
            groups.setdefault(group,[]).append(c.name)
        order=['🛡️ Moderation','⚙️ Serververwaltung','📈 Level & Rollen','💬 Community','🎵 Musik','💰 Economy','🎉 Spaß','ℹ️ Informationen','🧩 Sonstiges']
        e=discord.Embed(title='🐧 Mr. Flipper • Hilfe',description=f'Nutze Slash-Commands oder `{prefix}help <command>` für Details zu einem Befehl.',color=discord.Color.purple())
        for group in order:
            names=sorted(set(groups.get(group,[])))
            if names:e.add_field(name=group,value=' '.join(f'`/{name}`' for name in names)[:1024],inline=False)
        e.set_footer(text=f'{len(self.bot.commands)} Commands verfügbar')
        await ctx.send(embed=e)

    @commands.hybrid_command(name='info',description='Zeigt Informationen über Mr. Flipper und seine Funktionen.')
    async def info(self,ctx):
        e=discord.Embed(title=str(self.bot.user),description='All-in-One Discord Bot mit Moderation, AutoMod, Levels, Economy, Tickets, Musik, Rollen, Tags, Giveaways und Dashboard.',color=discord.Color.purple()); e.set_thumbnail(url=self.bot.user.display_avatar.url); await ctx.send(embed=e)

    @commands.hybrid_command(name='stats',description='Zeigt Statistiken zum Bot und seinen Servern.')
    async def stats(self,ctx):
        users=sum(g.member_count or 0 for g in self.bot.guilds); await ctx.send(f'📊 **{len(self.bot.guilds)}** Server • **{users:,}** Mitglieder • **{len(self.bot.commands)}** Commands')

    @commands.hybrid_command(name='uptime',description='Zeigt, wie lange der Bot bereits online ist.')
    async def uptime(self,ctx):
        s=int(time.time()-self.started); d,s=divmod(s,86400); h,s=divmod(s,3600); m,s=divmod(s,60); await ctx.send(f'⏱️ {d}d {h}h {m}m {s}s')

async def setup(bot): await bot.add_cog(InfoPlus(bot))
