import sys
import datetime
import json
import time
import pprint
import discord
from discord import message
from discord.ext import commands, tasks

PREFIX_TEXT = 'vn=='
client = commands.Bot(command_prefix=PREFIX_TEXT)
voice_member_count = {}

# [
#   guild_id: {
#     "channel": Discord Channel object
#     "send_time": Time to send the message (seconds since the epoch)
#     "message": Message string
#     "tag": "vc_start" / "vc_end"
#   }, ...
# ]
message_queue = {}

# [
#   guild_id: {
#     "notif_channel": channel_id
#     "message_delay": True/False
#   }, ...
# ]
guild_stat = {}

isTest = False
test_guild_id = None
test_channel_id = None


def update_guild_stat(gid, dic):
    global guild_stat

    json_data = {}
    try:
        with open("guild_status.json") as fin:
            json_data = json.load(fin)
    except FileNotFoundError as err:
        print("{} is not exist.".format(err.filename))
    
    if json_data.get(str(gid)) is None:
        json_data[str(gid)] = {}
    for k, v in dic.items():
        json_data[str(gid)][k] = v

    with open("guild_status.json", mode='w') as fout:
        json.dump(json_data, fout)
    
    guild_stat = json_data


@client.command(help="Set notification channel to where this command called")
async def set_channel(ctx):
    update_guild_stat(ctx.guild.id, {"notif_channel": ctx.channel.id})
    await ctx.send("updated notification channel")


@client.command(help="Toggle message delay")
async def delay(ctx, arg=None):
    if arg is None:
        msg = ""
        msg += "Usage: {}delay (on/off).\n".format(PREFIX_TEXT)
        await ctx.send(msg)
        return

    flag = None
    if arg == 'on' : flag = True
    if arg == 'off': flag = False
    if flag is None:
        await ctx.send("Argument is invalid. Please specify 'on' or 'off'.")
    else:
        update_guild_stat(ctx.guild.id, {"message_delay": flag})
        await ctx.send("Message delay is " + ("enabled" if flag else "disabled"))


@client.event
async def on_ready():
    global guild_stat

    print("logged in as {0.user}".format(client))
    await client.change_presence(activity=discord.Game(name=f"{PREFIX_TEXT}help"))
    try:
        with open("guild_status.json") as fin:
            guild_stat = json.load(fin)
    except FileNotFoundError:
        pass

    check_message_queue.start()


@tasks.loop(seconds=1)
async def check_message_queue():
    global message_queue

    tmp = {}
    for gid, value in message_queue.items():
        if value["send_time"] < time.time():
            st = time.localtime(value["send_time"])
            print("send a queue message:")
            print(f"\ttime    : {st.tm_year}/{st.tm_mon}/{st.tm_mday} ", end='')
            print(f"{st.tm_hour}:{st.tm_min}.{st.tm_sec}")
            print("\tguild   : {}".format(value["channel"].guild.name))
            print("\tchannel : {}".format(value["channel"].name))
            print("\tmessage : {}".format(value["message"]))

            await value["channel"].send(value["message"])
        else:
            tmp[gid] = value
    
    message_queue = tmp


@client.event
async def on_voice_state_update(member, before, after):
    global voice_member_count, message_queue
    global isTest, test_guild_id, test_channel_id

    if isTest and member.guild.id != test_guild_id:
        return

    guild = member.guild
    stat = guild_stat.get(str(guild.id))

    if stat is None:
        channel_to_send = guild.system_channel
        stat = {}
    else:
        channel_id = stat.get("notif_channel")
        channel_to_send = client.get_channel(channel_id)
    
    if isTest:
        channel_to_send = client.get_channel(test_channel_id)

    # counter init
    if voice_member_count.get(guild.id) is None:
        voice_member_count[guild.id] = 0

    # count up VC members
    num_vc_member = 0
    for vc in guild.voice_channels:
        members = client.get_channel(vc.id).members
        num_vc_member += len(members)
        for m in members:
            print("\tdetected member: {}".format(str(m)))

    # log
    print(datetime.datetime.now())
    print("\tVC status update detected in guild '{}'".format(guild.name))
    print("\tprev count is {}, now is {}".format(voice_member_count[guild.id], num_vc_member))

    msg = None
    delay = 0
    tag = ""
    if voice_member_count[guild.id] == 0 and num_vc_member > 0:
        delay = 10
        msg = "誰かが通話を始めたみたいです"
        tag = "vc_start"
        
    elif voice_member_count[guild.id] > 0 and num_vc_member == 0:
        if message_queue.get(guild.id) is None:
            msg = "そして誰もいなくなった..."
            tag = "vc_end"
        elif stat.get("message_delay"):
            print("\tVC is end, deleted message queue")
            message_queue.pop(guild.id)

    if msg is not None:
        if isTest: msg += " [test]"
        if stat.get("message_delay"):
            queue = {
                "channel"   : channel_to_send,
                "send_time" : time.time() + delay,
                "message"   : msg,
                "tag"       : tag
            }
            message_queue[guild.id] = queue
            print("added message queue: tag is {}, delay is +{}".format(tag, delay))
        else:
            await channel_to_send.send(msg)
            print("send message: tag is {}".format(tag))

    voice_member_count[guild.id] = num_vc_member


if __name__ == "__main__":
    print("Initializing...")

    with open("access_token.txt") as fin:
        token = fin.read()

    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        print("Detected testing flag")
        isTest = True
        with open("test_channel.json") as fin:
            json_data = json.load(fin)
            test_guild_id, test_channel_id = list(json_data.items())[0]
            test_guild_id = int(test_guild_id)
    
    print("Done")
    client.run(token)
