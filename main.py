import sys
import datetime
import json
import discord
from discord.ext import commands

PREFIX_TEXT = 'vn=='
client = commands.Bot(command_prefix=PREFIX_TEXT)
voice_member_count = {}
notif_channel = {}


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


@client.event
async def on_voice_state_update(member, before, after):
    global voice_member_count

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
        print("\tsend VC started message")
        await channel_to_send.send("誰かが通話を始めたみたいです")
    elif voice_member_count[guild_id] > 0 and num_vc_member == 0:
        print("\tsend VC end message")
        await channel_to_send.send("そして誰もいなくなった...")

    voice_member_count[guild_id] = num_vc_member


if __name__ == "__main__":
    print("initializing...")

    with open("access_token.txt") as fin:
        token = fin.read()
    print("Done")
    client.run(token)
