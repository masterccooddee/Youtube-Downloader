import flet as ft
import download
import asyncio
import os
import re
from windows_ProgressBar import WindowsTaskbar
import shutil
import sys
import ctypes
from _version import VERSION
from version_update import VersionUpdate
from debug import debug_print


# def toggle_console(e):
#     kernel32 = ctypes.WinDLL('kernel32')
#     user32 = ctypes.WinDLL('user32')
#     hWnd = kernel32.GetConsoleWindow()
#     global DEBUG_MODE
#     if hWnd == 0:
#         # 如果完全沒有 Console (例如打包成 no-console exe 時)，就配置一個新的
#         DEBUG_MODE = True
#         kernel32.AllocConsole()
#         # 重新導向 print 到這個新視窗
#         sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
#         sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
#         print("--- Debug Console Enabled ---")
#     else:
#         # 如果已經有 Console，就切換顯示/隱藏
#         if user32.IsWindowVisible(hWnd):
#             user32.ShowWindow(hWnd, 0) # 0 = SW_HIDE (隱藏)
#             DEBUG_MODE = False
#         else:
#             user32.ShowWindow(hWnd, 5) # 5 = SW_SHOW (顯示)
#             DEBUG_MODE = True

def main(page: ft.Page):
    
    page.title = f"YouTube 下載器 [{VERSION}]"
    page.theme_mode = ft.ThemeMode.LIGHT
    last_fetched_url = ""
    page.window.width = 900
    page.window.height = 950
    page.window.icon = "/ytdownload.ico"

    page.fonts = {
        "SourceHan": "/fonts/SourceHanSansTC-Medium.otf",
    }
    page.theme = ft.Theme(font_family="SourceHan")
    page.scroll = ft.ScrollMode.AUTO

    # check updates
    updater = VersionUpdate()

    update_container = ft.Container(content=ft.Text("是否要下載並安裝最新版本？"))
    downloading_text = ft.Text()
    downloading_progress = ft.ProgressBar(width=400, height=5, value=0.0)
    current_update_progress = 0.0
    current_update_state = "IDLE"


    async def update_clicked(e):
        update_dialog.actions.clear()
        update_dialog.update()

        update_container.content = ft.Column([
            downloading_text,
            downloading_progress
        ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # 使用 Column 包起來比較整齊
        page.update()
        asyncio.create_task(update_monitor())
        await updater.apply_update(callback=update_callback)

    async def update_monitor():
        """專門負責更新 UI 的異步迴圈"""
        FINISHED_STATES = ["ERROR", "VERIFYING_FAILED", "VERIFYING_SUCCESS"]
        while updater.need_update and current_update_state not in FINISHED_STATES:
            downloading_progress.value = current_update_progress
            match current_update_state:
                case "IDLE":
                    downloading_text.value = "準備下載最新版本..."
                case "DOWNLOADING":
                    downloading_text.value = f"下載中... {current_update_progress*100:.2f}%"
                case "VERIFYING":
                    downloading_text.value = f"驗證下載檔案中... {current_update_progress*100:.2f}%"
            downloading_progress.update()  # 單獨更新進度條
            downloading_text.update()  # 單獨更新文字
            await asyncio.sleep(0.1)  # 每 0.1 秒刷新一次 UI，避免卡死
        if current_update_state == "VERIFYING_SUCCESS":
            downloading_text.value = "更新完成，將重新啟動程式。"
            downloading_progress.value = 1.0
        elif current_update_state == "VERIFYING_FAILED":
            downloading_text.value = "更新失敗，請稍後再試。"
            downloading_progress.value = 0.0
        elif current_update_state == "ERROR":
            downloading_text.value = "更新過程中發生錯誤，請稍後再試。"
            downloading_progress.value = 0.0
        downloading_progress.update()
        downloading_text.update()

    def update_callback(progress, state):
        nonlocal current_update_progress, current_update_state
        current_update_progress = progress
        current_update_state = state

    current_ver_display = ft.Column(
        [
            ft.Text("目前版本", size=12, color=ft.Colors.GREY),
            ft.Container(
                content=ft.Text(VERSION, weight=ft.FontWeight.BOLD),
                padding=5,
                bgcolor="#E3E2E2",
                border_radius=5,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    new_ver_display = ft.Column(
        [
            ft.Text("最新版本", size=12, color=ft.Colors.GREEN),
            ft.Container(
                content=ft.Text(
                    updater.info.get('tag_name', '未知'), 
                    weight=ft.FontWeight.BOLD, 
                    color=ft.Colors.WHITE
                ),
                padding=5,
                bgcolor=ft.Colors.GREEN, # 用綠色強調新版
                border_radius=5,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    update_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color=ft.Colors.BLUE, size=28),
                    ft.Text("發現新版本！", size=20, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER, # 標題置中
            ),
            padding=ft.Padding.only(bottom=10) # 標題和下方內容的間距
        ),
        content=ft.Container(
            
            padding=ft.Padding.symmetric(vertical=10), # 增加上下內距
            content=ft.Column(
                [
                    # 版本對比區域
                    ft.Container(
                        content=ft.Row(
                            [
                                current_ver_display,
                                ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=ft.Colors.GREY_400, size=20),
                                new_ver_display,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER, # [修改] 讓箭頭垂直置中對齊版本號
                            spacing=20,
                        ),
                        bgcolor=ft.Colors.GREY_50, # 加個極淡的背景色框住版本區
                        padding=15,
                        border_radius=10,
                    ),
                    
                    ft.Divider(height=30, color=ft.Colors.TRANSPARENT), # [修改] 使用透明間距代替實線
                    
                    # 下載進度或詢問文字區域
                    update_container, 
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        actions=[
            ft.TextButton("稍後再說", on_click=lambda e: page.pop_dialog()),
            ft.TextButton("下載並安裝", on_click=update_clicked),
            ],
        alignment=ft.Alignment.CENTER,
        actions_alignment=ft.MainAxisAlignment.CENTER
    )
    
    if updater.need_update:
        page.show_dialog(update_dialog)
        
    # check dependencies
    missing_tools = []

    def check_dependencies():
        nonlocal missing_tools

        # 1. 檢查 FFmpeg (核心依賴)
        has_ffmpeg = shutil.which("ffmpeg")
        if not has_ffmpeg and not os.path.isfile("ffmpeg.exe"):
            missing_tools.append("ffmpeg")

        # 2. 檢查 JS Runtime (選用但強烈建議)
        # yt-dlp 支援 node 或 deno 來解簽名
        has_js_runtime = (
            shutil.which("deno") or shutil.which("node") or shutil.which("nodejs")
        )
        if not has_js_runtime:
            missing_tools.append("js_runtime")

        if len(missing_tools) > 0:
            return False
        return True

    def dependency_warnings(missing_tools):
        def close_warn(e):
            page.pop_dialog()

        async def set_to_clipboard(text_to_copy):
            await ft.Clipboard().set(text_to_copy)

        # 情況 A: 缺少 FFmpeg (這是紅燈，必須修)
        if "ffmpeg" in missing_tools:

            async def open_tutorial(e):
                # 這裡可以換成任何您想推薦的教學網址 (例如 GitHub Release 頁面或您的 Blog)
                url_launcher = ft.UrlLauncher()
                await url_launcher.launch_url(
                    "https://vocus.cc/article/684b6ec6fd89780001064fa8"
                )

            ffmpeg_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("⚠️ 缺少必要元件 (FFmpeg)"),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "系統偵測不到 [ffmpeg.exe]。",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.RED,
                            ),
                            ft.Divider(),
                            ft.Text("缺少此元件將導致："),
                            ft.Text("• 無法下載 1080p 以上高畫質 (僅剩 720p)"),
                            ft.Text("• 部分格式下載後會「只有畫面沒有聲音」"),
                            ft.Divider(),
                            ft.Text(
                                "【方法一：快速安裝指令】", weight=ft.FontWeight.BOLD
                            ),
                            ft.Text("請複製下方指令，在 PowerShell (管理員) 中執行："),
                            ft.Container(
                                content=ft.TextField(
                                    value="winget install Gyan.FFmpeg",
                                    read_only=True,
                                    border_color=ft.Colors.BLUE,
                                    height=50,
                                    text_size=13,
                                    suffix=ft.IconButton(
                                        ft.Icons.CONTENT_COPY,
                                        tooltip="複製到剪貼簿",
                                        on_click=lambda e: asyncio.create_task(
                                            set_to_clipboard(
                                                "winget install Gyan.FFmpeg"
                                            )
                                        ),
                                    ),
                                ),
                                margin=ft.Margin.only(bottom=10),
                            ),
                            ft.Text(
                                "安裝完成後，請務必重啟本程式。",
                                size=12,
                                color=ft.Colors.GREY,
                            ),
                            ft.Divider(),
                            ft.Text(
                                "【方法二：手動下載免安裝版】",
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text("點擊下方按鈕查看教學，下載 exe 軟體。"),
                        ],
                        tight=True,
                        spacing=5,
                    ),
                    width=450,
                ),
                actions=[
                    # [新增] 教學按鈕
                    ft.TextButton(
                        "下載/安裝教學",
                        icon=ft.Icons.HELP_OUTLINE,
                        on_click=open_tutorial,
                    ),
                    ft.TextButton("我知道風險，繼續使用", on_click=close_warn),
                ],
                actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,  # 按鈕左右分開
            )
            page.show_dialog(ffmpeg_dlg)

        # 情況 B: 缺少 JS Runtime (這是黃燈，建議修)
        if "js_runtime" in missing_tools:
            js_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("⚠️ 建議安裝 JavaScript 執行環境"),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "系統偵測不到 JavaScript 執行環境 (Node.js 或 Deno)。",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ORANGE,
                            ),
                            ft.Divider(),
                            ft.Text("缺少此元件將導致："),
                            ft.Text("• 部分影片無法下載，或下載失敗"),
                            ft.Text(
                                "• 若畫質選項無法正常顯示，請安裝此元件",
                                color=ft.Colors.RED,
                            ),
                            ft.Text("• 下載速度較慢"),
                            ft.Divider(),
                            ft.Text(
                                "建議安裝 Node.js 或 Deno，以提升下載相容性與速度。"
                            ),
                            ft.Container(height=15),
                            ft.TextField(
                                label="安裝指令(Deno)",
                                value="winget install DenoLand.Deno",
                                read_only=True,
                                border_color=ft.Colors.BLUE,
                                height=50,
                                text_size=13,
                                suffix=ft.IconButton(
                                    ft.Icons.CONTENT_COPY,
                                    tooltip="複製到剪貼簿",
                                    on_click=lambda e: asyncio.create_task(
                                        set_to_clipboard("winget install DenoLand.Deno")
                                    ),
                                ),
                            ),
                        ],
                        tight=True,
                        spacing=5,
                    ),
                    width=450,
                ),
                actions=[
                    ft.TextButton("我知道了", on_click=close_warn),
                ],
            )
            page.show_dialog(js_dlg)

    if not check_dependencies():
        dependency_warnings(missing_tools)

    current_video_info = {}
    directory_path = os.path.join(os.path.expanduser("~"), "Downloads")
    output_filename = ""

    taskbar_progress = WindowsTaskbar()

    # ///////////////////////
    # UI 元件建立區域
    # ///////////////////////

    # YouTube 連結輸入框 & loading ring
    loading_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)

    async def clear_url_action(e):
        url_input.value = ""
        url_input.update()

        await e.control.focus()  # 將焦點設回按鈕
        await asyncio.sleep(0.01)  # 確保焦點設定生效
        await url_input.focus()
        url_input.error = None

    async def paste_from_clipboard(e):
        clipboard_text = await ft.Clipboard().get()
        if not clipboard_text:
            return
        url_input.value = clipboard_text
        page.update()
        await url_input.focus()

    cross_button = ft.IconButton(
        icon=ft.Icons.CLEAR, icon_size=16, tooltip="清除", on_click=clear_url_action
    )
    paste_button = ft.IconButton(
        icon=ft.Icons.CONTENT_PASTE,
        icon_size=16,
        tooltip="貼上剪貼簿",
        on_click=paste_from_clipboard,
    )
    url_input_suffix = ft.Stack(
        controls=[loading_ring, cross_button],
        alignment=ft.Alignment.CENTER,
    )
    url_input_with_paste = ft.Row(
        controls=[url_input_suffix, paste_button],
        alignment=ft.MainAxisAlignment.END,
        spacing=0,
    )

    url_input = ft.TextField(
        label="YouTube 連結",
        width=400,
        text_size=16,
        content_padding=ft.Padding.only(left=10, right=10, top=20, bottom=8),
        suffix=ft.Container(
            content=url_input_with_paste,
            width=80,  # 給予足夠放下兩個按鈕與Loading的寬度 (約 40px * 2)
        ),
        on_change=lambda e: print(f"URL changed to: {e.control.value}"),
    )

    # 格式選擇(純audio or video)
    format_sliding = ft.CupertinoSlidingSegmentedButton(
        selected_index=0,
        controls=[ft.Text("音訊", size=16), ft.Text("影片", size=16)],
        thumb_color=ft.Colors.BLUE,
    )

    # 解析度下拉選單
    resolutions = ft.Dropdown(
        # label="可用解析度",
        hint_text="選擇解析度",
        width=200,
        height=40,
        text_size=14,
        content_padding=10,
        dense=True,
        border_color=ft.Colors.BLUE,
        disabled=True,
        on_select=lambda e: debug_print(
            f"Selected resolution: {(e.control.value).replace('p','')}"
        ),
    )

    # video info container
    video_title = ft.Text(
        value="請輸入網址...", size=16, weight=ft.FontWeight.W_700, width=320
    )
    video_img = ft.Image(
        src="/placeholder.png",
        width=320,
        height=180,
        border_radius=15,
        fit=ft.BoxFit.FIT_WIDTH,
    )
    video_details = ft.Text(value="", size=12, width=320)

    info_column = ft.Column(
        controls=[
            video_img,
            ft.Container(height=5),  # 間距
            video_title,
            video_details,
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        spacing=5,
        width=320,  # 限制這一欄的寬度
    )

    info_card = ft.Container(
        content=info_column,
        bgcolor=ft.Colors.WHITE,  # 白色背景，與底部的黃色形成對比
        padding=15,  # 內距
        border_radius=15,  # 圓角
        width=330,  # 固定寬度
        shadow=ft.BoxShadow(  # 加上一點浮起的陰影
            blur_radius=10,
            spread_radius=1,
            color=ft.Colors.BLACK_26,
            offset=ft.Offset(0, 5),
        ),
    )

    # 將格式與解析度並排，減少垂直空白
    settings_row = ft.Row(
        controls=[
            ft.Column(
                [ft.Text("格式", size=14, color=ft.Colors.GREY_700), format_sliding],
                spacing=5,
            ),
            ft.Column(
                [ft.Text("畫質", size=14, color=ft.Colors.GREY_700), resolutions],
                spacing=5,
            ),
        ],
        alignment=ft.MainAxisAlignment.START,
        spacing=40,
    )

    left_col = ft.Column(
        controls=[
            url_input,  # URL 輸入框放最上面
            loading_ring,  # loading ring 移到這裡或者跟 URL 同一行
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),  # 透明分隔線
            settings_row,  # 設定區塊
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        spacing=10,
    )

    # 更新 left_col controls
    left_col.controls = [
        ft.Text(
            "下載URL", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800
        ),
        url_input,  # 直接放輸入框即可，因為 Loading 已經在裡面了
        ft.Divider(height=30, color=ft.Colors.GREY_500),
        ft.Text(
            "下載選項",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_GREY_800,
        ),
        settings_row,
    ]

    dashboard_content = ft.Row(
        controls=[
            ft.Container(content=left_col, expand=True),  # 左側自適應填滿
            info_card,  # 右側固定寬度
        ],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.START,
        spacing=30,
    )

    # 用一個卡片包住整個上半部
    dashboard_card = ft.Container(
        content=dashboard_content,
        bgcolor="#F1F1B0",
        padding=25,
        border_radius=15,
        border=ft.Border.all(1, ft.Colors.GREY_200),
    )

    # 選擇下載目的地
    async def handle_get_directory_path(e: ft.Event[ft.Button]):
        nonlocal directory_path
        directory_path = await ft.FilePicker().get_directory_path()
        # print("Selected directory:", directory_path)
        dir_text_field.value = (
            directory_path if directory_path else dir_text_field.value
        )
        if not directory_path:
            directory_path = dir_text_field.value
        update_filename_preview()
        dir_text_field.update()

    dir_button = ft.Button(
        content="瀏覽",
        icon=ft.Icons.FOLDER_OPEN,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=5),
        ),
        on_click=handle_get_directory_path,
    )
    dir_text_field = ft.TextField(
        label="下載目錄", width=650, value=directory_path, read_only=True
    )
    dir_row = ft.Row(
        controls=[dir_text_field, dir_button],
        alignment=ft.MainAxisAlignment.START,
        spacing=15,
    )

    # 自訂輸出檔案名格式
    filename_preview = ft.Text(
        value="預覽檔名: (尚未載入影片)", color=ft.Colors.GREY_700, size=12
    )

    filename_input = ft.TextField(
        label="檔名格式",
        value="{title}",
        width=400,
        hint_text="拖拉上方標籤或手動輸入",
        text_size=14,
    )

    def update_filename_preview(e=None):
        """更新預覽文字"""
        nonlocal output_filename, directory_path
        fmt = filename_input.value
        if not current_video_info:
            filename_preview.value = "預覽檔名: (尚未載入影片)"
        elif fmt.strip() == "":
            filename_preview.value = "預覽檔名: (請輸入檔名格式)"
        else:
            safe_title = current_video_info.get("title", "Title")
            safe_duration = current_video_info.get("duration_string", "00-00")
            safe_views = str(current_video_info.get("view_count", 0))

            # 簡單取代
            preview_str = (
                fmt.replace("{title}", safe_title)
                .replace("{duration}", safe_duration)
                .replace("{views}", safe_views)
            )
            filename_preview.value = f"預覽檔名: {preview_str}"
            output_filename = os.path.join(directory_path, preview_str)
            # print(output_filename)
        if e:  # 如果是事件觸發，只更新文字
            filename_preview.update()

    filename_input.on_change = update_filename_preview

    def drag_accept(e: ft.DragTargetEvent):
        """處理拖放"""
        src = page.get_control(e.src_id)
        tag_code = src.data

        # 自動補上分隔線
        current_val = filename_input.value
        if current_val and not current_val.endswith(("-", "_", " ")):
            filename_input.value += "-" + tag_code
        else:
            filename_input.value += tag_code

        filename_input.update()
        update_filename_preview(None)  # 手動呼叫更新預覽

    # 定義標籤
    tags_data = [
        ("標題", "{title}", ft.Colors.INDIGO_100),
        ("總長", "{duration}", ft.Colors.TEAL_100),
        ("觀看數", "{views}", ft.Colors.AMBER_100),
    ]

    draggable_tags = ft.Row(
        controls=[
            ft.Draggable(
                group="filename_tags",
                content=ft.Container(
                    content=ft.Text(name, color=ft.Colors.BLACK),
                    bgcolor=color,
                    border_radius=20,  # 圓角
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),  # 內距
                    # border=ft.Border.all(2, ft.Colors.GREY_400), # 邊框
                ),
                content_feedback=ft.Chip(
                    label=ft.Text(name, color=ft.Colors.BLACK),
                    color=color,
                    padding=ft.Padding.symmetric(horizontal=1, vertical=5),
                    opacity=0.7,
                    shadow_color=ft.Colors.BLACK,
                    elevation=5,
                ),
                data=code,
            )
            for name, code, color in tags_data
        ]
    )

    filename_drag_target = ft.DragTarget(
        group="filename_tags",
        content=filename_input,
        on_accept=drag_accept,
    )

    filename_section = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "輸出檔名設定",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_GREY,
                ),
                draggable_tags,
                filename_drag_target,
                ft.Container(  # 預覽文字的美化
                    content=filename_preview,
                    bgcolor=ft.Colors.GREY_300,
                    padding=10,
                    border_radius=5,
                    width=650,  # 讓背景寬度固定
                ),
            ],
            spacing=10,
        ),
        padding=15,
        border=ft.Border.all(2, ft.Colors.GREY_300),
        border_radius=10,
    )

    # ///////////////////////
    # 進度顯示
    # ///////////////////////
    progress_bar = ft.ProgressBar(
        width=650,
        height=24,  # 加高
        value=0.0,
        color=ft.Colors.BLUE_ACCENT_700,  # 鮮豔一點的藍
        bgcolor=ft.Colors.GREY_400,
        border_radius=12,  # 圓角進度條
    )

    # 進度條內文字
    progress_text = ft.Text(
        value="IDLE",
        color=ft.Colors.WHITE,
        size=12,
    )

    # 使用 Stack 將文字疊加在進度條上
    progress_stack = ft.Stack(
        controls=[
            progress_bar,
            ft.Container(
                content=progress_text,
                alignment=ft.Alignment.CENTER,  # 讓文字在進度條範圍內置中
                width=650,  # 寬度需與進度條一致
                height=20,  # 高度需與進度條一致
            ),
        ]
    )

    def scale_animate(e: ft.HoverEvent):
        is_hovered = e.data
        c = e.control
        if e.control.disabled:
            return
        c.scale = 1.1 if is_hovered else 1.0
        c.bgcolor = ft.Colors.BLUE_600 if is_hovered else ft.Colors.BLUE
        if is_hovered:
            # 懸停時：模擬按鈕被輕微壓下或浮起，陰影變深或位置改變
            c.shadow = ft.BoxShadow(
                color=ft.Colors.BLUE_900,  # 深藍色陰影
                offset=ft.Offset(3, 6),  # 陰影向下拉長
                blur_radius=10,  # 稍微模糊一點，增加浮空感
                spread_radius=0,
            )
        else:
            # 沒懸停時：基本的立體感
            c.shadow = ft.BoxShadow(
                color=ft.Colors.BLUE_900,  # 使用深藍色模擬按鈕側面
                offset=ft.Offset(3, 4),  # 有一個固定的「厚度」在下方
                blur_radius=0,  # 不模糊，看起來像固體厚度
                spread_radius=0,
            )
        c.update()

    start_button = ft.Container(
        content=ft.Text("Download", size=16, color=ft.Colors.WHITE),
        disabled=False,
        bgcolor=ft.Colors.BLUE,
        padding=ft.Padding.symmetric(horizontal=5, vertical=10),
        border_radius=ft.BorderRadius.all(5),
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(
            color=ft.Colors.BLUE_900,  # 使用深藍色模擬按鈕側面
            offset=ft.Offset(3, 4),  # 有一個固定的「厚度」在下方
            blur_radius=0,  # 不模糊，看起來像固體厚度
            spread_radius=0,
        ),
        scale=1.0,
        animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        on_hover=scale_animate,
    )

    progress_bar_row = ft.Row(
        controls=[progress_stack, start_button],
        alignment=ft.MainAxisAlignment.START,
        spacing=15,
    )

    current_progress = 0.0
    download_status = "idle"
    current_progress_text = ""

    def progress_hook(d):

        nonlocal current_progress, download_status, current_progress_text
        if d["status"] == "downloading":

            # check what is downloading
            info = d.get("info_dict", {})
            vcodec = info.get("vcodec", "none")
            acodec = info.get("acodec", "none")

            current_type = ""
            if vcodec != "none" and acodec != "none":
                current_type = "Video+Audio"
            elif vcodec != "none" and acodec == "none":
                current_type = "Video"
            elif acodec != "none" and vcodec == "none":
                current_type = "Audio"

            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total_bytes:
                downloaded_bytes = d.get("downloaded_bytes", 0)
                percent = downloaded_bytes / total_bytes
                download_status = "downloading"
                current_progress = percent
                current_progress_text = (
                    f"{current_type} Downloading: {percent*100:.2f}%"
                )
                # 修改：印出類型
                debug_print(f"[{current_type}] Progress: {percent*100:.2f}%")
        elif d["status"] == "finished":
            download_status = "finished"
            current_progress = 1.0
            current_progress_text = "處理中..."
            debug_print()
            debug_print("下載完成，正在處理...")

    async def monitor_progress():
        """專門負責更新 UI 的異步迴圈"""
        if taskbar_progress.hwnd == 0:
            taskbar_progress.set_window_handle(page.title)

        while start_button.disabled:  # 當按鈕被禁用時(代表正在下載)持續執行
            progress_bar.value = current_progress
            progress_text.value = current_progress_text
            taskbar_progress.set_progress(current_progress * 100, 100)
            progress_bar.update()  # 單獨更新進度條
            progress_text.update()  # 單獨更新文字
            await asyncio.sleep(0.1)  # 每 0.1 秒刷新一次 UI，避免卡死

    async def download_button_clicked(e):
        nonlocal current_progress, current_progress_text
        if not current_video_info:
            url_input.error = "請先輸入有效的 YouTube 連結"
            url_input.update()
            return

        fmt = filename_input.value
        if fmt.strip() == "":
            filename_input.error = "請輸入檔名格式"
            filename_input.update()
            return

        progress_bar.value = 0.0
        current_progress = 0.0
        taskbar_progress.reset_progress()
        progress_text.value = "準備下載..."
        current_progress_text = "準備下載..."

        download_status = "idle"
        url = url_input.value.strip()
        output_path = output_filename
        debug_print(f"Path: {output_path}")
        start_button.disabled = True
        start_button.scale = 1.0
        start_button.shadow = None
        start_button.bgcolor = ft.Colors.GREY_500
        start_button.shadow = ft.BoxShadow(
            color=ft.Colors.BLACK,  # 使用深藍色模擬按鈕側面
            offset=ft.Offset(3, 4),  # 有一個固定的「厚度」在下方
            blur_radius=0,  # 不模糊，看起來像固體厚度
            spread_radius=0,
        )
        page.update()

        try:
            # 開始監控進度
            asyncio.create_task(monitor_progress())

            if format_sliding.selected_index == 0:
                # Audio
                await asyncio.to_thread(
                    download.download_audio, url, output_path, progress_hook
                )
            else:
                # Video
                await asyncio.to_thread(
                    download.download_video,
                    url,
                    output_path,
                    progress_hook,
                    (resolutions.value).replace("p", ""),
                )
        except Exception as ex:
            debug_print("下載發生錯誤:", ex)
        finally:
            start_button.disabled = False
            start_button.scale = 1.0
            start_button.shadow = ft.BoxShadow(
                color=ft.Colors.BLUE_900,  # 使用深藍色模擬按鈕側面
                offset=ft.Offset(3, 4),  # 有一個固定的「厚度」在下方
                blur_radius=0,  # 不模糊，看起來像固體厚度
                spread_radius=0,
            )
            start_button.bgcolor = ft.Colors.BLUE
            progress_text.value = "完成!!!"
            taskbar_progress.reset_progress()
            taskbar_progress.flash_window()
            page.update()

    start_button.on_click = download_button_clicked

    # Error banner
    def ok_button_clicked(e):
        page.pop_dialog()

    error_banner = ft.Banner(
        bgcolor=ft.Colors.RED_ACCENT_100,
        leading=ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
        content=None,
        actions=[ft.TextButton("OK", on_click=ok_button_clicked)],
    )

    # debug console
    # debug_col = ft.Column(
    #     controls=[
    #         ft.Container(
    #             content=ft.Text("切換 除錯主控台 (Console)"),
    #             bgcolor=ft.Colors.WHITE,
    #             on_click=toggle_console,
    #             margin=ft.Margin.only(left=10, top=0)
    #         )
    #     ],
    #     width=page.window.width,
    #     alignment=ft.MainAxisAlignment.START,
    #     horizontal_alignment=ft.CrossAxisAlignment.START,
    # )

    # ///////////////////////
    # 功能實作區域
    # ///////////////////////

    # 定義搜尋函式 (必須在 url_input 之前)
    async def search_video(e):
        nonlocal last_fetched_url

        url = url_input.value.strip()

        if loading_ring.visible:
            return

        if url == last_fetched_url:
            debug_print("URL 未變化，跳過處理")
            return  # 如果 URL 沒有變化，則不進行任何操作

        last_fetched_url = url  # 更新最後取得的 URL

        if not url:
            url_input.error = "請輸入有效的 YouTube 連結"
            page.update()
            return

        url_input.error = None

        # --- UI 更新：顯示載入狀態 ---
        cross_button.visible = False
        cross_button.disabled = True
        loading_ring.visible = True
        url_input.disabled = True
        resolutions.disabled = True
        page.update()

        # --- 定義要在背景執行的任務 ---

        try:
            # 耗時操作在這裡執行，不會卡住 UI
            info = await asyncio.to_thread(download.get_video_info, url)

            if info:

                title = info.get("title", "未知標題")
                img_url = info.get("thumbnail", "")
                duration = info.get("duration_string", "未知長度")
                views = info.get("view_count", 0)
                details = f"長度: {duration} | 觀看次數: {views:,}"

                available_resolutions = download.get_available_formats(info)
                debug_print(img_url)
                debug_print(title)
                debug_print(details)
                debug_print(available_resolutions)
                # 更新 UI 元件
                current_video_info.clear()
                current_video_info["info"] = info
                current_video_info["title"] = (
                    title.replace(":", "：").replace("/", "／").replace("\\", "-")
                )  # 避免檔名有非法字元
                current_video_info["duration_string"] = "⌛ " + duration.replace(
                    ":", "："
                )  # "duration.replace(":", "-")  # 避免檔名有冒號
                current_video_info["view_count"] = views
                update_filename_preview()  # 更新預覽文字
                video_img.src = img_url if img_url else "/placeholder.png"
                video_title.value = title
                video_details.value = details

                resolution_options = [
                    ft.DropdownOption(str(r) + "p") for r in available_resolutions
                ]
                resolutions.options = resolution_options
                resolutions.value = (
                    resolution_options[0].key if resolution_options else None
                )
                resolutions.disabled = False if resolution_options else True

            else:
                url_input.error = "找不到影片資訊"

        except Exception as ex:
            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            err_message = ansi_escape.sub("", str(ex))
            if "Unsupported URL" in err_message:
                url_input.error = "不支援的連結格式，請確認後再試"
            elif "Incomplete YouTube ID" in err_message:
                url_input.error = "無效的 YouTube 連結，請確認後再試"
            elif "[Piracy] This website is no longer supported" in err_message:
                url_input.error = "此網站已不再支援下載"
            else:
                page.pop_dialog()  # 關閉可能存在的對話框
                error_banner.content = ft.Text(f"發生錯誤: {err_message}")
                page.show_dialog(error_banner)

        finally:
            loading_ring.visible = False
            url_input.disabled = False
            cross_button.visible = True
            cross_button.disabled = False
            page.update()  # 確保畫面刷新

    # ///////////////////////
    # Bindings
    # ///////////////////////
    url_input.on_blur = search_video
    url_input.on_submit = search_video

    # ///////////////////////
    # Layout
    # ///////////////////////

    footer_col = ft.Column(
        controls=[
            ft.Text(
                "儲存位置",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_GREY,
            ),
            dir_row,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            progress_bar_row,  # 這裡保持原本的進度條+按鈕
        ],
        spacing=5,
    )

    total_col = ft.Column(
        controls=[
            dashboard_card,  # 上半部：淺灰背景儀表板
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            filename_section,  # 下載檔名設定 (原本寫好的)
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            footer_col,  # 底部：路徑與執行
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        spacing=15,  # 區塊間距
    )

    total_container = ft.Container(
        content=total_col,
        # width=1000,
        padding=30,  # 加大內部留白，讓畫面呼吸
        bgcolor=ft.Colors.WHITE,  # 確保背景是白的
        border_radius=20,  # 更大的圓角
        # 移除 border，改用 shadow
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.Colors.BLACK_26,  # 淡淡的陰影
            offset=ft.Offset(0, 5),
        ),
        margin=10,  # 留點邊界
    )

    # 設定頁面背景色，讓白卡片突顯出來
    page.bgcolor = ft.Colors.GREY_300

    page.add(total_container)


ft.run(main, assets_dir="assets")
