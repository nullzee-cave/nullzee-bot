# Contributing

Firstly, thanks for taking the time to contribute! Contributions made here will be reflected on the discord bot.

Below are the guidelines for contributing.

### Getting Started

The [README](https://github.com/nullzee-cave/nullzee-bot/projects?type=beta) is always a good place to check first, it contains a TODO list of everything that currently *needs* doing for the bot.
Please try to avoid asking questions in the issues page, use the [discussions](https://github.com/nullzee-cave/nullzee-bot/discussions) page instead.

### Issues

When creating an issue, please try to make sure you:
1. Don't create duplicate issues
2. Describe the issue in detail, providing as much information as possible.
   - If requesting a new feature, describe the feature in detail, including why it should be added.
   - If reporting a bug, fully explain how to reproduce the bug.

Issues missing any of this information may take longer to be dealt with than more detailed issues.

### Code Style

Some general tips and guidelines to follow when writing code for this bot:
- Follow [PEP8](https://peps.python.org/pep-0008/) wherever possible.
- British spellings of words should be used where applicable.
- This project uses double quotation marks (`" "`) for strings everywhere it is easily possible. Try to avoid using single quotation marks where they are unnecessary.
  - Uses such as strings inside f-strings are acceptable.
- Constants should all be located in `helpers/constants.py`.
- All secrets (like the bot token, or API keys) should be located in the gitignored `api_key.py` file.
  - If you wish to add something to `api_key.py`, write your code as if it is there and add it to the template, then mention its addition in your pull request.

### Pull Requests

When you're finished and happy with your changes, create a pull request (PR).
- Fill out the template. This will help you create a meaningful pull request which is both detailed and easy to understand.
- If this PR fixes or affects an issue, try to [link the PR to the issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue).
- We may ask for changes to be made before the PR is merged. If this is the case, we will not merge your PR until they are complete.

Once your PR is merged, the changes will take effect the next time the bot is updated. If possible, I will try to ensure that happens within 24h.
