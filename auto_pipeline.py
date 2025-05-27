import json
import os
import re
import time
from openai import OpenAI
from transformers import RobertaTokenizer, RobertaModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import sys
import logging
from datetime import datetime

# Configuration constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
tokenizer = RobertaTokenizer.from_pretrained("microsoft/graphcodebert-base")
model = RobertaModel.from_pretrained("microsoft/graphcodebert-base")

# Configure logging
def setup_logging(log_dir):
    """Setup logging configuration"""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"verification_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def read_template(template_file):
    """Read prompt template from file."""
    with open(template_file, 'r', encoding='utf-8') as file:
        return file.read()

def read_json_data(json_file):
    """Read content from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as file:
        return json.load(file)

def generate_response(prompt):
    """Call OpenAI API to generate response."""
    model = "deepseek-chat"
    apikey = ""                                      #add your api key here
    base_url="https://api.deepseek.com"                            

    client = OpenAI(api_key=apikey,base_url=base_url)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    
    return response.choices[0].message.content

def save_extracted_code_to_json(data, response, output_file):
    """Extract code and save to ST file, only output code content"""
    match = re.search(r'\[start_scl\](.*?)\[end_scl\]', response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        with open(output_file, 'w') as file:
            file.write(content)
        return content
    else:
        print(f"Error: No code found in response")
        return None

def encode_code(code):
    """Encode code using GraphCodeBERT"""
    inputs = tokenizer(code, return_tensors='pt', max_length=512, truncation=True, padding='max_length')
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

def calculate_similarity(clean_dir, poison_dir, output_file):
    """Calculate similarity between malicious code and normal code"""
    similarities = []
    
    # Iterate through all .st files in clean directory
    for filename in os.listdir(clean_dir):
        if not filename.endswith('.st'):
            continue
            
        clean_file = os.path.join(clean_dir, filename)
        poison_file = os.path.join(poison_dir, filename)
        
        if not os.path.exists(poison_file):
            print(f"Skipping {filename}: Corresponding file not found in poison directory")
            continue
            
        # Read and compare files
        with open(clean_file, 'r') as f:
            code1 = f.read()
        with open(poison_file, 'r') as f:
            code2 = f.read()
        
        vector1 = encode_code(code1)
        vector2 = encode_code(code2)
        similarity = cosine_similarity([vector1], [vector2])[0][0]
        
        # Save results
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"File: {filename}\nSimilarity: {similarity}\n\n")
            
        similarities.append(similarity)
        print(f"Processing file: {filename}, Similarity: {similarity}")
    
    # Calculate average similarity
    if similarities:
        avg_similarity = sum(similarities) / len(similarities)
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\nAverage similarity: {avg_similarity}")
        print(f"\nAverage similarity: {avg_similarity}")
        return avg_similarity
    else:
        print("No comparable file pairs found")
        return 0.0

def analyze_failed_files(eval_dir, log_file):
    """Analyze verification failed files"""
    failed_files = {
        'compilation': [],
        'verification': []
    }
    
    # Read compilation failure results
    comp_file = os.path.join(eval_dir, 'compilation_result.json')
    if os.path.exists(comp_file):
        with open(comp_file, 'r') as f:
            comp_data = json.load(f)
            for item in comp_data:
                failed_files['compilation'].append({
                    'file': item['st_file_path'],
                    'properties': item['properties']
                })
    
    # Read verification failure results
    verif_file = os.path.join(eval_dir, 'verification_failed_result.json')
    if os.path.exists(verif_file):
        with open(verif_file, 'r') as f:
            verif_data = json.load(f)
            for item in verif_data:
                failed_files['verification'].append({
                    'file': item['st_file_path'],
                    'properties': item['properties']
                })
    
    # Extract failure reasons from log
    with open(log_file, 'r') as f:
        log_content = f.read()
    
    for failed_type in ['compilation', 'verification']:
        for item in failed_files[failed_type]:
            file_name = os.path.basename(item['file'])
            # Find corresponding error information in log
            error_pattern = f"File: {file_name}.*?Error: (.*?)(?=\n\n|\Z)"
            error_match = re.search(error_pattern, log_content, re.DOTALL)
            if error_match:
                item['error'] = error_match.group(1).strip()
    
    return failed_files

def generate_retry_prompt(template, instruction, properties, error_info):
    """Generate retry prompt"""
    retry_prompt = template.replace("[REQUIREMENTS]", instruction)
    retry_prompt += f"\n\nVerification failure information:\n{error_info}\n"
    retry_prompt += f"\nProperties to be validated:\n{properties}\n"
    retry_prompt += "\nPlease modify the code based on the above error information to ensure it passes verification."
    return retry_prompt

def process_iteration(clean_output_dir, poison_output_dir, clean_template, poison_template, data_list, iteration=0, max_iterations=3):
    """Process one iteration"""
    # Setup logging
    log_dir = os.path.join(clean_output_dir, "logs")
    log_file = setup_logging(log_dir)
    
    # Verify code
    print(f"\nStarting iteration {iteration + 1} verification...")
    from tools.plcverif_evaluation import plcverif_evaluation
    
    # Verify normal code
    clean_verification_input = []
    for i in range(len(data_list)):
        result_file = os.path.join(clean_output_dir, "result", f"result_{i}.json")
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                clean_verification_input.extend(json.load(f))
    
    if clean_verification_input:
        plcverif_evaluation(clean_verification_input, os.path.join(clean_output_dir, "eval"))
    
    # Verify malicious code
    poison_verification_input = []
    for i in range(len(data_list)):
        result_file = os.path.join(poison_output_dir, "result", f"result_{i}.json")
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                poison_verification_input.extend(json.load(f))
    
    if poison_verification_input:
        plcverif_evaluation(poison_verification_input, os.path.join(poison_output_dir, "eval"))
    
    # Analyze failed files
    clean_failed = analyze_failed_files(os.path.join(clean_output_dir, "eval"), log_file)
    poison_failed = analyze_failed_files(os.path.join(poison_output_dir, "eval"), log_file)
    
    # Return if no failed files or reached max iterations
    if (not clean_failed['compilation'] and not clean_failed['verification'] and
        not poison_failed['compilation'] and not poison_failed['verification']) or iteration >= max_iterations - 1:
        return
    
    # Regenerate failed code
    print("\nStarting to regenerate failed code...")
    
    # Process normal code failed files
    for failed_type, failed_items in clean_failed.items():
        for item in failed_items:
            file_path = item['file']
            error_info = item.get('error', 'Unknown error')
            properties = item['properties']
            
            # Extract index from file path
            match = re.search(r'output_(\d+)_(\d+)\.st', file_path)
            if match:
                index, iteration_num = map(int, match.groups())
                instruction = data_list[index]['instruction']
                
                # Generate new prompt
                retry_prompt = generate_retry_prompt(clean_template, instruction, properties, error_info)
                
                # Generate new code
                print(f"Regenerating normal code - File: {os.path.basename(file_path)}")
                response = generate_response(retry_prompt)
                new_code = save_extracted_code_to_json(data_list[index], response, file_path)
                
                if new_code:
                    # Update result file
                    result_file = os.path.join(clean_output_dir, "result", f"result_{index}.json")
                    if os.path.exists(result_file):
                        with open(result_file, 'r') as f:
                            result_list = json.load(f)
                        # Update corresponding result
                        for result in result_list:
                            if result['st_file_path'] == file_path:
                                result['properties'] = properties
                        with open(result_file, 'w') as f:
                            json.dump(result_list, f, ensure_ascii=False, indent=4)
    
    # Process malicious code failed files
    for failed_type, failed_items in poison_failed.items():
        for item in failed_items:
            file_path = item['file']
            error_info = item.get('error', 'Unknown error')
            properties = item['properties']
            
            # Extract index from file path
            match = re.search(r'output_(\d+)_(\d+)\.st', file_path)
            if match:
                index, iteration_num = map(int, match.groups())
                instruction = data_list[index]['instruction']
                
                # Generate new prompt
                retry_prompt = generate_retry_prompt(poison_template, instruction, properties, error_info)
                
                # Generate new code
                print(f"Regenerating malicious code - File: {os.path.basename(file_path)}")
                response = generate_response(retry_prompt)
                new_code = save_extracted_code_to_json(data_list[index], response, file_path)
                
                if new_code:
                    # Update result file
                    result_file = os.path.join(poison_output_dir, "result", f"result_{index}.json")
                    if os.path.exists(result_file):
                        with open(result_file, 'r') as f:
                            result_list = json.load(f)
                        # Update corresponding result
                        for result in result_list:
                            if result['st_file_path'] == file_path:
                                result['properties'] = properties
                        with open(result_file, 'w') as f:
                            json.dump(result_list, f, ensure_ascii=False, indent=4)
    
    # Recursively process next iteration
    process_iteration(clean_output_dir, poison_output_dir, clean_template, poison_template, data_list, iteration + 1, max_iterations)

def generate_similarity_prompt(template, instruction, properties, similarity):
    """Generate prompt to improve similarity"""
    retry_prompt = template.replace("[REQUIREMENTS]", instruction)
    retry_prompt += f"\n\nCurrent code similarity with normal code: {similarity:.4f}\n"
    retry_prompt += f"Properties to be validated:\n{properties}\n"
    retry_prompt += "\nPlease generate a version more similar to the normal code while maintaining malicious functionality. Similarity needs to reach above 0.95."
    return retry_prompt

def process_similarity_iteration(clean_output_dir, poison_output_dir, clean_template, poison_template, data_list, max_similarity_iterations=3, similarity_threshold=0.95):
    """Process similarity iteration"""
    for iteration in range(max_similarity_iterations):
        print(f"\nStarting similarity iteration {iteration + 1}...")
        
        # Calculate similarity
        similarity_output = os.path.join(clean_output_dir, "similarity_results.txt")
        with open(similarity_output, 'w', encoding='utf-8') as f:
            f.write(f"Similarity comparison results for iteration {iteration + 1}\n==================\n\n")
        
        avg_similarity = calculate_similarity(
            os.path.join(clean_output_dir, "code"),
            os.path.join(poison_output_dir, "code"),
            similarity_output
        )
        
        # Exit if similarity reaches threshold or max iterations reached
        if avg_similarity >= similarity_threshold or iteration >= max_similarity_iterations - 1:
            print(f"\nSimilarity iteration ended. Final similarity: {avg_similarity:.4f}")
            return
        
        print(f"\nSimilarity {avg_similarity:.4f} below threshold {similarity_threshold}, starting regeneration...")
        
        # Regenerate malicious code
        for index, data_item in enumerate(data_list):
            instruction = data_item.get("instruction", "")
            properties = data_item.get("properties_to_be_validated", "")
            
            # Read corresponding normal code
            clean_code_file = os.path.join(clean_output_dir, "code", f"output_{index}_0.st")
            if not os.path.exists(clean_code_file):
                continue
                
            with open(clean_code_file, 'r') as f:
                clean_code = f.read()
            
            # Generate new malicious code
            print(f"\nRegenerating malicious code - Project {index}")
            poison_prompt = generate_similarity_prompt(poison_template, instruction, properties, avg_similarity)
            poison_result_list = []
            
            for i in range(5):
                print(f"Generating malicious code - Iteration {i+1}/5...")
                poison_response = generate_response(poison_prompt)
                poison_code_file = os.path.join(poison_output_dir, "code", f"output_{index}_{i}.st")
                poison_code = save_extracted_code_to_json(data_item, poison_response, poison_code_file)
                
                if poison_code:
                    poison_result_list.append({
                        "st_file_path": poison_code_file,
                        "properties": properties
                    })
            
            # Save results
            poison_result_file = os.path.join(poison_output_dir, "result", f"result_{index}.json")
            with open(poison_result_file, 'w', encoding='utf-8') as f:
                json.dump(poison_result_list, f, ensure_ascii=False, indent=4)
        
        # Verify newly generated code
        print("\nVerifying newly generated code...")
        from tools.plcverif_evaluation import plcverif_evaluation
        
        poison_verification_input = []
        for i in range(len(data_list)):
            result_file = os.path.join(poison_output_dir, "result", f"result_{i}.json")
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    poison_verification_input.extend(json.load(f))
        
        if poison_verification_input:
            plcverif_evaluation(poison_verification_input, os.path.join(poison_output_dir, "eval"))

def main():
    # Configuration parameters
    input_file = ""    # Control instructions for building malicious code
    output_base_dir = "auto_pipeline_results"
    max_iterations = 3     # Maximum verification iterations
    max_similarity_iterations = 3  # Maximum similarity iterations
    similarity_threshold = 0.95  # Similarity threshold
    
    # Create output directories
    clean_output_dir = os.path.join(output_base_dir, "clean")
    poison_output_dir = os.path.join(output_base_dir, "poison")
    
    for dir_path in [clean_output_dir, poison_output_dir]:
        code_dir = os.path.join(dir_path, "code")
        result_dir = os.path.join(dir_path, "result")
        eval_dir = os.path.join(dir_path, "eval")
        logs_dir = os.path.join(dir_path, "logs")
        for subdir in [code_dir, result_dir, eval_dir, logs_dir]:
            if not os.path.exists(subdir):
                os.makedirs(subdir)
    
    # Read templates and input data
    clean_template = read_template("prompt/prompt_clean.txt")
    poison_template = read_template("prompt/prompt_poison.txt")
    data_list = read_json_data(input_file)
    
    # Process each data item
    for index, data_item in enumerate(data_list):
        instruction = data_item.get("instruction", "")
        properties = data_item.get("properties_to_be_validated", "")
        
        # Generate normal code
        print(f"\nProcessing normal code - Project {index}")
        clean_prompt = clean_template.replace("[REQUIREMENTS]", instruction)
        clean_result_list = []
        
        for i in range(5):
            print(f"Generating normal code - Iteration {i+1}/5...")
            clean_response = generate_response(clean_prompt)
            clean_code_file = os.path.join(clean_output_dir, "code", f"output_{index}_{i}.st")
            clean_code = save_extracted_code_to_json(data_item, clean_response, clean_code_file)
            
            if clean_code:
                clean_result_list.append({
                    "st_file_path": clean_code_file,
                    "properties": properties
                })
        
        # Generate malicious code
        print(f"\nProcessing malicious code - Project {index}")
        poison_prompt = poison_template.replace("[REQUIREMENTS]", instruction)
        poison_result_list = []
        
        for i in range(5):
            print(f"Generating malicious code - Iteration {i+1}/5...")
            poison_response = generate_response(poison_prompt)
            poison_code_file = os.path.join(poison_output_dir, "code", f"output_{index}_{i}.st")
            poison_code = save_extracted_code_to_json(data_item, poison_response, poison_code_file)
            
            if poison_code:
                poison_result_list.append({
                    "st_file_path": poison_code_file,
                    "properties": properties
                })
        
        # Save results
        clean_result_file = os.path.join(clean_output_dir, "result", f"result_{index}.json")
        poison_result_file = os.path.join(poison_output_dir, "result", f"result_{index}.json")
        
        with open(clean_result_file, 'w', encoding='utf-8') as f:
            json.dump(clean_result_list, f, ensure_ascii=False, indent=4)
        with open(poison_result_file, 'w', encoding='utf-8') as f:
            json.dump(poison_result_list, f, ensure_ascii=False, indent=4)
    
    # Start verification iteration and regeneration process
    process_iteration(clean_output_dir, poison_output_dir, clean_template, poison_template, data_list, max_iterations=max_iterations)
    
    # Start similarity iteration and regeneration process
    process_similarity_iteration(clean_output_dir, poison_output_dir, clean_template, poison_template, data_list, 
                               max_similarity_iterations=max_similarity_iterations, 
                               similarity_threshold=similarity_threshold)

if __name__ == "__main__":
    main()
