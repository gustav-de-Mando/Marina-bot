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

    @commands.hybrid_command(name='hug',description='Umarmt ein Mitglied virtuell.')
    async def hug(self,ctx,member:discord.Member):await ctx.send(f'🤗 {ctx.author.mention} umarmt {member.mention}.')

    @commands.hybrid_command(name='pat',description='Tätschelt ein Mitglied virtuell.')
    async def pat(self,ctx,member:discord.Member):await ctx.send(f'👋 {ctx.author.mention} tätschelt {member.mention}.')

    @commands.hybrid_command(name='slap',description='Gibt einem Mitglied einen cartoonhaften Klaps.')
    async def slap(self,ctx,member:discord.Member):await ctx.send(f'😵 {ctx.author.mention} gibt {member.mention} einen cartoonhaften Klaps.')

    @commands.hybrid_command(name='poke',description='Stupst ein Mitglied virtuell an.')
    async def poke(self,ctx,member:discord.Member):await ctx.send(f'👉 {ctx.author.mention} stupst {member.mention} an.')

    @commands.hybrid_command(name='8ball',description='Beantwortet eine Frage zufällig wie eine Magic 8-Ball.')
    async def eightball(self,ctx,*,frage:str):await ctx.send('🎱 '+random.choice(['Ja.','Nein.','Sehr wahrscheinlich.','Eher nicht.','Frag später nochmal.','Sieht gut aus.','Unklar.']))

    @commands.hybrid_command(name='joke',description='Erzählt einen kurzen Witz.')
    async def joke(self,ctx):
        jokes=['Warum können Geister so schlecht lügen? Weil man durch sie hindurchsieht.','Was macht ein Keks unter einem Baum? Krümel.','Warum nehmen Programmierer eine Brille? Weil sie C# nicht sehen.']
        await ctx.send('😂 '+random.choice(jokes))

    @commands.hybrid_command(name='dadjoke',description='Erzählt einen zufälligen Dad-Joke.')
    async def dadjoke(self,ctx):
        try:
            d=await get_json('https://icanhazdadjoke.com/',params={}); await ctx.send('😄 '+d.get('joke','Kein Witz gefunden.'))
        except:await self.joke(ctx)

    @commands.hybrid_command(name='ship',description='Berechnet spielerisch einen Match-Wert zwischen zwei Mitgliedern.')
    async def ship(self,ctx,user1:discord.Member,user2:discord.Member):
        seed=min(user1.id,user2.id)^max(user1.id,user2.id);rng=random.Random(seed);pct=rng.randint(0,100);await ctx.send(f'💞 {user1.mention} + {user2.mention}: **{pct}%** Match')

    async def animal(self,ctx,kind):
        try:
            if kind=='cat':d=await get_json('https://api.thecatapi.com/v1/images/search');url=d[0]['url']
            else:d=await get_json('https://dog.ceo/api/breeds/image/random');url=d['message']
            e=discord.Embed(title={'cat':'🐱 Katze','dog':'🐶 Hund'}[kind]);e.set_image(url=url);await ctx.send(embed=e)
        except:await ctx.send('❌ Bilddienst ist gerade nicht erreichbar.')

    @commands.hybrid_command(name='cat',description='Zeigt ein zufälliges Katzenbild.')
    async def cat(self,ctx):await self.animal(ctx,'cat')

    @commands.hybrid_command(name='dog',description='Zeigt ein zufälliges Hundebild.')
    async def dog(self,ctx):await self.animal(ctx,'dog')

async def setup(bot):await bot.add_cog(Fun(bot))
