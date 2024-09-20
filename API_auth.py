import json
import time
import subprocess

from yt_dlp.extractor import abematv
from yt_dlp import YoutubeDL

import requests

class A(abematv.AbemaTVBaseIE):
    def __init__(self, *args, **kwargs):
        super(A, self).__init__(*args, **kwargs)
        
    def get_token(self):
        return self._get_device_token()

def get_header(sleep_time:int=1) -> dict:
    '''Get the header from the AbemaTV API.

    Args:
        sleep_time (int, optional): The time to sleep. Defaults to 1.

    Returns:
        dict: The header.
    '''
    y = YoutubeDL()
    a = A(downloader=y)
    headers = {
        "Referer": "https://abema.tv/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/123.0.6312.105 Safari/537.36",
        "authorization": f"bearer {a.get_token()}",
        "sec-ch-ua": "\"HeadlessChrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\""
    }
    return headers

def get_anime_list(only_free:bool=False, limit:int=20, start_index:int=0, headers:dict=None, sleep_time:int=1, proxies=None) -> dict:
    '''Get the list of anime from the AbemaTV API.
    
    Args:
        only_free (bool, optional): Whether to get only free anime. Defaults to False.
        limit (int, optional): The number of anime to get. Defaults to 20.
        start_index (int, optional): The start index. Defaults to 0.
        headers (dict, optional): The headers. Defaults to None.
        sleep_time (int, optional): The time to sleep. Defaults to 1.

    Returns:
        dict: The list of anime.
    '''
    if headers is None:
        headers = get_header(sleep_time=sleep_time)
    url = f'https://api.p-c3-e.abema-tv.com/v1/video/featureGenres/animation/cards?onlyFree={str(only_free).lower()}&limit={limit}&next={start_index}'
    response = requests.get(url, headers=headers, proxies=proxies)
    data = response.content.decode('utf-8')
    return json.loads(data)
    
def get_anime_overview(series_id:str, includes:str='liveEvent%2Cslot', headers:dict=None, sleep_time:int=1, proxies=None) -> dict:
    '''Get the overview of an anime from the AbemaTV API.

    Args:
        series_id (str): The series id of the anime.
        includes (str, optional): The includes. Defaults to 'liveEvent%2Cslot'.
        headers (dict, optional): The headers. Defaults to None.
        sleep_time (int, optional): The time to sleep. Defaults to 1.

    Returns:
        dict: The overview of the anime.
    '''
    if headers is None:
        headers = get_header(sleep_time=sleep_time)
    url = f'https://api.p-c3-e.abema-tv.com/v1/contentlist/series/{series_id}?includes={includes}'
    response = requests.get(url, headers=headers, proxies=proxies)
    data = response.content.decode('utf-8')
    return json.loads(data)

def get_episode_list(episode_group_id:str, season_id:str, limit:int=20, offset:int=0, order_type:str='asc', headers:dict=None, sleep_time:int=1, proxies=None) -> dict:
    '''Get the list of episodes from the AbemaTV API.

    Args:
        episode_group_id (str): The episode group id.
        season_id (str): The season id.
        limit (int, optional): The number of episodes to get. Defaults to 20.
        offset (int, optional): The offset. Defaults to 0.
        order_type (str, optional): The order type. Defaults to 'asc'.
        headers (dict, optional): The headers. Defaults to None.
        sleep_time (int, optional): The time to sleep. Defaults to 1.
    
    Returns:
        dict: The list of episodes.
    '''
    url = f'https://api.p-c3-e.abema-tv.com/v1/contentlist/episodeGroups/{episode_group_id}/contents?seasonId={season_id}&limit={limit}&offset={offset}&orderType=asc'
    response = requests.get(url, headers=headers, proxies=proxies)
    data = response.content.decode('utf-8')
    return json.loads(data)

