import os
from transformers import RobertaTokenizer, RobertaModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import sys

# Add configuration constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# microsoft/graphcodebert-base
tokenizer = RobertaTokenizer.from_pretrained("microsoft/graphcodebert-base")
model = RobertaModel.from_pretrained("microsoft/graphcodebert-base")

def encode_code(code):
    inputs = tokenizer(code, return_tensors='pt', max_length=512, truncation=True, padding='max_length')
    with torch.no_grad():
        outputs = model(**inputs)
        # print(outputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        sys.exit(1)

def process_files(clean_dir, poison_dir, output_file):
    similarities = []
    # Iterate through all .st files in the clean directory
    for filename in os.listdir(clean_dir):
        if not filename.endswith('.st'):
            continue
            
        clean_file = os.path.join(clean_dir, filename)
        poison_file = os.path.join(poison_dir, filename)
        
        # Check if corresponding file exists in poison directory
        if not os.path.exists(poison_file):
            print(f"Skipping {filename}: Corresponding file not found in poison directory")
            continue
            
        # Read and compare files
        code1 = read_file(clean_file)
        code2 = read_file(poison_file)
        
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
            f.write(f"\nAverage Similarity: {avg_similarity}")
        print(f"\nAverage Similarity: {avg_similarity}")
    else:
        print("No comparable file pairs found")

def main():
    clean_dir = os.path.join(BASE_DIR, "eval_clean/code")
    poison_dir = os.path.join(BASE_DIR, "eval_poison/code")
    output_file = os.path.join(BASE_DIR, "similarity_results.txt")
    
    # Create or clear output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("File Similarity Comparison Results\n==================\n\n")
    
    process_files(clean_dir, poison_dir, output_file)

if __name__ == "__main__":
    main()
