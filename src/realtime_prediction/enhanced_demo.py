#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版演示模式 - 完整的预测-执行-验证循环
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from client_server_architecture import (
    ActivityData, PredictionRequest, PredictionResponse,
    ClientConfig, logger
)
from prediction_executor import PredictionExecutor, PredictionValidator
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class EnhancedDemo:
    """增强版演示系统"""
    
    def __init__(self):
        self.config = ClientConfig()
        
        # 创建预测执行器（预览模式，不实际执行）
        self.executor = PredictionExecutor(enable_auto_execution=False)
        self.validator = PredictionValidator()
        
        # 模拟服务器预测结果
        self.demo_predictions = [
            "2025-06-28 18:00:15 - 访问网站 github.com 的页面 'MEMO/README.md at main · OSH-2025/MEMO'",
            "2025-06-28 18:01:30 - 访问网站 www.douban.com 的页面 '电影推荐'",
            "2025-06-28 18:02:45 - 切换到应用 Code.exe - 'windows_client.py - Visual Studio Code'",
            "2025-06-28 18:03:20 - 访问网站 github.com 的页面 'datawhalechina/self-llm'",
            "2025-06-28 18:04:10 - 打开应用 chrome.exe"
        ]
        
        # 模拟用户实际活动（用于验证）
        self.actual_activities = [
            {
                'type': 'website',
                'domain': 'github.com',
                'title': 'MEMO Project',
                'timestamp': datetime.now() + timedelta(seconds=10)
            },
            {
                'type': 'website', 
                'domain': 'www.douban.com',
                'title': '电影推荐页面',
                'timestamp': datetime.now() + timedelta(seconds=25)
            },
            {
                'type': 'application',
                'process_name': 'Code.exe',
                'window_title': 'VSCode',
                'timestamp': datetime.now() + timedelta(seconds=40)
            }
        ]
        
        self.demo_step = 0
        
    async def run_interactive_demo(self):
        """运行交互式演示"""
        print("="*60)
        print("🎭 增强版活动预测演示系统")
        print("="*60)
        print()
        print("本演示将展示完整的预测-执行-验证循环：")
        print("1. 📝 模拟用户活动数据")
        print("2. 🤖 LLM预测下一个活动")
        print("3. 🔍 解析预测结果")
        print("4. ⏰ 调度预测执行")
        print("5. 📊 验证预测准确性")
        print()
        
        input("按回车开始演示...")
        
        # 第一步：显示预测能力
        await self._demo_prediction_parsing()
        
        # 第二步：演示预测调度
        await self._demo_prediction_scheduling()
        
        # 第三步：演示准确性验证
        await self._demo_accuracy_validation()
        
        # 第四步：显示统计信息
        await self._demo_statistics()
        
        print("\n🎉 演示完成！")
        
    async def _demo_prediction_parsing(self):
        """演示预测解析功能"""
        print("\n" + "="*40)
        print("📋 第一部分：预测解析演示")
        print("="*40)
        
        for i, prediction_text in enumerate(self.demo_predictions, 1):
            print(f"\n🔮 预测 {i}: {prediction_text}")
            
            # 解析预测
            parsed = self.executor.parse_prediction(prediction_text)
            
            if parsed:
                print(f"✅ 解析成功:")
                print(f"   📱 类型: {parsed['type']}")
                
                if parsed['type'] == 'website':
                    print(f"   🌐 网站: {parsed['domain']}")
                    print(f"   📄 页面: {parsed.get('page_title', '未指定')}")
                    print(f"   🔗 URL: {parsed['url']}")
                elif parsed['type'] == 'application':
                    print(f"   💻 应用: {parsed['app_name']}")
                    print(f"   🖼️ 窗口: {parsed.get('window_title', '未指定')}")
                
                print(f"   📊 置信度: {parsed['confidence']:.1%}")
                
                # 添加到验证队列
                self.validator.add_prediction_for_validation(parsed, 60)
            else:
                print("❌ 解析失败")
            
            time.sleep(1)  # 演示间隔
        
        input("\n按回车继续...")
        
    async def _demo_prediction_scheduling(self):
        """演示预测调度功能"""
        print("\n" + "="*40)
        print("⏰ 第二部分：预测调度演示")
        print("="*40)
        
        print("\n🎯 预测调度策略:")
        print("- 高置信度预测：立即执行")
        print("- 中等置信度：延迟5秒执行") 
        print("- 低置信度：仅预览，不执行")
        print()
        
        for prediction_text in self.demo_predictions[:3]:
            parsed = self.executor.parse_prediction(prediction_text)
            
            if parsed:
                confidence = parsed['confidence']
                
                print(f"\n🔮 处理预测: {parsed['type']} - 置信度: {confidence:.1%}")
                
                if confidence >= 0.8:
                    print("✅ 高置信度 - 立即执行")
                    if input("是否实际执行此预测？(y/n): ").lower() == 'y':
                        # 启用实际执行
                        real_executor = PredictionExecutor(enable_auto_execution=True)
                        real_executor.schedule_execution(parsed, delay_seconds=0)
                        print("🚀 预测已执行！")
                    else:
                        print("🔍 预览模式 - 已跳过实际执行")
                        
                elif confidence >= 0.6:
                    print("⏳ 中等置信度 - 延迟执行")
                    delay = 5
                    if input(f"是否调度 {delay} 秒后执行？(y/n): ").lower() == 'y':
                        print(f"⏰ 已调度 {delay} 秒后执行")
                        # 这里只是演示，不实际执行
                    else:
                        print("🔍 预览模式 - 已跳过调度")
                else:
                    print("🔍 低置信度 - 仅预览")
                    self.executor.preview_prediction(prediction_text)
        
        input("\n按回车继续...")
        
    async def _demo_accuracy_validation(self):
        """演示准确性验证"""
        print("\n" + "="*40)
        print("📊 第三部分：准确性验证演示")  
        print("="*40)
        
        print("\n🎯 验证策略:")
        print("- 监控用户实际活动")
        print("- 与预测结果进行匹配")
        print("- 计算预测准确度")
        print("- 更新模型反馈")
        print()
        
        # 模拟实际活动发生
        for i, actual_activity in enumerate(self.actual_activities, 1):
            print(f"\n👤 模拟用户实际活动 {i}:")
            print(f"   类型: {actual_activity['type']}")
            
            if actual_activity['type'] == 'website':
                print(f"   网站: {actual_activity['domain']}")
                print(f"   页面: {actual_activity['title']}")
            elif actual_activity['type'] == 'application':
                print(f"   应用: {actual_activity['process_name']}")
                print(f"   窗口: {actual_activity['window_title']}")
            
            # 验证预测
            self.validator.validate_with_actual_activity(actual_activity)
            
            time.sleep(1)
        
        input("\n按回车查看验证结果...")
        
    async def _demo_statistics(self):
        """显示统计信息"""
        print("\n" + "="*40)
        print("📈 第四部分：统计信息汇总")
        print("="*40)
        
        # 执行器统计
        exec_stats = self.executor.get_execution_stats()
        print(f"\n🎯 执行器统计:")
        print(f"   总执行次数: {exec_stats['total_executions']}")
        print(f"   成功执行次数: {exec_stats['successful_executions']}")
        print(f"   成功率: {exec_stats['success_rate']:.1%}")
        print(f"   待执行预测: {exec_stats['pending_executions']}")
        
        # 验证器统计
        val_stats = self.validator.get_validation_stats()
        print(f"\n📊 验证器统计:")
        print(f"   总验证次数: {val_stats['total_validations']}")
        print(f"   平均准确度: {val_stats['average_accuracy']:.1%}")
        print(f"   待验证预测: {val_stats['pending_validations']}")
        
        # 最近验证结果
        if val_stats['recent_validations']:
            print(f"\n🔍 最近验证结果:")
            for validation in val_stats['recent_validations']:
                print(f"   预测: {validation['prediction']['type']} - 准确度: {validation['accuracy']:.1%}")
        
        print(f"\n💡 系统建议:")
        avg_accuracy = val_stats['average_accuracy']
        
        if avg_accuracy >= 0.8:
            print("   🟢 预测准确度优秀，可以启用自动执行")
        elif avg_accuracy >= 0.6:
            print("   🟡 预测准确度良好，建议延迟执行")
        elif avg_accuracy >= 0.4:
            print("   🟠 预测准确度一般，建议仅预览")
        else:
            print("   🔴 预测准确度较低，需要重新训练模型")
        
    async def run_quick_demo(self):
        """快速演示模式"""
        print("🚀 快速演示模式")
        print("-" * 30)
        
        # 展示预测解析
        sample_prediction = self.demo_predictions[0]
        print(f"\n🔮 示例预测: {sample_prediction}")
        
        parsed = self.executor.parse_prediction(sample_prediction)
        if parsed:
            print(f"✅ 解析结果: {parsed}")
            
            # 询问是否执行
            choice = input("\n是否实际执行此预测？(y/n): ").lower()
            
            if choice == 'y':
                real_executor = PredictionExecutor(enable_auto_execution=True)
                real_executor.schedule_execution(parsed)
                print("🚀 预测已执行！检查您的浏览器是否打开了相应页面。")
            else:
                print("🔍 预览模式 - 已跳过实际执行")
        
        print(f"\n📊 演示完成！")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="增强版预测演示")
    parser.add_argument("--quick", "-q", action="store_true", help="快速演示模式")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式演示模式")
    
    args = parser.parse_args()
    
    demo = EnhancedDemo()
    
    if args.quick:
        await demo.run_quick_demo()
    elif args.interactive:
        await demo.run_interactive_demo()
    else:
        print("🎭 增强版预测演示系统")
        print("=" * 40)
        print()
        print("选择演示模式:")
        print("1. 快速演示 (简单展示)")
        print("2. 交互式演示 (完整体验)")
        print()
        
        choice = input("请选择 (1-2): ")
        
        if choice == "1":
            await demo.run_quick_demo()
        elif choice == "2":
            await demo.run_interactive_demo()
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    asyncio.run(main()) 