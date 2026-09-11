import discord
from discord.ext import commands
from core.storage import execute,query,one

class RolesTags(commands.Cog):
    def __init__(self,bot):self.bot=bot

    @commands.hybrid_command(name='addrank',description='Macht eine Rolle selbst beitretbar.')
    @commands.has_permissions(manage_roles=True)
    async def addrank(self,ctx,role:discord.Role):execute('INSERT OR REPLACE INTO joinable_ranks(guild_id,role_id,name) VALUES(?,?,?)',(ctx.guild.id,role.id,role.name.lower()));await ctx.send(f'✅ {role.mention} ist jetzt ein Self-Rank.')

    @commands.hybrid_command(name='delrank',description='Entfernt eine selbst beitretbare Rolle.')
    @commands.has_permissions(manage_roles=True)
    async def delrank(self,ctx,role:discord.Role):execute('DELETE FROM joinable_ranks WHERE guild_id=? AND role_id=?',(ctx.guild.id,role.id));await ctx.send('✅ Self-Rank entfernt.')

    @commands.hybrid_command(name='selfrank',description='Tritt einer selbst beitretbaren Rolle bei oder verlässt sie.')
    async def selfrank(self,ctx,role:discord.Role):
        if not one('SELECT 1 FROM joinable_ranks WHERE guild_id=? AND role_id=?',(ctx.guild.id,role.id)):return await ctx.send('❌ Diese Rolle ist kein Self-Rank.')
        if role in ctx.author.roles:await ctx.author.remove_roles(role,reason='Self-rank');txt='verlassen'
        else:await ctx.author.add_roles(role,reason='Self-rank');txt='beigetreten'
        await ctx.send(f'✅ {role.mention} {txt}.')

    @commands.hybrid_command(name='ranks',description='Listet alle selbst beitretbaren Rollen auf.')
    async def ranks(self,ctx):
        rs=query('SELECT role_id FROM joinable_ranks WHERE guild_id=?',(ctx.guild.id,));roles=[ctx.guild.get_role(x['role_id']) for x in rs];roles=[r for r in roles if r];await ctx.send('**Self-Ranks:** '+(', '.join(r.mention for r in roles) if roles else 'Keine'))

    @commands.hybrid_command(name='roleinfo',description='Zeigt Informationen zu einer Rolle.')
    async def roleinfo(self,ctx,role:discord.Role):
        e=discord.Embed(title=role.name,color=role.color);e.add_field(name='ID',value=role.id);e.add_field(name='Mitglieder',value=len(role.members));e.add_field(name='Position',value=role.position);e.add_field(name='Mentionable',value=role.mentionable);e.add_field(name='Hoist',value=role.hoist);await ctx.send(embed=e)

    @commands.hybrid_command(name='roles',description='Listet die Rollen des Servers auf.')
    async def roles(self,ctx):await ctx.send((' '.join(r.mention for r in reversed(ctx.guild.roles[1:])) or 'Keine Rollen.')[:1900])

    @commands.hybrid_command(name='tag',description='Zeigt einen Tag an oder verwaltet Tags mit get, create, edit und delete.')
    async def tag(self,ctx,action:str,name:str|None=None,*,content:str|None=None):
        action=action.lower()
        if action not in {'get','create','edit','delete'}:name=action;action='get'
        if not name:return await ctx.send('❌ Tag-Name fehlt.')
        name=name.lower()
        if action=='get':
            r=one('SELECT content FROM tags WHERE guild_id=? AND name=?',(ctx.guild.id,name))
            if not r:return await ctx.send('❌ Tag nicht gefunden.')
            execute('UPDATE tags SET uses=uses+1 WHERE guild_id=? AND name=?',(ctx.guild.id,name));return await ctx.send(r['content'])
        if action=='create':
            if not content:return await ctx.send('❌ Inhalt fehlt.')
            if one('SELECT 1 FROM tags WHERE guild_id=? AND name=?',(ctx.guild.id,name)):return await ctx.send('❌ Tag existiert bereits.')
            execute('INSERT INTO tags(guild_id,name,content,owner_id) VALUES(?,?,?,?)',(ctx.guild.id,name,content,ctx.author.id));return await ctx.send('✅ Tag erstellt.')
        r=one('SELECT owner_id FROM tags WHERE guild_id=? AND name=?',(ctx.guild.id,name))
        if not r:return await ctx.send('❌ Tag nicht gefunden.')
        if r['owner_id']!=ctx.author.id and not ctx.author.guild_permissions.manage_messages:return await ctx.send('❌ Nur Besitzer oder Mods.')
        if action=='edit':
            if not content:return await ctx.send('❌ Inhalt fehlt.')
            execute('UPDATE tags SET content=? WHERE guild_id=? AND name=?',(content,ctx.guild.id,name));return await ctx.send('✅ Tag geändert.')
        execute('DELETE FROM tags WHERE guild_id=? AND name=?',(ctx.guild.id,name));await ctx.send('✅ Tag gelöscht.')

    @commands.hybrid_command(name='tags',description='Listet die meistgenutzten Tags des Servers auf.')
    async def tags(self,ctx):
        rows=query('SELECT name,uses FROM tags WHERE guild_id=? ORDER BY uses DESC,name LIMIT 50',(ctx.guild.id,));await ctx.send(', '.join(f"`{r['name']}` ({r['uses']})" for r in rows) if rows else 'Keine Tags.')

async def setup(bot):await bot.add_cog(RolesTags(bot))
