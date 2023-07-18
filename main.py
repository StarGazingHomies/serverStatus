import discord
from discord.ext import tasks
from mcstatus import JavaServer, dns
from datetime import datetime  # For timezone stuff
import pytz  # For timezone stuff
import socket
import sys
import traceback
from _socket import gaierror

intents = discord.Intents.default()
client = discord.Client(intents=intents)

with open("config.txt", "r") as fin:
    # Server IP
    IP = fin.readline().replace("\n", "")
    # Channel ID of the message to edit. For #server-status, this should be 594776724231684097
    CHANNEL_ID = int(fin.readline())
    ERROR_CHANNEL_ID = int(fin.readline())

# Message ID of the message to edit.
MESSAGE_ID = -1
# Set it to -1 if using the last bot message in the channel.
# Offline message - dunno if it's the right boop
OFFLINE_MSG = "Have an emergency boop <:boop:647192998010159134>"
# Make a token.txt file in the same directory and then paste the Discord bot token in.
# It's best not to have token in code. Safety and all that
with open("token.txt", "r") as fin:
    token = fin.readline().replace('\n', '')


# Note: Bot required permissions integer = 355328. Manage Messages for editing.


@tasks.loop(seconds=60)
async def update():
    # Wrapper to send an error message every time something goes wrong that is not retryable
    try:
        await _update()
    except Exception as e:
        s = traceback.format_exc()
        await sendErrorMessage(f"<@!523717630972919809>\n{s}")
        await stop()


async def _update():
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
            usersConnStr = "Nopony is online! <:phyllisno:633069063408451584>"
        else:
            usersConnStr = ""
            try:
                # Escape underscores
                usersConnected = [user['name'].replace('_', '\\_') for user in status.raw['players']['sample']]
                usersConnStr = '\n- ' + '\n- '.join(usersConnected)
            except KeyError:
                print("No usernames were given even though players are online!")
                print(status.raw['players'])

        # Embed description
        description = f"""**Currently online**: {status.players.online}/{status.players.max} ponies
**Version**: {status.version.name}
**Players**: {usersConnStr}"""
        # The message content
        content = f"**{status.description}**\n"  # Server MOTD as message content
        colour = 0x7289DA  # Some shade of blue

        # Crude "check if it's waterfall and not actually the server because it's down"
        if status.players.max == 1:
            print("The server is offline (behind Waterfall)!")
            title = "Status: Offline (behind Waterfall)"
            content = f"**SERVER OFFLINE**"
            description = OFFLINE_MSG
            colour = 0xe74c3c

    except (socket.timeout, gaierror, ConnectionRefusedError):
        print("The server is offline!")
        title = "Status: Offline"
        content = f"**SERVER OFFLINE**"
        description = OFFLINE_MSG
        colour = 0xe74c3c  # Some shade of red

    # Build embed
    embed = discord.Embed(title=title, description=description, colour=colour)
    embed.set_footer(text=f"{IP} | {timeStr}")

    try:
        # Get msg to edit
        channel = client.get_channel(CHANNEL_ID)
        msg_to_edit = await channel.fetch_message(MESSAGE_ID)
        await msg_to_edit.edit(content=content, embed=embed)
    except discord.errors.NotFound:
        # Message probably deleted
        await get_message()
        await _update()
    except discord.errors.Forbidden:
        await sendErrorMessage("Error: Bot does not have permissions to edit messages.")
    except Exception as e:
        await sendErrorMessage(f"Editing failed due to {e}.")


async def get_message():
    global MESSAGE_ID

    bot_message = None
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Invalid channel!")
        await stop()

    try:
        bot_message = await discord.utils.get(channel.history(limit=100), author=client.user)
    except AttributeError:
        await sendErrorMessage(f"Bot can not view the channel (history)!")

    if bot_message is not None:
        MESSAGE_ID = bot_message.id
        print(f"Found last message from bot: {MESSAGE_ID}")
    else:
        try:
            message = await channel.send("Getting server info...")
            MESSAGE_ID = message.id
        except Exception as e:
            await sendErrorMessage(client, f"Sending new message failed due to {e}")
            # No point in doing anything...
            await stop()


async def sendErrorMessage(errMsg):
    try:
        errorChannel = client.get_channel(ERROR_CHANNEL_ID)
        await errorChannel.send(errMsg)
    except Exception as e:
        print(f"Error sending error message due to {e}!")
    finally:
        print(errMsg)


async def stop():
    await client.close()
    sys.exit()


@client.event
async def on_ready():
    global MESSAGE_ID

    # Automatically get last bot message in the channel
    if MESSAGE_ID == -1:
        await get_message()

    update.start()


if __name__ == '__main__':
    client.run(token)
