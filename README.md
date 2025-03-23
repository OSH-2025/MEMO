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
| 初步调研 | 3.9       | **第一次会议(线上)** 确定课题方向为用ai优化内存管理，搭建MEMO homepage，讨论了接下来的任务<br />1. 不同linux版本的内存管理机制（what & why）<br/>2. 优化思路<br/>3. 可行性考察<br/> | 都来做1，下周三之前开始推进2、3                              |
| 初步调研 | 3.12      | 初步学习了OS内存管理相关知识，但对于技术优化一头雾水，课后咨询老师，建议（1） 用vllm部署模型，（2）并参考github上vllm相关项目、结合大模型 $`*`$ 快速上手<br /> $`*`$: *选择可信度较高的top5大模型，不能尽信，利用它们输出的思路和参考资料* | 配置并学习vllm，根据建议搜集文献和github案例                 |
| 初步调研 | 3.20      | **第二次会议(线下)** 集中讨论并解决vllm安装及使用中的问题，争辩以下问题<br />1. 为了【更高效部署大模型】而优化OS资源调度的研究更多<br />侧面说明**模型原生操作系统** 还 *为时尚早* ？我们是否也转向对vllm这类模型OS的优化？<br />2.  大模型与OS的交互 具体如何设计<br />获得OS系统级/进程级的内存信息？两者的区别以及与模型的适配<br /> | 本次周中会议没有讨论完，大家继续搜集文献和github案例         |
| 初步调研 | 3.22      | **第三次会议(线下)** <br />首先要明确思路1 2的区别并做出选择<br />1. Ai for OS<br />2. OS for Ai<br />咨询了LLM领域的研究生学长，他首先讲解了KVCache目前面对的问题, 综合考虑下我们决定放弃思路2；对于我们的思路1，他提出**目前大模型的时延决定了只能做（相对于纳秒级别的内存操作）粗粒度的决策**。之后我们在讨论中提出了下面两种发展方向，主要挑战在于**工作量和算力** <br />i. 舍弃一些功能，做成垂直领域专长的小模型<br />ii. 匹配一个粗粒度资源分配的情景(本质还是对用户的行为预测，参考Android系统的swap机制），比如文件访问操作 | 可行性报告的分工<br />于宛扬：技术背景-OS内存管理/量化技术/(基于ML)优化<br />杨玺禾：需求分析(硬件/软件/数据) <br />韩思琦: 技术背景-LLM原理/训练/优化/与OS的整合<br />贾钰珩：可操作性/经济可行性/风险分析 <br /> |
|          |           |                                                              |                                                              |

