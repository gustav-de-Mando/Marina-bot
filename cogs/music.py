import asyncio
import base64
import os
import re
import shutil

import aiohttp
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
    # YouTube ändert seine Player-Auslieferung regelmäßig. Mehrere Clients geben
    # yt-dlp eine bessere Chance, einen normalen, nicht-DRM Audio-Stream zu finden.
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
}
FFMPEG_OPTS = {
    'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
SPOTIFY_TRACK_RE = re.compile(r'(?:open\.spotify\.com/track/|spotify:track:)([A-Za-z0-9]+)')


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
        self._spotify_token = None
        self._spotify_token_expires = 0.0

    def q(self, guild_id):
        return self.queues.setdefault(guild_id, [])

    def voice_lock(self, guild_id):
        return self.voice_locks.setdefault(guild_id, asyncio.Lock())

    async def defer_if_needed(self, ctx):
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

    async def spotify_token(self):
        client_id = os.environ.get('SPOTIFY_CLIENT_ID', '').strip()
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET', '').strip()
        if not client_id or not client_secret:
            return None

        now = asyncio.get_running_loop().time()
        if self._spotify_token and now < self._spotify_token_expires - 30:
            return self._spotify_token

        basic = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
        headers = {'Authorization': f'Basic {basic}', 'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'client_credentials'}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post('https://accounts.spotify.com/api/token', headers=headers, data=data) as response:
                if response.status != 200:
                    raise RuntimeError(f'Spotify Auth HTTP {response.status}')
                payload = await response.json()
        self._spotify_token = payload['access_token']
        self._spotify_token_expires = now + int(payload.get('expires_in', 3600))
        return self._spotify_token

    async def spotify_track_query(self, query):
        match = SPOTIFY_TRACK_RE.search(query)
        if not match:
            return None

        token = await self.spotify_token()
        if not token:
            raise RuntimeError('Spotify ist nicht konfiguriert. SPOTIFY_CLIENT_ID und SPOTIFY_CLIENT_SECRET fehlen.')

        track_id = match.group(1)
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {'Authorization': f'Bearer {token}'}
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f'https://api.spotify.com/v1/tracks/{track_id}', headers=headers) as response:
                if response.status != 200:
                    raise RuntimeError(f'Spotify Track HTTP {response.status}')
                track = await response.json()

        artists = ', '.join(a.get('name', '') for a in track.get('artists', []) if a.get('name'))
        title = track.get('name') or 'Unbekannter Titel'
        # Spotify-Audio wird NICHT in Discord gestreamt. Wir verwenden nur die
        # Metadaten und suchen denselben Song anschließend auf YouTube.
        return f'{title} {artists} official audio'.strip(), title, artists

    async def extract_youtube(self, query):
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

    async def extract(self, query):
        spotify = await self.spotify_track_query(query)
        if spotify:
            search_query, spotify_title, spotify_artists = spotify
            track = await self.extract_youtube(search_query)
            track['requested_via'] = 'spotify'
            track['spotify_title'] = spotify_title
            track['spotify_artists'] = spotify_artists
            return track
        return await self.extract_youtube(query)

    async def cleanup_voice(self, guild):
        vc = guild.voice_client
        if vc is not None:
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass

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
                        await asyncio.wait_for(vc.move_to(target), timeout=10)
                    except Exception as exc:
                        print(f'❌ Voice move ({ctx.guild.id}): {type(exc).__name__}: {exc}')
                        await ctx.send(f'❌ Ich konnte nicht in deinen Voice-Channel wechseln: `{type(exc).__name__}`')
                        return None
                return vc

            if vc is not None:
                await self.cleanup_voice(ctx.guild)

            try:
                vc = await target.connect(timeout=10.0, reconnect=False, self_deaf=True)
                return vc
            except asyncio.TimeoutError:
                print(f'❌ Voice connect timeout ({ctx.guild.id})')
                await self.cleanup_voice(ctx.guild)
                await ctx.send('❌ Voice-Verbindung ist fehlgeschlagen (Timeout). Der Bot versucht nicht automatisch erneut zu joinen.')
            except discord.ClientException as exc:
                print(f'❌ Voice ClientException ({ctx.guild.id}): {exc}')
                existing = ctx.guild.voice_client
                if existing is not None and existing.is_connected():
                    return existing
                await self.cleanup_voice(ctx.guild)
                await ctx.send(f'❌ Voice-Verbindung fehlgeschlagen: `{exc}`')
            except Exception as exc:
                print(f'❌ Voice connect ({ctx.guild.id}): {type(exc).__name__}: {exc}')
                await self.cleanup_voice(ctx.guild)
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
            source = discord.FFmpegPCMAudio(track['url'], executable=self._ffmpeg, **FFMPEG_OPTS)
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
            self.bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.play_next(guild)))

        try:
            vc.play(source, after=after)
        except discord.ClientException as exc:
            print(f'❌ Voice play ({guild.id}): {exc}')

    @commands.hybrid_command(name='join', description='Verbindet den Bot mit deinem Voice-Channel.')
    async def join(self, ctx):
        await self.defer_if_needed(ctx)
        before = ctx.guild.voice_client
        vc = await self.ensure_voice(ctx)
        if vc:
            if before is vc and vc.is_connected():
                await ctx.send(f'🔊 Ich bin bereits in **{vc.channel}**.')
            else:
                await ctx.send(f'🔊 Verbunden mit **{vc.channel}**.')

    @commands.hybrid_command(name='leave', description='Trennt den Bot vom Voice-Channel und leert die Queue.')
    async def leave(self, ctx):
        await self.defer_if_needed(ctx)
        gid = ctx.guild.id
        self.q(gid).clear()
        self.current.pop(gid, None)
        self.looping.discard(gid)
        await self.cleanup_voice(ctx.guild)
        await ctx.send('👋 Voice verlassen und Queue geleert.')

    @commands.hybrid_command(name='play', description='Spielt YouTube-Suchen/Links oder Spotify-Tracklinks ab.')
    async def play(self, ctx, *, query: str):
        await self.defer_if_needed(ctx)
        vc = await self.ensure_voice(ctx)
        if not vc:
            return
        try:
            track = await self.extract(query)
        except Exception as exc:
            message = str(exc)
            print(f'❌ Musik-Quelle: {type(exc).__name__}: {message}')
            if 'DRM' in message.upper():
                return await ctx.send('❌ Diese Quelle ist DRM-geschützt und kann nicht abgespielt werden.')
            if 'Spotify ist nicht konfiguriert' in message:
                return await ctx.send('❌ Spotify-Link erkannt, aber Spotify API ist noch nicht konfiguriert.')
            return await ctx.send(f'❌ Audio konnte nicht geladen werden: `{type(exc).__name__}`')

        self.q(ctx.guild.id).append(track)
        if track.get('requested_via') == 'spotify':
            await ctx.send(f'🎵 Spotify erkannt: **{track["spotify_title"]}** – {track["spotify_artists"]}\n🔎 Passende YouTube-Audioquelle gefunden und zur Queue hinzugefügt.')
        else:
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
