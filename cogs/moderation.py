import time, discord
from discord.ext import commands
from core.storage import execute,query,one,add_warning,get_warnings,clear_warnings,delete_warning
from core.timeparse import parse_duration,human

async def log_case(ctx,action,member,reason,expires_at=None):
    _,cid=execute('INSERT INTO mod_cases(guild_id,user_id,moderator_id,action,reason,expires_at) VALUES(?,?,?,?,?,?)',(ctx.guild.id,member.id,ctx.author.id,action,reason,expires_at))
    return cid

class Moderation(commands.Cog):
    def __init__(self,bot): self.bot=bot
    def hierarchy(self,ctx,member):
        return ctx.author==ctx.guild.owner or (ctx.author.top_role>member.top_role and ctx.guild.me.top_role>member.top_role)

    @commands.hybrid_command(name='ban',description='Bannt ein Mitglied vom Server.')
    @commands.has_permissions(ban_members=True)
    async def ban(self,ctx,member:discord.Member,*,reason='Kein Grund angegeben'):
        if not self.hierarchy(ctx,member): return await ctx.send('❌ Rollen-Hierarchie verhindert das.')
        await member.ban(reason=reason); cid=await log_case(ctx,'ban',member,reason); await ctx.send(f'🔨 {member} gebannt. Case #{cid}')

    @commands.hybrid_command(name='unban',description='Entbannt einen Nutzer per ID.')
    @commands.has_permissions(ban_members=True)
    async def unban(self,ctx,user_id:str,*,reason='Kein Grund angegeben'):
        try: user=await self.bot.fetch_user(int(user_id)); await ctx.guild.unban(user,reason=reason)
        except: return await ctx.send('❌ Nutzer/Ban nicht gefunden.')
        _,cid=execute('INSERT INTO mod_cases(guild_id,user_id,moderator_id,action,reason) VALUES(?,?,?,?,?)',(ctx.guild.id,user.id,ctx.author.id,'unban',reason)); await ctx.send(f'✅ {user} entbannt. Case #{cid}')

    @commands.hybrid_command(name='softban',description='Bannt kurz und entbannt direkt wieder, um Nachrichten zu entfernen.')
    @commands.has_permissions(ban_members=True)
    async def softban(self,ctx,member:discord.Member,*,reason='Kein Grund angegeben'):
        if not self.hierarchy(ctx,member): return await ctx.send('❌ Rollen-Hierarchie verhindert das.')
        await ctx.guild.ban(member,reason=reason,delete_message_seconds=86400); await ctx.guild.unban(member,reason='Softban abgeschlossen'); cid=await log_case(ctx,'softban',member,reason); await ctx.send(f'✅ Softban ausgeführt. Case #{cid}')

    @commands.hybrid_command(name='kick',description='Kickt ein Mitglied vom Server.')
    @commands.has_permissions(kick_members=True)
    async def kick(self,ctx,member:discord.Member,*,reason='Kein Grund angegeben'):
        if not self.hierarchy(ctx,member): return await ctx.send('❌ Rollen-Hierarchie verhindert das.')
        await member.kick(reason=reason); cid=await log_case(ctx,'kick',member,reason); await ctx.send(f'👢 {member} gekickt. Case #{cid}')

    async def do_timeout(self,ctx,member,duration,reason,action='mute'):
        if not self.hierarchy(ctx,member): return await ctx.send('❌ Rollen-Hierarchie verhindert das.')
        try: seconds=parse_duration(duration,2419200)
        except ValueError as e: return await ctx.send(f'❌ {e}')
        until=discord.utils.utcnow()+__import__('datetime').timedelta(seconds=seconds); await member.timeout(until,reason=reason); cid=await log_case(ctx,action,member,reason,time.time()+seconds); await ctx.send(f'🔇 {member.mention}: {human(seconds)}. Case #{cid}')

    @commands.hybrid_command(name='mute',description='Gibt einem Mitglied einen Discord-Timeout, z. B. 30m, 2h oder 7d.')
    @commands.has_permissions(moderate_members=True)
    async def mute(self,ctx,member:discord.Member,duration:str='10m',*,reason='Kein Grund angegeben'): await self.do_timeout(ctx,member,duration,reason)

    @commands.hybrid_command(name='unmute',description='Entfernt den Timeout eines Mitglieds.')
    @commands.has_permissions(moderate_members=True)
    async def unmute(self,ctx,member:discord.Member,*,reason='Kein Grund angegeben'):
        await member.timeout(None,reason=reason); cid=await log_case(ctx,'unmute',member,reason); await ctx.send(f'🔊 Timeout entfernt. Case #{cid}')

    @commands.hybrid_command(name='warn',description='Verwarnt ein Mitglied und legt einen Mod-Case an.')
    @commands.has_permissions(moderate_members=True)
    async def warn(self,ctx,member:discord.Member,*,reason='Kein Grund angegeben'):
        wid=add_warning(ctx.guild.id,member.id,ctx.author.id,reason); cid=await log_case(ctx,'warn',member,reason); await ctx.send(f'⚠️ {member.mention} verwarnt. Warn #{wid}, Case #{cid}')

    @commands.hybrid_command(name='warnings',description='Zeigt die Verwarnungen eines Mitglieds.')
    @commands.has_permissions(moderate_members=True)
    async def warnings(self,ctx,member:discord.Member):
        rows=get_warnings(ctx.guild.id,member.id); text='\n'.join(f"#{r['id']} — {r['reason']} (<@{r['moderator_id']}>)" for r in rows) or 'Keine Verwarnungen.'; await ctx.send(text[:1900])

    @commands.hybrid_command(name='delwarn',description='Löscht eine Verwarnung anhand ihrer ID.')
    @commands.has_permissions(moderate_members=True)
    async def delwarn(self,ctx,warning_id:int): await ctx.send('✅ Verwarnung gelöscht.' if delete_warning(ctx.guild.id,warning_id) else '❌ Nicht gefunden.')

    @commands.hybrid_command(name='clearwarn',aliases=['clearwarnings'],description='Löscht alle Verwarnungen eines Mitglieds.')
    @commands.has_permissions(moderate_members=True)
    async def clearwarn(self,ctx,member:discord.Member): await ctx.send(f'✅ {clear_warnings(ctx.guild.id,member.id)} Verwarnungen gelöscht.')

    @commands.hybrid_command(name='note',description='Speichert eine interne Moderationsnotiz zu einem Mitglied.')
    @commands.has_permissions(moderate_members=True)
    async def note(self,ctx,member:discord.Member,*,text:str):
        _,nid=execute('INSERT INTO notes(guild_id,user_id,moderator_id,note) VALUES(?,?,?,?)',(ctx.guild.id,member.id,ctx.author.id,text)); await ctx.send(f'✅ Notiz #{nid} gespeichert.')

    @commands.hybrid_command(name='notes',description='Zeigt die Moderationsnotizen eines Mitglieds.')
    @commands.has_permissions(moderate_members=True)
    async def notes(self,ctx,member:discord.Member):
        rows=query('SELECT * FROM notes WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 25',(ctx.guild.id,member.id)); await ctx.send(('\n'.join(f"#{r['id']} — {r['note']} (<@{r['moderator_id']}>)" for r in rows) or 'Keine Notizen.')[:1900])

    @commands.hybrid_command(name='delnote',description='Löscht eine Moderationsnotiz anhand ihrer ID.')
    @commands.has_permissions(moderate_members=True)
    async def delnote(self,ctx,note_id:int): await ctx.send('✅ Gelöscht.' if execute('DELETE FROM notes WHERE guild_id=? AND id=?',(ctx.guild.id,note_id))[0] else '❌ Nicht gefunden.')

    @commands.hybrid_command(name='editnote',description='Bearbeitet eine Moderationsnotiz.')
    @commands.has_permissions(moderate_members=True)
    async def editnote(self,ctx,note_id:int,*,text:str): await ctx.send('✅ Geändert.' if execute('UPDATE notes SET note=? WHERE guild_id=? AND id=?',(text,ctx.guild.id,note_id))[0] else '❌ Nicht gefunden.')

    @commands.hybrid_command(name='clearnotes',description='Löscht alle Moderationsnotizen eines Mitglieds.')
    @commands.has_permissions(moderate_members=True)
    async def clearnotes(self,ctx,member:discord.Member): execute('DELETE FROM notes WHERE guild_id=? AND user_id=?',(ctx.guild.id,member.id)); await ctx.send('✅ Notizen gelöscht.')

    @commands.hybrid_command(name='case',description='Zeigt einen einzelnen Moderationsfall anhand seiner ID.')
    @commands.has_permissions(moderate_members=True)
    async def case(self,ctx,case_id:int):
        r=one('SELECT * FROM mod_cases WHERE guild_id=? AND id=?',(ctx.guild.id,case_id))
        if not r:return await ctx.send('❌ Case nicht gefunden.')
        e=discord.Embed(title=f"Case #{r['id']} • {r['action']}",description=r['reason']); e.add_field(name='User',value=f"<@{r['user_id']}> `{r['user_id']}`"); e.add_field(name='Moderator',value=f"<@{r['moderator_id']}>"); await ctx.send(embed=e)

    @commands.hybrid_command(name='modlogs',description='Zeigt die Moderationsfälle eines Mitglieds.')
    @commands.has_permissions(moderate_members=True)
    async def modlogs(self,ctx,member:discord.Member):
        rows=query('SELECT * FROM mod_cases WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 25',(ctx.guild.id,member.id)); await ctx.send(('\n'.join(f"#{r['id']} `{r['action']}` — {r['reason']}" for r in rows) or 'Keine Cases.')[:1900])

    @commands.hybrid_command(name='reason',description='Ändert den Grund eines Moderationsfalls.')
    @commands.has_permissions(moderate_members=True)
    async def reason(self,ctx,case_id:int,*,reason:str): await ctx.send('✅ Grund geändert.' if execute('UPDATE mod_cases SET reason=? WHERE guild_id=? AND id=?',(reason,ctx.guild.id,case_id))[0] else '❌ Case nicht gefunden.')

    @commands.hybrid_command(name='clear',description='Löscht Nachrichten im Chat, optional nur von einem bestimmten Mitglied.')
    @commands.has_permissions(manage_messages=True)
    async def clear(self,ctx,amount:commands.Range[int,1,1000]=10,member:discord.Member|None=None):
        count=0
        def check(message):
            nonlocal count
            if count>=amount:return False
            if member is not None and message.author.id!=member.id:return False
            count+=1
            return True
        deleted=await ctx.channel.purge(limit=min(max(amount*20,100),5000),check=check)
        target=f' von {member.mention}' if member else ''
        await ctx.send(f'🧹 {len(deleted)} Nachrichten{target} gelöscht.',delete_after=4)

    @commands.hybrid_command(name='slowmode',description='Setzt den Slowmode des aktuellen Text-Channels in Sekunden.')
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self,ctx,seconds:commands.Range[int,0,21600]): await ctx.channel.edit(slowmode_delay=seconds); await ctx.send(f'✅ Slowmode: {seconds}s')

    @commands.hybrid_command(name='lock',description='Sperrt den aktuellen Text-Channel für normale Mitglieder.')
    @commands.has_permissions(manage_channels=True)
    async def lock(self,ctx): await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=False); await ctx.send('🔒 Channel gesperrt.')

    @commands.hybrid_command(name='unlock',description='Entsperrt den aktuellen Text-Channel wieder.')
    @commands.has_permissions(manage_channels=True)
    async def unlock(self,ctx): await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=None); await ctx.send('🔓 Channel entsperrt.')

    @commands.hybrid_command(name='lockdown',description='Sperrt oder entsperrt alle Text-Channels des Servers.')
    @commands.has_permissions(administrator=True)
    async def lockdown(self,ctx,enabled:bool=True):
        n=0
        for ch in ctx.guild.text_channels:
            try: await ch.set_permissions(ctx.guild.default_role,send_messages=False if enabled else None); n+=1
            except: pass
        await ctx.send(f'🔒 Lockdown {"aktiv" if enabled else "beendet"} ({n} Channels).')

    @commands.hybrid_command(name='members',description='Listet die Mitglieder einer bestimmten Rolle auf.')
    async def members(self,ctx,role:discord.Role): await ctx.send((', '.join(m.mention for m in role.members) or 'Keine Mitglieder.')[:1900])

    @commands.hybrid_command(name='role',description='Gibt oder entfernt einem Mitglied eine Rolle.')
    @commands.has_permissions(manage_roles=True)
    async def role(self,ctx,member:discord.Member,role:discord.Role):
        if role in member.roles: await member.remove_roles(role); s='entfernt'
        else: await member.add_roles(role); s='gegeben'
        await ctx.send(f'✅ {role.mention} {s}.')

    @commands.hybrid_command(name='temprole',description='Gibt einem Mitglied eine Rolle für eine begrenzte Zeit.')
    @commands.has_permissions(manage_roles=True)
    async def temprole(self,ctx,member:discord.Member,role:discord.Role,duration:str):
        try:s=parse_duration(duration,31536000)
        except ValueError as e:return await ctx.send(f'❌ {e}')
        await member.add_roles(role,reason=f'Temp role by {ctx.author}'); execute('INSERT INTO temp_roles(guild_id,user_id,role_id,expires_at) VALUES(?,?,?,?)',(ctx.guild.id,member.id,role.id,time.time()+s)); await ctx.send(f'✅ {role.mention} für {human(s)}.')

    @commands.hybrid_command(name='rolepersist',description='Schaltet das Wiederherstellen einer Rolle nach erneutem Beitritt um.')
    @commands.has_permissions(manage_roles=True)
    async def rolepersist(self,ctx,member:discord.Member,role:discord.Role):
        r=one('SELECT 1 FROM role_persist WHERE guild_id=? AND user_id=? AND role_id=?',(ctx.guild.id,member.id,role.id))
        if r: execute('DELETE FROM role_persist WHERE guild_id=? AND user_id=? AND role_id=?',(ctx.guild.id,member.id,role.id)); t='deaktiviert'
        else: execute('INSERT OR IGNORE INTO role_persist(guild_id,user_id,role_id) VALUES(?,?,?)',(ctx.guild.id,member.id,role.id)); t='aktiviert'
        await ctx.send(f'✅ Role Persist {t}.')

    @commands.hybrid_command(name='modstats',description='Zeigt die Moderationsstatistik eines Moderators.')
    @commands.has_permissions(moderate_members=True)
    async def modstats(self,ctx,member:discord.Member|None=None):
        member=member or ctx.author; rows=query('SELECT action,COUNT(*) n FROM mod_cases WHERE guild_id=? AND moderator_id=? GROUP BY action',(ctx.guild.id,member.id)); await ctx.send('\n'.join(f"{r['action']}: **{r['n']}**" for r in rows) or 'Keine Moderationen.')

async def setup(bot): await bot.add_cog(Moderation(bot))
