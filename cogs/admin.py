import discord
from discord import app_commands
from discord.ext import commands
from core.storage import get_guild_settings, update_guild_settings


class Admin(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="prefix", description="Setzt den Text-Command-Prefix dieses Servers.")
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx: commands.Context, prefix: str):
        update_guild_settings(ctx.guild.id, prefix=prefix)
        await ctx.send(f"✅ Prefix ist jetzt `{prefix}`. Slash-Commands bleiben unverändert.")

    @commands.hybrid_command(name="module", description="Aktiviert oder deaktiviert ein Bot-Modul.")
    @commands.has_permissions(administrator=True)
    async def module(self, ctx: commands.Context, module: str, enabled: bool):
        allowed = {"automod","levels","welcome","goodbye","logs","tickets","suggestions","starboard","economy","music"}
        key = module.lower()
        if key not in allowed:
            return await ctx.send(f"❌ Module: {', '.join(sorted(allowed))}")
        update_guild_settings(ctx.guild.id, **{f"{key}_enabled": enabled})
        await ctx.send(f"✅ `{key}` ist jetzt **{'an' if enabled else 'aus'}**.")

    @commands.hybrid_command(name="setchannel", description="Legt einen System- oder Log-Channel fest.")
    @app_commands.choices(kind=[
        app_commands.Choice(name='Mod-Log', value='modlog'),
        app_commands.Choice(name='Nachrichten-Log (gelöscht/bearbeitet)', value='messagelog'),
        app_commands.Choice(name='Voice-Log', value='vclog'),
        app_commands.Choice(name='Willkommen', value='welcome'),
        app_commands.Choice(name='Verabschiedung', value='goodbye'),
        app_commands.Choice(name='Level-Up', value='levelup'),
        app_commands.Choice(name='Vorschläge', value='suggestions'),
        app_commands.Choice(name='Tickets', value='tickets'),
        app_commands.Choice(name='Starboard', value='starboard'),
        app_commands.Choice(name='Bump', value='bump'),
    ])
    @commands.has_permissions(administrator=True)
    async def setchannel(self, ctx: commands.Context, kind: str, channel: discord.TextChannel):
        allowed = {"modlog","messagelog","vclog","welcome","goodbye","levelup","suggestions","tickets","starboard","bump"}
        kind = kind.lower()
        if kind not in allowed:
            return await ctx.send(f"❌ Typen: {', '.join(sorted(allowed))}")
        update_guild_settings(ctx.guild.id, **{f"{kind}_channel": channel.id})
        await ctx.send(f"✅ `{kind}` → {channel.mention}")

    @commands.hybrid_command(name="autorole", description="Setzt oder entfernt die automatische Beitrittsrolle.")
    @commands.has_permissions(manage_roles=True)
    async def autorole(self, ctx: commands.Context, role: discord.Role | None = None):
        update_guild_settings(ctx.guild.id, autorole_id=role.id if role else None)
        await ctx.send(f"✅ Autorole: {role.mention if role else 'deaktiviert'}")

async def setup(bot): await bot.add_cog(Admin(bot))
