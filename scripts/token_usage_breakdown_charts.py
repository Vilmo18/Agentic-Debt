import json
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from collections import defaultdict, Counter
from scipy import stats

def aggregate_phase_tokens(phases: List[Dict[str, Any]]) -> Dict[str, int]:
    """Aggregate total tokens by phase name, maintaining order of first appearance and merging specific phases."""
    phase_tokens = {}
    phase_order = []  # Track order of first appearance
    
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
    
    for phase in phases:
        original_phase_name = phase["phase_name"]
        
        # Map to merged phase name if applicable
        phase_name = phase_mapping.get(original_phase_name, original_phase_name)
        
        # Sum up total tokens for this phase occurrence
        phase_total = sum(usage["total_tokens"] for usage in phase["token_usage"])
        
        # Add to existing phase total or create new entry
        if phase_name in phase_tokens:
            phase_tokens[phase_name] += phase_total
        else:
            phase_tokens[phase_name] = phase_total
            phase_order.append(phase_name)  # Track first appearance
    
    # Return ordered dictionary to maintain phase order
    return {phase: phase_tokens[phase] for phase in phase_order}

def create_pie_chart(project_data: Dict[str, Any], output_path: Path) -> Tuple[Dict[str, float], str, float]:
    """Create and save a pie chart for a single project. Returns phase percentages and highest phase info."""
    project_name = project_data["project_name"]
    phases = project_data["phases"]
    
    # Aggregate tokens by phase (maintaining order)
    phase_tokens = aggregate_phase_tokens(phases)
    
    # Calculate total tokens
    total_tokens = sum(phase_tokens.values())
    
    # Prepare data for pie chart (maintaining order)
    labels = list(phase_tokens.keys())
    sizes = list(phase_tokens.values())
    percentages = [(tokens / total_tokens) * 100 for tokens in sizes]
    
    # Find the largest slice
    max_idx = sizes.index(max(sizes))
    highest_phase = labels[max_idx]
    highest_percentage = percentages[max_idx]
    
    # Create explode array (0.1 for the largest slice, 0 for others)
    explode = [0.1 if i == max_idx else 0 for i in range(len(sizes))]
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create pie chart without labels and without autopct
    # Let matplotlib use its default colors
    wedges, texts = ax.pie(sizes, 
                          labels=None,  # No labels on the pie
                          startangle=90,
                          explode=explode)
    
    # Add title
    plt.title(f'Token Usage by Phase (ChatDev with GPT-5 Reasoning) - {project_name}\nTotal Tokens: {total_tokens:,}', 
              fontsize=16, pad=20, fontweight='bold')
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.axis('equal')
    
    # Always show legend (positioned to the right)
    # Move pie to the left to make room for legend
    ax.set_position([0.1, 0.1, 0.5, 0.8])
    
    # Create legend entries with phase name, percentage, and token count
    legend_labels = [f'{phase}: {pct:.1f}% ({tokens:,})' 
                    for phase, pct, tokens in zip(labels, percentages, sizes)]
    
    # Highlight the largest phase in the legend
    for i, label in enumerate(legend_labels):
        if i == max_idx:
            legend_labels[i] = f'★ {label}'  # Add star to largest
    
    ax.legend(wedges, legend_labels,
             title="Phases",
             loc="center left",
             bbox_to_anchor=(1, 0, 0.5, 1),
             fontsize=10,
             title_fontsize=11)
    
    # Tight layout
    plt.tight_layout()
    
    # Save the figure
    output_file = output_path / f"{project_name}_token_distribution.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Created pie chart: {output_file}")
    
    # Also print summary statistics
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Phase breakdown (in order of appearance):")
    for phase, tokens in phase_tokens.items():
        percentage = (tokens / total_tokens) * 100
        star = "★" if list(phase_tokens.values()).index(tokens) == max_idx else " "
        print(f"    {star} {phase}: {tokens:,} tokens ({percentage:.1f}%)")
    
    # Report highest phase for this project
    print(f"  >>> HIGHEST TOKEN USER: {highest_phase} with {highest_percentage:.1f}%")
    print("-" * 60)
    print()
    
    # Create percentage dictionary for averaging
    phase_percentages = {phase: pct for phase, pct in zip(labels, percentages)}
    
    return phase_percentages, highest_phase, highest_percentage

