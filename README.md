DiscordBot
==========

A Discord bot created using [discord.py] to help me manage my servers.

[discord.py]: https://github.com/Rapptz/discord.py


Running
----------
 **Python 3.5.3 or higher required**

Open a bash in the project root directory then run:
- pip install -U -r requirements.txt
- export DISCORD_TOKEN="\<your discord bot token here\>"
- python3 bot/main.py

Obs: In order to get a discord bot token, you must create an
application on https://discord.com/developers, select the newly created application,
navigate to _Bot_, then click on _click to reveal token_ (highlighted in the image below).

![bot_token_page](https://user-images.githubusercontent.com/2393869/113619247-239c3080-962f-11eb-9e1c-1c5045ade571.png)

------------------------------------------------------
Here's the current bot `!help`

```
I'm trying to help manage this server, specially with meetings.

H4CK3R:
  ping     Test my latency
Meetings:
  meeting  [start] - Manage meetings using subcommands
  schedule [add, list, del, clear] - Manage schedule using subcommands
No Category:
  help     Shows this message

Type !help command for more info on a command.
You can also type !help category for more info on a category.
```
