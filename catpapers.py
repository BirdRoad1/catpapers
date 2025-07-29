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

# Change these if need be
X_DISPLAY=':0' # Linux X11 display variable
IMAGES_PATH = './images/'

class Reddit:
    USER_AGENT = 'catpapers/1.0'

    @staticmethod
    def get_reddit_posts():
        """Fetch an array of Reddit posts"""
        req = Request('https://www.reddit.com/r/cats.json?limit=100', headers={
            'user-agent': Reddit.USER_AGENT
        })
        res = urlopen(req)
        data = json.loads(res.read())
        return data['data']['children']

    @staticmethod
    def download_file(url: str, dest: str):
        """Downloads the file at URL url to the path destination over HTTP"""
        req = Request(url, headers={
            'user-agent': Reddit.USER_AGENT
        })

        res = urlopen(req)
        with open(dest, 'wb') as file:
            file.write(res.read())

class Scheduler:
    @staticmethod
    def schedule_windows(cmd: str):
        """Use Windows task scheduler to schedule a command"""
        cmd = [f'SCHTASKS.EXE', '/CREATE', '/SC', 'MINUTE', '/MO', '20', '/TN', 'CatPapers', '/TR', cmd, '/F']
        
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
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
    print('No new cats found! Using existing cat!')
    
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
        
        return (url, file_name)
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
        (url, imagePath) = new_cat
        if not path.exists(images_dir):
            os.makedirs(images_dir)

        # Download image
        try:
            Reddit.download_file(url, imagePath)
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
        apply_local_cat()

if __name__ == '__main__':
    main()