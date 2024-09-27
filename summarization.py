from logging import getLogger, StreamHandler, FileHandler, Formatter, DEBUG
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False
formatter = Formatter('%(asctime)s : %(levelname)7s - %(message)s')
handler.setFormatter(formatter)
import datetime
import json
import pathlib
import zoneinfo

ON_DEMAND_TYPES = {
    1: 'プレミアム',
    2: '???',
    3: '無料'
}

def load_json(file_path:str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def save_json(data:dict, file_path:str) -> None:
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def unix_to_jst(unix_time:int) -> datetime.datetime:
    # UNIX時間をUTCとしてdatetimeに変換
    utc_time = datetime.datetime.utcfromtimestamp(unix_time)
    
    # JSTタイムゾーンのオブジェクトを取得
    jst_timezone = zoneinfo.ZoneInfo('Asia/Tokyo')
    
    # UTC時間をJSTに変換
    jst_time = utc_time.replace(tzinfo=datetime.timezone.utc).astimezone(jst_timezone)
    
    return jst_time

def get_file_paths(path:str) -> list:
    return [str(p).replace('\\', '/') for p in pathlib.Path(path).glob('*') if p.is_file()]

def get_file_names(path:str) -> list:
    return [p.name for p in pathlib.Path(path).glob('*') if p.is_file()]

def get_dir_paths(path:str) -> list:
    return [str(p).replace('\\', '/') for p in pathlib.Path(path).glob('*') if p.is_dir()]

def file_exisits(file_path:str) -> bool:
    return pathlib.Path(file_path).exists()

def main():
    data_path = './Data'
    anime_list = load_json(f'{data_path}/anime_list.json')

    summarization_data = {}

    for anime in anime_list['cards']:
        summarization_data[anime['seriesId']] = summarize_anime_overview(f'{data_path}/{anime["seriesId"]}')

    episode_dicts = {}
    episode_dirs, series_ids = get_episode_dirs(summarization_data)
    for epispde_dir in episode_dirs:
        episode_dicts.update(summarize_episode(epispde_dir))

    if file_exisits(f'{data_path}/summarization.json'):
        diff_summarization_data = {}
        old_summarization_data = load_json(f'{data_path}/summarization.json')
        for key, value in summarization_data.items():
            if key not in old_summarization_data.keys():
                if 'add' not in diff_summarization_data.keys():
                    diff_summarization_data['add'] = {}
                if key not in diff_summarization_data['add'].keys():
                    diff_summarization_data['add'][key] = {}
                    diff_summarization_data['add'][key]['title'] = value['title']
                diff_summarization_data['add'][key] = value
        for key, value in old_summarization_data.items():
            if key not in summarization_data.keys():
                if 'del' not in diff_summarization_data.keys():
                    diff_summarization_data['del'] = {}
                if key not in diff_summarization_data['del'].keys():
                    diff_summarization_data['del'][key] = {}
                    diff_summarization_data['del'][key]['title'] = value['title']
                diff_summarization_data['del'][key] = value
            else:
                for k, v in value.items():
                    if old_summarization_data[key][k] != summarization_data[key][k]:
                        if 'change' not in diff_summarization_data.keys():
                            diff_summarization_data['change'] = {}
                        if key not in diff_summarization_data['change'].keys():
                            diff_summarization_data['change'][key] = {}
                            diff_summarization_data['change'][key]['title'] = summarization_data[key]['title']
                        diff_summarization_data['change'][key][k+'_new'] = summarization_data[key][k]
                        diff_summarization_data['change'][key][k+'_old'] = old_summarization_data[key][k]
        save_json(diff_summarization_data, f'{data_path}/diff_summarization.json')

    if file_exisits(f'{data_path}/episode_summarization.json'):
        diff_episode_dicts = {}
        old_episode_dicts = load_json(f'{data_path}/episode_summarization.json')
        for (key, value), series_id in zip(episode_dicts.items(), series_ids):
            if key not in old_episode_dicts.keys():
                if 'add' not in diff_episode_dicts.keys():
                    diff_episode_dicts['add'] = {}
                logger.info(f'Added: {key}')
                diff_episode_dicts['add'][key] = {}
                diff_episode_dicts['add'][key]['id'] = value['id']
                diff_episode_dicts['add'][key]['animeTitle'] = load_json(f'{data_path}/{series_id}/overview.json')['title']
                diff_episode_dicts['add'][key]['episodeTitle'] = value['title']
                logger.info(f'{diff_episode_dicts["add"][key]["episodeTitle"]}')
                diff_episode_dicts['add'][key]['episodeNumber'] = value['episodeNumber']
                for k, v in value.items():
                    if k not in ['title']:    
                        diff_episode_dicts['add'][key][k] = v
        for key, value in old_episode_dicts.items():
            if key not in episode_dicts.keys():
                if 'del' not in diff_episode_dicts.keys():
                    diff_episode_dicts['del'] = {}
                if key not in diff_episode_dicts['del'].keys():
                    logger.info(f'Deleted: {key}')
                    diff_episode_dicts['del'][key] = {}
                    diff_episode_dicts['del'][key]['id'] = value['id']
                    diff_episode_dicts['del'][key]['animeTitle'] = load_json(f'{data_path}/{series_id}/overview.json')['title']
                    diff_episode_dicts['del'][key]['episodeTitle'] = value['title']
                    diff_episode_dicts['del'][key]['episodeNumber'] = value['episodeNumber']
                for k, v in value.items():
                    if k not in ['title']:
                        diff_episode_dicts['del'][key][k] = v
            else:
                for k, v in value.items():
                    if old_episode_dicts[key][k] != episode_dicts[key][k]:
                        if 'change' not in diff_episode_dicts.keys():
                            diff_episode_dicts['change'] = {}
                        if key not in diff_episode_dicts['change'].keys():
                            logger.info(f'Changed: {key}')
                            diff_episode_dicts['change'][key] = {}
                            diff_episode_dicts['change'][key]['id'] = value['id']
                            diff_episode_dicts['change'][key]['animeTitle'] = load_json(f'{data_path}/{series_id}/overview.json')['title']
                            diff_episode_dicts['change'][key]['episodeTitle'] = value['title']
                            diff_episode_dicts['change'][key]['episodeNumber'] = value['episodeNumber']
                        diff_episode_dicts['change'][key][k+'_new'] = episode_dicts[key][k]
                        diff_episode_dicts['change'][key][k+'_old'] = old_episode_dicts[key][k]
        save_json(diff_episode_dicts, f'{data_path}/diff_episode_summarization.json')

    save_json(summarization_data, f'{data_path}/summarization.json')
    save_json(episode_dicts, f'{data_path}/episode_summarization.json')
    
def summarize_anime_overview(series_path:str) -> dict:
    anime_dict = {}
    logger.info(f'Loading the anime list: {series_path}')
    overview_data = load_json(f'{series_path}/overview.json')
    
    # Overviewデータの要約
    anime_dict['title'] = overview_data['title']
    anime_dict['seasons'] = overview_data['seasons']
    anime_dict['version'] = overview_data['version']
    anime_dict['imageUpdatedAt'] = unix_to_jst(overview_data['imageUpdatedAt']).strftime('%Y-%m-%d %H:%M:%S')
    anime_dict['imageUpdatedAtUnix'] = overview_data['imageUpdatedAt']
    anime_dict['thumbnailUrl'] = f'{overview_data["thumbComponent"]["urlPrefix"]}/{overview_data["thumbComponent"]["filename"]}'
    anime_dict['portraitUrl'] = f'{overview_data["thumbPortraitComponent"]["urlPrefix"]}/{overview_data["thumbPortraitComponent"]["filename"]}'
    anime_dict['onDemandTypes'] = [ON_DEMAND_TYPES.get(t, '???') for t in overview_data['onDemandTypes']]
    logger.info(f'Loaded the anime list: {series_path}')
    return anime_dict

def get_episode_dirs_(path:str) -> list:
    episode_dirs = []
    for series_dir in get_dir_paths(path):
        if len(get_dir_paths(series_dir)) == 0:
            continue
        if file_exisits(f'{get_dir_paths(series_dir)[0]}/episode_data.json'):
            episode_dirs.append(series_dir)
            logger.info(f'Added: {series_dir}')
        else:
            for season_dir in get_dir_paths(series_dir):
                if len(get_dir_paths(season_dir)) == 0:
                    continue
                if file_exisits(f'{get_dir_paths(season_dir)[0]}/episode_data.json'):
                    episode_dirs.append(season_dir)
                    logger.info(f'Added: {season_dir}')
                else:
                    for episode_group_dir in get_dir_paths(season_dir):
                        if len(get_dir_paths(episode_group_dir)) == 0:
                            continue
                        if file_exisits(f'{get_dir_paths(episode_group_dir)[0]}/episode_data.json'):
                            episode_dirs.append(episode_group_dir)
                            logger.info(f'Added: {episode_group_dir}')
                        else:
                            Exception(f'Unknown directory: {episode_group_dir}')
    return episode_dirs

def get_episode_dirs(summarization_data:dict) -> list:
    episode_dirs = []
    series_ids = []
    for key, value in summarization_data.items():
        path = f'./Data/{key}'
        if len(get_dir_paths(path)) == 0:
            continue
        if file_exisits(f'{get_dir_paths(path)[0]}/episode_data.json'):
            episode_dirs.append(path)
            series_ids.append(key)
            logger.info(f'Added: {path}')
        else:
            for season_dir in get_dir_paths(path):
                if len(get_dir_paths(season_dir)) == 0:
                    continue
                if file_exisits(f'{get_dir_paths(season_dir)[0]}/episode_data.json'):
                    episode_dirs.append(season_dir)
                    series_ids.append(key)
                    logger.info(f'Added: {season_dir}')
                else:
                    for episode_group_dir in get_dir_paths(season_dir):
                        if len(get_dir_paths(episode_group_dir)) == 0:
                            continue
                        if file_exisits(f'{get_dir_paths(episode_group_dir)[0]}/episode_data.json'):
                            episode_dirs.append(episode_group_dir)
                            series_ids.append(key)
                            logger.info(f'Added: {episode_group_dir}')
                        else:
                            Exception(f'Unknown directory: {episode_group_dir}')
    return episode_dirs, series_ids

def summarize_episode(path:str) -> dict:
    logger.info(f'Loading the episode list: {path}')
    episode_dicts = {}
    if file_exisits(f'{path}/episode_list.json'):
        episode_list = load_json(f'{path}/episode_list.json')
    else:
        episode_list = load_json(f'{path}/episode_list_series.json')
    for episode in episode_list:
        episode_dict = {}
        episode_dict['id'] = episode['id']
        episode_dict['episodeNumber'] = episode['episode']['number']
        episode_dict['title'] = episode['episode']['title']
        episode_dict['content'] = episode['episode']['content']
        if file_exisits(f'{path}/episode_list.json'):
            episode_dict['onDemandType'] = ON_DEMAND_TYPES.get(episode['video']['terms'][0]['onDemandType'], '???')
            episode_dict['onDemandEndDate'] = unix_to_jst(episode['video']['terms'][0]['endAt']).strftime('%Y-%m-%d %H:%M:%S')
            episode_dict['onDemandEndDateUnix'] = episode['video']['terms'][0]['endAt']
        else:
            episode_dict['onDemandType'] = ON_DEMAND_TYPES.get(episode['terms'][0]['onDemandType'], '???')
            episode_dict['onDemandEndDate'] = unix_to_jst(episode['terms'][0]['endAt']).strftime('%Y-%m-%d %H:%M:%S')
            episode_dict['onDemandEndDateUnix'] = episode['terms'][0]['endAt']

        episode_detail = load_json(f'{path}/{episode["id"]}/episode_data.json')
        episode_dict['thumbnailUrls'] = []
        for key, value in episode_detail['providedInfo'].items():
            if isinstance(value, str):
                episode_dict['thumbnailUrls'].append(f'https://image.p-c2-x.abema-tv.com/image/programs/{episode["id"]}/{value}.png')
            elif isinstance(value, list):
                for v in value:
                    episode_dict['thumbnailUrls'].append(f'https://image.p-c2-x.abema-tv.com/image/programs/{episode["id"]}/{v}.png')
            else:
                logger.warning(f'Unknown type: {type(value)}')
        episode_dict['imageUpdatedAt'] = unix_to_jst(episode_detail['imageUpdatedAt']).strftime('%Y-%m-%d %H:%M:%S')
        episode_dict['imageUpdatedAtUnix'] = episode_detail['imageUpdatedAt']
        episode_dict['endAt'] = unix_to_jst(episode_detail['endAt']).strftime('%Y-%m-%d %H:%M:%S')
        episode_dict['endAtUnix'] = episode_detail['endAt']
        if 'freeEndAt' in episode_detail.keys():
            episode_dict['freeEndAt'] = unix_to_jst(episode_detail['freeEndAt']).strftime('%Y-%m-%d %H:%M:%S')
            episode_dict['freeEndAtUnix'] = episode_detail['freeEndAt']
        
        episode_dicts[episode['id']] = episode_dict
    logger.info(f'Loaded the episode list: {path}')
    return episode_dicts
        

if __name__ == '__main__':
    main()
