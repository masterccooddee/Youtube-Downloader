import yt_dlp

def progress_hook(d):

    playlist_title = ""
    if d['status'] == 'downloading':

        # check what is downloading
        info = d.get('info_dict', {})
        vcodec = info.get('vcodec', 'none')
        acodec = info.get('acodec', 'none')

        current_type = ""
        if vcodec != 'none' and acodec != 'none':
            current_type = "Video+Audio"
        elif vcodec != 'none' and acodec == 'none':
            current_type = "Video"
        elif acodec != 'none' and vcodec == 'none':
            current_type = "Audio"

        line1 = ''
        playlist_title = info.get('playlist_title')
        if playlist_title:
            index = info.get('playlist_index', 0)
            count = info.get('playlist_count', 0)
            line1 = (f'下載清單: \033[38;5;50m{playlist_title}\033[0m (\033[38;5;40m{index}\033[0m/\033[38;5;40m{count}\033[0m)')

        line2 = ''
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total_bytes:
            downloaded_bytes = d.get('downloaded_bytes', 0)
            percent = downloaded_bytes / total_bytes * 100
            # 修改：印出類型
            line2 = (f'[{current_type}] Progress: {percent:.2f}%')

        if playlist_title:
            # 如果是播放清單模式，我們印兩行
            # 1. 印出第一行 + 清除行尾
            print(f"{line1}\033[K") 
            # 2. 印出第二行 + 清除行尾 (不換行，準備下次被覆寫，或者用 end='' 配合游標回傳)
            print(f"{line2}\033[K")
            # 3. 將游標往上移兩行，回到第一行的開頭，準備給下一次 loop 更新
            print(f"\033[2F", end="") 
            

        else:
            # 單一影片模式，只印一行
            print(f"{line2}\033[K", end="\r")
    # elif d['status'] == 'finished':
    #     print()
    #     if playlist_title:
    #         print()
    #     print(f'下載完成，正在處理...')
    

def download_video(url: str, output_path: str,  progress_hook, resolution: str):
    ydl_opts = {
        'outtmpl': f'{output_path}.%(ext)s',
        'quiet' : True,
        'no_warnings': True,
        'noprogress': True,
        'overwrites': True,
        'format': f'bv[height<={resolution}]+ba/best',
        'noplaylist': True,
        'progress_hooks': [progress_hook],
        'merge_output_format': 'mp4',
        'js_runtimes': {'node':{},'deno':{}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
        ydl.download([url])

def download_video_playlist(url: str, output_path: str,  progress_hook):
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'quiet' : True,
        'no_warnings': True,
        'noprogress': True,
        'overwrites': True,
        'format': f'bv+ba/best',
        'progress_hooks': [progress_hook],
        'merge_output_format': 'mp4',

        'retries': 10,              # 下載失敗時自動重試 10 次 (預設只有 3 次)
        'fragment_retries': 10,     # 分片下載失敗時重試 10 次
        'ignoreerrors': True,       # 如果播放清單中某一部影片下載失敗，不要崩潰，繼續下載下一部
        'buffersize': 1024,
        'js_runtimes': {'node':{},'deno':{}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
        ydl.download([url])

def download_audio(url: str, output_path: str, progress_hook):
    ydl_opts = {
        'outtmpl': f'{output_path}.%(ext)s',
        'quiet' : True,
        'no_warnings': True,
        'noprogress': True,
        'overwrites': True,
        'format': 'bestaudio/best',
        'progress_hooks': [progress_hook],
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            
        }],
        'js_runtimes': {'node':{},'deno':{}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
        ydl.download([url])

def get_video_info(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'remote_components': ['ejs:github'],
        'js_runtimes': {'node':{},'deno':{}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
        info = ydl.extract_info(url, download=False)
    return info

def get_available_formats(info: dict):
    if info is None:
        return []
    formats = info.get('formats', [])
    if not formats:
        return []
    resolutions = set()
    for f in formats:
         if f.get('vcodec') != 'none' and f.get('height'):
            # print(f'Height: {f["height"]}, Width: {f["width"]}, Format ID: {f["format_id"]}, VCodec: {f["vcodec"]}, ACodec: {f["acodec"]}')

            resolutions.add(f['height'])
    return sorted(list(resolutions), reverse=True)

if __name__ == "__main__":
    url = 'https://youtube.com/playlist?list=PLxSscENEp7JhJi1De2SBVmkdPbKKUHZcg&si=cc_dBEDFov5udNom'
    info = get_video_info(url)
    # res = get_available_formats(info)
    # print("Available Resolutions:", res)
    # print(info['_type'])
    # print(info['entries'][0]['title'])
    download_video_playlist(url, 'C:\\Users\\arthu\\Downloads\\YT playlist test', progress_hook)
    # print(info['thumbnail'])