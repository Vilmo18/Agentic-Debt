import json
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
from typing import Dict, Any

def create_token_distribution_bar_chart(project_data: Dict[str, Any], output_path: Path):
    """Create a bar chart showing token distribution (input, output, reasoning) for each phase."""
    project_name = project_data["project_name"]
    phases = project_data["phases"]
    
    # Define phase mappings
    phase_mapping = {
        "DemandAnalysis": "Design",
        "LanguageChoose": "Design",
        "CodeComplete": "Code Completion",
        "CodeReviewComment": "Code Review",
        "CodeReviewModification": "Code Review",
        "TestErrorSummary": "Testing",
        "TestModification": "Testing",
        "EnvironmentDoc": "Documentation",
        "Reflection": "Documentation",
        "Manual": "Documentation"
    }
    
    # Aggregate tokens by phase
    phase_token_data = {}
    phase_order = []  # Track order of first appearance
    
    for phase in phases:
        original_phase_name = phase["phase_name"]
        phase_name = phase_mapping.get(original_phase_name, original_phase_name)
        
        # Initialize phase data if not exists
        if phase_name not in phase_token_data:
            phase_token_data[phase_name] = {
                'input': 0,
                'output': 0,
                'reasoning': 0
            }
            phase_order.append(phase_name)
        
        # Sum up tokens for this phase
        for usage in phase["token_usage"]:
            phase_token_data[phase_name]['input'] += usage["prompt_tokens"]
            # Output = completion - reasoning
            phase_token_data[phase_name]['output'] += (usage["completion_tokens"] - usage["reasoning_tokens"])
            phase_token_data[phase_name]['reasoning'] += usage["reasoning_tokens"]
    
    # Calculate totals across all phases
    total_data = {
        'input': sum(p['input'] for p in phase_token_data.values()),
        'output': sum(p['output'] for p in phase_token_data.values()),
        'reasoning': sum(p['reasoning'] for p in phase_token_data.values())
    }
    
    # Prepare data for plotting
    categories = ['Input', 'Output', 'Reasoning']
    phase_labels = phase_order + ['TOTAL']
    
    # Define colors for each category
    colors = {
        'input': "#0C84D3",      # Light blue
        'output': "#17C15E",     # Light green
        'reasoning': "#E4B048"   # Light orange
    }
    
    # Set up the figure
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Width of each bar and spacing
    bar_width = 0.25
    bar_spacing = 0.05  # Space between bars within a phase
    group_spacing = 0.4  # Space between phase groups
    
    # Calculate group width
    group_width = len(categories) * bar_width + (len(categories) - 1) * bar_spacing + group_spacing
    
    # X positions for each group
    x_positions = np.arange(len(phase_labels)) * group_width
    
    # Store all bars for finding max values
    all_bars = []
    
    # Create bars for legend (we'll use dummy bars for legend)
    dummy_bars = []
    for category, color_key in zip(categories, ['input', 'output', 'reasoning']):
        dummy_bar = ax.bar(0, 0, bar_width, color=colors[color_key], label=category)
        dummy_bars.append(dummy_bar)
    
    # Plot bars for each phase
    for i, phase_label in enumerate(phase_labels):
        if phase_label == 'TOTAL':
            data = total_data
        else:
            data = phase_token_data[phase_label]
        
        # Values for this phase
        values = [data['input'], data['output'], data['reasoning']]
        
        # Find the maximum value index for this group
        max_idx = values.index(max(values))
        
        # Plot bars for each category with spacing
        for j, (value, color_key) in enumerate(zip(values, ['input', 'output', 'reasoning'])):
            x_pos = x_positions[i] + j * (bar_width + bar_spacing)
            
            # Create bar with specific color
            bar = ax.bar(x_pos, value, bar_width, 
                         color=colors[color_key],
                         alpha=0.85,
                         edgecolor='black',
                         linewidth=1)
            
            # Emphasize the highest bar in this group with dark red border
            if j == max_idx:
                bar[0].set_edgecolor("#D31414")  # Dark red
                bar[0].set_linewidth(2.5)
            
            # Add value label on top of bar
            height = bar[0].get_height()
            ax.text(bar[0].get_x() + bar[0].get_width()/2., height + 0.01 * max(max(total_data.values()), 1),
                    f'{int(value):,}',
                    ha='center', va='bottom', fontsize=8, rotation=45 if value > 10000 else 0)
            
            all_bars.append((bar[0], value))
    
    # Set x-axis labels - center them under each group
    ax.set_xticks(x_positions + (len(categories) - 1) * (bar_width + bar_spacing) / 2)
    ax.set_xticklabels(phase_labels, rotation=45, ha='right', fontsize=10)
    
    # Separate TOTAL with a vertical line - position it between the last phase and TOTAL
    if len(phase_labels) > 1:
        # Calculate the midpoint between the last phase group and TOTAL group
        last_phase_end = x_positions[-2] + (len(categories) - 1) * (bar_width + bar_spacing) + bar_width
        total_start = x_positions[-1]
        line_position = (last_phase_end + total_start) / 2
        ax.axvline(x=line_position, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    
    # Labels and title
    ax.set_xlabel('Phase', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Tokens', fontsize=12, fontweight='bold')
    ax.set_title(f'Token Distribution by Phase (ChatDev with GPT-5 Reasoning) - {project_name}\n(Input vs Output vs Reasoning)',
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Create first legend for token types (horizontal)
    first_legend = ax.legend(loc='upper left', fontsize=10, title='Token Type', 
                            framealpha=0.9, ncol=3, columnspacing=1)
    
    # Add second legend for emphasized bars (horizontal)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='white', edgecolor='#D31414', linewidth=2.5, label='Highest in phase')
    ]
    ax.legend(handles=legend_elements, loc='upper center', fontsize=10, 
              framealpha=0.9, bbox_to_anchor=(0.5, 0.98))
    
    # Add back the first legend
    ax.add_artist(first_legend)
    
    # Set y-axis to start at 0 and add padding for labels
    ax.set_ylim(bottom=0, top=max([b[1] for b in all_bars]) * 1.15)
    
    # Format y-axis with comma separators
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # Tight layout
    plt.tight_layout()
    
    # Save the figure
    output_file = output_path / f"{project_name}_token_distribution_bars.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Created token distribution bar chart: {output_file}")
    
    # Print summary statistics
    print(f"  Total tokens across all phases:")
    print(f"    Input: {total_data['input']:,}")
    print(f"    Output: {total_data['output']:,}")
    print(f"    Reasoning: {total_data['reasoning']:,}")
    print(f"    Total (Input + Output + Reasoning): {sum(total_data.values()):,}")
    print(f"  Phase breakdown:")
    for phase in phase_order:
        data = phase_token_data[phase]
        print(f"    {phase}:")
        print(f"      Input: {data['input']:,}, Output: {data['output']:,}, Reasoning: {data['reasoning']:,}")
    print("-" * 60)
    print()

def analyze_non_input_dominated_phases(project_data: Dict[str, Any]):
    """Analyze which phases have output or reasoning tokens as the highest category."""
    project_name = project_data["project_name"]
    phases = project_data["phases"]
    
    # Phase mapping
    phase_mapping = {
        "DemandAnalysis": "Design",
        "LanguageChoose": "Design",
        "CodeComplete": "Code Completion",
        "CodeReviewComment": "Code Review",
        "CodeReviewModification": "Code Review",
        "TestErrorSummary": "Testing",
        "TestModification": "Testing",
        "EnvironmentDoc": "Documentation",
        "Reflection": "Documentation",
        "Manual": "Documentation"
    }
    
    # Aggregate tokens by phase
    phase_token_data = {}
    phase_order = []
    
    for phase in phases:
        original_phase_name = phase["phase_name"]
        phase_name = phase_mapping.get(original_phase_name, original_phase_name)
        
        if phase_name not in phase_token_data:
            phase_token_data[phase_name] = {
                'input': 0,
                'output': 0,
                'reasoning': 0
            }
            phase_order.append(phase_name)
        
        for usage in phase["token_usage"]:
            phase_token_data[phase_name]['input'] += usage["prompt_tokens"]
            phase_token_data[phase_name]['output'] += (usage["completion_tokens"] - usage["reasoning_tokens"])
            phase_token_data[phase_name]['reasoning'] += usage["reasoning_tokens"]
    
    # Find phases where output or reasoning is highest
    non_input_dominated_phases = []
    
    for phase_name in phase_order:
        data = phase_token_data[phase_name]
        values = [data['input'], data['output'], data['reasoning']]
        max_value = max(values)
        max_category_idx = values.index(max_value)
        
        if max_category_idx != 0:  # Not input
            category_name = ['input', 'output', 'reasoning'][max_category_idx]
            non_input_dominated_phases.append({
                'phase': phase_name,
                'dominant_category': category_name,
                'values': data
            })
    
    return non_input_dominated_phases, phase_order

def process_json_file_for_bars(json_file_path: str, output_dir: str = None):
    """Process the JSON file and create token distribution bar charts for each project."""
    json_path = Path(json_file_path)
    
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_file_path}")
        return
    
    # Set output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        # Default to same directory as JSON file
        output_path = json_path.parent / "token_input_vs_output_bar_charts"
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True)
    
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    projects = data.get("projects", [])
    
    if not projects:
        print("No projects found in the JSON file.")
        return
    
    print(f"Processing {len(projects)} projects for token input vs output bar charts...")
    print(f"Output directory: {output_path}\n")
    
    # Store analysis results for all projects
    all_analysis_results = []
    
    # Aggregate counts for each phase across all projects
    phase_aggregate = {}
    
    # Process each project
    for project in projects:
        try:
            # Create the bar chart
            create_token_distribution_bar_chart(project, output_path)
            
            # Perform analysis and store results
            non_input_dominated, total_phases = analyze_non_input_dominated_phases(project)
            
            all_analysis_results.append({
                'project_name': project.get('project_name', 'Unknown'),
                'non_input_dominated': non_input_dominated,
                'total_phases': total_phases
            })
            
            # Update aggregate counts
            for phase_info in non_input_dominated:
                phase = phase_info['phase']
                category = phase_info['dominant_category']
                
                if phase not in phase_aggregate:
                    phase_aggregate[phase] = {'output': 0, 'reasoning': 0}
                
                phase_aggregate[phase][category] += 1
            
        except Exception as e:
            print(f"Error processing project {project.get('project_name', 'Unknown')}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\nAll bar charts saved to: {output_path}")
    
    # Display analysis at the end
    print("\n")
    print("=" * 80)
    print("ANALYSIS: Phases where Output or Reasoning tokens dominate")
    print("=" * 80)
    
    for result in all_analysis_results:
        project_name = result['project_name']
        non_input_dominated = result['non_input_dominated']
        total_phases = result['total_phases']
        
        print(f"\nAnalysis for {project_name}:")
        print("-" * 60)
        
        if non_input_dominated:
            print(f"Phases where Output or Reasoning dominates: {len(non_input_dominated)}/{len(total_phases)}")
            for phase_info in non_input_dominated:
                phase = phase_info['phase']
                cat = phase_info['dominant_category']
                vals = phase_info['values']
                print(f"  • {phase}: {cat.upper()} dominates")
                print(f"    (Input: {vals['input']:,}, Output: {vals['output']:,}, Reasoning: {vals['reasoning']:,})")
        else:
            print(f"  All {len(total_phases)} phases are input-dominated")
        
        # Summary count
        output_dominated = sum(1 for p in non_input_dominated if p['dominant_category'] == 'output')
        reasoning_dominated = sum(1 for p in non_input_dominated if p['dominant_category'] == 'reasoning')
        
        print(f"\nSummary:")
        print(f"  - Output-dominated phases: {output_dominated}")
        print(f"  - Reasoning-dominated phases: {reasoning_dominated}")
        print(f"  - Total non-input-dominated phases: {len(non_input_dominated)}")
        print("=" * 80)
    
    # Display aggregate analysis
    print("\n")
    print("=" * 80)
    print("AGGREGATE ANALYSIS: Phase dominance across all traces")
    print("=" * 80)
    print(f"Total traces analyzed: {len(all_analysis_results)}")
    print()
    
    if phase_aggregate:
        # Sort phases by total count (output + reasoning)
        sorted_phases = sorted(phase_aggregate.items(), 
                              key=lambda x: x[1]['output'] + x[1]['reasoning'], 
                              reverse=True)
        
        print("Phases with Output or Reasoning dominance (sorted by frequency):")
        print("-" * 60)
        
        total_output_count = 0
        total_reasoning_count = 0
        
        for phase, counts in sorted_phases:
            output_count = counts['output']
            reasoning_count = counts['reasoning']
            total_count = output_count + reasoning_count
            
            total_output_count += output_count
            total_reasoning_count += reasoning_count
            
            print(f"\n{phase}:")
            print(f"  Total times dominated (non-input): {total_count}")
            print(f"    - Output dominated: {output_count} times")
            print(f"    - Reasoning dominated: {reasoning_count} times")
            
            # Calculate percentages
            if total_count > 0:
                output_pct = (output_count / total_count) * 100
                reasoning_pct = (reasoning_count / total_count) * 100
                print(f"  Distribution: Output {output_pct:.1f}% | Reasoning {reasoning_pct:.1f}%")
        
        print("\n" + "=" * 60)
        print("OVERALL SUMMARY:")
        print("-" * 60)
        print(f"Total non-input dominations across all traces: {total_output_count + total_reasoning_count}")
        print(f"  - Output dominations: {total_output_count}")
        print(f"  - Reasoning dominations: {total_reasoning_count}")
        
        if (total_output_count + total_reasoning_count) > 0:
            output_pct = (total_output_count / (total_output_count + total_reasoning_count)) * 100
            reasoning_pct = (total_reasoning_count / (total_output_count + total_reasoning_count)) * 100
            print(f"\nOverall distribution: Output {output_pct:.1f}% | Reasoning {reasoning_pct:.1f}%")
        
        print(f"\nNumber of unique phases with non-input dominance: {len(phase_aggregate)}")
        
    else:
        print("No phases found with output or reasoning dominance across all traces.")
    
    print("=" * 80)

# Script usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # UPDATE this to your JSON file path
        json_file_path = "/Users/macbook/Documents/MAS-Efficiency-Research/Experiments/RQ1/Results/ChatDev_GPT-5/ChatDev_GPT-5_Trace_Analysis_Results.json"
        output_dir = None
    
    process_json_file_for_bars(json_file_path, output_dir)