'''
	https://clips.twitch.tv/api/v2/clips/ + name
	https://clips.twitch.tv/api/v2/clips/ + name + "/status" 

'''
import logging
import requests
import json
import time

from bs4 import BeautifulSoup

def get_clipid(lnk):
	headers = {'User-agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1)','X-Requested-With': 'XMLHttpRequest'}
	r = requests.get('https://tgd.kr/clips/147250', headers=headers)
	rjs = json.loads(r.content)
	return rjs['data']['clip_id']

def get_info(clip_id):
        info = {"clip_id": clip_id ,"nickname":"", "twitch_home":"", "title":"", "gamename": "", "quality":"", "src":""}
        headers = {'User-agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1)'}
        # 제목, 스트리머 이름, 게임 종류, 스트리머 홈 주소 세팅
        r = requests.get('https://clips.twitch.tv/api/v2/clips/' + clip_id, headers=headers)
        rjs = json.loads(r.content)
        info['nickname'] = rjs['broadcaster_display_name']
        info['twitch_home'] = rjs['broadcaster_channel_url']
        info['title'] = rjs['title']
        info['gamename'] = rjs['game']

        # 클립 영상 품질, 다운로드 주소 세팅
        r = requests.get('https://clips.twitch.tv/api/v2/clips/' + clip_id + "/status", headers=headers)
        rjs = json.loads(r.content)
        info['quality'] = rjs['quality_options'][0]['quality']
        info['src'] = rjs['quality_options'][0]['source']
        return info

def download(lnk, infos):
        fs = open("download.log", 'r')
        clip_ids = []
        while True:
                lines = fs.readline()
                if not lines: break
                clip_ids.append(lines.strip())
        fs.close()

        try:
                a = clip_ids.index(infos['clip_id'])
                lf.warning("[System] " + infos['clip_id'] + "의 영상을 다운로드 한 적이 있어서 무시함!")
        except:
                fn = "./downloads/" + infos['title'] + ".mp4"
                r = requests.get(lnk)
                f=open(fn, 'wb');
                for chunk in r.iter_content(chunk_size=255):
                        if chunk:
                                f.write(chunk)
                f.close()
                df.info(infos['clip_id'])
                lf.info("[System] " + infos['clip_id'] + "의 영상을 다운로드 완료!")
        
if __name__ == '__main__':
    df = logging.getLogger("download")
    lf = logging.getLogger("system")

    df.setLevel(logging.INFO)
    lf.setLevel(logging.INFO)
    stream_hander = logging.StreamHandler()
    df.addHandler(stream_hander)
    lf.addHandler(stream_hander)

    filed_handler = logging.FileHandler('download.log')
    filel_handler = logging.FileHandler('system.log')
    df.addHandler(filed_handler)
    lf.addHandler(filel_handler)

    # 로깅 관련 선언들

    # ↓ 실제 코드 ↓

    #print(get_clipid('https://tgd.kr/clips/147250'))

    rinfo = get_info(get_clipid('https://tgd.kr/clips/147250'))

    #print(rinfo['src'])

    #download(rinfo['src'], rinfo)



