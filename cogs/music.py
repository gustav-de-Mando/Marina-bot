import asyncio
import shutil

import discord
import yt_dlp
from discord.ext import commands

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1',
    'extract_flat': False,
    'source_address': '0.0.0.0',
}
FFMPEG_OPTS = {
    'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


def ffmpeg_executable():
    system = shutil.which('ffmpeg')
    if system:
        return system
    if imageio_ffmpeg is not None:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    return 'ffmpeg'


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.current = {}
        self.looping = set()
        self.volumes = {}
        self.voice_locks = {}
        self.text_channels = {}
        self._ffmpeg = ffmpeg_executable()

    def q(self, guild_id):
        return self.queues.setdefault(guild_id, [])

    def voice_lock(self, guild_id):
        return self.voice_locks.setdefault(guild_id, asyncio.Lock())

    async def extract(self, query):
        loop = asyncio.get_running_loop()

        def work():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                data = ydl.extract_info(query, download=False)
                if data and 'entries' in data:
                    entries = [entry for entry in data.get('entries', []) if entry]
                    if not entries:
                        raise RuntimeError('Keine Treffer gefunden')
                    data = entries[0]
                if not data or not data.get('url'):
                    raise RuntimeError('Keine Audioquelle gefunden')
                return {
                    'title': data.get('title', 'Unbekannt'),
                    'url': data['url'],
                    'webpage': data.get('webpage_url') or data.get('original_url') or query,
                    'duration': data.get('duration'),
                }

        return await loop.run_in_executor(None, work)

    async def ensure_voice(self, ctx):
        voice_state = getattr(ctx.author, 'voice', None)
        target = voice_state.channel if voice_state else None
        if target is None:
            await ctx.send('❌ Du musst zuerst in einem Voice-Channel sein.')
            return None

        self.text_channels[ctx.guild.id] = ctx.channel.id
        async with self.voice_lock(ctx.guild.id):
            vc = ctx.guild.voice_client

            if vc is not None and vc.is_connected():
                if vc.channel != target:
                    try:
                        await vc.move_to(target)
                    except Exception as exc:
                        await ctx.send(f'❌ Ich konnte nicht in deinen Voice-Channel wechseln: `{type(exc).__name__}`')
                        return None
                return vc

            # Ein veralteter VoiceClient kann nach einem Verbindungsabbruch noch
            # registriert sein. Erst sauber entfernen, dann genau einmal verbinden.
            if vc is not None:
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                await asyncio.sleep(0.5)

            try:
                return await target.connect(timeout=20.0, reconnect=True, self_deaf=True)
            except asyncio.TimeoutError:
                await ctx.send('❌ Voice-Verbindung hat zu lange gebraucht. Versuch es gleich noch einmal.')
            except discord.ClientException as exc:
                # Falls Discord während des Handshakes bereits einen VoiceClient
                # registriert hat, diesen wiederverwenden statt erneut zu joinen.
                existing = ctx.guild.voice_client
                if existing is not None and existing.is_connected():
                    return existing
                await ctx.send(f'❌ Voice-Verbindung fehlgeschlagen: `{exc}`')
            except Exception as exc:
                await ctx.send(f'❌ Voice-Verbindung fehlgeschlagen: `{type(exc).__name__}`')
            return None

    async def play_next(self, guild):
        vc = guild.voice_client
        if vc is None or not vc.is_connected():
            return

        gid = guild.id
        if gid in self.looping and self.current.get(gid):
            track = self.current[gid]
        else:
            queue = self.q(gid)
            if not queue:
                self.current.pop(gid, None)
                return
            track = queue.pop(0)
            self.current[gid] = track

        try:
            source = discord.FFmpegPCMAudio(
                track['url'],
                executable=self._ffmpeg,
                **FFMPEG_OPTS,
            )
            source = discord.PCMVolumeTransformer(source, volume=self.volumes.get(gid, 0.5))
        except Exception as exc:
            print(f'❌ Musik/FFmpeg ({guild.id}): {type(exc).__name__}: {exc}')
            self.current.pop(gid, None)
            channel = guild.get_channel(self.text_channels.get(gid, 0))
            if channel:
                try:
                    await channel.send(f'❌ Wiedergabe konnte nicht gestartet werden: `{type(exc).__name__}`')
                except Exception:
                    pass
            if self.q(gid):
                await self.play_next(guild)
            return

        def after(error):
            if error:
                print(f'❌ Voice-Player ({guild.id}): {error}')
            self.bot.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.play_next(guild))
            )

        try:
            vc.play(source, after=after)
        except discord.ClientException as exc:
            print(f'❌ Voice play ({guild.id}): {exc}')

    @commands.hybrid_command(name='join', description='Verbindet den Bot mit deinem Voice-Channel.')
    async def join(self, ctx):
        before = ctx.guild.voice_client
        vc = await self.ensure_voice(ctx)
        if vc:
            if before is vc and vc.is_connected():
                await ctx.send(f'🔊 Ich bin bereits in **{vc.channel}**.')
            else:
                await ctx.send(f'🔊 Verbunden mit **{vc.channel}**.')

    @commands.hybrid_command(name='leave', description='Trennt den Bot vom Voice-Channel und leert die Queue.')
    async def leave(self, ctx):
        gid = ctx.guild.id
        self.q(gid).clear()
        self.current.pop(gid, None)
        self.looping.discard(gid)
        vc = ctx.guild.voice_client
        if vc is not None:
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass
        await ctx.send('👋 Voice verlassen und Queue geleert.')

    @commands.hybrid_command(name='play', description='Spielt einen Song oder fügt ihn zur Warteschlange hinzu.')
    async def play(self, ctx, *, query: str):
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()
        vc = await self.ensure_voice(ctx)
        if not vc:
            return
        try:
            track = await self.extract(query)
        except Exception as exc:
            print(f'❌ yt-dlp: {type(exc).__name__}: {exc}')
            return await ctx.send(f'❌ Audio konnte nicht geladen werden: `{type(exc).__name__}`')

        self.q(ctx.guild.id).append(track)
        await ctx.send(f'🎵 Hinzugefügt: **{track["title"]}**')
        if not vc.is_playing() and not vc.is_paused():
            await self.play_next(ctx.guild)

    @commands.hybrid_command(name='skip', description='Überspringt den aktuell laufenden Song.')
    async def skip(self, ctx):
        vc = ctx.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await ctx.send('⏭️ Übersprungen.')
        else:
            await ctx.send('❌ Nichts läuft.')

    @commands.hybrid_command(name='pause', description='Pausiert die aktuelle Wiedergabe.')
    async def pause(self, ctx):
        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send('⏸️ Pausiert.')
        else:
            await ctx.send('❌ Nichts läuft.')

    @commands.hybrid_command(name='resume', description='Setzt eine pausierte Wiedergabe fort.')
    async def resume(self, ctx):
        vc = ctx.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send('▶️ Fortgesetzt.')
        else:
            await ctx.send('❌ Nichts pausiert.')

    @commands.hybrid_command(name='stop', description='Stoppt die Musik und leert die Warteschlange.')
    async def stop(self, ctx):
        gid = ctx.guild.id
        self.q(gid).clear()
        self.looping.discard(gid)
        self.current.pop(gid, None)
        vc = ctx.guild.voice_client
        if vc:
            vc.stop()
        await ctx.send('⏹️ Gestoppt und Queue geleert.')

    @commands.hybrid_command(name='volume', description='Ändert die Musiklautstärke in Prozent.')
    async def volume(self, ctx, percent: commands.Range[int, 0, 100]):
        self.volumes[ctx.guild.id] = percent / 100
        vc = ctx.guild.voice_client
        if vc and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = percent / 100
        await ctx.send(f'🔊 Lautstärke: {percent}%')

    @commands.hybrid_command(name='queue', description='Zeigt den aktuellen Song und die Warteschlange.')
    async def queue_cmd(self, ctx):
        queue = self.q(ctx.guild.id)
        current = self.current.get(ctx.guild.id)
        lines = []
        if current:
            lines.append(f'▶️ **{current["title"]}**')
        lines += [f'`{i}.` {track["title"]}' for i, track in enumerate(queue[:15], 1)]
        await ctx.send('\n'.join(lines) if lines else 'Queue ist leer.')

    @commands.hybrid_command(name='loop', description='Schaltet die Wiederholung des aktuellen Songs um.')
    async def loop(self, ctx):
        gid = ctx.guild.id
        if gid in self.looping:
            self.looping.remove(gid)
            state = 'aus'
        else:
            self.looping.add(gid)
            state = 'an'
        await ctx.send(f'🔁 Loop: **{state}**')

    @commands.hybrid_command(name='nowplaying', description='Zeigt den aktuell laufenden Song.')
    async def nowplaying(self, ctx):
        track = self.current.get(ctx.guild.id)
        await ctx.send(f'🎶 **{track["title"]}**' if track else 'Nichts läuft.')


async def setup(bot):
    await bot.add_cog(Music(bot))
