import time,asyncio,discord
from discord.ext import commands
from core.storage import get_guild_settings,update_guild_settings
class Bump(commands.Cog):
    def __init__(self,bot):self.bot=bot;self.tasks={}
    @commands.hybrid_command(name='bump_setup')
    @commands.has_permissions(manage_guild=True)
    async def setup_bump(self,ctx,channel:discord.TextChannel|None=None,role:discord.Role|None=None):
        ch=channel or ctx.channel;update_guild_settings(ctx.guild.id,bump_channel=ch.id,bump_role=role.id if role else None);await ctx.send(f'✅ Bump-Reminder → {ch.mention}')
    @commands.hybrid_command(name='bump_now')
    @commands.has_permissions(manage_guild=True)
    async def bump_now(self,ctx):await self.schedule(ctx.guild)
    async def schedule(self,guild):
        s=get_guild_settings(guild.id);ch=guild.get_channel(int(s.get('bump_channel') or 0))
        if not ch:return
        old=self.tasks.get(guild.id)
        if old and not old.done():old.cancel()
        async def wait():
            await asyncio.sleep(7200);role=guild.get_role(int(s.get('bump_role') or 0));await ch.send(f'🔔 Bump ist wieder möglich! {role.mention if role else ""}')
        self.tasks[guild.id]=asyncio.create_task(wait())
        await ch.send('✅ Bump erkannt/gestartet. Erinnerung in 2 Stunden.')
    @commands.Cog.listener()
    async def on_message(self,m):
        if not m.guild or m.author.id!=302050872383242240:return
        if 'bump done' in m.content.lower() or any('bump done' in (e.description or '').lower() for e in m.embeds):await self.schedule(m.guild)
async def setup(bot):await bot.add_cog(Bump(bot))
