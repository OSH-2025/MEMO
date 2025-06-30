"""
Linux云服务器上的模型API服务
为Windows端提供LLM预测接口
"""

import os
import torch
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from peft import PeftModel
import logging
from datetime import datetime
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模型路径配置
BASE_MODEL_PATH = "/home/vipuser/llm/LLM-Research/Meta-Llama-3___1-8B-Instruct"
FINE_TUNED_MODEL_PATH = "/home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356"

app = FastAPI(title="LLM Activity Prediction API", version="1.0.0")

# 全局变量存储模型和分词器
model = None
tokenizer = None

class PredictionRequest(BaseModel):
    instruction: str
    input: str

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    timestamp: str

def load_model():
    """加载微调后的模型"""
    global model, tokenizer
    
    try:
        logger.info("开始加载基础模型...")
        # 加载基础模型
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        )
        
        logger.info("开始加载分词器...")
        # 加载分词器
        tokenizer = AutoTokenizer.from_pretrained(
            BASE_MODEL_PATH,
            use_fast=False,
            trust_remote_code=True
        )
        tokenizer.pad_token = tokenizer.eos_token
        
        logger.info("开始加载微调模型...")
        # 加载微调后的模型
        model = PeftModel.from_pretrained(base_model, FINE_TUNED_MODEL_PATH)
        model.eval()
        
        logger.info("模型加载完成!")
        return True
        
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        return False

def generate_prediction(instruction: str, input_text: str) -> Dict[str, Any]:
    """生成预测结果"""
    global model, tokenizer
    
    if model is None or tokenizer is None:
        raise HTTPException(status_code=500, detail="模型未加载")
    
    try:
        # 构建提示
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
        
        # 生成回答
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
        
        response = tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        ).strip()
        
        # 计算简单的置信度（基于响应长度和格式匹配）
        confidence = calculate_confidence(response)
        
        return {
            "prediction": response,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"生成预测时出错: {e}")
        raise HTTPException(status_code=500, detail=f"预测生成失败: {str(e)}")

def calculate_confidence(prediction: str) -> float:
    """计算预测置信度"""
    try:
        # 基于响应格式和内容计算置信度
        base_confidence = 0.5
        
        # 检查时间格式
        if "2024" in prediction and ":" in prediction:
            base_confidence += 0.2
        
        # 检查操作格式
        if any(keyword in prediction for keyword in ["启动应用", "切换到窗口", "访问网站", "访问文件"]):
            base_confidence += 0.2
        
        # 检查应用名称
        common_apps = ["chrome.exe", "notepad.exe", "explorer.exe", "code.exe", "calc.exe"]
        if any(app in prediction for app in common_apps):
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)  # 最大置信度0.95
        
    except:
        return 0.3  # 默认低置信度

@app.on_event("startup")
async def startup_event():
    """启动时加载模型"""
    logger.info("API服务启动中...")
    success = load_model()
    if not success:
        logger.error("模型加载失败，API服务可能无法正常工作")
    else:
        logger.info("API服务启动完成")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "LLM Activity Prediction API", "status": "running"}

@app.get("/health")
async def health_check():
    """健康检查"""
    model_status = "loaded" if model is not None else "not_loaded"
    return {
        "status": "healthy",
        "model_status": model_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict_activity(request: PredictionRequest):
    """预测用户活动"""
    try:
        result = generate_prediction(request.instruction, request.input)
        return PredictionResponse(**result)
    
    except Exception as e:
        logger.error(f"预测请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model_info")
async def model_info():
    """获取模型信息"""
    return {
        "base_model_path": BASE_MODEL_PATH,
        "fine_tuned_model_path": FINE_TUNED_MODEL_PATH,
        "model_loaded": model is not None,
        "tokenizer_loaded": tokenizer is not None
    }

if __name__ == "__main__":
    # 在云服务器上运行API服务
    uvicorn.run(
        app, 
        host="0.0.0.0",  # 监听所有网络接口
        port=8000,
        log_level="info"
    )