def create_descriptive_statistics_table(all_phase_percentages: Dict[str, List[float]], 
                                       output_path: Path,
                                       total_projects: int):
    """Create a descriptive statistics table for all phases and save to text file."""
    
    # Define fixed phase order
    fixed_phase_order = [
        "Design",
        "Coding",
        "Code Completion",
        "Code Review",
        "Testing",
        "Documentation"
    ]
    
    # Calculate statistics for each phase
    stats_table = []
    
    for phase in fixed_phase_order:
        if phase in all_phase_percentages and len(all_phase_percentages[phase]) > 0:
            values = np.array(all_phase_percentages[phase])
            
            # Calculate statistics
            mean_val = np.mean(values)
            std_val = np.std(values, ddof=1) if len(values) > 1 else 0.0
            median_val = np.median(values)
            min_val = np.min(values)
            max_val = np.max(values)
            
            # Shapiro-Wilk test for normality (only if n >= 3)
            if len(values) >= 3:
                shapiro_stat, p_value = stats.shapiro(values)
                is_normal = "Yes" if p_value > 0.05 else "No"
                normality_str = f"{shapiro_stat:.4f} (p={p_value:.4f})"
            else:
                is_normal = "N/A"
                normality_str = "N/A (n < 3)"
            
            stats_table.append({
                'Phase': phase,
                'N': len(values),
                'Mean': mean_val,
                'SD': std_val,
                'Median': median_val,
                'Min': min_val,
                'Max': max_val,
                'Shapiro-Wilk': normality_str,
                'Normal': is_normal
            })
    
    # Write to text file
    output_file = output_path / "descriptive_statistics_table.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 140 + "\n")
        f.write("DESCRIPTIVE STATISTICS: TOKEN USAGE BY PHASE (ChatDev with GPT-5 Reasoning)\n")
        f.write(f"Based on {total_projects} projects\n")
        f.write("=" * 140 + "\n\n")
        
        f.write("Statistics calculated only from projects where each phase appears.\n")
        f.write("All values represent percentages (%) of total tokens used in that project.\n")
        f.write("Shapiro-Wilk Test: p > 0.05 suggests data follows normal distribution.\n")
        f.write("\n" + "=" * 140 + "\n\n")
        
        # Header
        f.write(f"{'Phase':<30} {'N':<5} {'Mean':<8} {'SD':<8} {'Median':<8} {'Min':<8} {'Max':<8} {'Normal':<8}\n")
        f.write("-" * 140 + "\n")
        
        # Data rows
        for row in stats_table:
            f.write(f"{row['Phase']:<30} "
                   f"{row['N']:<5} "
                   f"{row['Mean']:>7.1f} "
                   f"{row['SD']:>7.1f} "
                   f"{row['Median']:>7.1f} "
                   f"{row['Min']:>7.1f} "
                   f"{row['Max']:>7.1f} "
                   f"{row['Normal']:<8}\n")
        
        f.write("\n" + "=" * 140 + "\n\n")
        
        # Detailed Shapiro-Wilk results
        f.write("SHAPIRO-WILK TEST DETAILS:\n")
        f.write("-" * 140 + "\n")
        for row in stats_table:
            f.write(f"{row['Phase']:<30} {row['Shapiro-Wilk']}\n")
        
        f.write("\n" + "=" * 140 + "\n")
    
    print(f"\nDescriptive statistics table saved to: {output_file}")
    
    # Also print to console
    print("\n" + "=" * 140)
    print("DESCRIPTIVE STATISTICS TABLE")
    print("=" * 140)
    print(f"{'Phase':<30} {'N':<5} {'Mean':<8} {'SD':<8} {'Median':<8} {'Min':<8} {'Max':<8} {'Normal':<8}")
    print("-" * 140)
    for row in stats_table:
        print(f"{row['Phase']:<30} "
              f"{row['N']:<5} "
              f"{row['Mean']:>7.1f} "
              f"{row['SD']:>7.1f} "
              f"{row['Median']:>7.1f} "
              f"{row['Min']:>7.1f} "
              f"{row['Max']:>7.1f} "
              f"{row['Normal']:<8}")
    print("=" * 140)

