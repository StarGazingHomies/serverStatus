import discord
from discord.ext import tasks
from mcstatus import JavaServer
from datetime import datetime  # For timezone stuff
import pytz  # For timezone stuff
import socket, sys
from _socket import gaierror

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Server IP
IP = "165.227.201.231"
# Channel ID of the message to edit. For #server-status, this should be 594776724231684097
CHANNEL_ID = 1082044825672626306
# Message ID of the message to edit.
# This should be 778718106935492639 for the current Server Status bot.
# Set it to -1 if using the last bot message in the channel.
MESSAGE_ID = -1
# Offline message - dunno if it's the right boop
OFFLINE_MSG = "Have an emergency boop <:boop:647192998010159134>"
# Make a token.txt file in the same directory and then paste the Discord bot token in.
# It's best not to have token in code. Safety and all that
with open("token.txt", "r") as fin:
    token = fin.readline().replace('\n', '')


@tasks.loop(seconds=60)
async def send_message():
    # Time
    local = pytz.timezone('US/Eastern')
    now = datetime.now()
    localtime = local.localize(now)
    utctime = localtime.astimezone(pytz.utc)
    timeStr = utctime.strftime('%H:%M:%S %D UTC')

    # Get server status & generate msg
    try:
        server = JavaServer.lookup(IP)
        status = server.status()
        print(f"The server has {status.players.online} player(s) online and replied in {status.latency} ms")
        # Embed title
        title = "Status: Online"
        # Players online
        if status.raw['players']['online'] == 0:
            usersConnStr = ""
        else:
            usersConnected = [user['name'] for user in status.raw['players']['sample']]
            usersConnStr = '\n- ' + '\n- '.join(usersConnected)
        # Embed description
        description = f"""**Currently online**: {status.players.online}/{status.players.max} ponies
**Version**: {status.version.name}
**Players**: {usersConnStr}"""
        # The message content
        content = f"**{status.description}**"

    except socket.timeout or gaierror or ConnectionRefusedError:
        print("The server is offline!")
        title = "Status: Offline"
        content = f"**SERVER OFFLINE**"
        description = OFFLINE_MSG

    # Build embed
    embed = discord.Embed(title=title, description=description, colour=0x7289DA)
    embed.set_footer(text=f"{IP} | {timeStr}")

    try:
        # Get msg to edit
        channel = client.get_channel(CHANNEL_ID)
        msg_to_edit = await channel.fetch_message(MESSAGE_ID)
        await msg_to_edit.edit(content=content, embed=embed)
    except discord.errors.NotFound:
        # Message probably deleted
        await get_message()
        await send_message()
    except Exception as e:
        print(f"Editing failed due to {e}.")


async def get_message():
    global MESSAGE_ID
    channel = client.get_channel(CHANNEL_ID)

    bot_message = await discord.utils.get(channel.history(limit=100), author=client.user)

    if bot_message is not None:
        MESSAGE_ID = bot_message.id
        print(f"Found last message from bot: {MESSAGE_ID}")
    else:
        try:
            message = await channel.send("Getting server info...")
            MESSAGE_ID = message.id
        except Exception as e:
            print(f"Sending new message failed due to {e}")
            # No point in doing anything
            client.loop.stop()
            sys.exit()


@client.event
async def on_ready():
    global MESSAGE_ID

    # Automatically get last bot message in the channel
    if MESSAGE_ID == -1:
        await get_message()

    send_message.start()


if __name__ == '__main__':
    client.run(token)
