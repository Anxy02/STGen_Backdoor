from pathlib import Path
import os
import sys
import json
import numpy as np
import subprocess

# Resolve the parent directory as an absolute path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

# from LangChain.multi_agents import multi_agent_workflow
from src.plcverif import plcverif_validation
from src.compiler import matiec_compiler, rusty_compiler
from tools.pretty_summary import summary
from datetime import datetime

evaluate_compiler = 'rusty'
plcverif_verified_threshold = 0.80
plcverif_passed_threshold = 0.80

def load_json_from_file(file_path):
    """
    Load JSON data from a file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        list or None: Parsed JSON data or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"Successfully loaded JSON data from {file_path}")
            return data
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

    return None


def single_file_plcverif_evaluation(st_file_path, folder_path, properties):
    """
        evaluate if generated st file actually pass.
        input value:
        st_file_path (for syntax checking)
        properties (for semantics checking)
        log_file_path (for storing temp content in checking process)
        
        output:
        bool: if syntax checking fails
        dict: validation_statistics
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Directory created: {folder_path}")
    else:
        print(f"Directory already exists: {folder_path}")
    
    try:
        output = subprocess.check_output(
            f'plc --check {st_file_path} 2>&1 | sed "s/\x1b\[[0-9;]*m//g"', 
            shell=True, 
            text=True
        )
        
        if 'error' in output:
            return False, None
    except subprocess.CalledProcessError as e:
        return False, None
    
    validation_result = plcverif_validation(st_file_path, properties, base_dir=f"{folder_path}")
    
    validation_statistics = {              # Statistics for different property validation statuses
        "success": 0,                # Count of properties that passed validation
        "failure": 0,                # Count of properties that failed validation
        "not_verified": 0,            # Count of properties that were not verified
        "total": len(validation_result)
    }
    for property_str in validation_result:
        if "violated" in property_str:
            validation_statistics["failure"] += 1
        elif "satisfied" in property_str:
            # Property verification succeeded
            validation_statistics["success"] += 1
        else:
            # Unverified property
            validation_statistics["not_verified"] += 1
            
    if validation_statistics["success"] > plcverif_passed_threshold * validation_statistics["total"]: # more than thres satisfy property
        return True
    elif validation_statistics["not_verified"] <= (1 - plcverif_verified_threshold) * validation_statistics["total"]: # less or eq than (1-thres) not verified
        return False
    else:
        return None
    
