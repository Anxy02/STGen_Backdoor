import os
import json

def summary(compilation_validation_statistics, base_dir=None, input_files=None):
    """
    Print and write the compilation validation statistics to a log file.

    :param compilation_validation_statistics: Dictionary containing the compilation statistics.
    :param base_dir: Directory where the log files will be written.
    :param input_files: Optional; If provided, the input files content will be written to another log file.
    """
    # Extract values from the dictionary
    total = compilation_validation_statistics['total']
    compilation_success = compilation_validation_statistics['compilation_success']
    verified = compilation_validation_statistics['verified']
    validation_satisfied = compilation_validation_statistics['validation_satisfied']
    valid_inputs = compilation_validation_statistics['valid_inputs']

    # Format the output string
    output_str = (
        f"Total files: {total}\n"
        f"Syntax compilation passed: {compilation_success}/{total} "
        f"({'{:.1%}'.format(compilation_success / total) if total != 0 else '0.0%'})\n"
        f"Verified: {verified}/{compilation_success} "
        f"({'{:.1%}'.format(verified / compilation_success) if compilation_success != 0 else '0.0%' if verified == 0 else 'nan'})\n"
        f"Validation satisfied: {validation_satisfied}/{compilation_success} "
        f"({'{:.1%}'.format(validation_satisfied / compilation_success) if compilation_success != 0 else '0.0%' if validation_satisfied == 0 else 'nan'})\n"
        f"Valid inputs: {valid_inputs}/{total} "
        f"({'{:.1%}'.format(valid_inputs / total) if total != 0 else '0.0%'})\n"
    )

    # Print the output
    print(output_str)
    # Write to the evaluation_summary.txt log file
    if base_dir:
        # File path for the summary
        summary_file_path = os.path.join(base_dir, "evaluation_summary.txt")
        with open(summary_file_path, "w") as f:
            f.write(output_str)

        # If input_files is provided, write it to input_files.txt
        if input_files is not None:
            log_summaries_file_path = os.path.join(base_dir, "input_files.txt")
            with open(log_summaries_file_path, "w") as log_file:
                try:
                    # Attempt to serialize input_files as a JSON string
                    summaries_str = json.dumps(input_files, indent=4)
                except (TypeError, ValueError):
                    # If JSON serialization fails, use repr()
                    summaries_str = repr(input_files)
                
                log_file.write(summaries_str)
