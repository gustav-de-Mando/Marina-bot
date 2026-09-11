import discord, random, asyncio
from discord.ext import commands
from core.storage import execute,query,one

class DynoManager(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @commands.hybrid_command(name='addemote',description='Fügt ein Custom-Emoji über eine Bild-URL hinzu.')
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def addemote(self,ctx,name:str,url:str):
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(url,timeout=15) as r:
                if r.status!=200: return await ctx.send('❌ Bild konnte nicht geladen werden.')
                data=await r.read()
        e=await ctx.guild.create_custom_emoji(name=name,image=data,reason=f'Von {ctx.author}')
        await ctx.send(f'✅ Emoji erstellt: {e}')

    @commands.hybrid_command(name='addmod',description='Fügt eine Moderatorrolle hinzu.')
    @commands.has_permissions(administrator=True)
    async def addmod(self,ctx,role:discord.Role):
        execute('INSERT OR IGNORE INTO moderators(guild_id,role_id) VALUES(?,?)',(ctx.guild.id,role.id)); await ctx.send(f'✅ {role.mention} ist Moderatorrolle.')

    @commands.hybrid_command(name='delmod',description='Entfernt eine Moderatorrolle.')
    @commands.has_permissions(administrator=True)
    async def delmod(self,ctx,role:discord.Role):
        execute('DELETE FROM moderators WHERE guild_id=? AND role_id=?',(ctx.guild.id,role.id)); await ctx.send('✅ Moderatorrolle entfernt.')

    @commands.hybrid_command(name='listmods',description='Listet die konfigurierten Moderatorrollen auf.')
    async def listmods(self,ctx):
        rows=query('SELECT role_id FROM moderators WHERE guild_id=?',(ctx.guild.id,)); roles=[ctx.guild.get_role(r['role_id']) for r in rows]; roles=[r for r in roles if r]
        await ctx.send('**Moderatorrollen:**\n'+('\n'.join(r.mention for r in roles) if roles else 'Keine.'))

    @commands.hybrid_command(name='addrole',description='Erstellt eine neue Serverrolle.')
    @commands.has_permissions(manage_roles=True)
    async def addrole(self,ctx,name:str,color:str='#99aab5',hoist:bool=False):
        try: c=discord.Color(int(color.lstrip('#'),16))
        except: return await ctx.send('❌ Farbe als Hex, z. B. `#5865F2`.')
        r=await ctx.guild.create_role(name=name,color=c,hoist=hoist,reason=f'Von {ctx.author}'); await ctx.send(f'✅ Rolle erstellt: {r.mention}')

    @commands.hybrid_command(name='delrole',description='Löscht eine Serverrolle.')
    @commands.has_permissions(manage_roles=True)
    async def delrole(self,ctx,role:discord.Role):
        n=role.name; await role.delete(reason=f'Von {ctx.author}'); await ctx.send(f'✅ Rolle `{n}` gelöscht.')

    @commands.hybrid_command(name='rolecolor',description='Ändert die Farbe einer Rolle.')
    @commands.has_permissions(manage_roles=True)
    async def rolecolor(self,ctx,role:discord.Role,color:str):
        try: c=discord.Color(int(color.lstrip('#'),16))
        except: return await ctx.send('❌ Ungültige Hex-Farbe.')
        await role.edit(color=c,reason=f'Von {ctx.author}'); await ctx.send('✅ Rollenfarbe geändert.')

    @commands.hybrid_command(name='rolename',description='Ändert den Namen einer Rolle.')
    @commands.has_permissions(manage_roles=True)
    async def rolename(self,ctx,role:discord.Role,*,name:str):
        await role.edit(name=name,reason=f'Von {ctx.author}'); await ctx.send('✅ Rollenname geändert.')

    @commands.hybrid_command(name='mentionable',description='Schaltet um, ob eine Rolle erwähnt werden kann.')
    @commands.has_permissions(manage_roles=True)
    async def mentionable(self,ctx,role:discord.Role):
        await role.edit(mentionable=not role.mentionable,reason=f'Von {ctx.author}'); await ctx.send(f'✅ Erwähnbar: **{role.mentionable}**')

    @commands.hybrid_command(name='announce',description='Sendet eine Ankündigung als Embed in einen Channel.')
    @commands.has_permissions(manage_messages=True)
    async def announce(self,ctx,channel:discord.TextChannel,*,text:str):
        e=discord.Embed(title='📢 Ankündigung',description=text,color=discord.Color.blurple()); e.set_footer(text=f'Von {ctx.author}')
        await channel.send(embed=e); await ctx.send('✅ Gesendet.',ephemeral=True)

    @commands.hybrid_command(name='command',description='Aktiviert oder deaktiviert einen Bot-Command auf diesem Server.')
    @commands.has_permissions(administrator=True)
    async def command_toggle(self,ctx,command_name:str,enabled:bool):
        execute('INSERT INTO command_rules(guild_id,command,enabled) VALUES(?,?,?) ON CONFLICT(guild_id,command) DO UPDATE SET enabled=excluded.enabled',(ctx.guild.id,command_name.lower().lstrip('/!'),int(enabled)))
        await ctx.send(f'✅ `{command_name}`: **{"an" if enabled else "aus"}**')

    async def _ignore(self,ctx,kind,target_id):
        row=one('SELECT 1 FROM ignored WHERE guild_id=? AND kind=? AND target_id=?',(ctx.guild.id,kind,target_id))
        if row:
            execute('DELETE FROM ignored WHERE guild_id=? AND kind=? AND target_id=?',(ctx.guild.id,kind,target_id)); state='nicht mehr ignoriert'
        else:
            execute('INSERT OR IGNORE INTO ignored(guild_id,kind,target_id) VALUES(?,?,?)',(ctx.guild.id,kind,target_id)); state='ignoriert'
        await ctx.send(f'✅ Ziel wird {state}.')

    @commands.hybrid_command(name='ignorechannel',description='Ignoriert oder aktiviert Bot-Commands in einem bestimmten Channel wieder.')
    @commands.has_permissions(administrator=True)
    async def ignorechannel(self,ctx,channel:discord.TextChannel): await self._ignore(ctx,'channel',channel.id)

    @commands.hybrid_command(name='ignorerole',description='Ignoriert oder aktiviert Bot-Commands für eine bestimmte Rolle wieder.')
    @commands.has_permissions(administrator=True)
    async def ignorerole(self,ctx,role:discord.Role): await self._ignore(ctx,'role',role.id)

    @commands.hybrid_command(name='ignoreuser',description='Ignoriert oder aktiviert Bot-Commands für einen bestimmten Nutzer wieder.')
    @commands.has_permissions(administrator=True)
    async def ignoreuser(self,ctx,member:discord.Member): await self._ignore(ctx,'user',member.id)

    @commands.hybrid_command(name='ignored',description='Zeigt ignorierte Channels, Rollen und Nutzer.')
    async def ignored(self,ctx):
        rows=query('SELECT kind,target_id FROM ignored WHERE guild_id=? ORDER BY kind',(ctx.guild.id,)); lines=[]
        for r in rows:
            obj=ctx.guild.get_channel(r['target_id']) if r['kind']=='channel' else ctx.guild.get_role(r['target_id']) if r['kind']=='role' else ctx.guild.get_member(r['target_id'])
            lines.append(f"• {r['kind']}: {getattr(obj,'mention',r['target_id'])}")
        await ctx.send('\n'.join(lines) if lines else 'Keine Ignore-Regeln.')

    @commands.hybrid_command(name='setnick',description='Ändert den Nickname eines Mitglieds.')
    @commands.has_permissions(manage_nicknames=True)
    async def setnick(self,ctx,member:discord.Member,*,nickname:str|None=None):
        await member.edit(nick=nickname,reason=f'Von {ctx.author}'); await ctx.send('✅ Nickname geändert.')

async def setup(bot): await bot.add_cog(DynoManager(bot))
