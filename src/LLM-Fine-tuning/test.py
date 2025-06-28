from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from peft import PeftModel

mode_path = '/home/vipuser/llm/LLM-Research'
lora_path = '/home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356' # 换成你自己的路径

# 加载tokenizer
tokenizer = AutoTokenizer.from_pretrained(mode_path, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# 加载模型
model = AutoModelForCausalLM.from_pretrained(
    mode_path, 
    device_map="auto",
    torch_dtype=torch.bfloat16,
    trust_remote_code=True
).eval()

# 加载lora权重
model = PeftModel.from_pretrained(model, model_id=lora_path)

# 构造与训练一致的prompt
system_prompt = (
    "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
    "你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。输出格式类似\"2025-05-22 08:30:38 - 访问网站 github.com 的页面 'README.md at main · OSH-2025/MEMO'\"，注意这里的网页或应用只考虑已知确定的网页和应用。\n"
    "<|eot_id|>"
)

user_prompt = (
    "<|start_header_id|>user<|end_header_id|>\n\n"
    "根据用户之前的活动序列，预测下一个可能的活动。\n"
    "用户活动序列:\n"
    "2025-05-22 08:06:33 - 访问网站 www.douban.com 的页面 '【盘个剧本押个C】【Game of Thrones】1st episode 《All men must die》'\n"
    "2025-05-22 08:30:07 - 访问网站 github.com 的页面 'self-llm/examples/AMchat-高等数学 at master · datawhalechina/self-llm'\n"
    "2025-05-22 08:30:17 - 访问网站 github.com 的页面 'MEMO/feasibility_report/Fine-tuning of LLM.md at main · OSH-2025/MEMO'\n"
    "2025-05-22 08:30:34 - 访问网站 github.com 的页面 'MEMO/src at main · OSH-2025/MEMO'\n"
    "<|eot_id|>"
)

assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"

full_prompt = system_prompt + user_prompt + assistant_prompt

# 转token id
inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

# 生成
with torch.no_grad():
    generated_ids = model.generate(
        input_ids=inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=128,
        temperature=0.7,
        do_sample=True,
        top_p=0.95,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id
    )

# 解码，仅取新生成的部分
response = tokenizer.decode(generated_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

print("用户活动序列：")
print(user_prompt)
print("\n模型预测的下一个活动：")
print(response.strip())