def create_average_bar_chart(all_project_percentages: List[Dict[str, float]], 
                            output_path: Path,
                            highest_phase_info: Dict[str, List[float]],
                            all_phase_percentages: Dict[str, List[float]],
                            highest_phase_counter: Counter):
    """Create an average bar chart across all projects showing mean and std dev."""
    total_projects = len(all_project_percentages)
    
    # Define fixed phase order
    fixed_phase_order = [
        "Design",
        "Coding",
        "Code Completion",
        "Code Review",
        "Testing",
        "Documentation"
    ]
    
    # Calculate statistics for each phase
    phase_stats = {}
    for phase in fixed_phase_order:
        # Get percentages ONLY from projects where this phase appears
        phase_percentages = [project[phase] for project in all_project_percentages if phase in project]
        
        if len(phase_percentages) > 0:
            avg_when_present = np.mean(phase_percentages)
            std_when_present = np.std(phase_percentages, ddof=1) if len(phase_percentages) > 1 else 0.0
            
            # Perform Shapiro-Wilk test for normality (only if n >= 3)
            normality_test = None
            is_normal = None
            if len(phase_percentages) >= 3:
                stat, p_value = stats.shapiro(phase_percentages)
                normality_test = {'statistic': stat, 'p_value': p_value}
                # Common threshold: p > 0.05 suggests normal distribution
                is_normal = p_value > 0.05
            
            phase_stats[phase] = {
                'average': avg_when_present,
                'std': std_when_present,
                'count': len(phase_percentages),
                'min': min(phase_percentages),
                'max': max(phase_percentages),
                'all_values': sorted(phase_percentages),
                'normality_test': normality_test,
                'is_normal': is_normal
            }
    
    # Filter out phases that don't appear in any project
    labels = [phase for phase in fixed_phase_order if phase in phase_stats]
    
    # Prepare data for bar chart (maintaining fixed order)
    averages = [phase_stats[label]['average'] for label in labels]
    std_devs = [phase_stats[label]['std'] for label in labels]
    counts = [phase_stats[label]['count'] for label in labels]
    
    # Create compact figure
    fig, ax = plt.subplots(figsize=(7, 6))
    
    # Create positions for bars with spacing 0.2 units apart instead of default 1.0
    x_pos = np.arange(len(labels)) * 0.2
    
    # Bar size (width=0.1)
    bars = ax.bar(x_pos, averages, yerr=std_devs, 
                   width=0.1,
                   capsize=5, alpha=0.8,
                   edgecolor='black', linewidth=1.5)
    
    # Add value labels on top of bars
    for i, (bar, avg, std, count) in enumerate(zip(bars, averages, std_devs, counts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + std + 1,
                f'{avg:.1f}%±{std:.1f}%\n(n={count})',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Highest average phase
    max_idx = averages.index(max(averages))
    # bars[max_idx].set_edgecolor('gold')
    # bars[max_idx].set_linewidth(3)
    
    # Set labels and title
    ax.set_ylabel('Average Token Usage (%)', fontsize=13, fontweight='bold')
    ax.set_title(f'ChatDev with GPT-5 Reasoning',
                 fontsize=15, fontweight='bold', pad=15)
    
    # Set x-axis labels
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=11)

    # Tick label sizes
    ax.tick_params(axis='both', which='major', labelsize=11)

    # Add grid for easier reading
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Set y-axis limits to accommodate text labels above bars
    max_height = max([avg + std for avg, std in zip(averages, std_devs)])
    ax.set_ylim(bottom=0, top=max_height * 1.15)

    # Adjust x-axis limits to fit spacing
    ax.set_xlim(-0.15, (len(labels) - 1) * 0.2 + 0.15)

    # Tight layout with reduced padding
    plt.tight_layout(pad=1.5)
    
    # Save the figure with high DPI for clarity
    output_file = output_path / "AVERAGE_token_distribution_BAR.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n{'='*80}")
    print(f"Created average bar chart: {output_file}")
    print(f"{'='*80}")
    
    # Report which phase was highest most often
    print(f"\nMOST FREQUENTLY HIGHEST PHASE:")
    print("-" * 80)
    for phase, count in highest_phase_counter.most_common():
        print(f"  {phase}: {count} times ({count/total_projects*100:.1f}% of projects)")
    
    print("\nNORMALITY TEST RESULTS (Shapiro-Wilk Test):")
    print("(H0: Data follows normal distribution; p > 0.05 suggests normality)")
    print("-" * 80)
    for phase in labels:
        stats_data = phase_stats[phase]
        if stats_data['normality_test']:
            p_val = stats_data['normality_test']['p_value']
            result = "✓ NORMAL" if stats_data['is_normal'] else "✗ NOT NORMAL"
            print(f"  {phase}: p-value = {p_val:.4f} → {result}")
        else:
            print(f"  {phase}: Insufficient data (n={stats_data['count']}) for normality test")
    
    print("\nAVERAGE PHASE STATISTICS ACROSS ALL PROJECTS:")
    print("(Averages calculated only from projects where phase appears)")
    print("-" * 80)
    
    for phase in labels:
        stats_data = phase_stats[phase]
        star = "★" if labels[max_idx] == phase else " "
        
        # Add normality indicator
        normality_indicator = ""
        if stats_data['is_normal'] is not None:
            normality_indicator = " [NORMAL]" if stats_data['is_normal'] else " [NON-NORMAL]"
        
        print(f"\n{star} {phase}{normality_indicator}:")
        print(f"    Average When Present: {stats_data['average']:.1f}% ± {stats_data['std']:.1f}%")
        print(f"    Range When Present: {stats_data['min']:.1f}% - {stats_data['max']:.1f}%")
        print(f"    Appears in: {stats_data['count']}/{total_projects} projects")
        
        # Show all sorted percentage values for this phase
        print(f"    All percentage values (sorted): {', '.join(f'{v:.1f}%' for v in stats_data['all_values'])}")
        
        # If this phase was highest in any project, show the percentage range
        if phase in highest_phase_info and highest_phase_info[phase]:
            values = sorted(highest_phase_info[phase])
            print(f"    >>> When highest in projects: {', '.join(f'{v:.1f}%' for v in values)}")
    print("-" * 80)

