# Nullzee's Slave Bot
The discord bot found in [Nullzee's Cave](https://discord.com/invite/nullzee).

#

### TODO:
- General cleanup (believe it or not, this is the most time-consuming task on the list)
- Make weekly leaderboard reset weekly after sending the leaderboard into a dedicated channel, add weekly as a giveaway req somehow, and possibly a role and/or achievement for top 3 on the last week's leaderboard.
- Update to dpy 2.0
- Update server_info
- Improve mass_ban to cut after a full line instead of halfway through
- Make sure lockdown actually works as intended
- Rewrite the level roles system because it's terrible
- Work on the dashboard
- When discord add dropdowns to modals make a staff application command
- Make an inverse function of string_to_seconds() from utils.py and use it to make channel_command_cooldown() in bot.py and end_log() in moderation_utils.py include the duration of the punishment which has ended
- Prevent report from breaking when a message without any content is reported, such as an embed