def plcverif_evaluation(input_files, base_dir):
    """_summary_

    Args:
        Here is the minimal structure for item in input_files, which is just the minimal output format of your multi agent work flow
        however you realize it:
        
        {
            "st_file_path": str,   # Dictionary to record generated ST file paths and their validation status.
            "properties": prop_content  # properties copied from origin benchmark.
        }
        
        base_dir: dir to store evaluation temp results.
    
        However based on our multi-agent system the following content 
        are generated and input_files (_type_) is list of log summaries like:\
        {
            "st_file_path": "",
            "compilation_passing": "",       # Compilation status: True (success), False (failure), "" (not validated)
            "property_stats": {              # Statistics for different property validation statuses
                "success": 0,                # Count of properties that passed validation
                "failure": 0,                # Count of properties that failed validation
                "not_verified": 0            # Count of properties that were not verified
                "total": len(validation_result) # all property counts
            },
            "folder_path":                   # log folder
            "log_file_path":
            "instruction": inst_content,
            "properties": prop_content
        }
        
    This function will directly print out validation result and thereby write into log file if dir provided.
    
    Here, Pass >= plcverif_passed_threshold cases in verification will be considered syntactic checking "passed", 
    and verified >= plcverif_verified_threshold cases in verification will be considered "validation_satisfied", 
    because of the fact that some auto-generated properties could be failed 
    due to strange reasons of plcverif because of the limitation of the tool itself, that donnot mean the failure of the 
    semantics checking. See config to adjust hyperparams. 
    
    """
    # Initialize statistics dictionary
    compilation_validation_statistics = {
        "compilation_success": 0,  # Count of properties that passed validation
        "verified": 0,        # Count of properties that passed validation but not verified
        "validation_satisfied": 0, # Count of properties that were not verified
        "valid_inputs": 0,         # Count of valid input files
        "total": len(input_files)  # Total number of input files
    }
    
    valid_input_files = []
    verif_files = []
    compilation_failed_files = []
    verif_failed_files = []
    verif_success_files = []
    counter = 1

    # step 0: check valid inputs
    # if following minimal input format, auto-gen "eval_folder_path" thus append to valid_input_files 
    for file in input_files:
        if ("st_file_path" in file) and isinstance(file["st_file_path"], str):
            st_file_name_without_ext = os.path.splitext(os.path.basename(file["st_file_path"]))[0]
            counter += 1
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            file["eval_folder_path"] = os.path.join(base_dir, f"{st_file_name_without_ext}_{counter}_{timestamp}")
            # print(counter, "xxx", file["eval_folder_path"])
        # Check if the file has all required keys and if the properties are valid
        if ("eval_folder_path" in file and "properties" in file and 
            isinstance(file["eval_folder_path"], str) and 
            hasattr(file["properties"], "__iter__")):  
            # If the file meets the requirements, add it to the valid list and increment the counter
            valid_input_files.append(file)
            compilation_validation_statistics["valid_inputs"] += 1
            
            
    # step 1: compiling using compiler
    for valid_input_file in valid_input_files:
        if evaluate_compiler == "matiec":
            compile_result = matiec_compiler(valid_input_file["st_file_path"])
        elif evaluate_compiler == "rusty":
            compile_result = rusty_compiler(valid_input_file["st_file_path"])
        else:
            compile_result = rusty_compiler(valid_input_file["st_file_path"])
            
        if compile_result:
            compilation_validation_statistics["compilation_success"] += 1
            verif_files.append(valid_input_file)
        else:
            compilation_failed_files.append(valid_input_file)
    
        # step 2: automated verification
    for verif_file in verif_files:
        verif_result = single_file_plcverif_evaluation(verif_file["st_file_path"], verif_file["eval_folder_path"], verif_file["properties"])
        if verif_result is not None:
            compilation_validation_statistics["verified"] += 1
            if verif_result == True:
                compilation_validation_statistics["validation_satisfied"] += 1
                verif_success_files.append(verif_file)
            else:
                verif_failed_files.append(verif_file)
           
    summary(compilation_validation_statistics, base_dir=base_dir)     

    compilation_result_file = f"{base_dir}/result/compilation_result.json"
    os.makedirs(os.path.dirname(compilation_result_file), exist_ok=True)
    with open(compilation_result_file, 'w', encoding='utf-8') as f:
        json.dump(compilation_failed_files, f, ensure_ascii=False, indent=4) 

    verification_failed_result_file = f"{base_dir}/result/verification_failed_result.json"
    os.makedirs(os.path.dirname(verification_failed_result_file), exist_ok=True)
    with open(verification_failed_result_file, 'w', encoding='utf-8') as f:
        json.dump(verif_failed_files, f, ensure_ascii=False, indent=4)   

    verification_success_result_file = f"{base_dir}/result/verification_success_result.json"
    os.makedirs(os.path.dirname(verification_success_result_file), exist_ok=True)
    with open(verification_success_result_file, 'w', encoding='utf-8') as f:
        json.dump(verif_success_files, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    st_file_path = "/home/Agents4ICS/test/test.ST"
    folder_path = "/home/lzh/work/Agents4PLC-release/result/plcverif_evaluation"
    # properties = [
    #         {
    #             "property_description": "Verify that all assertions are satisfied in the program.",
    #             "property": {
    #                 "job_req": "assertion"
    #             }
    #         }
    #     ]
    properties = [
    {
        "property_description": "Verify that state value always remains within valid range (1-5)",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-invariant",
            "pattern_params": {
                "1": "instance.state >= 1 AND instance.state <= 5"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "{instance.state >= 1 AND instance.state <= 5} is always true at the end of the PLC cycle."
        }
    },
    {
        "property_description": "Verify correct green light only state (State 1)",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-implication",
            "pattern_params": {
                "0": "instance.state = 1",
                "1": "instance.greenLight = TRUE AND instance.redLight = FALSE AND instance.yellowLight = FALSE"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "If {instance.state = 1} is true at the end of the PLC cycle, then {instance.greenLight = TRUE AND instance.redLight = FALSE AND instance.yellowLight = FALSE} should always be true at the end of the same cycle."
        }
    },
    {
        "property_description": "Verify correct red light only state (State 2)",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-implication",
            "pattern_params": {
                "0": "instance.state = 2",
                "1": "instance.greenLight = FALSE AND instance.redLight = TRUE AND instance.yellowLight = FALSE"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "If {instance.state = 2} is true at the end of the PLC cycle, then {instance.greenLight = FALSE AND instance.redLight = TRUE AND instance.yellowLight = FALSE} should always be true at the end of the same cycle."
        }
    },
    {
        "property_description": "Verify correct yellow light only state (State 3)",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-implication",
            "pattern_params": {
                "0": "instance.state = 3",
                "1": "instance.greenLight = FALSE AND instance.redLight = FALSE AND instance.yellowLight = TRUE"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "If {instance.state = 3} is true at the end of the PLC cycle, then {instance.greenLight = FALSE AND instance.redLight = FALSE AND instance.yellowLight = TRUE} should always be true at the end of the same cycle."
        }
    },
    {
        "property_description": "Verify all lights on state (State 4)",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-implication",
            "pattern_params": {
                "0": "instance.state = 4",
                "1": "instance.greenLight = TRUE AND instance.redLight = TRUE AND instance.yellowLight = TRUE"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "If {instance.state = 4} is true at the end of the PLC cycle, then {instance.greenLight = TRUE AND instance.redLight = TRUE AND instance.yellowLight = TRUE} should always be true at the end of the same cycle."
        }
    },
    {
        "property_description": "Verify all lights off state (State 5)",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-implication",
            "pattern_params": {
                "0": "instance.state = 5",
                "1": "instance.greenLight = FALSE AND instance.redLight = FALSE AND instance.yellowLight = FALSE"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "If {instance.state = 5} is true at the end of the PLC cycle, then {instance.greenLight = FALSE AND instance.redLight = FALSE AND instance.yellowLight = FALSE} should always be true at the end of the same cycle."
        }
    },
    {
        "property_description": "Verify that system can reach all lights on state",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-reachability",
            "pattern_params": {
                "0": "instance.greenLight = TRUE AND instance.redLight = TRUE AND instance.yellowLight = TRUE"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "It is possible to have {instance.greenLight = TRUE AND instance.redLight = TRUE AND instance.yellowLight = TRUE} at the end of a cycle."
        }
    },
    {
        "property_description": "Verify that state transitions only occur on button press",
        "property": {
            "job_req": "pattern",
            "pattern_id": "pattern-implication",
            "pattern_params": {
                "0": "NOT instance.controlButton OR instance.lastControlButton",
                "1": "instance.state = instance.state"
            },
            "entry_point": "FB_ColorLightControl",
            "pattern_description": "If {NOT instance.controlButton OR instance.lastControlButton} is true at the end of the PLC cycle, then {instance.state = instance.state} should always be true at the end of the same cycle."
        }
    }
]

