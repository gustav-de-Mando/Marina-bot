from discord.ext import commands
from core.storage import execute,query,one,get_guild_settings
class CustomCommands(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.hybrid_command(name='custom',description='Custom Command: run/create/edit/delete.')
    async def custom(self,ctx,action:str,name:str|None=None,*,response:str|None=None):
        action=action.lower()
        if action not in {'run','create','edit','delete'}:
            name=action;action='run'
        if not name:return await ctx.send('❌ Name fehlt.')
        name=name.lower().strip().lstrip('!/')
        if action=='run':
            r=one('SELECT response FROM custom_commands WHERE guild_id=? AND name=? AND enabled=1',(ctx.guild.id,name))
            if not r:return await ctx.send('❌ Custom Command nicht gefunden/deaktiviert.')
            execute('UPDATE custom_commands SET uses=uses+1 WHERE guild_id=? AND name=?',(ctx.guild.id,name));return await ctx.send(self.render(r['response'],ctx.author,ctx.guild,ctx.channel)[:2000])
        if not ctx.author.guild_permissions.manage_guild:return await ctx.send('❌ Dafür brauchst du „Server verwalten“.')
        if action in {'create','edit'}:
            if not response:return await ctx.send('❌ Antworttext fehlt.')
            if action=='create' and self.bot.get_command(name):return await ctx.send('❌ Name kollidiert mit einem eingebauten Command.')
            if not name.replace('-','').replace('_','').isalnum():return await ctx.send('❌ Name darf nur Buchstaben/Zahlen/_/- enthalten.')
            execute('INSERT INTO custom_commands(guild_id,name,response,owner_id) VALUES(?,?,?,?) ON CONFLICT(guild_id,name) DO UPDATE SET response=excluded.response,enabled=1',(ctx.guild.id,name,response,ctx.author.id));return await ctx.send(f'✅ Custom Command `{name}` gespeichert.')
        n=execute('DELETE FROM custom_commands WHERE guild_id=? AND name=?',(ctx.guild.id,name))[0];await ctx.send('✅ Gelöscht.' if n else '❌ Nicht gefunden.')
    def render(self,text,user,guild,channel):return text.replace('{user}',user.mention).replace('{server}',guild.name).replace('{channel}',channel.mention)
    @commands.hybrid_command(name='customs',description='Listet Custom Commands.')
    async def customs(self,ctx):
        rows=query('SELECT name,enabled,uses FROM custom_commands WHERE guild_id=? ORDER BY name',(ctx.guild.id,));await ctx.send(', '.join(f"`{r['name']}` {'✅' if r['enabled'] else '❌'} ({r['uses']})" for r in rows) if rows else 'Keine Custom Commands.')
    @commands.Cog.listener()
    async def on_message(self,m):
        if not m.guild or m.author.bot:return
        prefix=get_guild_settings(m.guild.id).get('prefix','!')
        if not m.content.startswith(prefix):return
        name=m.content[len(prefix):].split(maxsplit=1)[0].lower()
        if not name or self.bot.get_command(name):return
        r=one('SELECT response FROM custom_commands WHERE guild_id=? AND name=? AND enabled=1',(m.guild.id,name))
        if not r:return
        execute('UPDATE custom_commands SET uses=uses+1 WHERE guild_id=? AND name=?',(m.guild.id,name));await m.channel.send(self.render(r['response'],m.author,m.guild,m.channel)[:2000])
async def setup(bot):await bot.add_cog(CustomCommands(bot))
