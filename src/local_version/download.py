from modelscope import snapshot_download
model_dir = snapshot_download('qwen/Qwen3-0.6B', cache_dir='./models', revision='master')
print(f"Model saved at {model_dir}")