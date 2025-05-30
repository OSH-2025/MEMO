# Hi, this is MEMO📝

我们是备忘录小组，这个朴实的名字源于我们的初衷：基于模型预测的内存管理优化

Team members (排名不分先后)

* 于宛扬 
* 杨玺禾
* 韩思琦
* 贾钰珩

## 项目进度🎯

| 阶段     | 时间      | 进展                                                         | 分工                                                         |
| -------- | --------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 选题     | 3.5 - 3.8 | 自行探索/咨询前辈，确定了一些ai+OS的方向<br />1. 通过模型预测优化内存管理/资源调度<br />2. 多任务环境下基于ML的进程调度器<br />3. OS控制台的自动预测代码补全 | 无明确分工                                                   |
| 初步调研 | 3.9       | **第一次会议(线上)** 确定课题方向为用ai优化内存管理，搭建MEMO homepage，讨论了接下来的任务<br />1. 不同linux版本的内存管理机制（what & why）<br/>2. 优化思路<br/>3. 可行性考察<br/> | 所有人：来做1<br />下周三之前开始推进2、3                  |
| 初步调研 | 3.12      | 初步学习了OS内存管理相关知识，但对于技术优化一头雾水，课后咨询老师，建议（1） 用vllm部署模型，（2）并参考github上vllm相关项目、结合大模型 $`*`$ 快速上手<br /> $`*`$: *选择可信度较高的top5大模型，不能尽信，利用它们输出的思路和参考资料* | 配置并学习vllm，根据建议搜集文献和github案例                 |
| 初步调研 | 3.20      | **第二次会议(线下)** 集中讨论并解决vllm安装及使用中的问题，争辩以下问题<br />1. 为了【更高效部署大模型】而优化OS资源调度的研究更多<br />侧面说明**模型原生操作系统** 还 *为时尚早* ？我们是否也转向对vllm这类模型OS的优化？<br />2.  大模型与OS的交互 具体如何设计<br />获得OS系统级/进程级的内存信息？两者的区别以及与模型的适配<br /> | 本次周中会议没有讨论完，大家继续搜集文献和github案例         |
| 初步调研 | 3.22      | **第三次会议(线下)** <br />首先要明确思路1 2的区别并做出选择<br />1. Ai for OS<br />2. OS for Ai<br />咨询了LLM领域的研究生学长，他首先讲解了KVCache目前面对的问题, 综合考虑下我们决定放弃思路2；对于我们的思路1，他提出**目前大模型的时延决定了只能做（相对于纳秒级别的内存操作）粗粒度的决策**。之后我们在讨论中提出了下面两种发展方向，主要挑战在于**工作量和算力** <br />i. 舍弃一些功能，做成垂直领域专长的小模型<br />ii. 匹配一个粗粒度资源分配的情景(本质还是对用户的行为预测，参考Android系统的swap机制），比如文件访问操作 | 可行性报告的分工<br />于宛扬：技术背景-OS内存管理/量化技术/(基于ML)优化<br />杨玺禾：需求分析(硬件/软件/数据) <br />韩思琦: 技术背景-LLM原理/训练/优化/与OS的整合<br />贾钰珩：可操作性/经济可行性/风险分析 <br />|
| 调研报告 | 3.27      | **第四次会议(线下)**<br />集中研读了往届作业的github，分析和我们课题的关系、以及可以学习利用的部分<br />拟定了调研报告的框架、主体部分的分工，讨论写作时要注意的问题 $`*`$，并采用USTC Latex协作<br /> | **调研报告主体**分工<br />贾钰珩： 1.1 Linux 系统的内存管理<br/>韩思琦： 1.2 LLM及部署<br/>杨玺禾： 2.1 利用LLM优化Linux内存管理<br/>于宛扬： 2.2 LLM与OS的交互 |
| 调研报告 | 3.31 | **第五次会议(线下)**<br />根据本周一上课时老师对其他小组报告的点评和建议，以及周末调研的成果，确认接下来的任务是继续完善调研报告，之后研讨以对齐认知。<br />调整了内容顺序( 2.1 和 2.2 对调）和详略（压缩1.2对KVCache的阐述，增设1.3 LSTM（长短期记忆）预测算法）<br /> | **调研报告主体**分工<br />贾钰珩： 1.1，1.3，深度学习算法的数学原理<br/>韩思琦： 1.2 ，深度学习算法的数学原理<br/>杨玺禾： 2.1，相关工作，前瞻性<br/>于宛扬： 2.1，相关工作 |
| 可行性报告 | 4.3 | **第六次会议(线下)**<br />从头梳理了调研报告的内容（*一些Typo还未修正*），轮流分享调研结果，本次会议主要成果：<br />1. 研讨论文疑难杂点。韩思琦概述了深度学习算法的脉络和方法，贾钰珩讲解RNN（递归神经网络）、LSTM的设计和流程，大家一起讨论了Precision, Recall, F1等评价指标。<br />2. 调研成果对接。杨玺禾调研的【应用预测】文献中提到从电脑抓取的上下文缺乏语义信息，但于宛扬调研的【AIOS】中已经开发并集成了LLM-based语义文件系统，动摇了这一局限性，可行性大大提高。 | 所有人：阅读2024年的可行性报告，梳理框架 |
| 可行性报告 | 4.6-4.10 | QQ群内完成：可行性报告及实践分工<br />于宛扬：构建数据集， AIOS在windows+ollama部署 <br />杨玺禾：AIOS在linux+vllm的部署，LSFS的扩展<br />韩思琦：AIOS在windows+API部署，深度学习相关技术<br />贾钰珩：模型训练相关技术 | 【备注】经历了一些动态调整，左侧是最终分工 |
| 可行性报告 | 4.10 | **第七次会议(线下)**<br />集中研讨并解决了AIOS部署和LSFS实操的问题（ *TODO：AIOS的官方文档写的过于简略，遇到的问题和解决方案可以整理在手册中供后来者参考* ）<br />讨论已经完成的数据集部分报告，就首要问题达成一致：扩展LSFS，至少需要支持可执行文件和操作。 |  |
| 中期汇报 | 4.17-4.22 | 4.17 **第八次会议(线上)**<br />中期汇报分工，准备讲稿及对应PPT<br />4.22 **第九次会议(线下)**<br />讨论4.21周一其他小组的汇报，整理AI+OS相关建议，新增调研任务：检索增强生成(RAG)，并入课题思路；<br />组内汇报，并整合PPT<br /> | 中期汇报<br />韩思琦：研究背景<br />于宛扬：可行性研究/数据集<br />杨玺禾：可行性研究/LSFS扩展<br />贾钰珩：课题框架梳理，继续调研大模型训练技术 |
| 中期调研 | 4.23 | 汇报完成🙌✨ 整理老师和同学们的建议，规划下一部调研：<br />1. 学习**大模型微调** 【优先选择微调，RAG次之】<br />2. 学习数据集构建 | 调研<br />韩思琦：大模型微调<br />贾钰珩：数据收集和处理 |
| 实践🚩<br />五月需要取得初步成果 | 5.2-5.8 | **第10次会议(线上)** <br />韩思琦根据调研成果，讲解微调技术并复现甄嬛传agent，提出问题：由于缺少物理GPU，部分库无法调用; 贾钰珩讲解主要的系统审计方法。<br/>分工如右侧<br />**第11次会议(线上)**<br /> *请假：贾钰珩(赴京考试)*<br />讨论五一期间的学习成果，试运行用户程序获取和数据分析的python脚本 | 韩思琦：整理调研结果上传github<br/>贾钰珩：复现子系统审计主系统脚本<br/>杨玺禾：云GPU环境配置<br/>于宛扬：处理进程记录为数据集的格式、程序 |
| 🚩数据收集与处理 | 5.9-5.22 | **第12次会议(线下)**<br />修改数据收集脚本，处理其中输出重复、无意义（系统自动调用etc.）、错误（直接读取网页历史导致etc.）的bug，调整数据分析脚本的键值对，生成信息更丰富的数据集 <br/>**第13次会议(线下)**<br />数据收集和分析的脚本定型，在云主机上尝试用不同的模型进行微调 | |
| 🚩大模型微调 | 5.23-5.29 | **第14次会议(线下)**<br />基于组员三人（周三，共计10+h）的数据集lora微调模型 `Meta-Llama-3___1-8B-Instruct` ，输出用户的**下一个操作及准确时间**，准确率可达33%，随数据量增加而提高；<br />根据llm输出的利用python实现了一个简单的程序调用脚本，成功打开了预测的网页<br />当前问题：1. 由于总体数据量偏低（十几分钟即完成微调），无法分辨出用户数目的增加与预测准确率的关系 2. 下一步考虑大模型调用系统API，即将llm与程序调用脚本连接起来，之后再逐步实现 实时监测与调控用户操作 3. 微调0.5B小模型，探索本地运行可行性 | 所有人：继续收集数据<br />韩思琦：1<br/>贾钰珩：3<br/>杨玺禾：2<br/>于宛扬：2 |
|  |  |  |  |
|  |  |  |  |
| 🌑期末汇报 | 7月初 | 敬请期待 |  |
