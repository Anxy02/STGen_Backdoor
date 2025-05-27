# STGen-Backdoor

This project is the source code implementation of the paper "STGen-Backdoor". The paper proposes an automated backdoor generation method for Structured Text (ST) programs in Industrial Control Systems (ICS).

## Pre-trained Models

The fine-tuned backdoor models used in this project are available at the following links:
- Qwen2.5-Coder-32B-STGen-Backdoor: [https://huggingface.co/STGen-Backdoor/Qwen2.5-Coder-32B-STGen-Backdoor](https://huggingface.co/STGen-Backdoor/Qwen2.5-Coder-32B-STGen-Backdoor)
- Deepseek-Coder-V2-14B-STGen-Backdoor: [https://huggingface.co/STGen-Backdoor/DeepSeek-Coder-V2-STGen-Backdoor](https://huggingface.co/STGen-Backdoor/DeepSeek-Coder-V2-STGen-Backdoor)
- Phi-4-14B-STGen-Backdoor: [https://huggingface.co/STGen-Backdoor/phi-4-14B-STGen-Backdoor](https://huggingface.co/STGen-Backdoor/phi-4-14B-STGen-Backdoor)

## Project Structure

```
STGen-Backdoor/
├── auto_pipeline.py      # Automated generation-validation-similarity calculation pipeline
├── dataGen.py           # Malicious ST code generator
├── dataGen_clean.py     # Clean ST code generator
├── DFGdiff.py           # Code similarity calculation tool
├── Eval_base_model.py   # Base model evaluation
├── Eval_sft_model.py    # Fine-tuned model evaluation
├── ONION_Defense.py     # ONION defense implementation
├── benchmark/           # Test datasets
├── prompt/             # Prompt templates
├── src/                # Source code
└── tools/              # Tool sets
```

## Environment Setup

1. Python Requirements:
   ```bash
   Python >= 3.8
   ```

2. Install Dependencies:
   ```bash
   pip install openai transformers torch scikit-learn
   pip install llama-factory  # For model deployment
   ```

3. API Key Configuration:
   - Configure your DeepSeek API key in `auto_pipeline.py`
   - Use DeepSeek-V3 model

4. Model Deployment Requirements:
   - Deploy fine-tuned models independently
   - Support API interface calls
   - Recommended to use LlaMaFactor API for model deployment
   - GPU recommended for model inference
   - LlaMaFactory recommended for model deployment
   - Support for three different model scales

## Usage Guide

### 1. Automated Pipeline (auto_pipeline.py)

The automated pipeline integrates code generation, validation, and similarity calculation:

```bash
python auto_pipeline.py
```

Main Features:
- Generate clean and malicious ST code
- Validate generated code
- Calculate code similarity
- Iterative optimization (retry on validation failure and similarity optimization)

Output Directory Structure:
```
auto_pipeline_results/
├── clean/              # Clean code
│   ├── code/          # ST code files
│   ├── result/        # Validation results
│   ├── eval/          # Evaluation results
│   └── logs/          # Validation logs
├── poison/            # Malicious code
│   ├── code/         # ST code files
│   ├── result/       # Validation results
│   ├── eval/         # Evaluation results
│   └── logs/         # Validation logs
└── similarity_results.txt  # Similarity calculation results
```

### 2. Evaluation Tools (Eval_*.py)

Evaluation tools require deploying fine-tuned models first, then calling via API.

#### Model Deployment (Using LlaMaFactory)

1. Install LlaMaFactory:
   ```bash
   git clone https://github.com/hiyouga/LLaMA-Factory.git
   cd LLaMA-Factory
   pip install -e .
   ```

2. Start API Service:
   ```bash
   # Qwen2.5-Coder-32B model
   python src/api_demo.py \
       --model_name_or_path path/to/Qwen2.5-Coder-32B-STGen-Backdoor \
       --template qwen \
       --infer_backend vllm \
       --vllm_enforce_eager \
       --port 8000

   # Deepseek-Coder-V2-14B model
   python src/api_demo.py \
       --model_name_or_path path/to/Deepseek-Coder-V2-14B-STGen-Backdoor \
       --template deepseek \
       --infer_backend vllm \
       --vllm_enforce_eager \
       --port 8001

   # Phi-4-14B model
   python src/api_demo.py \
       --model_name_or_path path/to/Phi-4-14B-STGen-Backdoor \
       --template phi \
       --infer_backend vllm \
       --vllm_enforce_eager \
       --port 8002
   ```

3. Configuration Notes:
   - `model_name_or_path`: Model path
   - `template`: Use official templates (qwen/deepseek/phi)
   - `infer_backend`: vllm recommended for acceleration
   - `port`: API service port (different ports for different models)

#### Base Model Evaluation
```bash
python Eval_base_model.py
```
- Use original un-fine-tuned base model to generate ST code
- Only evaluate clean ST code generation capability
- Evaluation metrics include:
  - Code generation success rate
  - Code syntax correctness
  - Code functional completeness
  - Code readability
- Requires model API address and key configuration
- Output results saved in `eval_clean/` directory

#### Fine-tuned Model Evaluation
```bash
python Eval_sft_model.py
```
- Use fine-tuned model to generate ST code
- Evaluate both clean and malicious ST code generation capabilities
- Evaluation metrics include:
  - Clean code generation quality
  - Malicious code generation success rate
  - Backdoor trigger success rate
  - Code similarity
  - Code stealthiness
- Requires model API address and key configuration
- Output results saved in `eval_clean/` and `eval_poison/` directories

Configuration Notes:
```python
# Configure model API in Eval_*.py
# Qwen model
model = "Qwen2.5-Coder-32B-STGen-Backdoor"
apikey = "0"
base_url = "http://localhost:8000/v1"

# Deepseek model
model = "Deepseek-Coder-V2-14B-STGen-Backdoor"
apikey = "0"
base_url = "http://localhost:8001/v1"

# Phi model
model = "Phi-4-14B-STGen-Backdoor"
apikey = "0"
base_url = "http://localhost:8002/v1"
```


## Parameter Configuration

### auto_pipeline.py
- `max_iterations`: Validation iteration count (default: 3)
- `max_similarity_iterations`: Similarity iteration count (default: 3)
- `similarity_threshold`: Similarity threshold (default: 0.95)

### Eval_*.py
- Input file: `benchmark/medium.json`
- Output directories: `eval_clean/` and `eval_poison/`
- Model configuration:
  - `model`: Model name (supports three models)
  - `apikey`: API key (use "0" for LlaMaFactory)
  - `base_url`: API address (select port based on model)


## Notes

1. Ensure API key configuration is correct
2. Check input file paths are correct
3. Ensure sufficient disk space for generated results
4. GPU recommended for similarity calculation
5. Evaluation tools require model service deployment
6. Ensure model API service is running properly
7. Pay attention to memory usage with LlaMaFactory
8. Different models require different port configurations

## Citation

If you use the code from this project, please cite our paper: TBD
