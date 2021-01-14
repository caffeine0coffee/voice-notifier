import sys
import discord

client = discord.Client()

voice_member_count = dict()


@client.event
async def on_ready():
    print("logged in as {0.user}".format(client))


@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    # await msg.channel.send("Hello")


@client.event
async def on_voice_state_update(member, before, after):
    global voice_member_count
    guild = before.channel.guild
    guild_id = guild.id
    if not before.channel and after.channel:
        voice_member_count[guild_id] += 1
        if voice_member_count[guild_id] == 1:
            await guild.system_channel.send("誰かが通話を始めたみたいです")
    elif before.channel and not after.channel:
        voice_member_count[guild_id] -= 1
        if voice_member_count[guild_id] == 0:
            await guild.system_channel.send("そして誰もいなくなった...")


if __name__ == "__main__":
    args = sys.argv
    debug_flg = len(args) >= 2 and args[1] == "debug"
    with open("access_token.txt") as fin:
        token = fin.read()
        client.run(token)
