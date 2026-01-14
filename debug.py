DEBUG_MODE = False

def debug_print(*args, **kwargs):
    """除錯用印出函式"""
    if DEBUG_MODE:
        print("[DEBUG]:", *args, **kwargs)