import json
import re
from pathlib import Path
from typing import Dict, Any

def process_log_file(log_file_path: str) -> Dict[str, Any]:
    """Process a single ChatDev log file and extract required information."""
    
    result = {
        "project_name": None,
        "task_prompt": None,
        "phases": [],
        "software_info": {}
    }
    
    current_phase = None
    current_phase_tokens = []
    project_name_found = False
    task_prompt_found = False
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Extract project_name (first occurrence only) - look for both formats
        if not project_name_found and "**project_name**" in line:
            # Format 1: **project_name**: value
            if "**project_name**:" in line:
                parts = line.split("**project_name**:")
                if len(parts) > 1:
                    result["project_name"] = parts[1].strip()
                    project_name_found = True
            # Format 2: table format | **project_name** | value |
            elif "|" in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    result["project_name"] = parts[2].strip()
                    project_name_found = True
        
        # Extract task_prompt (first occurrence only)
        if not task_prompt_found and "**task_prompt**" in line:
            # Format 1: **task_prompt**: value
            if "**task_prompt**:" in line:
                parts = line.split("**task_prompt**:")
                if len(parts) > 1:
                    result["task_prompt"] = parts[1].strip()
                    task_prompt_found = True
            # Format 2: table format | **task_prompt** | value |
            elif "|" in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    result["task_prompt"] = parts[2].strip()
                    task_prompt_found = True
        
        # Extract phase_name from table format
        if "**phase_name**" in line and "|" in line:
            # Save previous phase if it exists and has tokens
            if current_phase and current_phase_tokens:
                result["phases"].append({
                    "phase_name": current_phase,
                    "token_usage": current_phase_tokens.copy()
                })
            
            # Extract new phase name
            parts = line.split('|')
            if len(parts) >= 3:
                current_phase = parts[2].strip()
                current_phase_tokens = []
        
        # Extract token usage
        if "**[OpenAI_Usage_Info Receive]**" in line:
            token_info = {}
            
            # Look in the next few lines for token information
            for j in range(i+1, min(i+8, len(lines))):
                if j < len(lines):
                    next_line = lines[j].strip()
                    
                    if next_line.startswith("prompt_tokens:"):
                        token_info["prompt_tokens"] = int(next_line.split(":")[1].strip())
                    elif next_line.startswith("completion_tokens:"):
                        token_info["completion_tokens"] = int(next_line.split(":")[1].strip())
                    elif next_line.startswith("total_tokens:"):
                        token_info["total_tokens"] = int(next_line.split(":")[1].strip())
                    elif next_line.startswith("reasoning_tokens:"):
                        token_info["reasoning_tokens"] = int(next_line.split(":")[1].strip())
            
            if len(token_info) == 4:  # All four values found
                current_phase_tokens.append(token_info)
    
    # Save the last phase if exists
    if current_phase and current_phase_tokens:
        result["phases"].append({
            "phase_name": current_phase,
            "token_usage": current_phase_tokens
        })
    
    # Extract final software info - look for the very last occurrence
    final_software_section = ""
    
    # Find all occurrences of "Software Info" and take the last one
    software_info_positions = []
    for i, line in enumerate(lines):
        if "Software Info" in line and ("**[Software Info]**" in line or "Software Info:" in line):
            software_info_positions.append(i)
    
    if software_info_positions:
        last_pos = software_info_positions[-1]
        
        # Extract from the last software info section
        for i in range(last_pos, min(last_pos + 25, len(lines))):
            if i < len(lines):
                final_software_section += lines[i] + "\n"
        
        # Extract values from software info section
        other_patterns = [
            ("cost", [r'💰\*\*cost\*\*=\$([0-9.]+)', r'\*\*cost\*\*=\$([0-9.]+)']),
            ("num_code_files", [r'📃\*\*num_code_files\*\*=(\d+)', r'\*\*num_code_files\*\*=(\d+)']),
            ("code_lines", [r'📃\*\*code_lines\*\*=(\d+)', r'\*\*code_lines\*\*=(\d+)']),
            ("num_utterances", [r'🗣\*\*num_utterances\*\*=(\d+)', r'\*\*num_utterances\*\*=(\d+)']),
            ("num_self_reflections", [r'🤔\*\*num_self_reflections\*\*=(\d+)', r'\*\*num_self_reflections\*\*=(\d+)']),
            ("num_prompt_tokens", [r'❓\*\*num_prompt_tokens\*\*=(\d+)', r'\*\*num_prompt_tokens\*\*=(\d+)']),
            ("num_completion_tokens", [r'❗\*\*num_completion_tokens\*\*=(\d+)', r'\*\*num_completion_tokens\*\*=(\d+)']),
        ]
        
        for field, patterns in other_patterns:
            for pattern in patterns:
                match = re.search(pattern, final_software_section)
                if match:
                    if field == "cost":
                        result["software_info"][field] = float(match.group(1))
                    else:
                        result["software_info"][field] = int(match.group(1))
                    break

    # Now look for num_total_tokens, num_reasoning_tokens and duration in the ENTIRE final portion of the log
    # These appear after the Software Info section
    final_portion = "\n".join(lines[-50:])  # Last 50 lines of the file
    
    # Look for num_total_tokens
    total_tokens_patterns = [
        r'🌟\*\*num_total_tokens\*\*=(\d+)',
        r'\*\*num_total_tokens\*\*=(\d+)',
    ]
    
    for pattern in total_tokens_patterns:
        match = re.search(pattern, final_portion)
        if match:
            result["software_info"]["num_total_tokens"] = int(match.group(1))
            break

    # Look for num_reasoning_tokens
    reasoning_tokens_patterns = [
        r'💡\*\*num_reasoning_tokens\*\*=(\d+)',
        r'\*\*num_reasoning_tokens\*\*=(\d+)',
    ]

    for pattern in reasoning_tokens_patterns:
        match = re.search(pattern, final_portion)
        if match:
            result["software_info"]["num_reasoning_tokens"] = int(match.group(1))
            break

    # Look for duration
    duration_patterns = [
        r'🕑\*\*duration\*\*=([0-9.]+s)',
        r'\*\*duration\*\*=([0-9.]+s)',
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, final_portion)
        if match:
            result["software_info"]["duration"] = match.group(1)
            break
    
    return result

