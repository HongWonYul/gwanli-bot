# imports
import configparser
import platform
import time

import nextcord
import redis
from nextcord import Interaction
from nextcord.ext import commands

# load config & language
config = configparser.ConfigParser()
config.read('config.ini')
lang = configparser.ConfigParser()
lang.read('language.ini')

token = config['CREDENTIALS']['token']
owner_id = str(config['CREDENTIALS']['owner_id'])
prefix = config['SETTINGS']['prefix']
status = config['SETTINGS']['status']
status_message = config['SETTINGS']['status_message']
status_type = config['SETTINGS']['status_type']
host = config['REDIS']['host']
port = config['REDIS']['port']
password = config['REDIS']['password']
db = config['REDIS']['db']

# check config
error_count = 0

if len(prefix) > 1:
    print('Error: Prefix must be only one character.')
    error_count += 1

if status not in ['online', 'idle', 'dnd', 'invisible']:
    print('Error: Status must be one of online, idle, dnd, or invisible.')
    error_count += 1

if status_type not in ['playing', 'streaming', 'listening', 'watching']:
    print('Error: Status type must be one of playing, streaming, listening, or watching.')
    error_count += 1

if len(status_message) > 128:
    print('Error: Status message must be less than 128 characters.')
    error_count += 1

if error_count > 0:
    print('Please change the config file (config.ini) and try again.')
    print('Exiting in 5 seconds...')
    time.sleep(5)
    exit()

# check redis connection
try:
    print(f'Connecting to Redis... ({host}:{port} Database: {db})')
    r = redis.Redis(host=host, port=port, password=password, decode_responses=True, db=db)
    r.ping()
    print(f'Connected to redis.')
except:
    print('Error: Could not connect to Redis server.')
    print('Please change the config file (config.ini) and try again.')
    print('Exiting in 5 seconds...')
    time.sleep(5)
    exit()

# discord setup
intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True

client = commands.Bot(command_prefix=prefix, intents=intents)


# Bot startup
@client.event
async def on_ready():
    # set status
    if status_type == 'playing':
        await client.change_presence(activity=nextcord.Game(name=status_message), status=status)
    elif status_type == 'streaming':
        await client.change_presence(activity=nextcord.Streaming(name=status_message, url='https://twich.tv'),
                                     status=status)
    elif status_type == 'listening':
        await client.change_presence(
            activity=nextcord.Activity(type=nextcord.ActivityType.listening, name=status_message), status=status)
    elif status_type == 'watching':
        await client.change_presence(
            activity=nextcord.Activity(type=nextcord.ActivityType.watching, name=status_message), status=status)
    # print startup message
    owner_name = await client.fetch_user(owner_id)
    print('======================================')
    print(f'Logged in as {client.user.name}#{client.user.discriminator} ({client.user.id})')
    print(f'Owner: {owner_name} ({owner_id})')
    print(f'Currenly running nextcord {nextcord.__version__} on python {platform.python_version()}')
    print('======================================')

#settings module
@client.slash_command(name='settings', description='봇의 설정을 변경합니다.', dm_permission=False, default_member_permissions=8)
async def settings(interaction: Interaction):
    welcome = r.get(f"welcome:{interaction.guild.id}")
    if welcome is None:
        welcome = '`없음`'
    else:
        welcome = f'<#{welcome}>'
    embed = nextcord.Embed(title=f'**{interaction.guild.name}**서버 설정', description='', color=0x2F3136)
    embed.add_field(name='환영 채널', value=welcome, inline=False)
    view = dropdownview()
    await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

class dropdown(nextcord.ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="환영 채널 변경", value=0, emoji="👋"),
        ]
        super().__init__(placeholder="변경할 설정을 선택하세요.", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: Interaction):
        if self.values[0] == "0":
            original = await interaction.response.send_message(embed=nextcord.Embed(title="환영 채널 변경", description="15초 안에 변경할 환영 채널을 `#`를 이용하여 언급해 주세요.", color=0x2F3136), ephemeral=True)
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            try:
                msg = await client.wait_for('message', check=check, timeout=15)
                if msg.content.startswith("<#") and msg.content.endswith(">"):
                    channel = msg.content[2:-1]
                    if channel.isdigit():
                        channel = client.get_channel(int(channel))
                        if channel is not None:
                            await original.edit(embed=nextcord.Embed(title="환영 채널 변경", description=f"환영 채널이 `{channel.name}`으로 변경되었습니다.", color=0x2F3136))
                            r.set(f"welcome:{interaction.guild.id}", channel.id)
                        else:
                            await original.edit(embed=nextcord.Embed(title="환영 채널 변경", description="채널을 찾을 수 없습니다.", color=0x2F3136))
                    else:
                        await original.edit(embed=nextcord.Embed(title="환영 채널 변경", description="채널을 찾을 수 없습니다.", color=0x2F3136))
                else:
                    await original.edit(embed=nextcord.Embed(title="오류", description="채널을 `#`를 이용하여 언급해 주세요.", color=0x2F3136))
            except:
                await original.edit("" ,embed=nextcord.Embed(title="시간 초과", description="15초 안에 채널을 언급하지 않으셨습니다.\n다시 시도해 주세요.", color=nextcord.Color.red()))

class dropdownview(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(dropdown())


#welcome module
@client.event
async def on_member_join(member):
    welcome_ch = r.get(f"welcome:{member.guild.id}")
    if welcome_ch is not None:
        welcome_ch = client.get_channel(int(welcome_ch))
        if welcome_ch is not None:
            embed = nextcord.Embed(title=f"환영합니다!", description=f"{member.name}님이 서버에 참여하셨습니다! 이제 이 서버에는 {member.guild.member_count}명의 사람이 있습니다!", color=0x2F3136)
            embed.set_footer(text=f"{member.guild.name}에 오신 것을 환영합니다!")
            await welcome_ch.send(embed=embed)

client.run(token)