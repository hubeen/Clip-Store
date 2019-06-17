'''
	https://clips.twitch.tv/api/v2/clips/ + name
	https://clips.twitch.tv/api/v2/clips/ + name + "/status" 
    BadPrettyAubergineMoreCowbell
'''

import os
import sys
import optparse
import collections
import webbrowser

import googleapiclient.errors
import oauth2client

from youtube_upload import auth
from youtube_upload import upload_video
from youtube_upload import categories
from youtube_upload import lib
from youtube_upload import playlists

import logging
import requests
import json
import time

from bs4 import BeautifulSoup

try:
    import progressbar
except ImportError:
    progressbar = None

class InvalidCategory(Exception): pass
class OptionsError(Exception): pass
class AuthenticationError(Exception): pass
class RequestError(Exception): pass

EXIT_CODES = {
    OptionsError: 2,
    InvalidCategory: 3,
    RequestError: 3,
    AuthenticationError: 4,
    oauth2client.client.FlowExchangeError: 4,
    NotImplementedError: 5,
}

WATCH_VIDEO_URL = "https://www.youtube.com/watch?v={id}"

debug = lib.debug
struct = collections.namedtuple


def get_clipid(lnk):
    try:
        headers = {'User-agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1)','X-Requested-With': 'XMLHttpRequest'}
        r = requests.get(lnk, headers=headers)
        rjs = json.loads(r.content)
        return rjs['data']['clip_id']
    except:
        pass

def get_info(clip_id):
    try:
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
    except:
        pass
    

def download(lnk, infos):
    try:
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
                try:
                    upload("[" + infos['nickname'] + "] " + infos['title'], "스트리머 트위치 주소 : " + infos['twitch_home'] + "\n제목:" + infos['title'] , "클립봇,트위치,twitch,클립,clip," + infos['nickname'] + "," + infos['gamename'], "./downloads/" + infos['title'] + ".mp4")

                except googleapiclient.errors.HttpError as error:
                    response = bytes.decode(error.content, encoding=lib.get_encoding()).strip()
                    raise RequestError("Server response: {0}".format(response))
    except:
        pass


def get_progress_info():
    """Return a function callback to update the progressbar."""
    progressinfo = struct("ProgressInfo", ["callback", "finish"])

    if progressbar:
        bar = progressbar.ProgressBar(widgets=[
            progressbar.Percentage(), ' ',
            progressbar.Bar(), ' ',
            progressbar.FileTransferSpeed(),
        ])
        def _callback(total_size, completed):
            if not hasattr(bar, "next_update"):
                if hasattr(bar, "maxval"):
                    bar.maxval = total_size
                else:
                    bar.max_value = total_size
                bar.start()
            bar.update(completed)
        def _finish():
            if hasattr(bar, "next_update"):
                return bar.finish()
        return progressinfo(callback=_callback, finish=_finish)
    else:
        return progressinfo(callback=None, finish=lambda: True)

def get_category_id(category):
    """Return category ID from its name."""
    if category:
        if category in categories.IDS:
            ncategory = categories.IDS[category]
            debug("Using category: {0} (id={1})".format(category, ncategory))
            return str(categories.IDS[category])
        else:
            msg = "{0} is not a valid category".format(category)
            raise InvalidCategory(msg)

def upload_youtube_video(youtube, title, description, tags, video_path):
    """Upload video with index (for split videos)."""
    u = lib.to_utf8
    total_videos = 0
    title = u(title) #타이틀
    if hasattr(u('string'), 'decode'):   
        description = u(description or "").decode("string-escape")
    else:
        description = description
      
    tags = [u(s.strip()) for s in (tags or "").split(",")]
    ns = dict(title=title, n=1+1, total=total_videos)
    title_template = u("{title} [{n}/{total}]")
    complete_title = (title_template.format(**ns) if total_videos > 1 else title)
    progress = get_progress_info()
    category_id = get_category_id(None)
    request_body = {
        "snippet": {
            "title": complete_title,
            "description": description,
            "categoryId": category_id,
            "tags": tags,
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",

        },
        "status": {
            "privacyStatus": ("public" ),
            "publishAt": None,

        },
        "recordingDetails": {
            "location": lib.string_to_dict(None),
            "recordingDate": None,
        },
    }

    debug("Start upload: {0}".format(video_path))
    try:
        video_id = upload_video.upload(youtube, video_path, 
            request_body, progress_callback=progress.callback, 
            chunksize=8388608)
    finally:
        progress.finish()
    return video_id

def get_youtube_handler(sepath):
    """Return the API Youtube object."""
    home = os.path.expanduser("~")
    default_client_secrets = lib.get_first_existing_filename(
        [sys.prefix, os.path.join(sys.prefix, "local")],
        "share/youtube_upload/client_secrets.json")  
    default_credentials = os.path.join(home, ".youtube-upload-credentials.json")
    client_secrets = sepath or default_client_secrets or \
        os.path.join(home, ".client_secrets.json")
    credentials = default_credentials

    get_code_callback = (auth.browser.get_code 
        if None else auth.console.get_code)
    return auth.get_resource(client_secrets, credentials,
        get_code_callback=get_code_callback)

def upload(title, description, tags, path, output=sys.stdout):
    """Run the main scripts from the parsed options/args."""
    
    print("merong!\n\n\n\n")

    youtube = get_youtube_handler("D:\\Clip Store\\youtube-upload-master\\client_secrets.json")

    if youtube:
        video_id = upload_youtube_video(youtube, title, description, tags, path)
        video_url = WATCH_VIDEO_URL.format(id=video_id)
        debug("Video URL: {0}".format(video_url))
                
    else:
        raise AuthenticationError("Cannot get youtube resource")

        

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

#print(get_clipid('https://tgd.kr/clips/147250'))
maxed = 500
while(maxed>-1):
    if(maxed==0):
        maxed=1

    cnt = 20

    headers = {'User-agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1)'}
    r = requests.get("https://tgd.kr/clips/lists/" + str(maxed) +  "?sortby=new&date_range=overall", headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    mydivs = soup.findAll("div", {"class": "clips"})

    # 1 page = 20

    for div in mydivs:
        print(div.get('data-id'))
        rinfo = get_info(get_clipid('https://tgd.kr/clips/' + div.get('data-id')))
        if(rinfo != None):
            download(rinfo['src'], rinfo)
        #print(div.get('data-id') + " : " + str(cnt) + " : " + str(maxed))
        cnt-=1

    if(cnt == 0):
        maxed-=1
