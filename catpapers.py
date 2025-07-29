#!/usr/bin/python3

from urllib.request import urlopen, Request
import json
import os.path as path
import os
import subprocess
import random
import platform

USER_AGENT = 'catpapers/1.0'
SPI_SETDESKWALLPAPER = 20 # win32 set wallpaper

def get_reddit_posts():
    req = Request('https://www.reddit.com/r/cats.json?limit=100', headers={
        'user-agent': USER_AGENT
    })
    res = urlopen(req)
    data = json.loads(res.read())
    return data['data']['children']

def download_file(url: str, dest: str):
    req = Request(url, headers={
        'user-agent': USER_AGENT
    })

    res = urlopen(req)
    with open(dest, 'wb') as file:
        file.write(res.read())

def apply_wallpaper(path: str) -> bool:
    system = platform.system()
    if system == 'Windows':
        import ctypes
        if not hasattr(ctypes, 'windll'):
            raise Exception('Could not find win32 API')
        
        ctypes.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, path.encode(), 0)
        return True
    elif system == 'Linux':
        print(f'Loaded wallpaper: {path}')
        return subprocess.call(['/usr/bin/feh','--bg-scale',path]) == 0
    else:
        print('Unknown system')
        return False

def main():
    imagesDir = path.normpath(path.join(os.path.dirname(__file__), './images/'))

    try:
        posts = get_reddit_posts()
    except Exception as err:
        print(f'Failed to get reddit posts: {err}')
        return

    found_cat = False
    while len(posts) > 0:
        # Find undownloaded cat from Reddit
        post = random.choice(posts)
        posts.remove(post)
        post_data = post['data']
        if post_data['is_video']:
            continue # skip videos
        url: str = post_data['url']
        if not url.endswith('png') and not url.endswith('jpg') and not url.endswith('.jpeg'):
            continue # only png/jpeg
        
        file_name = url.split('/').pop().replace('/','')

        imagePath = path.join(imagesDir, file_name)
        if path.exists(imagePath):
            continue

        found_cat = True
        break

    if found_cat:
        if not path.exists(imagesDir):
            os.makedirs(imagesDir)

        # Download image
        try:
            download_file(url, imagePath)
        except Exception as err:
            print(f'Failed to download image! {err}')
            return

        if not path.exists(imagePath):
            print('Downloaded image does not exist')
            return
        
        status = apply_wallpaper(imagePath)
        print('Status: ' + str(status))
    else:
        # No cat found, fallback to local files
        print('No new cats found! Using existing cat!')
        imgs = os.listdir(imagesDir)
        if len(imgs) == 0:
            print('No cat images stored :(')
            exit(1)
        
        file = path.join(imagesDir, random.choice(imgs))
        try:
            apply_wallpaper(file)
        except Exception as err:
            print(f'Failed to apply wallpaper: {err}')

if __name__ == '__main__':
    main()