def process_json_file(json_file_path: str, output_dir: str = None):
    """Process the JSON file and create pie charts for each project and a bar chart for averages."""
    json_path = Path(json_file_path)
    
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_file_path}")
        return
    
    # Set output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        # Default to same directory as JSON file
        output_path = json_path.parent / "token_distribution_charts"
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True)
    
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    projects = data.get("projects", [])
    
    if not projects:
        print("No projects found in the JSON file.")
        return
    
    print(f"Processing {len(projects)} projects...")
    print(f"Output directory: {output_path}\n")
    
    # Track percentages for averaging and highest phases
    all_project_percentages = []
    highest_phase_info = defaultdict(list)  # phase -> list of percentages when it was highest
    highest_phase_counter = Counter()  # Count how many times each phase was highest
    all_phase_percentages = defaultdict(list)  # phase -> list of ALL percentages across projects
    
    # Process each project
    for project in projects:
        try:
            phase_percentages, highest_phase, highest_percentage = create_pie_chart(project, output_path)
            all_project_percentages.append(phase_percentages)
            
            # Track highest phase info
            highest_phase_info[highest_phase].append(highest_percentage)
            highest_phase_counter[highest_phase] += 1
            
            # Track all percentages for each phase
            for phase, pct in phase_percentages.items():
                all_phase_percentages[phase].append(pct)
            
        except Exception as e:
            print(f"Error processing project {project.get('project_name', 'Unknown')}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\nAll individual pie charts saved to: {output_path}")
    
    # Create average bar chart
    if len(all_project_percentages) > 0:
        create_average_bar_chart(all_project_percentages, output_path, highest_phase_info, 
                               all_phase_percentages, highest_phase_counter)
        
        # Create descriptive statistics table
        create_descriptive_statistics_table(all_phase_percentages, output_path, len(projects))

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
    
    process_json_file(json_file_path, output_dir)