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

# Slash-Commands werden nach Funktionen gruppiert. So zählen z. B. /music,
# /economy und /backup jeweils nur als EIN Top-Level-Command bei Discord.
GROUP_DESCRIPTIONS={
    'config':'Server- und Bot-Einstellungen.',
    'mod':'Moderationsbefehle und Mod-Fälle.',
    'channel':'Channel- und Rollenverwaltung.',
    'levels':'Level- und XP-Verwaltung.',
    'tickets':'Ticket-System verwalten.',
    'utils':'Nützliche Server- und Nutzerbefehle.',
    'counting':'Counting-System verwalten.',
    'games':'Kleine Spiele und Zufallsbefehle.',
    'reactions':'Reaction-Roles verwalten.',
    'fun':'Spaß- und Social-Befehle.',
    'music':'Musiksteuerung.',
    'economy':'Economy-System.',
    'bump':'Bump-Erinnerungen verwalten.',
    'backup':'Server-Backups verwalten.',
    'giveaway':'Giveaways verwalten.',
    'starboard':'Starboard verwalten.',
    'custom':'Custom Commands verwalten.',
    'welcome':'Welcome- und Goodbye-System.',
    'server':'Weitere Serververwaltung.',
    'tools':'Weitere nützliche Tools.',
    'roles':'Rollen, Self-Ranks und Tags.'
}

ROOT_SLASH_COMMANDS={'help','rank','leaderboard','suggest','ping'}
MOD_CHANNEL_COMMANDS={'clear','slowmode','lock','unlock','lockdown','members','role','temprole','rolepersist'}
LEVEL_ADMIN_COMMANDS={'setxp','addxp','levelrole','levelroles','levelroles_create'}

MODULE_GROUPS={
    'cogs.admin':'config',
    'cogs.tickets':'tickets',
    'cogs.utility':'utils',
    'cogs.counting':'counting',
    'cogs.dice':'games',
    'cogs.reaction_roles':'reactions',
    'cogs.fun':'fun',
    'cogs.music':'music',
    'cogs.economy':'economy',
    'cogs.bump':'bump',
    'cogs.backup':'backup',
    'cogs.giveaways':'giveaway',
    'cogs.starboard':'starboard',
    'cogs.custom_commands':'custom',
    'cogs.welcome':'welcome',
    'cogs.dyno_manager':'server',
    'cogs.dyno_misc':'tools',
    'cogs.dyno_roles_tags':'roles'
}

def slash_group_for(command):
    name=getattr(command,'name','')
    if name in ROOT_SLASH_COMMANDS:return None
    module=getattr(getattr(command,'callback',None),'__module__','')
    if module=='cogs.moderation':return 'channel' if name in MOD_CHANNEL_COMMANDS else 'mod'
    if module=='cogs.levels':return 'levels' if name in LEVEL_ADMIN_COMMANDS else None
    if module=='cogs.info_plus':return None
    return MODULE_GROUPS.get(module)

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
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._feature_groups={}

    def _get_feature_group(self,name):
        group=self._feature_groups.get(name)
        if group is None:
            group=app_commands.Group(name=name,description=GROUP_DESCRIPTIONS[name])
            self._feature_groups[name]=group
            super().add_command(group)
        return group

    def add_command(self,command,*,guild=None,guilds=None,override=False):
        # Normale Cog-Hybrid-Commands kommen ohne guild/guilds hier an. Diese
        # werden automatisch in Feature-Gruppen einsortiert. Prefix-Commands
        # behalten dabei weiterhin ihren bisherigen Namen, z. B. -play.
        if guild is None and guilds is None and not isinstance(command,app_commands.Group):
            group_name=slash_group_for(command)
            if group_name:
                group=self._get_feature_group(group_name)
                try:
                    group.add_command(command,override=override)
                except TypeError:
                    group.add_command(command)
                return None
            return super().add_command(command,override=override)
        if guild is not None:
            return super().add_command(command,guild=guild,override=override)
        if guilds is not None:
            return super().add_command(command,guilds=guilds,override=override)
        return super().add_command(command,override=override)

    async def interaction_check(self,interaction:discord.Interaction)->bool:
        if not interaction.guild or not interaction.command:return True
        command_name=getattr(interaction.command,'name','')
        data=interaction.data or {}
        options=data.get('options') or []
        if options and isinstance(options[0],dict) and options[0].get('name'):
            command_name=options[0]['name']
        ok=allowed_for(interaction.guild,interaction.channel,interaction.user,command_name)
        if not ok:
            try: await interaction.response.send_message('❌ Dieser Command ist hier deaktiviert oder ignoriert.',ephemeral=True)
            except: pass
        return ok

async def dynamic_prefix(bot,message):
    if not message.guild:return commands.when_mentioned_or(DEFAULT_PREFIX)(bot,message)
    return commands.when_mentioned_or(get_guild_settings(message.guild.id).get('prefix',DEFAULT_PREFIX))(bot,message)

intents=discord.Intents.default(); intents.message_content=True; intents.members=True; intents.reactions=True; intents.voice_states=True
bot=commands.Bot(command_prefix=dynamic_prefix,intents=intents,help_command=None,case_insensitive=True,tree_cls=UnifiedTree)

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
            # Globale Slash-Commands sind auf Desktop und Mobile verfügbar und
            # funktionieren auch auf weiteren Servern. Alte Guild-Duplikate des
            # Testservers werden vorher entfernt.
            gid=os.environ.get('GUILD_ID','').strip()
            if gid.isdigit():
                guild=discord.Object(id=int(gid))
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
            synced=await bot.tree.sync()
            print(f'🔄 {len(synced)} gruppierte globale Slash-Commands synchronisiert.')
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
    print(f'✅ {loaded}/{len(COGS)} Cogs geladen • {len(bot.commands)} Prefix/Hybrid-Commands • {len(bot.tree.get_commands())} Top-Level Slash-Commands')

def run_dashboard():
    app=create_dashboard(bot); app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)),use_reloader=False)

async def main():
    async with bot:
        await load_cogs(); token=os.environ.get('DISCORD_TOKEN')
        if not token:raise RuntimeError('DISCORD_TOKEN fehlt')
        Thread(target=run_dashboard,daemon=True).start(); await bot.start(token)

if __name__=='__main__':asyncio.run(main())
