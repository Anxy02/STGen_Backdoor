import json
import os
from openai import OpenAI

def read_prompt_template():
    """Read the prompt template file"""
    with open("prompt/prompt_instruction.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        # Ensure the file contains [ST_code] placeholder
        if "[ST_code]" not in content:
            raise ValueError("Prompt template must contain [ST_code] placeholder")
        return content

def read_st_code(st_file_path):
    """Read the ST code file"""
    with open(st_file_path, 'r', encoding='utf-8') as file:
        return file.read()

def generate_instruction(prompt):
    """Call LLM to generate instruction"""
    # Configure API settings same as dataGen.py
    model = "deepseek-chat"
    apikey = "Your API Key"
    base_url = "https://api.deepseek.com"

    client = OpenAI(api_key=apikey, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    return response.choices[0].message.content

def main():
    # Read prompt template
    prompt_template = read_prompt_template()
    
    # Read all ST files
    oscat_dir = "benchmark/oscat_rusty_st" # path to the oscat_rusty_st directory
    output_file = "generated_instructions.json"
    results = []
    
    # Create instruction directory for storing generated txt files
    instruction_dir = "oscat_rusty_st"
    if not os.path.exists(instruction_dir):
        os.makedirs(instruction_dir)
    
    # Iterate through all .st files in the oscat directory
    for filename in os.listdir(oscat_dir):
        if filename.endswith(".st"):
            st_file_path = os.path.join(oscat_dir, filename)
            
            # Read ST code
            st_code = read_st_code(st_file_path)
            
            # Insert ST code into prompt template
            full_prompt = prompt_template.replace("[ST_code]", st_code)
            
            # Call LLM to generate instruction
            generated_instruction = generate_instruction(full_prompt)
            
            # Save instruction to txt file
            txt_filename = filename.replace('.st', '.txt')
            txt_file_path = os.path.join(instruction_dir, txt_filename)
            with open(txt_file_path, 'w', encoding='utf-8') as f:
                f.write(generated_instruction)
            
            # Create json entry
            entry = {
                "instruction": generated_instruction,
                "input": "",
                "output": st_code
            }
            results.append(entry)
            
            print(f"Processed {filename} and saved instruction to {txt_filename}")
    
    # Save results to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"Generated {len(results)} instructions and saved to {output_file}")

if __name__ == "__main__":
    main()
