import subprocess
import webbrowser
import time
from datetime import datetime

# 示例调度表：星期几 + 时间(HH:MM) -> [软件列表], [网址列表]
schedule = {
    ('Thursday', '20:59'): {
        'apps': ['D:\\VSCode-win32-x64-1.99.0\\Code.exe'],
        'urls': ['github.com', 'www.runoob.com']
    }
}

# 记录已启动的任务，防止重复触发
executed = set()

def open_resources(apps, urls):
    for app in apps:
        try:
            subprocess.Popen(app)
            print(f"[{datetime.now()}] 启动应用: {app}")
        except Exception as e:
            print(f"无法启动 {app}: {e}")

    for url in urls:
        full_url = f"https://{url}" if not url.startswith("http") else url
        try:
            webbrowser.open(full_url)
            print(f"[{datetime.now()}] 打开网址: {full_url}")
        except Exception as e:
            print(f"无法打开网址 {url}: {e}")

while True:
    now = datetime.now()
    weekday = now.strftime('%A')  # Monday, Tuesday, ...
    current_time = now.strftime('%H:%M')

    key = (weekday, current_time)
    if key in schedule and key not in executed:
        task = schedule[key]
        open_resources(task.get('apps', []), task.get('urls', []))
        executed.add(key)

    time.sleep(60)  # 每分钟检查一次
