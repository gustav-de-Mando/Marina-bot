import os,asyncio
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from threading import Thread
from core.storage import init_db,get_guild_settings,one
from dashboard.app import create_dashboard

load_dotenv(); init_db()
DEFAULT_PREFIX=os.environ.get('DEFAULT_PREFIX','-')[:5] or '-'
BOT_NAME=os.environ.get('BOT_NAME','Mr. Flipper')
MAX_TOP_LEVEL_SLASH=100

def allowed_for(guild,channel,user,command_name):
    if not guild:return True
    if getattr(user,'guild_permissions',None) and (user.guild_permissions.administrator or user.guild_permissions.manage_guild):return True
    if one('SELECT 1 FROM command_rules WHERE guild_id=? AND command=? AND enabled=0',(guild.id,command_name.lower())):return False
    if one('SELECT 1 FROM ignored WHERE guild_id=? AND kind=? AND target_id=?',(guild.id,'channel',channel.id)):return False
    if one('SELECT 1 FROM ignored WHERE guild_id=? AND kind=? AND target_id=?',(guild.id,'user',user.id)):return False
    for role in getattr(user,'roles',[]):
        if one('SELECT 1 FROM ignored WHERE guild_id=? AND kind=? AND target_id=?',(guild.id,'role',role.id)):return False
    return True

class UnifiedTree(app_commands.CommandTree):
    def add_command(self,command,*,guild=None,guilds=None,override=False):
        # Discord erlaubt maximal 100 Top-Level Slash-Commands. Hybrid-Commands
        # über dem Limit bleiben als Prefix-Commands verfügbar, statt ganze Cogs
        # beim Laden scheitern zu lassen.
        if guild is None and guilds is None:
            current=len(super().get_commands(guild=None))
            if current>=MAX_TOP_LEVEL_SLASH:
                print(f'⚠️ Slash-Limit erreicht: /{getattr(command,"name","?")} bleibt nur als Prefix-Command verfügbar.')
                return None
            return super().add_command(command,override=override)
        if guild is not None:
            return super().add_command(command,guild=guild,override=override)
        return super().add_command(command,guilds=guilds,override=override)

    async def interaction_check(self,interaction:discord.Interaction)->bool:
        if not interaction.guild or not interaction.command:return True
        ok=allowed_for(interaction.guild,interaction.channel,interaction.user,interaction.command.name)
        if not ok:
            try: await interaction.response.send_message('❌ Dieser Command ist hier deaktiviert oder ignoriert.',ephemeral=True)
            except: pass
        return ok

async def dynamic_prefix(bot,message):
    if not message.guild:return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,message)
    return commands.when_mentioned_or(get_guild_settings(message.guild.id).get('prefix',DEFAULT_PREFIX))(bot,message)

intents=discord.Intents.default(); intents.message_content=True; intents.members=True; intents.reactions=True; intents.voice_states=True
bot=commands.Bot(command_prefix=dynamic_prefix,intents=intents,help_command=None,case_insensitive=True,tree_cls=UnifiedTree)

# Reihenfolge = Slash-Priorität. Die wichtigsten/gewünschten Module werden zuerst
# registriert. Falls wir über 100 kommen, funktionieren spätere Commands weiterhin
# mit Prefix, statt dass das komplette Cog nicht geladen wird.
COGS=[
    'cogs.admin','cogs.moderation','cogs.info_plus','cogs.levels','cogs.tickets',
    'cogs.suggestions','cogs.utility','cogs.counting','cogs.dice','cogs.reaction_roles',
    'cogs.fun','cogs.music','cogs.economy','cogs.bump','cogs.backup','cogs.giveaways',
    'cogs.starboard','cogs.custom_commands','cogs.welcome','cogs.automod','cogs.logging_plus',
    'cogs.dyno_manager','cogs.dyno_misc','cogs.dyno_roles_tags'
]

@bot.check
async def global_prefix_check(ctx):
    if not ctx.command:return True
    ok=allowed_for(ctx.guild,ctx.channel,ctx.author,ctx.command.name)
    if not ok: await ctx.send('❌ Dieser Command ist hier deaktiviert oder ignoriert.')
    return ok

def ensure_command_descriptions():
    for command in bot.commands:
        desc=(getattr(command,'description','') or '').strip()
        if not desc or desc=='…':
            desc=f'Führt den Befehl {command.name} aus.'
            command.description=desc
        app_command=getattr(command,'app_command',None)
        if app_command is not None:
            app_desc=(getattr(app_command,'description','') or '').strip()
            if not app_desc or app_desc=='…':app_command.description=desc[:100]

@bot.event
async def on_ready():
    print(f'✅ {BOT_NAME} eingeloggt als {bot.user} ({bot.user.id})'); await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name='deinen Server'))
    if not getattr(bot,'_synced_once',False):
        try:
            ensure_command_descriptions()
            gid=os.environ.get('GUILD_ID','').strip()
            if gid.isdigit():
                g=discord.Object(id=int(gid))
                bot.tree.copy_global_to(guild=g)
                synced=await bot.tree.sync(guild=g)
                bot.tree.clear_commands(guild=None)
                await bot.tree.sync()
                print(f'🔄 {len(synced)} Slash-Commands für Test-Server synchronisiert; globale Duplikate entfernt.')
            else:
                synced=await bot.tree.sync(); print(f'🔄 {len(synced)} globale Slash-Commands synchronisiert.')
            bot._synced_once=True
        except Exception as e:print('Sync-Fehler:',e)

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,(commands.CommandNotFound,commands.CheckFailure)):return
    if isinstance(error,commands.MissingPermissions):return await ctx.send('❌ Dafür fehlen dir Berechtigungen.')
    if isinstance(error,commands.BotMissingPermissions):return await ctx.send('❌ Mir fehlen dafür Discord-Berechtigungen.')
    if isinstance(error,(commands.BadArgument,commands.MissingRequiredArgument)):return await ctx.send(f'❌ Ungültige/fehlende Eingabe: `{ctx.command.qualified_name} {ctx.command.signature}`')
    print('Command-Fehler:',repr(error)); await ctx.send(f'❌ Fehler: {error}')

async def load_cogs():
    loaded=0
    for cog in COGS:
        try:
            await bot.load_extension(cog); loaded+=1; print('✅ Cog:',cog)
        except Exception as e:print('❌ Cog:',cog,e)
    print(f'✅ {loaded}/{len(COGS)} Cogs geladen • {len(bot.commands)} Prefix/Hybrid-Commands • {len(bot.tree.get_commands())} Slash-Commands im Tree')

def run_dashboard():
    app=create_dashboard(bot); app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)),use_reloader=False)

async def main():
    async with bot:
        await load_cogs(); token=os.environ.get('DISCORD_TOKEN')
        if not token:raise RuntimeError('DISCORD_TOKEN fehlt')
        Thread(target=run_dashboard,daemon=True).start(); await bot.start(token)

if __name__=='__main__':asyncio.run(main())
