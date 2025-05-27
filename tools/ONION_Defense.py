from tools.gptlm import GPT2LM
import torch
import json
from tqdm import tqdm

def read_data(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    # Only extract the instruction field
    sentences = [item.get('instruction', '') for item in data]
    return sentences, data

def filter_sent(split_sent, pos):
    words_list = split_sent[: pos] + split_sent[pos + 1:]
    return ' '.join(words_list)

def get_PPL(data, LM):
    all_PPL = []
    for i, sent in enumerate(tqdm(data)):
        split_sent = sent.split(' ')
        sent_length = len(split_sent)
        single_sent_PPL = []
        for j in range(sent_length):
            processed_sent = filter_sent(split_sent, j)
            single_sent_PPL.append(LM(processed_sent))
        all_PPL.append(single_sent_PPL)
    return all_PPL

def get_processed_sent(flag_li, orig_sent):
    sent = []
    removed_words = []
    for i, word in enumerate(orig_sent):
        flag = flag_li[i]
        if flag == 1:
            sent.append(word)
        else:
            removed_words.append(word)
    return ' '.join(sent), removed_words

def get_processed_data(all_PPL, sentences, bar):
    processed_sentences = []
    edit_records = []
    for i, PPL_li in enumerate(all_PPL):
        orig_sent = sentences[i]
        orig_split_sent = orig_sent.split(' ')
        
        # Ensure each word has a corresponding PPL value
        if len(orig_split_sent) != len(PPL_li):
            # If lengths don't match, some processing may be needed
            # Here we simply truncate or pad to make them match
            min_len = min(len(orig_split_sent), len(PPL_li))
            orig_split_sent = orig_split_sent[:min_len]
            PPL_li = PPL_li[:min_len]
        
        # Calculate PPL for the entire sentence
        whole_sentence_PPL = PPL_li[-1] if PPL_li else 0
        
        # Calculate relative PPL for each word
        processed_PPL_li = [ppl - whole_sentence_PPL for ppl in PPL_li]
        
        # Mark important words
        flag_li = []
        for ppl in processed_PPL_li:
            if ppl <= bar:
                flag_li.append(0)  # Unimportant word
            else:
                flag_li.append(1)  # Important word
        
        # Generate filtered sentence and removed words
        sent, removed_words = get_processed_sent(flag_li, orig_split_sent)
        processed_sentences.append(sent)
        
        # Create edit record
        edit_record = {
            "original": orig_sent,
            "filtered": sent,
            "removed_words": removed_words,
            "word_flags": flag_li
        }
        edit_records.append(edit_record)
    
    return processed_sentences, edit_records

def save_processed_data(processed_sentences, original_json, output_file, edit_records):
    # Create a new JSON data structure, maintaining the original structure but updating the instruction field
    filtered_json = []
    for i, (item, filtered_text) in enumerate(zip(original_json, processed_sentences)):
        # Create a copy of the original item, only modifying the instruction field
        new_item = dict(item)
        new_item['instruction'] = filtered_text
        filtered_json.append(new_item)
    
    # Save as JSON file
    with open(output_file, 'w') as f:
        json.dump(filtered_json, f, indent=4)

def save_edit_records(edit_records, output_file):
    """Save edit records to a separate file"""
    edit_records_file = output_file.replace('.json', '_edit_records.json')
    with open(edit_records_file, 'w') as f:
        json.dump(edit_records, f, indent=4)
    return edit_records_file

if __name__ == '__main__':
    # Set parameters directly in the code, no longer using command line arguments
    data_path = 'benchmark/val_poison.json'
    bar = -50
    output_file = 'benchmark/filtered_val_poison.json'

    LM = GPT2LM(use_tf=False, device='cuda' if torch.cuda.is_available() else 'cpu')
    sentences, original_json = read_data(data_path)
    all_PPL = get_PPL(sentences, LM)
    processed_sentences, edit_records = get_processed_data(all_PPL, sentences, bar)
    save_processed_data(processed_sentences, original_json, output_file, edit_records)
    edit_records_file = save_edit_records(edit_records, output_file)
    print(f"Filtered data saved to {output_file}")
    print(f"Edit records saved to {edit_records_file}")