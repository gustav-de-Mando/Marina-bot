import json
import time

from discord.ext import commands

from core.storage import execute, get_guild_settings, one, query, update_guild_settings


class Backup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        execute('''CREATE TABLE IF NOT EXISTS bot_backups(
            guild_id BIGINT NOT NULL,
            backup_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(guild_id,backup_id)
        )''')

    @commands.hybrid_command(name='backup_create', description='Erstellt ein dauerhaft gespeichertes Konfigurations-Backup.')
    @commands.has_permissions(administrator=True)
    async def create(self, ctx):
        backup_id = str(int(time.time()))
        data = {
            'id': backup_id,
            'guild_id': ctx.guild.id,
            'settings': get_guild_settings(ctx.guild.id),
            'level_roles': [dict(x) for x in query('SELECT level,role_id FROM level_roles WHERE guild_id=?', (ctx.guild.id,))],
            'joinable_ranks': [dict(x) for x in query('SELECT role_id,name FROM joinable_ranks WHERE guild_id=?', (ctx.guild.id,))],
            'tags': [dict(x) for x in query('SELECT name,content,owner_id,uses FROM tags WHERE guild_id=?', (ctx.guild.id,))],
        }
        execute('''INSERT INTO bot_backups(guild_id,backup_id,data_json) VALUES(?,?,?)
                   ON CONFLICT(guild_id,backup_id) DO UPDATE SET data_json=excluded.data_json''',
                (ctx.guild.id, backup_id, json.dumps(data, ensure_ascii=False)))
        await ctx.send(f'💾 Backup `{backup_id}` dauerhaft gespeichert.')

    @commands.hybrid_command(name='backup_list', description='Zeigt die gespeicherten Backups des Servers.')
    @commands.has_permissions(administrator=True)
    async def list(self, ctx):
        rows = query('SELECT backup_id FROM bot_backups WHERE guild_id=? ORDER BY backup_id DESC LIMIT 20', (ctx.guild.id,))
        await ctx.send('Backups: ' + (', '.join(f'`{row["backup_id"]}`' for row in rows) if rows else 'Keine'))

    @commands.hybrid_command(name='backup_restore', description='Stellt ein gespeichertes Konfigurations-Backup wieder her.')
    @commands.has_permissions(administrator=True)
    async def restore(self, ctx, backup_id: str):
        row = one('SELECT data_json FROM bot_backups WHERE guild_id=? AND backup_id=?', (ctx.guild.id, backup_id))
        if not row:
            return await ctx.send('❌ Backup nicht gefunden.')
        data = json.loads(row['data_json'])
        update_guild_settings(ctx.guild.id, **data.get('settings', {}))
        execute('DELETE FROM level_roles WHERE guild_id=?', (ctx.guild.id,))
        execute('DELETE FROM joinable_ranks WHERE guild_id=?', (ctx.guild.id,))
        execute('DELETE FROM tags WHERE guild_id=?', (ctx.guild.id,))
        for item in data.get('level_roles', []):
            execute('''INSERT INTO level_roles(guild_id,level,role_id) VALUES(?,?,?)
                       ON CONFLICT(guild_id,level) DO UPDATE SET role_id=excluded.role_id''',
                    (ctx.guild.id, item['level'], item['role_id']))
        for item in data.get('joinable_ranks', []):
            execute('''INSERT INTO joinable_ranks(guild_id,role_id,name) VALUES(?,?,?)
                       ON CONFLICT(guild_id,role_id) DO UPDATE SET name=excluded.name''',
                    (ctx.guild.id, item['role_id'], item['name']))
        for item in data.get('tags', []):
            execute('''INSERT INTO tags(guild_id,name,content,owner_id,uses) VALUES(?,?,?,?,?)
                       ON CONFLICT(guild_id,name) DO UPDATE SET
                       content=excluded.content,owner_id=excluded.owner_id,uses=excluded.uses''',
                    (ctx.guild.id, item['name'], item['content'], item['owner_id'], item.get('uses', 0)))
        await ctx.send('✅ Backup-Konfiguration wiederhergestellt. Discord-Rollen/Channels werden absichtlich nicht gelöscht oder neu erstellt.')


async def setup(bot):
    await bot.add_cog(Backup(bot))
