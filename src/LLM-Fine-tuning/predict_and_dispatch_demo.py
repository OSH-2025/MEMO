import os
import torch
import webbrowser
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from peft import PeftModel, PeftConfig
import re

# 映射：常用应用名 -> 可执行文件路径（请根据你的实际环境补充/修改）
APP_PATHS = {
    "微信": r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    "QQ": r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
    "Word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "Excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    # ...根据你的需求继续添加
}

def parse_activity(activity_text):
    if not activity_text:
        return None, None, None
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.+)"
    match = re.match(pattern, activity_text)
    if not match:
        return None, None, None
    timestamp = match.group(1)
    action_text = match.group(2)

    operation_type, target = None, None
    if "启动应用:" in action_text:
        operation_type = "process_start"
        app_match = re.search(r"启动应用: (.+)", action_text)
        if app_match:
            target = app_match.group(1)
    elif "关闭应用:" in action_text:
        operation_type = "process_end"
        app_match = re.search(r"关闭应用: (.+)", action_text)
        if app_match:
            target = app_match.group(1)
    elif "访问网站" in action_text:
        operation_type = "browser_history"
        website_match = re.search(r"访问网站 ([^ ]+)", action_text)
        if website_match:
            target = website_match.group(1)
    elif "访问文件:" in action_text:
        operation_type = "file_access"
        file_match = re.search(r"访问文件: (.+)", action_text)
        if file_match:
            target = file_match.group(1)
    elif "切换到窗口:" in action_text:
        operation_type = "window_focus"
        window_match = re.search(r"切换到窗口: (.+)", action_text)
        if window_match:
            target = window_match.group(1)
    elif "使用应用:" in action_text:
        operation_type = "app_usage"
        usage_match = re.search(r"使用应用: (.+)", action_text)
        if usage_match:
            target = usage_match.group(1)
    return timestamp, operation_type, target

def generate_prediction(model, tokenizer, instruction, input_text):
    system_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "Cutting Knowledge Date: December 2023\n"
        "Today Date: 26 Jul 2024\n\n"
        "你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。请确保输出格式与输入格式一致，应为\"时间 - 操作\"的形式。\n"
        "<|eot_id|>"
    )
    user_prompt = (
        "<|start_header_id|>user<|end_header_id|>\n\n"
        f"{instruction}\n{input_text}"
        "<|eot_id|>"
    )
    assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
    prompt = system_prompt + user_prompt + assistant_prompt
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    generation_config = GenerationConfig(
        max_new_tokens=100,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id
    )
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            generation_config=generation_config
        )
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return response

def preload_app(app_name):
    exe_path = APP_PATHS.get(app_name)
    if exe_path and os.path.exists(exe_path):
        os.startfile(exe_path)
        print(f"已启动应用: {app_name}")
    else:
        print(f"未找到应用 [{app_name}] 的路径，请完善 APP_PATHS")

def preload_website(url):
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    print(f"已打开网页: {url}")

def demo_dispatch(predicted_text):
    ts, op_type, target = parse_activity(predicted_text)
    print(f"\n【预测结果】：{predicted_text}")
    print(f"解析 - 时间: {ts}, 操作类型: {op_type}, 目标: {target}")
    if op_type == "process_start" and target:
        print("准备启动应用...")
        preload_app(target)
    elif op_type == "browser_history" and target:
        print("准备打开网页...")
        preload_website(target)
    else:
        print(f"暂不支持该类型调度: {op_type}, 目标: {target}")

if __name__ == "__main__":
    # 加载微调后的模型和tokenizer（注意路径！）
    model = AutoModelForCausalLM.from_pretrained(
        './LLM-Research/Meta-Llama-3___1-8B-Instruct',
        device_map="auto",
        torch_dtype=torch.bfloat16
    )
    tokenizer = AutoTokenizer.from_pretrained(
        './LLM-Research/Meta-Llama-3___1-8B-Instruct',
        use_fast=False,
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token

    # === DEMO交互区 ===
    print("\n==== 用户行为预测Demo ====\n")
    instruction = "请根据下列用户最近操作，预测下一个最有可能的用户活动。"
    # 手动输入历史活动
    print("请输入用户最近的操作序列(可多行，回车后Ctrl+Z结束)：")
    print("（例如：\n2024-07-26 09:59:12 - 启动应用: 微信\n2024-07-26 09:59:40 - 访问网站 baidu.com\n）")
    print("输入历史序列：")
    input_lines = []
    try:
        while True:
            line = input()
            if line.strip() == '': break
            input_lines.append(line)
    except EOFError:
        pass
    input_text = '\n'.join(input_lines)

    print("\n正在预测...")
    pred = generate_prediction(model, tokenizer, instruction, input_text)
    demo_dispatch(pred)