def process_log_folder(traces_folder_path: str, output_file: str = "ChatDev_GPT-5_Trace_Analysis_Results.json"):
    """Process all .log files in subdirectories of the specified folder."""
    
    traces_folder = Path(traces_folder_path)

    if not traces_folder.exists() or not traces_folder.is_dir():
        print(f"Traces folder not found: {traces_folder_path}")
        return
    
    # Find all .log files in subdirectories
    log_files = list(traces_folder.rglob("*.log"))

    if not log_files:
        print(f"No .log files found in subdirectories of {traces_folder_path}")
        return
    
    results = {"projects": []}
    
    for log_file in log_files:
        print(f"Processing: {log_file.name} (from {log_file.parent.name})")
        try:
            project_data = process_log_file(str(log_file))
            results["projects"].append(project_data)
            print(f"  ✓ Successfully processed {log_file.name}")
            print(f"    - Project: {project_data['project_name']}")
            print(f"    - Phases: {len(project_data['phases'])}")
            print(f"    - Software info fields: {list(project_data['software_info'].keys())}")
        except Exception as e:
            print(f"  ✗ Error processing {log_file.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Get the script directory for output file
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file
    
    # Save results to JSON file in the same directory as the script
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    print(f"Total projects processed: {len(results['projects'])}")

# Script usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        traces_folder_path = sys.argv[1]
    else:
        traces_folder_path = "/Users/macbook/Documents/MAS-Efficiency-Research/Experiments/RQ1/Traces/ChatDev_GPT-5"  # Change this to your traces folder path

    process_log_folder(traces_folder_path)
