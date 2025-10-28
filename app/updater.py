import requests
import webbrowser
import tkinter as tk
from tkinter import messagebox
from packaging import version

# --- 配置 ---
# #############################################################################
# ## 重要：请将此值修改为您自己的GitHub仓库，格式为 "用户名/仓库名" ##
# #############################################################################
GITHUB_REPO = "ericzheng316/cost_analyzer"  # 例如 "johndoe/cost-analyzer"


API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def check_for_updates(current_version: str):
    """
    检查GitHub上是否有新版本，并弹窗提示用户。

    Args:
        current_version: 当前应用的版本号 (例如 "1.0.0")。
    """
    print("正在检查更新...")
    try:
        response = requests.get(API_URL, timeout=5) # 设置5秒超时
        response.raise_for_status()  # 如果请求失败 (例如 404), 则抛出异常
        
        latest_release = response.json()
        latest_version_str = latest_release['tag_name'].lstrip('v') # 去掉版本号前的 'v'
        download_url = latest_release['html_url']

        print(f"当前版本: {current_version}, 最新版本: {latest_version_str}")

        # 使用 packaging.version 来安全地比较版本号
        if version.parse(latest_version_str) > version.parse(current_version):
            print("发现新版本！准备弹窗提示用户...")
            _show_update_prompt(current_version, latest_version_str, download_url)
        else:
            print("当前已是最新版本。")

    except requests.exceptions.RequestException as e:
        print(f"检查更新失败: {e}")
    except Exception as e:
        print(f"处理更新数据时发生未知错误: {e}")

def _show_update_prompt(current_v: str, new_v: str, url: str):
    """使用Tkinter创建一个简单的弹窗来提示用户。"""
    # 创建一个隐藏的根窗口
    root = tk.Tk()
    root.withdraw()

    # 创建消息框
    title = "发现新版本"
    message = f"您当前的版本是 {current_v}，现已推出新版本 {new_v}。\n\n是否立即前往下载页面？"
    
    # askyesno 会返回 True (是) 或 False (否)
    if messagebox.askyesno(title, message):
        print("用户选择更新，正在打开下载页面...")
        webbrowser.open(url)
    else:
        print("用户选择稍后更新。")
    
    # 销毁Tkinter根窗口
    root.destroy()