def get_episode_overview(episode_id:str, division:int=0, includes:str='tvod', headers:dict=None, sleep_time:int=1, proxies=None) -> dict:
    '''Get the overview of an episode from the AbemaTV API.

    Args:
        episode_id (str): The episode id.
        division (int, optional): The division. Defaults to 0.
        includes (str, optional): The includes. Defaults to 'tvod'.
        headers (dict, optional): The headers. Defaults to None.
        sleep_time (int, optional): The time to sleep. Defaults to 1.

    Returns:
        dict: The overview of the episode.
    '''
    if headers is None:
        headers = get_header(sleep_time=sleep_time)
    url = f'https://api.p-c3-e.abema-tv.com/v1/video/programs/{episode_id}?division={division}&include={includes}'
    response = requests.get(url, headers=headers, proxies=proxies)
    data = response.content.decode('utf-8')
    return json.loads(data)

def save_json(data:dict, file_name:str='API_data.json', indent:int=4, ensure_ascii:bool=False):
    '''Save the data to a JSON file.

    Args:
        data (dict): The data to save.
        file_name (str, optional): The name of the file. Defaults to 'API_data.json'.
        indent (int, optional): The indentation. Defaults to 4.
        ensure_ascii (bool, optional): Whether to ensure ASCII. Defaults to False.
    '''
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

def download_image(url:str, file_name:str='image.jpg', headers:dict=None, proxies=None):
    '''Download an image.

    Args:
        url (str): The URL of the image.
        file_name (str, optional): The name of the file. Defaults to 'image.jpg'.
        headers (dict, optional): The headers. Defaults to None.
    '''
    response = requests.get(url, headers=headers, proxies=proxies)
    with open(file_name, 'wb') as f:
        f.write(response.content)

def tor_start(tor_file:str) -> subprocess.Popen:
    tor_path = subprocess.run(['which', 'tor'], stdout=subprocess.PIPE).stdout.decode('utf-8').replace('\n', '')
    tor_process = subprocess.Popen(
        [tor_path, "-f", tor_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"Torプロセスの起動を開始しました。PID: {tor_process.pid}")

    while True:
            line = tor_process.stdout.readline()
            if "Bootstrapped 100%" in line:
                return tor_process

            if not line and tor_process.poll() is not None:
                break
    tor_process.terminate()
    print('Torプロセスが終了しました。')
    tor_process.wait()

if __name__ == '__main__':
    proxies = {
        'http': 'socks5://localhost:9050',
        'https': 'socks5://localhost:9050'
    }
    print('Getting the header...')
    header = get_header()
    save_json(header, 'API_header.json')
    time.sleep(1)

    print('Getting the anime list...')
    anime_list = get_anime_list(headers=header, limit=100, proxies=proxies)
    save_json(anime_list, 'API_anime_list.json')
    time.sleep(1)

    thumbnail_url = anime_list['cards'][0]['thumbComponent']['urlPrefix'] + '/' + anime_list['cards'][0]['thumbComponent']['filename']
    print(f'Downloading the thumbnail image: {thumbnail_url}...')
    download_image(thumbnail_url, 'API_anime_thumbnail.png', headers=header)
    time.sleep(1)

    print('Getting the anime overview...')
    anime_index = 1
    anime_overview = get_anime_overview(anime_list['cards'][anime_index]['seriesId'], headers=header, proxies=proxies)
    save_json(anime_overview, 'API_anime_overview.json')
    time.sleep(1)

    print('Getting the episode list...')
    season_index = 0
    episode_group_id = anime_overview['seasons'][season_index]['episodeGroups'][0]['id']
    season_id = anime_overview['seasons'][season_index]['id']
    episode_list = get_episode_list(episode_group_id, season_id, headers=header, limit=100, offset=0, proxies=proxies)
    save_json(episode_list, 'API_episode_list.json')
    time.sleep(1)

    print('Getting the episode overview...')
    episode_index = 0
    episode_id = episode_list['episodeGroupContents'][episode_index]['id']
    episode_overview = get_episode_overview(episode_id, headers=header, proxies=proxies)
    save_json(episode_overview, 'API_episode_overview.json')

