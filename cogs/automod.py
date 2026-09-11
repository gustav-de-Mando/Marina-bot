import re,time
from collections import defaultdict,deque
from datetime import timedelta
import discord
from discord.ext import commands
from core.storage import get_guild_settings
INVITE=re.compile(r'(?:discord\.gg|discord(?:app)?\.com/invite)/[A-Za-z0-9-]+',re.I)
LINK=re.compile(r'https?://\S+|www\.\S+',re.I)
class AutoMod(commands.Cog):
    def __init__(self,bot):self.bot=bot;self.history=defaultdict(lambda:deque(maxlen=10));self.duplicates=defaultdict(lambda:deque(maxlen=4))
    async def punish(self,m,reason):
        try:await m.delete()
        except:pass
        s=get_guild_settings(m.guild.id);minutes=int(s.get('automod_timeout_minutes',5))
        if minutes>0:
            try:await m.author.timeout(discord.utils.utcnow()+timedelta(minutes=min(minutes,40320)),reason=f'AutoMod: {reason}')
            except:pass
        try:await m.channel.send(f'⚠️ {m.author.mention}: {reason}',delete_after=6)
        except:pass
    @commands.Cog.listener()
    async def on_message(self,m):
        if not m.guild or m.author.bot:return
        s=get_guild_settings(m.guild.id)
        if not s.get('automod_enabled',False) or m.author.guild_permissions.manage_messages:return
        content=m.content.lower();words=[w.strip().lower() for w in s.get('blocked_words',[]) if w.strip()]
        if words and any(w in content for w in words):return await self.punish(m,'gesperrtes Wort')
        if s.get('block_invites',False) and INVITE.search(m.content):return await self.punish(m,'Discord-Einladung nicht erlaubt')
        if s.get('anti_links',False) and LINK.search(m.content):return await self.punish(m,'Links sind nicht erlaubt')
        if s.get('anti_mass_mentions',False) and len(set(x.id for x in m.mentions))>=int(s.get('mention_limit',5)):return await self.punish(m,'zu viele Erwähnungen')
        if s.get('anti_caps',False):
            letters=[c for c in m.content if c.isalpha()]
            if len(letters)>=12 and sum(c.isupper() for c in letters)/len(letters)>.75:return await self.punish(m,'zu viele Großbuchstaben')
        key=(m.guild.id,m.author.id);now=time.monotonic();self.history[key].append(now);self.duplicates[key].append(content.strip())
        if s.get('anti_spam',False) and len(self.history[key])>=6 and now-self.history[key][-6]<8:return await self.punish(m,'Spam erkannt')
        if s.get('anti_spam',False) and len(self.duplicates[key])>=4 and len(set(self.duplicates[key]))==1 and content.strip():return await self.punish(m,'wiederholter Spam erkannt')
async def setup(bot):await bot.add_cog(AutoMod(bot))
