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
    #getting all the settings from redis
    welcome = r.get(f"welcome:{interaction.guild.id}")
    welcome_msg = r.get(f"welcome_msg:{interaction.guild.id}")

    #changing the text so users can understand it
    if welcome is None:
        welcome = '`없음`'
    else:
        welcome = f'<#{welcome}>'
    if welcome_msg is None:
        welcome_msg = '`없음`'
    else:
        welcome_msg = (welcome_msg.replace('{0}', '<유저>')).replace('{1}', '<인원수>')

    embed = nextcord.Embed(title=f'**{interaction.guild.name}**서버 설정', description='', color=0x2F3136)
    embed.add_field(name='환영 채널', value=welcome, inline=True)
    embed.add_field(name='환영 메시지', value=welcome_msg, inline=True)
    view = dropdownview()
    await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

class dropdown(nextcord.ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="환영 채널 변경", value=0, emoji="👋"),
            nextcord.SelectOption(label="환영 메세지 변경", value=1, emoji="📝"),
        ]
        super().__init__(placeholder="변경할 설정을 선택하세요.", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: Interaction):
        if self.values[0] == "0":
            embed = nextcord.Embed(title="환영 채널 변경", description="15초 안에 변경할 환영 채널을 `#`를 이용하여 언급해 주세요.", color=0x2F3136)
            embed.add_field(name="예시", value=interaction.channel.mention, inline=True)
            original = await interaction.response.send_message(embed=embed, ephemeral=True)
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            try:
                msg = await client.wait_for('message', check=check, timeout=15)
                if msg.content.startswith("<#") and msg.content.endswith(">"):
                    channel = msg.content[2:-1]
                    if channel.isdigit():
                        channel = client.get_channel(int(channel))
                        if channel is not None:
                            await original.edit(embed=nextcord.Embed(title="환영 채널 변경", description=f"환영 채널이 `{channel.name}`으로 변경되었습니다.", color=nextcord.Color.green()))
                            r.set(f"welcome:{interaction.guild.id}", channel.id)
                        else:
                            await original.edit(embed=nextcord.Embed(title="환영 채널 변경", description="채널을 찾을 수 없습니다.", color=0x2F3136))
                    else:
                        await original.edit(embed=nextcord.Embed(title="환영 채널 변경", description="채널을 찾을 수 없습니다.", color=0x2F3136))
                else:
                    await original.edit(embed=nextcord.Embed(title="오류", description="채널을 `#`를 이용하여 언급해 주세요.", color=0x2F3136))
            except:
                await original.edit("" ,embed=nextcord.Embed(title="시간 초과", description="15초 안에 채널을 언급하지 않으셨습니다.\n다시 시도해 주세요.", color=nextcord.Color.red()))
        elif self.values[0] == "1":
            embed = nextcord.Embed(title="환영 메세지 변경", description="30초 안에 변경할 환영 메세지를 입력해 주세요.\n<유저>는 새로운 유저 언급으로 대체되고, <인원수>는 서버 총 인원수로 대채됩니다.\n또한, 디스코드 텍스토 포매팅도 사용이 가능합니다.", color=0x2F3136)
            embed.add_field(name="예시", value="<유저>님, **<인원수>**번째 유저로서 환영합니다!", inline=True)
            original = await interaction.response.send_message(embed=embed, ephemeral=True)
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            try:
                msg = await client.wait_for('message', check=check, timeout=30)
                embed = nextcord.Embed(title="환영 메세지 변경", description=f"환영 메세지가 성공적으로 변경되었습니다.", color=nextcord.Color.green())
                embed.add_field(name="변경된 환영 메세지", value=msg.content, inline=False)
                msg = (msg.content.replace("<유저>", "{0}")).replace("<인원수>", "{1}")
                await original.edit(embed=embed)
                r.set(f"welcome_msg:{interaction.guild.id}", msg)
            except:
                await original.edit(embed=nextcord.Embed(title="시간 초과", description="15초 안에 메세지를 입력하지 않으셨습니다.\n다시 시도해 주세요.", color=nextcord.Color.red()))

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
            welcome_msg = r.get(f"welcome_msg:{member.guild.id}")
            if welcome_msg is None:
                welcome_msg = "{0}님이 서버에 참여하셨습니다! 이제 이 서버에는 {1}명의 사람이 있습니다!"
            embed = nextcord.Embed(title=f"환영합니다!", description=welcome_msg.format(member.mention, member.guild.member_count), color=0x2F3136)
            embed.set_footer(text=f"{member.guild.name}에 오신 것을 환영합니다!")
            await welcome_ch.send(embed=embed)

client.run(token)