import subprocess
import itertools
import json
import os
import time

# 显卡资源
GPU_MEM_GB = 24  # 4090 24G
MEM_HEADROOM_GB = 2  # 预留部分显存防止爆掉
MAX_USE_GB = GPU_MEM_GB - MEM_HEADROOM_GB

# 搜索空间
batch_sizes = [2, 1]  # 优先尝试大，再降小
max_lengths = [512]
learning_rates = [2e-4, 1e-4]
lora_rs = [8, 4]
lora_alphas = [32]
lora_dropouts = [0.1]
grad_steps = [4, 8]

# 允许最大重试次数（遇到OOM自动降配最多几次）
MAX_RETRIES = 2

# 结果记录
result_file = "grid_search_results.jsonl"

# 主程序路径
TRAIN_SCRIPT = "train.py"  # 改成你的主程序实际文件名

def run_one_trial(params):
    cmd = [
        "python", TRAIN_SCRIPT,
        "--per_device_train_batch_size", str(params['batch_size']),
        "--per_device_eval_batch_size", str(params['batch_size']),
        "--max_length", str(params['max_length']),
        "--learning_rate", str(params['learning_rate']),
        "--lora_r", str(params['lora_r']),
        "--lora_alpha", str(params['lora_alpha']),
        "--lora_dropout", str(params['lora_dropout']),
        "--gradient_accumulation_steps", str(params['grad_steps']),
        "--num_train_epochs", "3",
        "--output_dir", params['output_dir'],
    ]
    my_env = os.environ.copy()
    my_env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    log_file = os.path.join(params['output_dir'], "train.log")
    os.makedirs(params['output_dir'], exist_ok=True)

    print(f"\n==== Running: {cmd} ====")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=my_env, timeout=36000)
        output = result.stdout + "\n" + result.stderr
        with open(log_file, "w") as f:
            f.write(output)
        if "CUDA out of memory" in output or "torch.OutOfMemoryError" in output:
            return "OOM", output
        acc = None
        for line in output.splitlines():
            if "验证集预测准确率:" in line:
                try:
                    acc = float(line.strip().split(":")[-1])
                except Exception as e:
                    print(f"准确率解析异常: {e}")
        return acc, output
    except subprocess.TimeoutExpired:
        with open(log_file, "a") as f:
            f.write("\nTimeout Exception\n")
        return "TIMEOUT", "Timeout"
    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"\nException: {str(e)}\n")
        return "ERROR", str(e)

def main():
    # 搜索所有超参数组合
    search_space = list(itertools.product(
        batch_sizes,
        max_lengths,
        learning_rates,
        lora_rs,
        lora_alphas,
        lora_dropouts,
        grad_steps
    ))

    tried = set()
    if os.path.exists(result_file):
        with open(result_file) as f:
            for line in f:
                record = json.loads(line)
                param_tuple = tuple(sorted(record['params'].items()))
                tried.add(param_tuple)

    for idx, combo in enumerate(search_space):
        params = {
            'batch_size': combo[0],
            'max_length': combo[1],
            'learning_rate': combo[2],
            'lora_r': combo[3],
            'lora_alpha': combo[4],
            'lora_dropout': combo[5],
            'grad_steps': combo[6],
            'output_dir': f"output/gs_bs{combo[0]}_ml{combo[1]}_lr{combo[2]}_r{combo[3]}_a{combo[4]}_d{combo[5]}_gs{combo[6]}"
        }
        param_tuple = tuple(sorted(params.items()))
        if param_tuple in tried:
            print(f"跳过已尝试配置: {params}")
            continue

        # 每个组合允许降配重试
        success = False
        cur_params = params.copy()
        for retry in range(MAX_RETRIES+1):
            acc, output = run_one_trial(cur_params)
            if acc == "OOM":
                print(f"OOM! batch_size={cur_params['batch_size']}, max_length={cur_params['max_length']}")
                # 优先降batch_size，再降max_length
                if cur_params['batch_size'] > 1:
                    cur_params['batch_size'] -= 1
                elif cur_params['max_length'] > 128:
                    new_len = 128
                    for ml in sorted(max_lengths):
                        if ml < cur_params['max_length']:
                            new_len = ml
                            break
                    cur_params['max_length'] = new_len
                else:
                    print("已降到最小 batch/max_length，跳过")
                    break
            elif acc == "TIMEOUT":
                print("超时，跳过")
                break
            elif acc == "ERROR":
                print("未知错误，跳过")
                break
            else:
                # 成功
                record = {
                    "params": cur_params,
                    "accuracy": acc,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                with open(result_file, "a") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"完成: {cur_params} 准确率: {acc}")
                success = True
                break

        if not success:
            # 记录失败的信息
            record = {
                "params": cur_params,
                "accuracy": None,
                "fail_reason": output,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(result_file, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()