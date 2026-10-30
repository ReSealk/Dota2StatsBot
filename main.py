import sqlite3 as sq
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button
import requests
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv(dotenv_path='configs.env')
botToken = os.getenv('BOT_TOKEN')
e621api = os.getenv('E621_API')
e621login = os.getenv('E621_LOGIN')

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

con = sq.connect('database.db')
cur = con.cursor()
print('--------------')
print('connected to database')

client = commands.Bot(command_prefix='d!', intents=intents, help_command=None)

class MyView(View):
    def __init__(self, match_id: int):
        super().__init__()
        self.match_id = match_id
    
    @button(label='Пики/Баны', style=discord.ButtonStyle.blurple)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        reqs = requests.get(f'https://api.opendota.com/api/matches/{self.match_id}')
        heroes = requests.get('https://api.opendota.com/api/heroes').json()
        embed=discord.Embed(title="Пики/баны", color=0x0000ff)
        for i in range(18):
            heroid = reqs.json()['picks_bans'][i]['hero_id']
            hero = next((item for item in heroes if item.get("id") == heroid), None)
            embed.add_field(name=f'{'пик' if reqs.json()['picks_bans'][i]['is_pick'] == True else 'бан'} {'света' if reqs.json()['picks_bans'][i]['team'] == 0 else "тьмы" }', value=hero['localized_name'], inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600 
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    return "%d:%02d:%02d" % (hour, minutes, seconds)

@client.event
async def on_ready():
    print(f'connected to discord as {client.user}')

@client.command(aliases=['getmatch','game','match','stats','matchstats','gamestats'])
async def __getmatch(ctx, match_id: int = None):
    if match_id == None:
        await ctx.send('правильный формат: d!match <айди матча>')
        return
    req = requests.get(f'https://api.opendota.com/api/matches/{match_id}')
    rq = req.json()
    vict = 'тьмы'
    if rq['radiant_win'] == 1: vict = 'света'
    embed=discord.Embed(title=f"игра {str(match_id)}", description=f"победа сил {vict}", color=0x00ff00)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    embed.add_field(name="Длительность", value=convert(rq['duration']), inline=True)
    embed.add_field(name="Счёт", value=f"{rq['radiant_score']}:{rq['dire_score']}", inline=True)
    await ctx.send(embed=embed, view=MyView(match_id))

@client.command(aliases=['furry','getfurry','e621'])
async def __furry(ctx):
    header = {
        'User-Agent': 'discordBot/1.0 (by Re_Sea1k)'
    }
    req = requests.get(f'http://e621.net//posts/random.json?api_key={e621api}&login={e621login}',headers=header)
    await ctx.send(req.json()['post']['file']['url'])

client.run(token=botToken)