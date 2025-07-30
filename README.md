# CatPapers

A python script for Linux that changes your wallpaper to a random cat wallpaper from Reddit.
This script supports Windows and Linux only.

## How to use

In a terminal, run `python3 catpapers.py` or `./catpapers.py`.

You can also use this in a bash script or a cron script as shown in the next section.

If you want to schedule a wallpaper change, you can use `./catpapers.py schedule`.

If you want to run the script detached from the shell, you can use `./catpapers.py bg`

### Reddit OAuth
If you're getting 403 or other errors, you should use Reddit OAuth. Using OAuth instead of unauthenticated endpoints also grants a higher ratelimit, so it's highly recommended:

1. Create an app at https://old.reddit.com/prefs/apps/. Select the "script" option. The name, description, and redirect uri can be anything.
2. Copy the client id (the random characters under "personal use script") into the REDDIT_CLIENT_ID variable.
3. Copy the client secret (labeled "secret") into the REDDIT_CLIENT_SECRET variable.

Now, you should be good to go!