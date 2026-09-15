import os
from pathlib import Path

# 程序资源跟随源码；账号、日志与临时文件可放在独立的私有运行目录。
ASSET_DIR = Path(__file__).parent.resolve()
BASE_DIR = Path(os.environ.get("SAU_BASE_DIR", ASSET_DIR)).resolve()
XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = ""  # optional, e.g. C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = True  # default headless behavior for uploader/examples
DEBUG_MODE = False  # 服务端默认不等待人工调试
# Optional proxy for the YouTube uploader. Where youtube.com is blocked, direct
# connections time out and the (patchright) chromium does NOT use the system proxy.
# Point this at your local proxy port, e.g. "http://127.0.0.1:7890". None = no proxy.
YT_PROXY = None
