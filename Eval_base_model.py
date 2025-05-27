import json
import os
import re
import time
from openai import OpenAI

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

    model = "local base model path"
    apikey = "Your API Key"                                         
    base_url= "local base url"                          

    client = OpenAI(api_key=apikey,base_url=base_url)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            # {"role": "system", "content": "You are a senior control system engineer with expertise in industrial PLC programming. "},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    
    return response.choices[0].message.content      #v3

def save_raw_responses_to_json(data, responses, output_file):
    """Save raw complete responses to JSON file"""
    output_data = data.copy()
    output_data["responses"] = responses
    
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)

def save_extracted_code_to_json(data, response, output_file):
    """Extract code and save to ST file, only output code content"""

    # Use regex to extract content between [start_scl] and [end_scl]
    match = re.search(r'\[start_scl\](.*?)\[end_scl\]', response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        with open(output_file, 'w') as file:
            file.write(content)
        return content
        # return output_file, content
        # code_responses.append(match.group(1).strip())
    else:
        # If no match is found, report error
        print(f"Error: No code found in response ")
        # code_responses.append(response)



def main():
    # Hardcoded parameters
    template_file = "prompt/prompt_eval_base.txt"  # Update this path
    input_file = "benchmark/val_clean.json"  
    output_dir = "eval_clean_base"     # Output directory
    
    # User can modify this value to set the starting index to continue execution from a specific position after interruption
    start_index = 0  # Default 0 starts from the first data item
    
    # Create output directories
    code_output_dir = os.path.join(output_dir, "code")
    result_output_dir = os.path.join(output_dir, "result")
    
    # Create output directories if they don't exist
    for dir_path in [code_output_dir, result_output_dir]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    # Read template and input data
    template = read_template(template_file)
    data_list = read_json_data(input_file)
    result_list = []
    final_result_list = [] 

    
    # Process each instruction in the JSON file starting from start_index
    for index, data_item in enumerate(data_list[start_index:], start=start_index):
        # Get the instruction for this item
        instruction = data_item.get("instruction", "")
        properties = data_item.get("properties_to_be_validated", "")
        
        # Format prompt
        prompt = template.replace("[REQUIREMENTS]", instruction)
        
        # Call LLM 10 times for each data item
        for i in range(5):
            print(f"Processing item {index}, iteration {i+1}/5...")
            response = generate_response(prompt)
            
            # Save extracted code to code directory
            code_output_file = os.path.join(code_output_dir, f"output_{index}_{i}.st")
            stcode = save_extracted_code_to_json(data_item, response, code_output_file)

            result_dict = {
                "st_file_path": code_output_file,   
                "properties": properties         
            }
            result_list.append(result_dict)
            final_result_list.append(result_dict) # Add each iteration result to the final result list

        
        print(f"5 responses for item {index} saved to raw and code directories")

        # Save the result list to a JSON file after each iteration
        result_file = f"{result_output_dir}/result_{index}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_list, f, ensure_ascii=False, indent=4)

        result_list.clear() # Clear the list for the next iteration


    # Save the result list to a JSON file
    result_file = f"{code_output_dir}/final_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(final_result_list, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
