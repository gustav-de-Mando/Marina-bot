import discord,random,aiohttp
from discord.ext import commands

async def get_json(url,params=None):
    timeout=aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url,params=params,headers={'User-Agent':'AllInOneDiscordBot/1.0'}) as r:
            if r.status!=200: raise RuntimeError(f'HTTP {r.status}')
            return await r.json(content_type=None)

class Fun(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.hybrid_command(name='hug')
    async def hug(self,ctx,member:discord.Member):await ctx.send(f'🤗 {ctx.author.mention} umarmt {member.mention}.')
    @commands.hybrid_command(name='pat')
    async def pat(self,ctx,member:discord.Member):await ctx.send(f'👋 {ctx.author.mention} tätschelt {member.mention}.')
    @commands.hybrid_command(name='slap')
    async def slap(self,ctx,member:discord.Member):await ctx.send(f'😵 {ctx.author.mention} gibt {member.mention} einen cartoonhaften Klaps.')
    @commands.hybrid_command(name='poke')
    async def poke(self,ctx,member:discord.Member):await ctx.send(f'👉 {ctx.author.mention} stupst {member.mention} an.')
    @commands.hybrid_command(name='8ball')
    async def eightball(self,ctx,*,frage:str):await ctx.send('🎱 '+random.choice(['Ja.','Nein.','Sehr wahrscheinlich.','Eher nicht.','Frag später nochmal.','Sieht gut aus.','Unklar.']))
    @commands.hybrid_command(name='joke')
    async def joke(self,ctx):
        jokes=['Warum können Geister so schlecht lügen? Weil man durch sie hindurchsieht.','Was macht ein Keks unter einem Baum? Krümel.','Warum nehmen Programmierer eine Brille? Weil sie C# nicht sehen.']
        await ctx.send('😂 '+random.choice(jokes))
    @commands.hybrid_command(name='dadjoke')
    async def dadjoke(self,ctx):
        try:
            d=await get_json('https://icanhazdadjoke.com/',params={}); await ctx.send('😄 '+d.get('joke','Kein Witz gefunden.'))
        except:await self.joke(ctx)
    @commands.hybrid_command(name='ship')
    async def ship(self,ctx,user1:discord.Member,user2:discord.Member):
        seed=min(user1.id,user2.id)^max(user1.id,user2.id);rng=random.Random(seed);pct=rng.randint(0,100);await ctx.send(f'💞 {user1.mention} + {user2.mention}: **{pct}%** Match')
    async def animal(self,ctx,kind):
        try:
            if kind=='cat':d=await get_json('https://api.thecatapi.com/v1/images/search');url=d[0]['url']
            elif kind=='dog':d=await get_json('https://dog.ceo/api/breeds/image/random');url=d['message']
            else:d=await get_json('https://dog.ceo/api/breed/pug/images/random');url=d['message']
            e=discord.Embed(title={'cat':'🐱 Katze','dog':'🐶 Hund','pug':'🐾 Mops'}[kind]);e.set_image(url=url);await ctx.send(embed=e)
        except:await ctx.send('❌ Bilddienst ist gerade nicht erreichbar.')
    @commands.hybrid_command(name='cat')
    async def cat(self,ctx):await self.animal(ctx,'cat')
    @commands.hybrid_command(name='dog')
    async def dog(self,ctx):await self.animal(ctx,'dog')
    @commands.hybrid_command(name='pug')
    async def pug(self,ctx):await self.animal(ctx,'pug')
    @commands.hybrid_command(name='github')
    async def github(self,ctx,repository:str):
        repo=repository.removeprefix('https://github.com/').strip('/')
        try:d=await get_json(f'https://api.github.com/repos/{repo}');await ctx.send(embed=discord.Embed(title=d['full_name'],url=d['html_url'],description=d.get('description') or 'Keine Beschreibung.').add_field(name='⭐ Stars',value=d['stargazers_count']).add_field(name='🍴 Forks',value=d['forks_count']).add_field(name='Sprache',value=d.get('language') or '?'))
        except:await ctx.send('❌ Repository nicht gefunden oder GitHub nicht erreichbar.')
    @commands.hybrid_command(name='itunes')
    async def itunes(self,ctx,*,song:str):
        try:
            d=await get_json('https://itunes.apple.com/search',{'term':song,'entity':'song','limit':1});r=d['results'][0];e=discord.Embed(title=r['trackName'],url=r.get('trackViewUrl'),description=r['artistName']);e.set_thumbnail(url=r.get('artworkUrl100'));e.add_field(name='Album',value=r.get('collectionName','?'));await ctx.send(embed=e)
        except:await ctx.send('❌ Song nicht gefunden.')
    @commands.hybrid_command(name='pokemon')
    async def pokemon(self,ctx,name:str):
        try:
            d=await get_json(f'https://pokeapi.co/api/v2/pokemon/{name.lower()}');e=discord.Embed(title=d['name'].title(),description='Typ: '+', '.join(x['type']['name'] for x in d['types']));e.set_thumbnail(url=d['sprites']['front_default']);e.add_field(name='Höhe',value=d['height']);e.add_field(name='Gewicht',value=d['weight']);await ctx.send(embed=e)
        except:await ctx.send('❌ Pokémon nicht gefunden.')
    @commands.hybrid_command(name='space')
    async def space(self,ctx):
        try:d=await get_json('http://api.open-notify.org/iss-now.json');p=d['iss_position'];await ctx.send(f"🛰️ ISS aktuell ungefähr bei **{float(p['latitude']):.2f}°, {float(p['longitude']):.2f}°**.")
        except:await ctx.send('❌ ISS-Dienst ist gerade nicht erreichbar.')
    @commands.hybrid_command(name='covid')
    async def covid(self,ctx,country:str='world'):
        try:
            url='https://disease.sh/v3/covid-19/all' if country.lower()=='world' else f'https://disease.sh/v3/covid-19/countries/{country}'
            d=await get_json(url);await ctx.send(f"🦠 **{d.get('country','Weltweit')}** — Fälle: **{d.get('cases',0):,}**, Todesfälle: **{d.get('deaths',0):,}**, Genesen: **{d.get('recovered',0):,}**. Quelle: disease.sh")
        except:await ctx.send('❌ Statistik nicht verfügbar.')
    @commands.hybrid_command(name='dynoavatar')
    async def dynoavatar(self,ctx,member:discord.Member|None=None):
        member=member or ctx.author;e=discord.Embed(title=f'Avatar von {member.display_name}',description='Eigener Avatar-Viewer im Dyno-Stil.',color=discord.Color.blurple());e.set_image(url=member.display_avatar.with_size(512).url);await ctx.send(embed=e)
async def setup(bot):await bot.add_cog(Fun(bot))
