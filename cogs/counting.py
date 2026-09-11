import json,os,asyncio
from discord.ext import commands
FILE='data/counting.json';lock=asyncio.Lock()
def load():
    try:
        with open(FILE,encoding='utf-8') as f:return json.load(f)
    except:return {}
def save(d):
    os.makedirs('data',exist_ok=True)
    with open(FILE,'w',encoding='utf-8') as f:json.dump(d,f,indent=2)
class Counting(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.hybrid_command(name='counting_setup')
    @commands.has_permissions(manage_guild=True)
    async def setup_count(self,ctx):
        async with lock:d=load();d[str(ctx.guild.id)]={'channel':ctx.channel.id,'count':0,'last_user':None};save(d)
        await ctx.send('✅ Counting hier aktiviert. Start mit **1**.')
    @commands.hybrid_command(name='counting_reset')
    @commands.has_permissions(manage_messages=True)
    async def reset(self,ctx):
        async with lock:d=load();g=d.get(str(ctx.guild.id));
        if not g:return await ctx.send('❌ Counting nicht aktiv.')
        g['count']=0;g['last_user']=None;save(d);await ctx.send('🔄 Zähler zurückgesetzt.')
    @commands.hybrid_command(name='counting_stop')
    @commands.has_permissions(manage_guild=True)
    async def stop(self,ctx):
        async with lock:d=load();d.pop(str(ctx.guild.id),None);save(d)
        await ctx.send('✅ Counting deaktiviert.')
    @commands.Cog.listener()
    async def on_message(self,m):
        if not m.guild or m.author.bot:return
        d=load();g=d.get(str(m.guild.id))
        if not g or m.channel.id!=g['channel']:return
        if not m.content.strip().isdigit():return
        num=int(m.content.strip());expected=g['count']+1
        if num!=expected or g['last_user']==m.author.id:
            try:await m.add_reaction('❌')
            except:pass
            g['count']=0;g['last_user']=None;save(d);return await m.channel.send(f'💥 Falsch! Erwartet war **{expected}**. Neustart bei **1**.')
        g['count']=num;g['last_user']=m.author.id;save(d)
        try:await m.add_reaction('✅')
        except:pass
async def setup(bot):await bot.add_cog(Counting(bot))
