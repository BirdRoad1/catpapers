#!/usr/bin/python3

from urllib.request import urlopen, Request
import json
import os.path as path
import os
import subprocess
import random
import platform
import sys
import getpass
import ctypes
import base64
from http.client import HTTPResponse
from time import time
from math import floor
from typing import Optional
from uuid import uuid4
import urllib.parse

# Change these if need be
X_DISPLAY=':0' # Linux X11 display variable
IMAGES_PATH = './images/'
REDDIT_CLIENT_ID = ''
REDDIT_CLIENT_SECRET = ''

class Reddit:
    _USER_AGENT = 'catpapers/1.0'
    _AUTH_FILE = path.join(path.dirname(__file__), "catpapers-auth.json")
    _SHOULD_AUTH = REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET
    _token: str = None
    
    @staticmethod
    def _request_token() -> Optional[str]:
        if Reddit._token != None:
            return Reddit._token
        
        if len(REDDIT_CLIENT_ID) == 0 or len(REDDIT_CLIENT_SECRET) == 0:
            return None
        
        uid = str(uuid4())
        if path.exists(Reddit._AUTH_FILE):
            with open(Reddit._AUTH_FILE, 'r') as file:
                data = json.loads(file.read())
                uid = data['uid']
                if data['expires'] > floor(time()) + 20:
                    print('Found cached token!')
                    token = data['access_token']
                    Reddit._token = token
                    return token
                
        url = 'https://www.reddit.com/api/v1/access_token'
        data = f'grant_type=client_credentials&device_id={uid}'.encode('utf-8')
        
        req = Request(url=url, headers={
            'user-agent': Reddit._USER_AGENT,
            'authorization': 'Basic ' + base64.b64encode(f'{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')
        }, data=data)
        
        res: HTTPResponse = urlopen(req)
        data = json.loads(res.read())
        if 'access_token' not in data:
            print('No access_token received from Reddit!')
            return None
        
        expires = floor(time() + data['expires_in'])
        token = data['access_token']
        
        Reddit._token = token
        
        auth_data = {
            'access_token': token,
            'expires': expires,
            'uid': uid
        }
        
        with open(Reddit._AUTH_FILE, 'w') as file:
            file.write(json.dumps(auth_data))
        
        print('Received new token!')
        return token
    
    @staticmethod
    def _get_headers(auth: bool = True):
        headers = {
            'user-agent': Reddit._USER_AGENT,
        }
        
        if auth:
            token = Reddit._request_token()
            if token != None:
                headers['authorization'] = f'Bearer {token}'

        return headers

    @staticmethod
    def _reddit_request(endpoint: str) -> Request:
        headers = Reddit._get_headers()
        hostname = 'oauth.reddit.com' if 'authorization' in headers else 'reddit.com'

        return Request(f'https://{hostname}{endpoint}', headers=headers)
            
    @staticmethod
    def get_reddit_posts():
        """Fetch an array of Reddit posts"""
        
        req = Reddit._reddit_request('/r/cats.json?limit=100')
        res = urlopen(req)
        data = json.loads(res.read())
        return data['data']['children']

    @staticmethod
    def download_file(url: str, dest: str):
        """Downloads the file at URL url to the path destination over HTTP"""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'http' and parsed.scheme != 'https':
            raise Exception('URL must be http(s)')
        
        is_reddit_url = parsed.hostname == 'i.redd.it' and parsed.scheme == 'https'
        
        req = Request(url, headers=Reddit._get_headers(auth=is_reddit_url))
        res = urlopen(req)
        with open(dest, 'wb') as file:
            file.write(res.read())

class Scheduler:
    @staticmethod
    def schedule_windows(cmd: str):
        """Use Windows task scheduler to schedule a command"""
        cmd = [f'SCHTASKS.EXE', '/CREATE', '/SC', 'MINUTE', '/MO', '20', '/TN', 'CatPapers', '/TR', cmd, '/F']
        
        oc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = proc.wait()
        if result != 0:
            out, err = proc.communicate()
            raise Exception(out + err)
    
    @staticmethod
    def schedule_linux(cmd: str):
        """Use Linux cron to schedule a command"""
        line_to_add = f'*/20 * * * * {cmd}'

        crontab_process = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        crontab_process.wait()

        crontab: str = crontab_process.communicate()[0].decode('utf-8')
        if line_to_add in crontab:
            raise Exception('Already scheduled')
        
        if not crontab.endswith('\n'):
            crontab += '\n'
        
        crontab += line_to_add + '\n'

        create_crontab_proc = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        create_crontab_proc.stdin.write(crontab.encode())

        _, err = create_crontab_proc.communicate()
        if err:
            raise Exception(f'Failed to install crontab: {err}')

