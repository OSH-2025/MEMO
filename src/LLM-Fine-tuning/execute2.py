import os
import webbrowser
import subprocess
from datetime import datetime
import time

BUFFER_FILE = "prediction.buffer"

def read_entries():
    """读取 prediction.buffer 中的所有记录"""
    if not os.path.exists(BUFFER_FILE):
        return []
    with open(BUFFER_FILE, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file if line.strip()]

def write_entries(entries):
    """将更新后的记录写回 prediction.buffer"""
    with open(BUFFER_FILE, 'w', encoding='utf-8') as file:
        for entry in entries:
            file.write(entry + '\n')

def parse_entry(entry):
    """解析单行记录"""
    parts = entry.split(' - ')
    if len(parts) != 2:
        return None
    info, path = parts
    tag, weekday_str, time_str = info.split()
    return {
        'type': tag,
        'weekday': weekday_str,
        'time': time_str,
        'target': path.strip('"')  # 去除可能的引号
    }

def should_run_now(entry_info):
    now = datetime.now()
    current_weekday = now.strftime("%A")  # e.g., Friday
    current_time = now.strftime("%H:%M:%S")
    return current_weekday == entry_info['weekday'] and current_time == entry_info['time']

def confirm_launch(entry_info):
    target_type = "网页" if entry_info['type'] == 'urls' else "应用程序"
    return input(f"是否现在打开 {target_type}：{entry_info['target']}? (y/n): ").lower() == 'y'

def launch(entry_info):
    if entry_info['type'] == 'urls':
        webbrowser.open(entry_info['target'])
    elif entry_info['type'] == 'apps':
        try:
            subprocess.Popen(entry_info['target'])
        except Exception as e:
            print(f"无法打开应用程序: {e}")

def main():
    entries = read_entries()
    updated_entries = []

    for entry in entries:
        info = parse_entry(entry)
        if info and should_run_now(info):
            if confirm_launch(info):
                launch(info)
                updated_entries.append(entry)  # 保留未到时间或无效格式记录
                # 不加入 updated_entries，相当于“完成执行后从文件中删除”
            else:
                print("用户拒绝，删除该条记录")
                # 不加入 updated_entries，相当于“用户拒绝后从文件中删除”
        else:
            updated_entries.append(entry)  # 保留未到时间或无效格式记录

    write_entries(updated_entries)

if __name__ == "__main__":
    main()
