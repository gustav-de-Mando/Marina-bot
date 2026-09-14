import asyncio
from discord.ext import commands
from core.storage import execute, one

lock = asyncio.Lock()


class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        execute('''CREATE TABLE IF NOT EXISTS counting_state(
            guild_id BIGINT PRIMARY KEY,
            channel_id BIGINT NOT NULL,
            count INTEGER DEFAULT 0,
            last_user BIGINT
        )''')

    @commands.hybrid_command(name='counting_setup', description='Aktiviert Counting im aktuellen Channel.')
    @commands.has_permissions(manage_guild=True)
    async def setup_count(self, ctx):
        async with lock:
            execute('''INSERT INTO counting_state(guild_id,channel_id,count,last_user)
                       VALUES(?,?,0,NULL)
                       ON CONFLICT(guild_id) DO UPDATE SET
                       channel_id=excluded.channel_id,count=0,last_user=NULL''',
                    (ctx.guild.id, ctx.channel.id))
        await ctx.send('✅ Counting hier aktiviert. Start mit **1**.')

    @commands.hybrid_command(name='counting_reset', description='Setzt den Counting-Zähler auf 0 zurück.')
    @commands.has_permissions(manage_messages=True)
    async def reset(self, ctx):
        async with lock:
            state = one('SELECT guild_id FROM counting_state WHERE guild_id=?', (ctx.guild.id,))
            if not state:
                return await ctx.send('❌ Counting nicht aktiv.')
            execute('UPDATE counting_state SET count=0,last_user=NULL WHERE guild_id=?', (ctx.guild.id,))
        await ctx.send('🔄 Zähler zurückgesetzt.')

    @commands.hybrid_command(name='counting_stop', description='Deaktiviert Counting auf diesem Server.')
    @commands.has_permissions(manage_guild=True)
    async def stop(self, ctx):
        async with lock:
            execute('DELETE FROM counting_state WHERE guild_id=?', (ctx.guild.id,))
        await ctx.send('✅ Counting deaktiviert.')

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return
        state = one('SELECT channel_id,count,last_user FROM counting_state WHERE guild_id=?', (message.guild.id,))
        if not state or message.channel.id != state['channel_id']:
            return
        if not message.content.strip().isdigit():
            return

        async with lock:
            state = one('SELECT channel_id,count,last_user FROM counting_state WHERE guild_id=?', (message.guild.id,))
            if not state or message.channel.id != state['channel_id']:
                return
            num = int(message.content.strip())
            expected = state['count'] + 1
            if num != expected or state['last_user'] == message.author.id:
                try:
                    await message.add_reaction('❌')
                except Exception:
                    pass
                execute('UPDATE counting_state SET count=0,last_user=NULL WHERE guild_id=?', (message.guild.id,))
                return await message.channel.send(f'💥 Falsch! Erwartet war **{expected}**. Neustart bei **1**.')

            execute('UPDATE counting_state SET count=?,last_user=? WHERE guild_id=?',
                    (num, message.author.id, message.guild.id))
        try:
            await message.add_reaction('✅')
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Counting(bot))
