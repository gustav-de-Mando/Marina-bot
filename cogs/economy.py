import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from core.storage import execute, one, query

CURRENCY = '💵'
SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']


def now():
    return datetime.now(timezone.utc)


def parse_dt(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def deck():
    cards = [(rank, suit) for rank in RANKS for suit in SUITS]
    random.shuffle(cards)
    return cards


def value(hand):
    total = sum(11 if rank == 'A' else 10 if rank in 'JQK' else int(rank) for rank, _ in hand)
    aces = sum(rank == 'A' for rank, _ in hand)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def fmt(hand):
    return ' '.join(f'`{rank}{suit}`' for rank, suit in hand)


def account(guild_id, user_id):
    execute('''INSERT INTO economy_accounts(guild_id,user_id,wallet,bank)
               VALUES(?,?,500,0) ON CONFLICT(guild_id,user_id) DO NOTHING''',
            (guild_id, user_id))
    return one('SELECT * FROM economy_accounts WHERE guild_id=? AND user_id=?', (guild_id, user_id))


def set_account(guild_id, user_id, *, wallet=None, bank=None, last_daily=None, last_work=None):
    row = account(guild_id, user_id)
    execute('''UPDATE economy_accounts SET wallet=?,bank=?,last_daily=?,last_work=?
               WHERE guild_id=? AND user_id=?''', (
        row['wallet'] if wallet is None else max(0, int(wallet)),
        row['bank'] if bank is None else max(0, int(bank)),
        row['last_daily'] if last_daily is None else last_daily,
        row['last_work'] if last_work is None else last_work,
        guild_id, user_id,
    ))
    return account(guild_id, user_id)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        execute('''CREATE TABLE IF NOT EXISTS economy_accounts(
            guild_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            wallet INTEGER DEFAULT 500,
            bank INTEGER DEFAULT 0,
            last_daily TEXT,
            last_work TEXT,
            PRIMARY KEY(guild_id,user_id)
        )''')

    def acc(self, ctx, member=None):
        member = member or ctx.author
        return member, account(ctx.guild.id, member.id)

    @commands.hybrid_command(name='balance', description='Zeigt Wallet, Bank und Gesamtguthaben.')
    async def balance(self, ctx, member: discord.Member | None = None):
        member, acc = self.acc(ctx, member)
        embed = discord.Embed(title=f'💰 Konto von {member.display_name}', color=discord.Color.green())
        embed.add_field(name='Wallet', value=f"{acc['wallet']:,} {CURRENCY}")
        embed.add_field(name='Bank', value=f"{acc['bank']:,} {CURRENCY}")
        embed.add_field(name='Gesamt', value=f"{acc['wallet'] + acc['bank']:,} {CURRENCY}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='daily', description='Holt deine tägliche Economy-Belohnung ab.')
    async def daily(self, ctx):
        _, acc = self.acc(ctx)
        current = now()
        last = parse_dt(acc['last_daily'])
        if last and current - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (current - last)
            return await ctx.send(f'❌ Nächste Daily in **{int(remaining.total_seconds() // 3600)}h {int(remaining.total_seconds() % 3600 // 60)}m**.')
        amount = random.randint(200, 500)
        acc = set_account(ctx.guild.id, ctx.author.id, wallet=acc['wallet'] + amount, last_daily=current.isoformat())
        await ctx.send(f'📅 +**{amount:,} {CURRENCY}** • Wallet: **{acc["wallet"]:,}**')

    @commands.hybrid_command(name='work', description='Verdient Spielgeld durch Arbeit.')
    async def work(self, ctx):
        _, acc = self.acc(ctx)
        current = now()
        last = parse_dt(acc['last_work'])
        if last and current - last < timedelta(minutes=30):
            remaining = timedelta(minutes=30) - (current - last)
            return await ctx.send(f'❌ Du kannst in **{max(1, int(remaining.total_seconds() // 60))} Min.** wieder arbeiten.')
        amount = random.randint(50, 200)
        set_account(ctx.guild.id, ctx.author.id, wallet=acc['wallet'] + amount, last_work=current.isoformat())
        await ctx.send(f'💼 Arbeit erledigt: +**{amount:,} {CURRENCY}**')

    @commands.hybrid_command(name='deposit', description='Zahlt Spielgeld von der Wallet auf die Bank ein.')
    async def deposit(self, ctx, amount: str):
        _, acc = self.acc(ctx)
        amount_value = acc['wallet'] if amount.lower() == 'all' else int(amount) if amount.isdigit() else 0
        if amount_value <= 0 or amount_value > acc['wallet']:
            return await ctx.send('❌ Ungültiger Betrag.')
        set_account(ctx.guild.id, ctx.author.id, wallet=acc['wallet'] - amount_value, bank=acc['bank'] + amount_value)
        await ctx.send(f'🏦 {amount_value:,} eingezahlt.')

    @commands.hybrid_command(name='withdraw', description='Hebt Spielgeld von der Bank in die Wallet ab.')
    async def withdraw(self, ctx, amount: str):
        _, acc = self.acc(ctx)
        amount_value = acc['bank'] if amount.lower() == 'all' else int(amount) if amount.isdigit() else 0
        if amount_value <= 0 or amount_value > acc['bank']:
            return await ctx.send('❌ Ungültiger Betrag.')
        set_account(ctx.guild.id, ctx.author.id, wallet=acc['wallet'] + amount_value, bank=acc['bank'] - amount_value)
        await ctx.send(f'💸 {amount_value:,} abgehoben.')

    @commands.hybrid_command(name='pay', description='Überweist einem Mitglied Spielgeld.')
    async def pay(self, ctx, member: discord.Member, amount: int):
        if member.bot or member == ctx.author or amount <= 0:
            return await ctx.send('❌ Ungültig.')
        sender = account(ctx.guild.id, ctx.author.id)
        receiver = account(ctx.guild.id, member.id)
        if sender['wallet'] < amount:
            return await ctx.send('❌ Nicht genug Wallet-Guthaben.')
        set_account(ctx.guild.id, ctx.author.id, wallet=sender['wallet'] - amount)
        set_account(ctx.guild.id, member.id, wallet=receiver['wallet'] + amount)
        await ctx.send(f'💸 {amount:,} {CURRENCY} an {member.mention}.')

    @commands.hybrid_command(name='rob', description='Versucht im Economy-Spiel Spielgeld zu stehlen.')
    async def rob(self, ctx, member: discord.Member):
        if member.bot or member == ctx.author:
            return await ctx.send('❌ Ungültiges Ziel.')
        actor = account(ctx.guild.id, ctx.author.id)
        target = account(ctx.guild.id, member.id)
        if target['wallet'] < 50:
            return await ctx.send('❌ Ziel hat zu wenig Spielgeld.')
        if random.random() < .4:
            amount = random.randint(50, min(500, target['wallet']))
            set_account(ctx.guild.id, ctx.author.id, wallet=actor['wallet'] + amount)
            set_account(ctx.guild.id, member.id, wallet=target['wallet'] - amount)
            text = f'🦹 Im Spiel erfolgreich: +{amount:,} {CURRENCY}'
        else:
            amount = random.randint(100, 300)
            set_account(ctx.guild.id, ctx.author.id, wallet=max(0, actor['wallet'] - amount))
            text = f'🚔 Im Spiel gescheitert: -{amount:,} {CURRENCY}'
        await ctx.send(text)

    @commands.hybrid_command(name='richlist', description='Zeigt die reichsten Economy-Konten des Servers.')
    async def richlist(self, ctx):
        rows = query('''SELECT user_id,wallet,bank FROM economy_accounts
                        WHERE guild_id=? ORDER BY (wallet+bank) DESC LIMIT 10''', (ctx.guild.id,))
        lines = []
        for i, row in enumerate(rows, 1):
            member = ctx.guild.get_member(row['user_id'])
            name = member.display_name if member else str(row['user_id'])
            lines.append(f'`{i}.` **{name}** — {row["wallet"] + row["bank"]:,} {CURRENCY}')
        await ctx.send(embed=discord.Embed(title='💰 Richlist', description='\n'.join(lines) or 'Keine Daten.'))

    @commands.hybrid_command(name='blackjack', description='Startet eine Runde Blackjack mit Spielgeld.')
    async def blackjack(self, ctx, einsatz: int):
        if einsatz <= 0:
            return await ctx.send('❌ Einsatz muss positiv sein.')
        acc = account(ctx.guild.id, ctx.author.id)
        key = f'{ctx.guild.id}_{ctx.author.id}'
        if acc['wallet'] < einsatz:
            return await ctx.send('❌ Nicht genug Spielgeld.')
        if key in self.games:
            return await ctx.send('❌ Du hast bereits ein Spiel.')
        cards = deck()
        player = [cards.pop(), cards.pop()]
        dealer = [cards.pop(), cards.pop()]
        self.games[key] = {'deck': cards, 'player': player, 'dealer': dealer, 'stake': einsatz,
                           'guild_id': ctx.guild.id, 'user_id': ctx.author.id}
        if value(player) == 21:
            acc = account(ctx.guild.id, ctx.author.id)
            win = int(einsatz * 1.5)
            set_account(ctx.guild.id, ctx.author.id, wallet=acc['wallet'] + win)
            self.games.pop(key, None)
            return await ctx.send(f'🃏 Blackjack! +{win:,} {CURRENCY}')
        await ctx.send(embed=self.embed(player, dealer, einsatz, True), view=BlackjackView(self, key, ctx.author.id))

    def embed(self, player, dealer, stake, hidden=False, result=None):
        embed = discord.Embed(title='🃏 Blackjack', color=discord.Color.blurple())
        embed.add_field(name=f'Deine Hand ({value(player)})', value=fmt(player), inline=False)
        embed.add_field(name='Dealer (?)' if hidden else f'Dealer ({value(dealer)})',
                        value=f'{fmt([dealer[0]])} `??`' if hidden else fmt(dealer), inline=False)
        embed.add_field(name='Einsatz', value=f'{stake:,} {CURRENCY}')
        if result:
            embed.add_field(name='Ergebnis', value=result, inline=False)
        return embed

    async def finish(self, interaction, key):
        game = self.games.pop(key, None)
        if not game:
            return
        while value(game['dealer']) < 17:
            game['dealer'].append(game['deck'].pop())
        player_value = value(game['player'])
        dealer_value = value(game['dealer'])
        stake = game['stake']
        delta = 0
        if player_value > 21:
            delta = -stake
            result = f'Bust: -{stake:,}'
        elif dealer_value > 21 or player_value > dealer_value:
            delta = stake
            result = f'Gewonnen: +{stake:,}'
        elif player_value == dealer_value:
            result = 'Unentschieden'
        else:
            delta = -stake
            result = f'Verloren: -{stake:,}'
        acc = account(game['guild_id'], game['user_id'])
        set_account(game['guild_id'], game['user_id'], wallet=max(0, acc['wallet'] + delta))
        await interaction.response.edit_message(embed=self.embed(game['player'], game['dealer'], stake, False, result), view=None)


class BlackjackView(discord.ui.View):
    def __init__(self, cog, key, user_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.key = key
        self.user_id = user_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message('❌ Nicht dein Spiel.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Hit 🃏', style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):
        game = self.cog.games.get(self.key)
        if not game:
            return await interaction.response.send_message('Spiel beendet.', ephemeral=True)
        game['player'].append(game['deck'].pop())
        if value(game['player']) >= 21:
            return await self.cog.finish(interaction, self.key)
        await interaction.response.edit_message(embed=self.cog.embed(game['player'], game['dealer'], game['stake'], True), view=self)

    @discord.ui.button(label='Stand 🛑', style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):
        await self.cog.finish(interaction, self.key)

    async def on_timeout(self):
        self.cog.games.pop(self.key, None)


async def setup(bot):
    await bot.add_cog(Economy(bot))
