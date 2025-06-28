from datetime import datetime
import time
import threading
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button

BUFFER_FILE = "prediction_buffer.csv"
user_choice_event = threading.Event()
task_to_prompt = None
user_choice_result = None

# ========== 文件读取与任务判断 ==========
def read_entries():
    if not os.path.exists(BUFFER_FILE):
        return []
    try:
        with open(BUFFER_FILE, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(f"[错误] 读取失败: {e}")
        return []

def write_entries(entries):
    with open(BUFFER_FILE, 'w', encoding='utf-8') as file:
        for entry in entries:
            file.write(entry + '\n')

def parse_entry(entry):
    parts = entry.split(' - ')
    if len(parts) != 2:
        return None
    try:
        tag, weekday_str, time_str = parts[0].split()
        return {
            'type': tag,
            'weekday': weekday_str,
            'time': time_str,
            'target': parts[1].strip('"')
        }
    except ValueError:
        return None

def should_run_now(entry_info):
    now = datetime.now()
    return (now.strftime("%A") == entry_info['weekday']
            and now.strftime("%H:%M:%S") == entry_info['time'])

# ========== GUI 弹窗 ==========
def on_yes(event):
    global user_choice_result
    user_choice_result = 'yes'
    user_choice_event.set()
    plt.close()

def on_no(event):
    global user_choice_result
    user_choice_result = 'no'
    user_choice_event.set()
    plt.close()

def prompt_with_buttons_gui(title_text):
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.canvas.manager.set_window_title("Task Confirmation")
    ax.set_axis_off()

    # 背景图案
    x = np.linspace(0, 10, 400)
    y = np.sin(x * 2) * 0.5 + 0.5
    bg = np.outer(np.ones_like(y), y)
    ax.imshow(bg, extent=[0, 1, 0, 1], aspect='auto', cmap='plasma', alpha=0.4)

    ax.text(0.5, 0.75, title_text, fontsize=14, ha='center', va='center', weight='bold', color='navy', wrap=True)

    ax_yes = plt.axes([0.25, 0.2, 0.2, 0.15])
    ax_no = plt.axes([0.55, 0.2, 0.2, 0.15])
    b_yes = Button(ax_yes, 'yes', color='lightgreen', hovercolor='green')
    b_no = Button(ax_no, 'no', color='lightcoral', hovercolor='red')

    b_yes.on_clicked(on_yes)
    b_no.on_clicked(on_no)

    plt.show()

# ========== 子线程检查任务 ==========
def run_scheduler():
    global task_to_prompt
    while True:
        entries = read_entries()
        updated_entries = []
        for entry in entries:
            info = parse_entry(entry)
            if info and should_run_now(info):
                task_to_prompt = info
                user_choice_event.clear()
                while not user_choice_event.is_set():
                    time.sleep(0.1)
                if user_choice_result == 'yes':
                    launch(info)
                    updated_entries.append(entry)
                else:
                    print("用户拒绝任务")
            else:
                updated_entries.append(entry)
        write_entries(updated_entries)
        time.sleep(1)

def launch(info):
    if info['type'] == 'urls':
        webbrowser.open(info['target'])
    elif info['type'] == 'apps':
        try:
            subprocess.Popen(info['target'])
        except Exception as e:
            print(f"无法打开应用程序: {e}")

# ========== 主线程 GUI 驱动 ==========
def gui_loop():
    global task_to_prompt
    while True:
        if task_to_prompt:
            info = task_to_prompt
            msg = f"Do you want to open {'webpage' if info['type'] == 'urls' else 'application'}:\n{info['target']}?"
            prompt_with_buttons_gui(msg)
            task_to_prompt = None
        else:
            time.sleep(0.1)

# ========== 启动 ==========
def main():
    print("🎯 启动成功，任务轮询中...")
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True
    thread.start()
    gui_loop()

if __name__ == "__main__":
    main()
