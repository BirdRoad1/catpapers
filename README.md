# CatPapers

A python script for Linux that changes your wallpaper to a random cat wallpaper from Reddit.

## How to use

In a terminal, run `python3 catpapers.py` or `./catpapers.py`.

You can also use this in a bash script or a cron script as shown in the next section.

## Cron script
To make the wallpaper change periodically, you can use cron to execute this script periodically.

The following command appends a line to your user crontab that runs catpapers.py every 5 minutes

```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * DISPLAY=:0 XAUTHORITY=/home/$(whoami)/.Xauthority python3 /path/to/catpapers.py") | crontab -
```