SPI_SETDESKWALLPAPER = 20 # win32 set wallpaper
DETACHED_PROCESS = 0x00000008 # start detached process on windows
system = platform.system()
images_dir = path.normpath(path.join(os.path.dirname(__file__), IMAGES_PATH))

def apply_wallpaper(path: str) -> bool:
    """Set the desktop background to the image at path"""
    if system == 'Windows':
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

def schedule():
    """Schedule the current script to run periodically"""
    if system == 'Windows':       
        python_binary = sys.executable
        pythonw_binary = path.join(path.dirname(python_binary), 'pythonw.exe')
        py_cmd = f'"{pythonw_binary}" "{__file__}" bg'
        try:
            Scheduler.schedule_windows(py_cmd)
            print('Task successfully scheduled!')
        except Exception as err:
            print(f'Failed to schedule task: {err}')
    elif system == 'Linux':
        try:
            Scheduler.schedule_linux(f'DISPLAY={X_DISPLAY} XAUTHORITY=/home/{getpass.getuser()}/.Xauthority python3 {__file__}')
            print(f'Success! New crontab: {crontab}')
        except Exception as err:
            print(f'Failed to create crontab: {err}')

def rerun_bg():
    """Re-run this script in the background, detached from the terminal"""
    if system == 'Windows':
        subprocess.Popen([sys.executable, __file__], creationflags=DETACHED_PROCESS, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen([sys.executable, __file__], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    exit()

def is_image(file_name: str) -> bool:
    return file_name.endswith('png') or file_name.endswith('jpg') or file_name.endswith('jpeg')


def apply_local_cat():
    """Apply a cat wallpaper from locally cached images"""    
    if not path.exists(images_dir):
        print('No cat images stored :(')
        return
    
    imgs = os.listdir(images_dir)
    if len(imgs) == 0:
        print('No cat images stored :(')
        exit(1)
    
    file = path.join(images_dir, random.choice(imgs))
    try:
        apply_wallpaper(file)
    except Exception as err:
        print(f'Failed to apply wallpaper: {err}')

def get_new_cat(posts):
    """Try and find a cat that has not been cached from Reddit posts"""
    found_cat = False
    while len(posts) > 0:
        # Find undownloaded cat from Reddit
        post = random.choice(posts)
        posts.remove(post)
        post_data = post['data']
        if post_data['is_video']:
            continue # skip videos
        url: str = post_data['url']
        if not is_image(url):
            continue # only png/jpeg
        
        file_name = url.split('/').pop().replace('/','')

        imagePath = path.join(images_dir, file_name)
        if path.exists(imagePath):
            continue
        
        return (url, imagePath)
    return None

def main():
    if len(sys.argv) == 2:
        if sys.argv[1].lower() == 'schedule':
            schedule()
        elif sys.argv[1].lower() == 'bg':
            # re-run this script in the background
            rerun_bg()
        else:
            print('Invalid option')
        return
    elif len(sys.argv) > 2:
        print('Invalid usage')
        return
    
    try:
        posts = Reddit.get_reddit_posts()
    except Exception as err:
        print(f'Failed to get reddit posts: {err}')
        return

    new_cat = get_new_cat(posts)
    
    if new_cat != None:
        (url, image_path) = new_cat
        if not path.exists(images_dir):
            os.makedirs(images_dir)

        # Download image
        try:
            Reddit.download_file(url, image_path)
        except Exception as err:
            print(f'Failed to download image! {err}')
            print('Falling back to cached cat images')
            apply_local_cat()
            return

        if not path.exists(image_path):
            print('Downloaded image does not exist! Using cached cat images instead')
            apply_local_cat()
            return
        
        status = apply_wallpaper(image_path)
        print('Status: ' + str(status))
    else:
        # No cat found, fallback to local files
        print('No new cats found! Using existing cat!')
        apply_local_cat()

if __name__ == '__main__':
    main()