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
notif_channel = {}
message_queue = {}

isTest = False
test_guild_id = None
test_channel_id = None


@client.command(help="set notification channel to where this command called")
async def set_channel(ctx):
    notif_channel[ctx.guild.id] = ctx.channel

    ids = {gid: c.id for gid,c in notif_channel.items()}
    with open("notification_channel.json", mode='w') as fout:
        json.dump(ids, fout)

    await ctx.send("updated notification channel")


@client.event
async def on_ready():
    global notif_channel
    print("logged in as {0.user}".format(client))
    await client.change_presence(activity=discord.Game(name=f"{PREFIX_TEXT}help"))
    ids = {}
    try:
        with open("notification_channel.json") as fin:
            ids = json.load(fin)
    except FileNotFoundError:
        pass
    notif_channel = {int(gid): client.get_channel(cid) for gid,cid in ids.items()}
    check_message_queue.start()


@tasks.loop(seconds=1)
async def check_message_queue():
    global message_queue

    tmp = {}
    for gid, value in message_queue.items():
        if value["send_time"] < time.time():
            st = time.localtime(value["send_time"])
            print("send a queue:")
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
    guild_id = guild.id
    print(datetime.datetime.now())
    print("\tVC status update detected in guild '{}'".format(guild.name))

    if voice_member_count.get(guild_id) is None:
        voice_member_count[guild_id] = 0

    num_vc_member = 0
    for vc in guild.voice_channels:
        members = client.get_channel(vc.id).members
        num_vc_member += len(members)
        for m in members:
            print("\tdetected member: {}".format(str(m)))

    print("\tprev count is {}, now is {}".format(voice_member_count[guild_id], num_vc_member))

    channel_to_send = notif_channel.get(guild_id, guild.system_channel)
    if voice_member_count[guild_id] == 0 and num_vc_member > 0:
        print("\tadd VC started message queue (+10s)")
        queue = {
            "channel"   : channel_to_send,
            "send_time" : time.time() + 10,
            "message"   : "誰かが通話を始めたみたいです" + " [test]" if isTest else ""
        }
        message_queue[guild_id] = queue
        
    elif voice_member_count[guild_id] > 0 and num_vc_member == 0:
        if message_queue.get(guild_id) is None:
            print("\tadd VC eed message queue")
            queue = {
                "channel"   : channel_to_send,
                "send_time" : time.time(),
                "message"   : "そして誰もいなくなった..." + " [test]" if isTest else ""
            }
            message_queue[guild_id] = queue
        else:
            print("\tVC is end, deleted message queue")
            message_queue.pop(guild_id)

    voice_member_count[guild_id] = num_vc_member


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
