import math, random, time
import discord
from discord.ext import commands
from core.storage import get_guild_settings, get_level_user, set_level_user, leaderboard as db_leaderboard, get_level_roles, set_level_role, delete_level_role

def needed(level:int): return max(100, int(100 * (level ** 1.45)))
def level_from_xp(xp:int):
    level=0; rest=xp
    while rest >= needed(level+1): rest -= needed(level+1); level += 1
    return level, rest, needed(level+1)

class Levels(commands.Cog):
    def __init__(self, bot): self.bot=bot

    async def apply_roles(self, member, level):
        rows=get_level_roles(member.guild.id)
        eligible=[r for r in rows if level >= r['level']]
        if not eligible: return
        chosen=max(eligible,key=lambda r:r['level'])
        level_role_ids={r['role_id'] for r in rows}
        remove=[r for r in member.roles if r.id in level_role_ids and r.id != chosen['role_id']]
        add=member.guild.get_role(chosen['role_id'])
        try:
            if remove: await member.remove_roles(*remove, reason="Levelrolle aktualisiert")
            if add and add not in member.roles: await member.add_roles(add, reason="Levelrolle erreicht")
        except discord.HTTPException: pass

    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.guild or message.author.bot: return
        s=get_guild_settings(message.guild.id)
        if not s.get('levels_enabled',True): return
        row=get_level_user(message.guild.id,message.author.id); now=time.time()
        if now-row['last_xp'] < int(s.get('xp_cooldown',45)): return
        before,_,_=level_from_xp(row['xp'])
        gain=random.randint(int(s.get('xp_min',15)),int(s.get('xp_max',25)))
        vals=set_level_user(message.guild.id,message.author.id,xp=row['xp']+gain,messages=row['messages']+1,last_xp=now)
        after,_,_=level_from_xp(vals['xp'])
        if after>before:
            await self.apply_roles(message.author,after)
            cid=s.get('levelup_channel'); ch=message.guild.get_channel(int(cid)) if cid else message.channel
            if ch: await ch.send(f"🎉 {message.author.mention} ist jetzt **Level {after}**!")

    @commands.hybrid_command(name='rank',aliases=['profile','level'],description='Zeigt Level, XP und Fortschritt eines Mitglieds.')
    async def rank(self,ctx,member:discord.Member|None=None):
        member=member or ctx.author; row=get_level_user(ctx.guild.id,member.id); lvl,cur,nxt=level_from_xp(row['xp'])
        e=discord.Embed(title=f"📊 Rang von {member.display_name}",color=member.color)
        e.set_thumbnail(url=member.display_avatar.url); e.add_field(name='Level',value=str(lvl)); e.add_field(name='XP',value=f"{row['xp']:,}"); e.add_field(name='Fortschritt',value=f"{cur:,}/{nxt:,}")
        e.add_field(name='Nachrichten',value=f"{row['messages']:,}")
        await ctx.send(embed=e)

    @commands.hybrid_command(name='leaderboard',aliases=['lb'],description='Zeigt die Level-Rangliste des Servers.')
    async def leaderboard(self,ctx):
        lines=[]
        for i,r in enumerate(db_leaderboard(ctx.guild.id,10),1):
            m=ctx.guild.get_member(r['user_id']); name=m.display_name if m else str(r['user_id']); lvl,_,_=level_from_xp(r['xp']); lines.append(f"`{i}.` **{name}** — Level {lvl} · {r['xp']:,} XP")
        await ctx.send(embed=discord.Embed(title='🏆 Leaderboard',description='\n'.join(lines) or 'Noch keine Daten.',color=discord.Color.gold()))

    @commands.hybrid_command(name='setxp',description='Setzt die XP eines Mitglieds auf einen bestimmten Wert.')
    @commands.has_permissions(administrator=True)
    async def setxp(self,ctx,member:discord.Member,xp:int):
        set_level_user(ctx.guild.id,member.id,xp=xp); lvl,_,_=level_from_xp(max(0,xp)); await self.apply_roles(member,lvl); await ctx.send(f"✅ {member.mention}: {max(0,xp):,} XP / Level {lvl}")

    @commands.hybrid_command(name='addxp',description='Fügt einem Mitglied XP hinzu oder zieht XP ab.')
    @commands.has_permissions(administrator=True)
    async def addxp(self,ctx,member:discord.Member,xp:int):
        row=get_level_user(ctx.guild.id,member.id); new=max(0,row['xp']+xp); set_level_user(ctx.guild.id,member.id,xp=new); lvl,_,_=level_from_xp(new); await self.apply_roles(member,lvl); await ctx.send(f"✅ {member.mention}: {new:,} XP / Level {lvl}")

    @commands.hybrid_command(name='levelrole',description='Verknüpft ein Level mit einer Rolle oder entfernt die Verknüpfung.')
    @commands.has_permissions(manage_roles=True)
    async def levelrole(self,ctx,level:int,role:discord.Role|None=None):
        if level<1: return await ctx.send('❌ Level muss mindestens 1 sein.')
        if role is None: delete_level_role(ctx.guild.id,level); return await ctx.send(f'✅ Levelrolle für Level {level} entfernt.')
        if role >= ctx.guild.me.top_role: return await ctx.send('❌ Rolle muss unter meiner Bot-Rolle liegen.')
        set_level_role(ctx.guild.id,level,role.id); await ctx.send(f'✅ Level {level} → {role.mention}')

    @commands.hybrid_command(name='levelroles',description='Zeigt alle eingerichteten Levelrollen.')
    async def levelroles(self,ctx):
        rows=get_level_roles(ctx.guild.id); text='\n'.join(f"Level **{r['level']}** → <@&{r['role_id']}>" for r in rows) or 'Keine Levelrollen.'; await ctx.send(embed=discord.Embed(title='🏅 Levelrollen',description=text))

    @commands.hybrid_command(name='levelroles_create',description='Erstellt automatisch die Standard-Levelrollen und verknüpft sie.')
    @commands.has_permissions(manage_roles=True)
    async def levelroles_create(self,ctx):
        levels=[5,10,15,20,25,30,40,50,75,100]; made=[]
        for lvl in levels:
            name=f"Level {lvl}"
            role=discord.utils.get(ctx.guild.roles,name=name)
            if not role: role=await ctx.guild.create_role(name=name,reason=f"Levelrolle von {ctx.author}")
            set_level_role(ctx.guild.id,lvl,role.id); made.append(role.mention)
        await ctx.send('✅ Levelrollen erstellt/verbunden:\n'+' '.join(made))

async def setup(bot): await bot.add_cog(Levels(bot))
