import os,json,time,discord
from discord.ext import commands
from core.storage import get_guild_settings,update_guild_settings,query,execute
DIR='data/backups'
class Backup(commands.Cog):
    def __init__(self,bot):self.bot=bot;os.makedirs(DIR,exist_ok=True)
    def path(self,gid,bid):return os.path.join(DIR,f'{gid}_{bid}.json')
    @commands.hybrid_command(name='backup_create')
    @commands.has_permissions(administrator=True)
    async def create(self,ctx):
        bid=str(int(time.time()));data={'id':bid,'guild_id':ctx.guild.id,'settings':get_guild_settings(ctx.guild.id),'level_roles':[dict(x) for x in query('SELECT level,role_id FROM level_roles WHERE guild_id=?',(ctx.guild.id,))],'joinable_ranks':[dict(x) for x in query('SELECT role_id,name FROM joinable_ranks WHERE guild_id=?',(ctx.guild.id,))],'tags':[dict(x) for x in query('SELECT name,content,owner_id,uses FROM tags WHERE guild_id=?',(ctx.guild.id,))]}
        with open(self.path(ctx.guild.id,bid),'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
        await ctx.send(f'💾 Backup `{bid}` erstellt.')
    @commands.hybrid_command(name='backup_list')
    @commands.has_permissions(administrator=True)
    async def list(self,ctx):
        ids=[x.removeprefix(f'{ctx.guild.id}_').removesuffix('.json') for x in os.listdir(DIR) if x.startswith(f'{ctx.guild.id}_')];await ctx.send('Backups: '+(', '.join(f'`{x}`' for x in sorted(ids,reverse=True)[:20]) if ids else 'Keine'))
    @commands.hybrid_command(name='backup_restore')
    @commands.has_permissions(administrator=True)
    async def restore(self,ctx,backup_id:str):
        try:
            with open(self.path(ctx.guild.id,backup_id),encoding='utf-8') as f:d=json.load(f)
        except:return await ctx.send('❌ Backup nicht gefunden.')
        update_guild_settings(ctx.guild.id,**d.get('settings',{}));execute('DELETE FROM level_roles WHERE guild_id=?',(ctx.guild.id,));execute('DELETE FROM joinable_ranks WHERE guild_id=?',(ctx.guild.id,));execute('DELETE FROM tags WHERE guild_id=?',(ctx.guild.id,))
        for x in d.get('level_roles',[]):execute('INSERT OR REPLACE INTO level_roles(guild_id,level,role_id) VALUES(?,?,?)',(ctx.guild.id,x['level'],x['role_id']))
        for x in d.get('joinable_ranks',[]):execute('INSERT OR REPLACE INTO joinable_ranks(guild_id,role_id,name) VALUES(?,?,?)',(ctx.guild.id,x['role_id'],x['name']))
        for x in d.get('tags',[]):execute('INSERT OR REPLACE INTO tags(guild_id,name,content,owner_id,uses) VALUES(?,?,?,?,?)',(ctx.guild.id,x['name'],x['content'],x['owner_id'],x.get('uses',0)))
        await ctx.send('✅ Backup-Konfiguration wiederhergestellt. Discord-Rollen/Channels werden absichtlich nicht gelöscht/neu erstellt.')
async def setup(bot):await bot.add_cog(Backup(bot))
