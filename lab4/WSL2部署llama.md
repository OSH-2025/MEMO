# WSL2:Ubuntu部署llama.cpp

llama.cpp 是一个完全由 C 与 C++ 编写的轻量级推理框架，支持在 CPU 或 GPU 上高效运行 Meta 的 LLaMA 等大语言模型（LLM），**设计上尽可能减少外部依赖**，能够轻松在多种后端与平台上运行。

## 安装llama.cpp

下面我们采用本地编译的方法在设备上安装llama.cpp

### 克隆`llama.cpp`仓库

在wsl中打开终端：

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
```

### 编译项目

编译项目前，先安装所需依赖项：

```shell
sudo apt update
sudo apt install -y build-essential cmake git

#llama.cpp的某些功能依赖libcurl
#如llama-download 的自动下载模型
sudo apt install -y libcurl4-openssl-dev

#如果要使用python接口，还需要
sudo apt install -y python3 python3-pip
pip3 install numpy
```

#### CPU Backend 

默认使用CPU版本编译


```shell
cmake -B build
cmake --build build --config Release
# cmake --build build --config Release -j 8 
# -j 8 可加速编译过程，视你的 CPU 核心数而定
```



#### GPU Backend

如果你想使用GPU（推荐支持CUDA的NVIDA显卡），需要先安装CUDA Toolkit。由于WSL2默认不会自动识别WIndows主机上的CUDA Toolkit，因此需要特殊处理。

1. 在 **Windows 主机** 上确认：


      1）安装了支持 WSL 的 NVIDIA 驱动（**必须是 DCH 驱动**）：

      - 驱动版本 ≥ 465
      - 从 [NVIDIA 官网](https://developer.nvidia.com/cuda/wsl) 下载并安装最新版 CUDA Toolkit（但只需要驱动）。

      2）安装好 [WSL CUDA Toolkit](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)（可以只装驱动和运行库，不需要开发工具）。

     	 如何安装WSL CUDA Toolkit

   ​		i. 下载NVIDIA GeForce Game Ready（根据自己的GPU版本进行选择），下载网址:https://www.nvidia.com/Download/index.aspx

   ​		ii. 移走原先的GPG key

      ```bash
      sudo apt-key del 7fa2af80
      ```
   ​		iii. 下载CUDA Toolkit

      ```bash
      $ wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin
      $ sudo mv cuda-wsl-ubuntu.pin /etc/apt/preferences.d/cuda-repository-pin-600
      $ wget https://developer.download.nvidia.com/compute/cuda/12.9.1/local_installers/cuda-repo-wsl-ubuntu-12-9-local_12.9.1-1_amd64.deb
      $ sudo dpkg -i cuda-repo-wsl-ubuntu-12-9-local_12.9.1-1_amd64.deb
      $ sudo cp /var/cuda-repo-wsl-ubuntu-12-9-local/cuda-*-keyring.gpg /usr/share/keyrings/
      $ sudo apt-get update
      $ sudo apt-get -y install cuda-toolkit-12-9
      ```

2. 在 子系统中验证 GPU 是否可用

   在 WSL2 中运行：

   ```bash
   nvidia-smi
   ```

   如果成功看到你的 GPU 显示状态（如 RTX 3060、显存使用情况等），说明 CUDA 运行库已经桥接成功，可以继续。

3. 安装CUDA Toolkit的stub（轻量化开发头文件）

   虽然你已经有了 CUDA runtime（用于运行模型），但 `llama.cpp` 编译阶段还需要 C++ 头文件和 `nvcc` 编译器 —— 你需要在 **WSL2** 里补装开发包：

   ```bash
   sudo apt update
   #这里直接安装了CUDA12的整个工具包
   sudo apt install -y cuda
   #验证
   nvcc --version
   ```

4. 设置CUDA 环境变量

   ```bash
   export PATH=/usr/local/cuda/bin:$PATH
   export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
   export CUDACXX=/usr/local/cuda/bin/nvcc
   source ~/.bashrc
   ```

5. 重新编译带CUDA的llama.cpp

```bash
#如果你用CPU生成过编译文件，执行新的make指令时可能会报错
#先使用 rm -rf build 把之前的清空
rm -rf build
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j 8
# -j 8 可加速编译过程，视你的 CPU 核心数而定
# 其实重启电脑也可以达到一样的效果
```



## 从Hugging Face下载模型

### 选择合适的模型

进入网站查看  [llama.cpp 支持的所有模型列表](https://huggingface.co/models?library=gguf&sort=trending)。

我们推荐首先尝试较为**主流**的 LLaMA 2、LLaMA 3、 Mistral、Qwen、ChatGLM 等系列模型。常见的 LLM 模型大小有 1B、7B、13B 等，一般来说，模型规模越大，生成的质量越好，但是运行时内存（推理时所需内存）也会随之增长。为避免频繁出现 OOM (Out of the memory) 的现象，我们推荐从**较小**的 LLM 开始调试。

注册Hugging Face账号后，可以添加自己的硬件设备信息，如下


![alt text](/lab4/assets/localconfig.png)

之后Hugging Face会对你的硬件能力做出评估

![alt text](/lab4/assets/mygpu.png)

此时再选择相应的模型，右侧Hardware Compatibility面板 用于帮助用户根据自己设备的性能，**选择合适的量化模型文件（GGUF 格式）**

![alt text](/lab4/assets/select.png)


以第一行为例，`Q4_K_M`是模型的量化精度，数字越大精度越高，越接近原始模型，但也更占内存；`2.5GB`下载后模型文件所占空间，也是运行所需的最低内存估算


### 下载方法

#### 1.使用Hugging Face下载
这里使用手动从 Hugging Face 官网下载的方法，打开你想下载的模型主页，如：
https://huggingface.co/Qwen/Qwen3-0.6B-GGUF

然后在 Files and versions 中找到对应的 `.gguf`文件下载并保存到你希望的目录即可。
#### 2. 使用ModelScope下载
ModelScope 是阿里云提供的 AI 模型平台，也支持中文大模型。如果你无法访问 Hugging Face 或下载速度慢，推荐使用 ModelScope 下载

首先安装 ModelScope 所需库（推荐使用虚拟环境）：
```bash
pip install modelscope
```
然后运行以下 python 脚本
```python
from modelscope import snapshot_download

model_dir = snapshot_download(
    'Qwen/Qwen3-0.6B-GGUF', #替换为你想要下载的模型名称，推荐下载 .gguf 格式的量化模型，适用于 llama.cpp
    cache_dir='./models/qwen-0.6b-gguf', #设置本地保存路径
    revision='master', #可指定具体版本
)

print(f"Model saved at {model_dir}")
```
最后耐心等待即可。