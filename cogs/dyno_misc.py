import discord, random, time, math, re, asyncio
from discord.ext import commands
from core.storage import execute,query,one
from core.timeparse import parse_duration,human

class Misc(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @commands.hybrid_command(name='afk',description='Setzt deinen AFK-Status mit optionalem Grund.')
    async def afk(self,ctx,*,reason='AFK'):
        execute('INSERT INTO afk(guild_id,user_id,reason,since) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET reason=excluded.reason,since=excluded.since',(ctx.guild.id,ctx.author.id,reason,time.time())); await ctx.send(f'💤 AFK gesetzt: {reason}')

    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.guild or message.author.bot:return
        afk=one('SELECT 1 FROM afk WHERE guild_id=? AND user_id=?',(message.guild.id,message.author.id))
        if afk:
            execute('DELETE FROM afk WHERE guild_id=? AND user_id=?',(message.guild.id,message.author.id))
            try: await message.channel.send(f'👋 {message.author.mention}, AFK beendet.',delete_after=5)
            except: pass
        for m in message.mentions[:5]:
            r=one('SELECT reason,since FROM afk WHERE guild_id=? AND user_id=?',(message.guild.id,m.id))
            if r:
                try: await message.channel.send(f'💤 **{m}** ist AFK: {r["reason"]}',delete_after=8)
                except: pass

    @commands.hybrid_command(name='color',description='Zeigt eine eingegebene Hex-Farbe als Embed an.')
    async def color(self,ctx,hexcode:str):
        try:c=discord.Color(int(hexcode.lstrip('#'),16))
        except:return await ctx.send('❌ Hex-Farbe wie `#5865F2`.')
        await ctx.send(embed=discord.Embed(title=f'#{c.value:06X}',color=c))

    @commands.hybrid_command(name='randomcolor',description='Erzeugt und zeigt eine zufällige Farbe.')
    async def randomcolor(self,ctx):
        c=discord.Color(random.randint(0,0xFFFFFF)); await ctx.send(embed=discord.Embed(title=f'#{c.value:06X}',color=c))

    @commands.hybrid_command(name='emotes',description='Listet die Custom-Emojis des Servers auf.')
    async def emotes(self,ctx): await ctx.send((' '.join(str(e) for e in ctx.guild.emojis) or 'Keine Custom Emojis.')[:1900])

    @commands.hybrid_command(name='membercount',description='Zeigt die aktuelle Mitgliederzahl des Servers.')
    async def membercount(self,ctx): await ctx.send(f'👥 **{ctx.guild.member_count}** Mitglieder')

    @commands.hybrid_command(name='whois',description='Zeigt kompakte Informationen zu einem Mitglied.')
    async def whois(self,ctx,member:discord.Member|None=None):
        member=member or ctx.author; e=discord.Embed(title=str(member),color=member.color); e.set_thumbnail(url=member.display_avatar.url); e.add_field(name='ID',value=member.id); e.add_field(name='Account',value=discord.utils.format_dt(member.created_at,'R')); e.add_field(name='Beigetreten',value=discord.utils.format_dt(member.joined_at,'R') if member.joined_at else '?'); e.add_field(name='Top-Rolle',value=member.top_role.mention); await ctx.send(embed=e)

    @commands.hybrid_command(name='inviteinfo',description='Zeigt Informationen zu einem Discord-Einladungslink.')
    async def inviteinfo(self,ctx,invite:str):
        try:i=await self.bot.fetch_invite(invite)
        except:return await ctx.send('❌ Invite ungültig/nicht erreichbar.')
        await ctx.send(f'**{i.guild.name if i.guild else "Unbekannt"}** • Channel: {getattr(i.channel,"name","?")} • Member: {getattr(i,"approximate_member_count",None) or "?"}')

    @commands.hybrid_command(name='roll',description='Würfelt eine zufällige Zahl mit frei wählbarer Seitenzahl.')
    async def roll(self,ctx,sides:commands.Range[int,2,1000000]=6): await ctx.send(f'🎲 **{random.randint(1,sides)}** / {sides}')

    @commands.hybrid_command(name='flip',description='Wirft eine virtuelle Münze.')
    async def flip(self,ctx): await ctx.send('🪙 '+random.choice(['Kopf','Zahl']))

    @commands.hybrid_command(name='rps',description='Spielt Schere, Stein, Papier gegen den Bot.')
    async def rps(self,ctx,choice:str):
        choice=choice.lower(); opts=['stein','papier','schere']
        if choice not in opts:return await ctx.send('❌ stein/papier/schere')
        bot=random.choice(opts); wins={('stein','schere'),('schere','papier'),('papier','stein')}; result='Unentschieden' if choice==bot else ('Gewonnen!' if (choice,bot) in wins else 'Verloren!'); await ctx.send(f'🤖 {bot} — **{result}**')

    @commands.hybrid_command(name='poll',description='Erstellt eine einfache Ja-Nein-Umfrage mit Reaktionen.')
    async def poll(self,ctx,*,question:str):
        e=discord.Embed(title='📊 Umfrage',description=question,color=discord.Color.blurple()); m=await ctx.send(embed=e); await m.add_reaction('👍'); await m.add_reaction('👎')

    @commands.hybrid_command(name='distance',description='Berechnet die Luftlinie zwischen zwei Koordinaten in Kilometern.')
    async def distance(self,ctx,lat1:float,lon1:float,lat2:float,lon2:float):
        r=6371; p1,p2=map(math.radians,[lat1,lat2]); dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1); a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2; d=2*r*math.asin(math.sqrt(a)); await ctx.send(f'📏 Luftlinie: **{d:.2f} km**')

    @commands.hybrid_command(name='remindme',description='Speichert eine Erinnerung für später.')
    async def remindme(self,ctx,duration:str,*,message:str):
        try:s=parse_duration(duration,31536000)
        except ValueError as e:return await ctx.send(f'❌ {e}')
        execute('INSERT INTO reminders(user_id,guild_id,channel_id,message,remind_at) VALUES(?,?,?,?,?)',(ctx.author.id,ctx.guild.id,ctx.channel.id,message,time.time()+s)); await ctx.send(f'⏰ Erinnerung in {human(s)} gespeichert.')

    @commands.hybrid_command(name='highlights',description='Fügt persönliche Highlight-Wörter hinzu, entfernt sie oder listet sie auf.')
    async def highlights(self,ctx,phrase:str|None=None):
        if phrase:
            r=one('SELECT 1 FROM highlights WHERE guild_id=? AND user_id=? AND phrase=?',(ctx.guild.id,ctx.author.id,phrase.lower()))
            if r: execute('DELETE FROM highlights WHERE guild_id=? AND user_id=? AND phrase=?',(ctx.guild.id,ctx.author.id,phrase.lower())); state='entfernt'
            else: execute('INSERT OR IGNORE INTO highlights(guild_id,user_id,phrase) VALUES(?,?,?)',(ctx.guild.id,ctx.author.id,phrase.lower())); state='hinzugefügt'
            return await ctx.send(f'✅ Highlight {state}.')
        rows=query('SELECT phrase FROM highlights WHERE guild_id=? AND user_id=?',(ctx.guild.id,ctx.author.id)); await ctx.send(', '.join(f'`{r["phrase"]}`' for r in rows) or 'Keine Highlights.')

async def setup(bot): await bot.add_cog(Misc(bot))
