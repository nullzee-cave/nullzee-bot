# Nullzee's Slave Bot

The discord bot found in [Nullzee's Cave](https://discord.com/invite/nullzee).

If you are adding new features which have not been discussed, or you are unsure if your addition works, please commit to a new branch and open a pull request.

---

### TODO

*Numbered lists are used to denote order of importance*

#### Urgent:

1. Update to dpy 2.0
2. Make sure lockdown actually works as intended

#### Other:

1. Make weekly leaderboard reset weekly after sending the leaderboard into a dedicated channel, add weekly as a giveaway req somehow, and possibly a role and/or achievement for top 3 on the last week's leaderboard
2. Do the TODOs in this project
3. Rewrite the level roles system because it's terrible
4. Improve mass_ban to cut after a full line instead of halfway through
5. Update server_info

- Add descriptions to achievements without any
- Make an inverse function of string_to_seconds() from utils.py and use it to make output from channel_command_cooldown() in bot.py nicer, and have end_log() in moderation_utils.py include the duration of the punishment which has ended
- Prevent report from breaking when a message without any content is reported, such as an embed
- Work on the dashboard
- When discord add dropdowns to modals make a staff application command
