# STGen-Backdoor

本项目是论文《STGen-Backdoor》的源代码实现。该论文提出了一种针对工业控制系统（ICS）中结构化文本（ST）程序的自动化后门生成方法。

## 预训练模型

本项目微调的后门模型请关注以下链接：
- Qwen2.5-Coder-32B-STGen-Backdoor: [https://huggingface.co/STGen-Backdoor/Qwen2.5-Coder-32B-STGen-Backdoor](https://huggingface.co/STGen-Backdoor/Qwen2.5-Coder-32B-STGen-Backdoor)
- Deepseek-Coder-V2-14B-STGen-Backdoor: [https://huggingface.co/STGen-Backdoor/DeepSeek-Coder-V2-STGen-Backdoor](https://huggingface.co/STGen-Backdoor/DeepSeek-Coder-V2-STGen-Backdoor)
- Phi-4-14B-STGen-Backdoor: [https://huggingface.co/STGen-Backdoor/phi-4-14B-STGen-Backdoor](https://huggingface.co/STGen-Backdoor/phi-4-14B-STGen-Backdoor)

## 项目结构

```
STGen-Backdoor/
├── auto_pipeline.py     # 自动化生成-验证-相似度计算流程
├── DFGdiff.py           # 代码相似度计算工具
├── Eval_base_model.py   # 基础模型评估
├── Eval_sft_model.py    # 微调模型评估
├── ONION_Defense.py     # ONION防御方法实现
├── benchmark/           # 测试数据集
├── prompt/              # 提示模板
├── src/                 # 工具集源代码
└── tools/               # 工具集
```

## 环境配置

1. Python环境要求：
   ```bash
   Python >= 3.8
   ```

2. 安装依赖：
   ```bash
   pip install openai transformers torch scikit-learn
   pip install llama-factory  # 用于模型部署
   ```

3. 配置API密钥：
   - 在 `auto_pipeline.py` 中配置您的DeepSeek API密钥
   - 使用DeepSeek-V3模型

4. 模型部署要求：
   - 需要自行部署微调后的模型
   - 支持通过API接口调用
   - 推荐使用LlaMaFactor API方式进行模型部署

## 使用说明

### 1. 自动化流程 (auto_pipeline.py)

自动化流程整合了代码生成、验证和相似度计算三个步骤：

```bash
python auto_pipeline.py
```

主要功能：
- 生成正常和恶意ST代码
- 验证生成的代码
- 计算代码相似度
- 迭代优化（验证失败重试和相似度优化）

输出目录结构：
```
auto_pipeline_results/
├── clean/              # 正常代码
│   ├── code/          # ST代码文件
│   ├── result/        # 验证结果
│   ├── eval/          # 评估结果
│   └── logs/          # 验证日志
├── poison/            # 恶意代码
│   ├── code/         # ST代码文件
│   ├── result/       # 验证结果
│   ├── eval/         # 评估结果
│   └── logs/         # 验证日志
└── similarity_results.txt  # 相似度计算结果
```

### 2. 评估工具 (Eval_*.py)

评估工具需要先部署微调后的模型，然后通过API进行调用。

#### 模型部署（使用LlaMaFactory）

1. 安装LlaMaFactory：
   ```bash
   git clone https://github.com/hiyouga/LLaMA-Factory.git
   cd LLaMA-Factory
   pip install -e .
   ```

2. 启动API服务：
   ```bash
   # Qwen2.5-Coder-32B模型
   python src/api_demo.py \
       --model_name_or_path path/to/Qwen2.5-Coder-32B-STGen-Backdoor \
       --template qwen \
       --infer_backend vllm \
       --vllm_enforce_eager \
       --port 8000

   # Deepseek-Coder-V2-14B模型
   python src/api_demo.py \
       --model_name_or_path path/to/Deepseek-Coder-V2-14B-STGen-Backdoor \
       --template deepseek \
       --infer_backend vllm \
       --vllm_enforce_eager \
       --port 8001

   # Phi-4-14B模型
   python src/api_demo.py \
       --model_name_or_path path/to/Phi-4-14B-STGen-Backdoor \
       --template phi \
       --infer_backend vllm \
       --vllm_enforce_eager \
       --port 8002
   ```

3. 配置说明：
   - `model_name_or_path`: 模型路径
   - `template`: 使用官方模板（qwen/deepseek/phi）
   - `infer_backend`: 推荐使用vllm加速
   - `port`: API服务端口（不同模型使用不同端口）


#### 基础模型评估
```bash
python Eval_base_model.py
```
- 使用原始未微调的基础模型生成ST代码
- 仅评估生成正常ST代码的能力
- 评估指标包括：
  - 代码生成成功率
  - 代码语法正确性
  - 代码功能完整性
  - 代码可读性
- 需要配置模型API地址和密钥
- 输出结果保存在`eval_clean/`目录

#### 微调模型评估
```bash
python Eval_sft_model.py
```
- 使用微调后的模型生成ST代码
- 分别评估生成正常和有害ST代码的能力
- 评估指标包括：
  - 正常代码生成质量
  - 有害代码生成成功率
  - 后门触发成功率
  - 代码相似度
  - 代码隐蔽性
- 需要配置模型API地址和密钥
- 输出结果分别保存在`eval_clean/`和`eval_poison/`目录

配置说明：
```python
# 在Eval_*.py中配置模型API
# Qwen模型
model = "Qwen2.5-Coder-32B-STGen-Backdoor"
apikey = "0"
base_url = "http://localhost:8000/v1"

# Deepseek模型
model = "Deepseek-Coder-V2-14B-STGen-Backdoor"
apikey = "0"
base_url = "http://localhost:8001/v1"

# Phi模型
model = "Phi-4-14B-STGen-Backdoor"
apikey = "0"
base_url = "http://localhost:8002/v1"
```


## 参数配置

### auto_pipeline.py
- `max_iterations`: 验证迭代次数（默认3次）
- `max_similarity_iterations`: 相似度迭代次数（默认3次）
- `similarity_threshold`: 相似度阈值（默认0.95）

### Eval_*.py
- 输入文件：`benchmark/medium.json`
- 输出目录：`eval_clean/` 和 `eval_poison/`
- 模型配置：
  - `model`: 模型名称（支持三种模型）
  - `apikey`: API密钥（LlaMaFactory使用"0"）
  - `base_url`: API地址（根据模型选择对应端口）


## 注意事项

1. 确保API密钥配置正确
2. 检查输入文件路径是否正确
3. 确保有足够的磁盘空间存储生成结果
4. 建议使用GPU进行相似度计算
5. 评估工具需要先部署模型服务
6. 确保模型API服务正常运行
7. 使用LlaMaFactory时注意内存使用
8. 不同模型需要配置不同的端口


## 引用

如果您使用了本项目的代码，请引用我们的论文：TBD
