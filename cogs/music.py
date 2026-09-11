import asyncio,discord,yt_dlp
from discord.ext import commands
YDL_OPTS={'format':'bestaudio/best','noplaylist':True,'quiet':True,'default_search':'ytsearch','extract_flat':False}
FFMPEG_OPTS={'before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options':'-vn'}
class Music(commands.Cog):
    def __init__(self,bot):self.bot=bot;self.queues={};self.current={};self.looping=set();self.volumes={}
    def q(self,g):return self.queues.setdefault(g,[])
    async def extract(self,query):
        loop=asyncio.get_running_loop()
        def work():
            with yt_dlp.YoutubeDL(YDL_OPTS) as y:
                d=y.extract_info(query,download=False)
                if 'entries' in d:d=d['entries'][0]
                return {'title':d.get('title','Unbekannt'),'url':d.get('url'),'webpage':d.get('webpage_url') or d.get('original_url') or query,'duration':d.get('duration')}
        return await loop.run_in_executor(None,work)
    async def ensure_voice(self,ctx):
        if not getattr(ctx.author,'voice',None) or not ctx.author.voice.channel:
            await ctx.send('❌ Du musst in einem Voice-Channel sein.');return None
        if ctx.guild.voice_client:return ctx.guild.voice_client
        return await ctx.author.voice.channel.connect()
    async def play_next(self,guild):
        vc=guild.voice_client
        if not vc:return
        gid=guild.id
        if gid in self.looping and self.current.get(gid):track=self.current[gid]
        else:
            q=self.q(gid)
            if not q:self.current.pop(gid,None);return
            track=q.pop(0);self.current[gid]=track
        src=discord.FFmpegPCMAudio(track['url'],**FFMPEG_OPTS);src=discord.PCMVolumeTransformer(src,volume=self.volumes.get(gid,.5))
        def after(err):self.bot.loop.call_soon_threadsafe(lambda:asyncio.create_task(self.play_next(guild)))
        vc.play(src,after=after)
    @commands.hybrid_command(name='join')
    async def join(self,ctx):
        vc=await self.ensure_voice(ctx)
        if vc:await ctx.send(f'🔊 Verbunden mit **{vc.channel}**.')
    @commands.hybrid_command(name='leave')
    async def leave(self,ctx):
        if ctx.guild.voice_client:await ctx.guild.voice_client.disconnect(force=True)
        self.q(ctx.guild.id).clear();self.current.pop(ctx.guild.id,None);await ctx.send('👋 Voice verlassen.')
    @commands.hybrid_command(name='play')
    async def play(self,ctx,*,query:str):
        vc=await self.ensure_voice(ctx)
        if not vc:return
        if ctx.interaction:
            await ctx.defer()
        try:t=await self.extract(query)
        except Exception as e:return await ctx.send(f'❌ Audio konnte nicht geladen werden: {type(e).__name__}')
        self.q(ctx.guild.id).append(t);await ctx.send(f'🎵 Hinzugefügt: **{t["title"]}**')
        if not vc.is_playing() and not vc.is_paused():await self.play_next(ctx.guild)
    @commands.hybrid_command(name='skip')
    async def skip(self,ctx):
        vc=ctx.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):vc.stop();await ctx.send('⏭️ Übersprungen.')
        else:await ctx.send('❌ Nichts läuft.')
    @commands.hybrid_command(name='pause')
    async def pause(self,ctx):
        vc=ctx.guild.voice_client
        if vc and vc.is_playing():vc.pause();await ctx.send('⏸️ Pausiert.')
        else:await ctx.send('❌ Nichts läuft.')
    @commands.hybrid_command(name='resume')
    async def resume(self,ctx):
        vc=ctx.guild.voice_client
        if vc and vc.is_paused():vc.resume();await ctx.send('▶️ Fortgesetzt.')
        else:await ctx.send('❌ Nichts pausiert.')
    @commands.hybrid_command(name='stop')
    async def stop(self,ctx):
        self.q(ctx.guild.id).clear();self.looping.discard(ctx.guild.id);vc=ctx.guild.voice_client
        if vc:vc.stop()
        await ctx.send('⏹️ Gestoppt und Queue geleert.')
    @commands.hybrid_command(name='volume')
    async def volume(self,ctx,percent:commands.Range[int,0,100]):
        self.volumes[ctx.guild.id]=percent/100
        vc=ctx.guild.voice_client
        if vc and isinstance(vc.source,discord.PCMVolumeTransformer):vc.source.volume=percent/100
        await ctx.send(f'🔊 Lautstärke: {percent}%')
    @commands.hybrid_command(name='queue')
    async def queue_cmd(self,ctx):
        q=self.q(ctx.guild.id);cur=self.current.get(ctx.guild.id);lines=[]
        if cur:lines.append(f'▶️ **{cur["title"]}**')
        lines += [f'`{i}.` {t["title"]}' for i,t in enumerate(q[:15],1)]
        await ctx.send('\n'.join(lines) if lines else 'Queue ist leer.')
    @commands.hybrid_command(name='loop')
    async def loop(self,ctx):
        gid=ctx.guild.id
        if gid in self.looping:self.looping.remove(gid);state='aus'
        else:self.looping.add(gid);state='an'
        await ctx.send(f'🔁 Loop: **{state}**')
    @commands.hybrid_command(name='nowplaying')
    async def nowplaying(self,ctx):
        t=self.current.get(ctx.guild.id);await ctx.send(f'🎶 **{t["title"]}**' if t else 'Nichts läuft.')
async def setup(bot):await bot.add_cog(Music(bot))
