from logging import getLogger, StreamHandler, FileHandler, Formatter, DEBUG
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False
formatter = Formatter('%(asctime)s : %(levelname)7s - %(message)s')
handler.setFormatter(formatter)
from datetime import datetime
import json
from json.decoder import JSONDecodeError
import pathlib
import queue
import requests
import subprocess
import threading
import time

import API_auth
#/dev/sde2             219G   64G  145G  31% /
# Time: 6053.77sec(all Data)

class Abema_Data:
    def __init__(self):
        start = time.perf_counter()
        self.BASE_PATH = '/home/kotetsu/Program/Python/Abema_DL/Abema_data'
        make_path(self.BASE_PATH)

        now = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        file_handler = FileHandler(f'./log/{now}.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        self.headers = API_auth.get_header()
        self.tor_files = [
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc01',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc02',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc03',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc04',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc05',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc06',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc07',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc08',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc09',
            '/home/kotetsu/Program/Python/Abema_DL/tor_file/torrc10',
        ]
        self.proxies_list = [
            'socks5://127.0.0.1:9050',
            'socks5://127.0.0.1:9051',
            'socks5://127.0.0.1:9052',
            'socks5://127.0.0.1:9053',
            'socks5://127.0.0.1:9054',
            'socks5://127.0.0.1:9055',
            'socks5://127.0.0.1:9056',
            'socks5://127.0.0.1:9057',
            'socks5://127.0.0.1:9058',
            'socks5://127.0.0.1:9059',
        ]
        self.thread_send_queue = queue.Queue()
        self.thread_recv_queue = queue.Queue()

        self.sleep_time = 0.5

        start_index = 0
        limit = 100
        logger.info(f'{threading.currentThread().getName()}: Downloading anime list... {start_index}~{start_index+limit-1}')
        temp_anime_list = API_auth.get_anime_list(headers=self.headers, limit=limit, start_index=start_index)
        time.sleep(1)
        anime_list = temp_anime_list
        start_index += limit
        del anime_list['paging']
        while len(temp_anime_list['cards'])!=0:
            logger.info(f'{threading.currentThread().getName()}: Downloading anime list... {start_index}~{start_index+limit-1}')
            temp_anime_list = API_auth.get_anime_list(headers=self.headers, limit=limit, start_index=start_index)
            time.sleep(1)
            anime_list['cards'].extend(temp_anime_list.get('cards', []))
            start_index += limit
            API_auth.save_json(anime_list, f'{self.BASE_PATH}/anime_list.json')    

        self.threads = []
        for i, (proxy, tor_file) in enumerate(zip(self.proxies_list, self.tor_files)):
            logger.info(f"スレッド{i}を起動します。")
            thread = threading.Thread(target=self.thread_Abema_data_DL, args=(proxy, tor_file, ), daemon=True)
            thread.start()
            self.threads.append(thread)

        self.download_img_list = []
        for i, anime in enumerate(anime_list.get('cards', [])):
            ANIME_PATH           = f"{self.BASE_PATH}/{anime['seriesId']}"
            ANIME_OVERVIEW_PATH  = f"{ANIME_PATH}/overview.json"
            ANIME_THUMBNAIL_URL  = f"{anime['thumbComponent']['urlPrefix']}/{anime['thumbComponent']['filename']}"
            ANIME_THUMBNAIL_PATH = f"{ANIME_PATH}/{anime['thumbComponent']['filename']}"
            ANIME_PORTRAIT_URL   = f"{anime['thumbPortraitComponent']['urlPrefix']}/{anime['thumbPortraitComponent']['filename']}"
            ANIME_PORTRAIT_PATH  = f"{ANIME_PATH}/{anime['thumbPortraitComponent']['filename']}"
            self.download_img_list.append({
                'url': ANIME_THUMBNAIL_URL,
                'file_name': ANIME_THUMBNAIL_PATH
            })
            self.download_img_list.append({
                'url': ANIME_PORTRAIT_URL,
                'file_name': ANIME_PORTRAIT_PATH
            })
            self.thread_send_queue.put({
                'func': 'get_anime_overview', 
                'series_id': anime['seriesId'], 
                'anime_path':ANIME_PATH, 
                'overview_path': ANIME_OVERVIEW_PATH, 
                'text':f'Anime : {i+1}/{len(anime_list["cards"])}',
            })
        for _ in range(len(self.threads)):self.thread_send_queue.put({'func': 'stop'})

        flag_num = 0
        while True:
            try:
                if flag_num>=len(self.threads) and self.thread_recv_queue.empty():
                    logger.info(f"{threading.currentThread().getName()}: Queue length={self.thread_send_queue.qsize():>5}, 全てのスレッドが終了しました。")
                    break
                item = self.thread_recv_queue.get(timeout=1)
                logger.info(f'{threading.currentThread().getName()}: Queue length={self.thread_send_queue.qsize():>5}, {item["func"]}の処理を行います。')
                if item.get('end', False):
                    flag_num += 1
                elif item['func'] == 'get_anime_overview':
                    make_path(item['anime_path'])
                    API_auth.save_json(item['data'], item['overview_path'])
                    logger.info(f"{threading.currentThread().getName()}: Queue length={self.thread_send_queue.qsize():>5}, {item['overview_path']}の詳細情報を保存しました。")
                    seasons = item['data'].get('seasons', [])
                    if seasons is None:
                        continue
                    for j, season in enumerate(seasons):
                        SEASON_ID = season['id']
                        SEASON_PATH = f"{item['anime_path']}/{SEASON_ID}"
                        SEASON_THUMBNAIL_URL = f"{season['thumbComponent']['urlPrefix']}/{season['thumbComponent']['filename']}"
                        SEASON_THUMBNAIL_PATH = f"{SEASON_PATH}/{season['thumbComponent']['filename']}"
                        self.download_img_list.append({
                            'url': SEASON_THUMBNAIL_URL,
                            'file_name': SEASON_THUMBNAIL_PATH
                        })
                        for k, episode_group in enumerate(season.get('episodeGroups', [])):
                            EPISODE_GROUP_ID = episode_group['id']
                            EPISODE_GROUP_PATH = f"{SEASON_PATH}/{EPISODE_GROUP_ID}"
                            EPISODE_GROUP_EPISODE_LIST_PATH = f"{EPISODE_GROUP_PATH}/episode_list.json"
                            self.thread_send_queue.put({
                                'func': 'get_episode_list', 
                                'season_id': SEASON_ID, 
                                'episode_group_id': EPISODE_GROUP_ID, 
                                'episode_group_path': EPISODE_GROUP_PATH, 
                                'episode_group_episode_list_path': EPISODE_GROUP_EPISODE_LIST_PATH, 
                                'text':f'Season : {j+1}/{len(seasons)}, EpisodeGroup : {k+1}/{len(season["episodeGroups"])}, {item["text"]}',
                                'episode_list': [], 
                                'offset': 0,
                            })
                elif item['func'] == 'get_episode_list':
                    make_path(item['episode_group_path'])
                    API_auth.save_json(item['data'], item['episode_group_episode_list_path'])
                    logger.info(f"{threading.currentThread().getName()}: Queue length={self.thread_send_queue.qsize():>5}, {item['episode_group_path']}/episode_list.jsonのエピソードリストを保存しました。")
                    for l, episode in enumerate(item['data']):
                        EPISODE_ID = episode['id']
                        EPISODE_PATH = f"{item['episode_group_path']}/{EPISODE_ID}"
                        EPISODE_DATA_PATH = f"{EPISODE_PATH}/episode_data.json"
                        EPISODE_THUMBNAIL_URL = f"{episode['thumbComponent']['urlPrefix']}/{episode['thumbComponent']['filename']}"
                        EPISODE_THUMBNAIL_PATH = f"{EPISODE_PATH}/{episode['thumbComponent']['filename']}"
                        self.download_img_list.append({
                            'url': EPISODE_THUMBNAIL_URL,
                            'file_name': EPISODE_THUMBNAIL_PATH
                        })
                        if not file_exists(EPISODE_DATA_PATH):
                            self.thread_send_queue.put({
                                'func': 'get_episode_overview', 
                                'episode_id': EPISODE_ID, 
                                'episode_path': EPISODE_PATH, 
                                'episode_data_path': EPISODE_DATA_PATH, 
                                'text':f'Epiode : {l+1}/{len(item["data"])}, {item["text"]}', 
                            })
                elif item['func'] == 'get_episode_overview':
                    make_path(item['episode_path'])
                    API_auth.save_json(item['data'], item['episode_data_path'])
                    logger.info(f"{threading.currentThread().getName()}: Queue length={self.thread_send_queue.qsize():>5}, {item['episode_data_path']}の詳細情報を保存しました。")
            except queue.Empty:
                logger.info(f"{threading.currentThread().getName()}: Queue length={self.thread_send_queue.qsize():>5}, キューが空です。待機中...")
                pass


        for thread in self.threads:
            thread.join()

        for i, anime in enumerate(anime_list.get('cards', [])):
            ANIME_PATH           = f"{self.BASE_PATH}/{anime['seriesId']}"
            ANIME_OVERVIEW_PATH  = f"{ANIME_PATH}/overview.json"
            ANIME_THUMBNAIL_PATH = f"{ANIME_PATH}/{anime['thumbComponent']['filename']}"
            PORTRAIT_PATH        = f"{ANIME_PATH}/{anime['thumbPortraitComponent']['filename']}"
            assert file_exists(ANIME_OVERVIEW_PATH)
            logger.info(f"{threading.currentThread().getName()}: {ANIME_OVERVIEW_PATH}の詳細情報を取得を確認しました。")
            #assert file_exists(ANIME_THUMBNAIL_PATH)
            #logger.info(f"{ANIME_THUMBNAIL_PATH}のサムネイルを取得を確認しました。")
            #assert file_exists(PORTRAIT_PATH)
            #logger.info(f"{PORTRAIT_PATH}のポートレートを取得を確認しました。")
            anime_data = load_json(ANIME_OVERVIEW_PATH)
            seasons = anime_data.get('seasons', [])
            if seasons is None:
                continue
            for j, season in enumerate(seasons):
                SEASON_ID = season['id']
                SEASON_PATH = f"{ANIME_PATH}/{SEASON_ID}"
                SEASON_THUMBNAIL_PATH = f"{SEASON_PATH}/{season['thumbComponent']['filename']}"
                #assert file_exists(SEASON_THUMBNAIL_PATH)
                #logger.info(f"{SEASON_THUMBNAIL_PATH}のサムネイルを取得を確認しました。")
                for k, episode_group in enumerate(season.get('episodeGroups', [])):
                    EPISODE_GROUP_ID = episode_group['id']
                    EPISODE_GROUP_PATH = f"{SEASON_PATH}/{EPISODE_GROUP_ID}"
                    EPISODE_GROUP_EPISODE_LIST_PATH = f"{EPISODE_GROUP_PATH}/episode_list.json"
                    assert file_exists(EPISODE_GROUP_EPISODE_LIST_PATH)
                    logger.info(f"{threading.currentThread().getName()}: {EPISODE_GROUP_EPISODE_LIST_PATH}のエピソードリストを取得を確認しました。")
                    episode_list = load_json(EPISODE_GROUP_EPISODE_LIST_PATH)
                    for l, episode in enumerate(episode_list):
                        EPISODE_ID = episode['id']
                        EPISODE_PATH = f"{EPISODE_GROUP_PATH}/{EPISODE_ID}"
                        EPISODE_DATA_PATH = f"{EPISODE_PATH}/episode_data.json"
                        assert file_exists(EPISODE_DATA_PATH)
                        logger.info(f"{threading.currentThread().getName()}: {EPISODE_DATA_PATH}の詳細情報を取得を確認しました。")
        logger.info(f"全てのアニメの詳細情報を取得しました。Time: {time.perf_counter()-start:.2f}sec")
        

    def tor_start(self, tor_file) -> list[subprocess.Popen]:
        tor_process = API_auth.tor_start(tor_file)
        logger.info(f"Torプロセスが起動しました。PID: {tor_process.pid}")
        return tor_process

    def thread_Abema_data_DL(self, proxy, tor_file):
        error_num = 0
        process = self.tor_start(tor_file)
        self.test_acsess(proxy)
        thread_name = threading.currentThread().getName()
        logger.info(f"{thread_name:>10}: proxy {proxy}")
        proxies = {
            'http': proxy,
            'https': proxy
        }
        flag=False
        while True:
            try:
                if flag and self.thread_send_queue.empty():
                    logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, スレッドを終了します。")
                    process.terminate()
                    process.wait()
                    logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, Torプロセスが終了しました。")
                    recv_data = {
                        'func': 'stop',
                        'end': True,
                    }
                    self.thread_recv_queue.put(recv_data)
                    break
                item = self.thread_send_queue.get(timeout=2)
                if item['func'] == 'stop':
                    if flag or not self.thread_send_queue.empty():
                        self.thread_send_queue.put(item)
                    else:
                        flag = True
                elif item['func'] == 'get_anime_overview':
                    logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, アニメの詳細情報を取得します。SeriesID: {item['series_id']}, {item['text']}")
                    try:
                        anime_overview = API_auth.get_anime_overview(item['series_id'], headers=self.headers, proxies=proxies)
                        #logger.info(f"{thread_name:>10}: 取得したアニメの詳細情報：{anime_overview}")
                    except JSONDecodeError:
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, JSONDecodeErrorが発生しました。")
                        error_num, process = self.error_occured(error_num, process, tor_file, proxy)
                        self.thread_send_queue.put(item)
                        time.sleep(self.sleep_time)
                        continue
                    except:
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, 予期せぬエラーが発生しました。")
                        
                        process.terminate()
                        process.wait()
                        logger.info(f"{thread_name:>10}: Torプロセスが終了しました。")
                        process = self.tor_start(tor_file)
                        self.test_acsess(proxy)
                        error_num = 0

                        self.thread_send_queue.put(item)
                        time.sleep(self.sleep_time)
                        continue
                    time.sleep(self.sleep_time)
                    logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, アニメの詳細情報の取得が完了しました。SeriesID: {item['series_id']}, {item['text']}")
                    recv_data = {
                        'func': item['func'],
                        'data': anime_overview,
                        'anime_path': item['anime_path'],
                        'overview_path': item['overview_path'],
                        'text': item['text'],
                    }
                    self.thread_recv_queue.put(recv_data)
                elif item['func'] == 'get_episode_list':
                    logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, エピソードリストを取得します。SeasonID: {item['season_id']}, EpisodeGroupID: {item['episode_group_id']}, {item['text']}")
                    limit = 100
                    try:
                        episode_list = API_auth.get_episode_list(item['episode_group_id'], item['season_id'], offset=item['offset'], limit=limit, headers=self.headers, proxies=proxies)
                        item['episode_list'].extend(episode_list['episodeGroupContents'])
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, 取得したエピソードリストの長さ：{len(episode_list['episodeGroupContents'])}, 合計：{len(item['episode_list'])}")
                        #logger.info(f"{thread_name:>10}: {episode_list}")
                        item['offset'] += limit
                        if len(episode_list['episodeGroupContents']) != 0:
                            logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, 取得途中です。SeasonID: {item['season_id']}, EpisodeGroupID: {item['episode_group_id']}, {item['text']}")
                            self.thread_send_queue.put(item)
                    except JSONDecodeError:
                        logger.info(f"{thread_name:>10}: JSONDecodeErrorが発生しました。")
                        error_num, process = self.error_occured(error_num, process, tor_file, proxy)
                        self.thread_send_queue.put(item)
                        time.sleep(self.sleep_time)
                        continue
                    except:
                        logger.info(f"{thread_name:>10}: 予期せぬエラーが発生しました。")
                        
                        process.terminate()
                        process.wait()
                        logger.info(f"{thread_name:>10}: Torプロセスが終了しました。")
                        process = self.tor_start(tor_file)
                        self.test_acsess(proxy)
                        error_num = 0

                        self.thread_send_queue.put(item)
                        time.sleep(self.sleep_time)
                        continue
                    time.sleep(self.sleep_time)
                    if len(episode_list['episodeGroupContents']) == 0:
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, エピソードリストの取得が完了しました。SeasonID: {item['season_id']}, EpisodeGroupID: {item['episode_group_id']}, {item['text']}")
                        recv_data = {
                            'func': item['func'],
                            'data': item['episode_list'],
                            'season_id': item['season_id'],
                            'episode_group_id': item['episode_group_id'],
                            'episode_group_path': item['episode_group_path'],
                            'episode_group_episode_list_path': item['episode_group_episode_list_path'],
                            'text': item['text'],
                        }
                        self.thread_recv_queue.put(recv_data)
                elif item['func'] == 'get_episode_overview':
                    logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, エピソードの詳細情報を取得します。EpisodeID: {item['episode_id']}, {item['text']}")
                    try:
                        episode_data = API_auth.get_episode_overview(item['episode_id'], headers=self.headers, proxies=proxies)
                    except JSONDecodeError:
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, JSONDecodeErrorが発生しました。")
                        error_num, process = self.error_occured(error_num, process, tor_file, proxy)
                        self.thread_send_queue.put(item)
                        time.sleep(self.sleep_time)
                        continue
                    except:
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, 予期せぬエラーが発生しました。")
                        
                        process.terminate()
                        process.wait()
                        logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, Torプロセスが終了しました。")
                        process = self.tor_start(tor_file)
                        self.test_acsess(proxy)
                        error_num = 0

                        self.thread_send_queue.put(item)
                        time.sleep(self.sleep_time)
                        continue
                    time.sleep(self.sleep_time)
                    recv_data = {
                        'func': item['func'],
                        'data': episode_data,
                        'episode_path': item['episode_path'],
                        'episode_data_path': item['episode_data_path'],
                        'text': item['text'],
                    }
                    self.thread_recv_queue.put(recv_data)
            except queue.Empty:
                logger.info(f"{thread_name:>10}: Queue length={self.thread_send_queue.qsize():>5}, キューが空です。待機中...")

    def error_occured(self, error_num, process, tor_file, proxy, reset_tor_num=5):
        error_num += 1
        if error_num > reset_tor_num:
            process.terminate()
            process.wait()
            logger.info(f"Torプロセスが終了しました。")
            process = self.tor_start(tor_file)
            self.test_acsess(proxy)
            error_num = 0
        return error_num, process

    def test_acsess(self, proxy):
        proxies = {
            'http': proxy,
            'https': proxy,
        }
        logger.info(f"proxy {proxy} でアクセステストを行います。")
        res = requests.get('https://checkip.amazonaws.com', proxies=proxies).text.replace('\n', '')
        logger.info(f'proxy {proxy} でのIPアドレス：{res}')

def make_path(path: str) -> None:

    '''ディレクトリの作成を行う関数

    Args:
        path : 作成するディレクトリのパス
    '''
    p = pathlib.Path(path)
    if not p.exists():
        p.mkdir(parents=True)

def file_exists(path: str) -> bool:
    '''ファイルの存在確認を行う関数

    Args:
        path : ファイルのパス

    Returns:
        bool : ファイルが存在するかどうか
    '''
    p = pathlib.Path(path)
    return p.exists()

def load_json(path: str) -> dict:
    '''JSONファイルの読み込みを行う関数

    Args:
        path : JSONファイルのパス

    Returns:
        dict : JSONファイルの内容
    '''
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == '__main__':
    abema_data = Abema_Data()
