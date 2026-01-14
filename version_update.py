from _version import VERSION
import requests
import hashlib
import os
import sys
import asyncio
from debug import debug_print
import textwrap

class VersionUpdate:
    def __init__(self):
        self.api_url = 'https://api.github.com/repos/masterccooddee/Youtube-Downloader/releases/latest'
        self.info = {}
        self.now_version = VERSION
        self.need_update = False
        if self.fetch_latest_info():
            self.check_for_update()
        
    
    def fetch_latest_info(self):
        response = requests.get(self.api_url)
        if response.status_code == 200:
            githubinfo = response.json()
            for asset in githubinfo['assets']:
                if asset['name'].endswith('.exe'):
                    download_url = asset['browser_download_url']
                    filename = asset['name']
                    total_size = asset['size']
                    sha256_checksum = asset.get('digest')
                    if sha256_checksum:
                        sha256_checksum = sha256_checksum.split(':')[-1]
                    self.info = {
                        'tag_name': githubinfo['tag_name'],
                        'download_url': download_url,
                        'update_exe': "update_" + filename,
                        'total_size': total_size,
                        'sha256_checksum': sha256_checksum
                    }
                    break
            return True
        else:
            debug_print(f"取得失敗，狀態碼: {response.status_code}")
            return False
        
    def check_for_update(self):
        latest_version = self.info.get('tag_name', self.now_version)
        self.need_update = (latest_version != self.now_version)

    def download_latest(self, callback=None):
        if not self.need_update:
            debug_print("No update needed.")
            return True
        
        download_url = self.info['download_url']
        update_filename = self.info['update_exe']
        total_size = self.info['total_size']
        sha256_checksum = self.info['sha256_checksum']
        
        download_byte = 0
        state = "IDLE"
        try:
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(update_filename, 'wb') as f:
                    state = "DOWNLOADING"
                    for chunk in r.iter_content(chunk_size=131072):
                        f.write(chunk)
                        download_byte += len(chunk)
                        progress = (download_byte / total_size)
                        if callback:
                            callback(progress, state)
                        debug_print(f"下載進度: {progress*100:.2f}%", end='\r')
            debug_print(f"\n已下載最新版本: {update_filename}")
            if sha256_checksum:
                state = "VERIFYING"
                if callback:
                    callback(0.0, state)
                sha256 = hashlib.sha256()

                filesize = os.path.getsize(update_filename)
                verified_bytes = 0

                with open(update_filename, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                        verified_bytes += len(chunk)
                        verify_progress = verified_bytes / filesize
                        if callback:
                            callback(verify_progress, state)
                calculated_checksum = sha256.hexdigest()
                debug_print(f"計算出的 SHA256 校驗碼: {calculated_checksum}")
                if calculated_checksum.lower() == sha256_checksum.lower():
                    debug_print("SHA256 校驗成功")
                    if callback:
                        callback(1.0, "VERIFYING_SUCCESS")
                        return True
                else:
                    debug_print("SHA256 校驗失敗")
                    if callback:
                        callback(1.0, "VERIFYING_FAILED")
                    if os.path.exists(update_filename):
                        os.remove(update_filename)
                    return False # <--- [修改] 驗證失敗回傳 False
            return True
        except Exception as e:
            debug_print(f"下載或驗證失敗: {e}")
            if callback:
                callback(0.0, "ERROR")
            return False
        
    async def apply_update(self, callback=None):
        """執行更新的程式"""
        success = await asyncio.to_thread(self.download_latest, callback)
        if not success:
            debug_print("更新下載或驗證失敗，取消更新。")
            return

        if getattr(sys, 'frozen', False):
            # 如果是打包後的 exe，真正的路徑在 sys.executable
            current_exe = sys.executable
        else:
            # 如果是開發環境的 py 腳本，用 __file__ (或者 sys.argv[0])
            debug_print("警告：偵測到開發環境，跳過實際更新替換步驟。")
            debug_print(f"新版檔案已下載至：{os.path.abspath(self.info['update_exe'])}")
            debug_print("若要測試完整更新流程，請先執行 flet pack/pyinstaller 打包後再測。")
            return

        my_pid = os.getpid()
        update_exe = os.path.abspath(self.info['update_exe'])
        bat_content = textwrap.dedent(f"""
        @echo off
        chcp 65001 > nul
        setlocal
        set "PID={my_pid}"
        set "OLD_APP={current_exe}"
        set "NEW_APP={update_exe}"
        echo [Updater] 等待主程式 (PID: {my_pid}) 完全關閉...

        :LOOP
        :: 檢查 PID 是否存在 (這就是您問的那行指令)
        tasklist /FI "PID eq %PID%" 2>NUL | find /I /N "%PID%" >NUL

        :: 如果 ERRORLEVEL 是 0，代表還活著，跳轉回去繼續等
        if "%ERRORLEVEL%"=="0" (
            timeout /t 1 /nobreak >nul
            goto LOOP
        )

        echo [Updater] 主程式已關閉，開始替換檔案...

        :: 稍微緩衝一下，確保檔案鎖釋放
        timeout /t 1 /nobreak >nul

        :: 強制刪除舊版
        :DEL_LOOP
        if exist "%OLD_APP%" (
            echo 嘗試刪除舊版...
            del /f /q "%OLD_APP%"
            if exist "%OLD_APP%" (
                echo 刪除失敗，檔案可能仍被鎖定，等待 1 秒後重試...
                timeout /t 1 /nobreak >nul
                goto DEL_LOOP
            )
        )

        :: 將新下載的檔案移動過來
        echo 正在套用新版本...
        if exist "%NEW_APP%" move /y "%NEW_APP%" "%OLD_APP%"

        echo [Updater] 更新成功！正在準備重新啟動...
        echo 請稍候，正在等待系統釋放資源...

        :: 嘗試以追加模式開啟檔案，這會強迫系統檢查寫入權限
        :: 如果防毒軟體還在掃描，這裡通常會拒絕存取
        :CHECK_LOCK
        (call >> "%OLD_APP%" ) 2>nul
        if errorlevel 1 (
            echo [等待] 防毒軟體掃描中或系統緩衝未寫入...
            timeout /t 1 /nobreak >nul
            goto CHECK_LOCK
        )

        explorer.exe "%OLD_APP%"

        :: 自我刪除這個批次檔
        del "%~f0"
        """).strip()
        bat_path = os.path.join(os.path.dirname(update_exe), "update_script.bat")
        with open(bat_path, 'w', encoding='utf-8') as bat_file:
            bat_file.write(bat_content)
        
        debug_print("啟動更新程式...")
        os.startfile(bat_path)
        sys.exit(0)
