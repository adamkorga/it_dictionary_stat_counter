import argparse
import statistics
import sys
import csv
import os
from bs4 import BeautifulSoup


def parse_document(html_path):
    """
    Parse the HTML document and build a nested structure of parts, sections, and subsections.
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    report = []
    current_part = None
    current_section = None
    current_subsection = None

    # Iterate over all elements
    for elem in soup.body.descendants:
        if not hasattr(elem, 'name') or not elem.name:
            continue

        if elem.name == 'h1':  # New part
            part_title = elem.get_text(strip=True)
            if not part_title:
                continue
            current_part = {
                'part': part_title,
                'sections': []
            }
            report.append(current_part)
            current_section = None
            current_subsection = None
        elif elem.name == 'h2' and current_part is not None:
            sec_title = elem.get_text(strip=True)
            if not sec_title:
                continue
            section = {
                'title': sec_title,
                'level': 2,
                'tables': [],
                'text_chunks': [],
                'intro_length': 0,
                'quote_hint_length': 0,
                'unfinished': False,
                'subsections': [],
                'has_table': False
            }
            current_part['sections'].append(section)
            current_section = section
            current_subsection = None
        elif elem.name == 'h3' and current_section is not None:
            sub_title = elem.get_text(strip=True)
            if not sub_title:
                continue
            subsection = {
                'title': sub_title,
                'level': 3,
                'tables': [],
                'text_chunks': [],
                'intro_length': 0,
                'quote_hint_length': 0,
                'unfinished': False,
                'has_table': False
            }
            current_section['subsections'].append(subsection)
            current_subsection = subsection
        elif elem.name == 'table' and current_section is not None:
            # Determine which section/subsection to update
            target_section = current_subsection if current_subsection else current_section
            
            # Calculate intro length from text preceding the table
            if target_section['text_chunks']:
                intro_text = ' '.join(target_section['text_chunks'])
                target_section['intro_length'] = len(intro_text)
                # Clear text chunks since they're now counted as intro
                target_section['text_chunks'] = []
            
            # Mark that this section has a table
            target_section['has_table'] = True
            
            # Count rows excluding header
            rows = elem.find_all('tr')
            count_terms = max(len(rows) - 1, 0)
            target_section['tables'].append(count_terms)
        elif elem.name == 'blockquote' and current_section is not None:
            # This is now handled as part of text collection
            pass
        elif elem.name == 'p' and current_section is not None:
            # Check if this paragraph is inside a table - if so, skip it
            if elem.find_parent('table') is not None:
                continue
                
            text = elem.get_text(strip=True)
            # Determine which section/subsection to update
            target_section = current_subsection if current_subsection else current_section
            target_section['text_chunks'].append(text)

    # Process remaining text chunks as quote/hint for sections that have tables
    def finalize_section_text(section):
        if section.get('has_table') and section['text_chunks']:
            # Text after table is quote/hint
            quote_text = ' '.join(section['text_chunks'])
            section['quote_hint_length'] = len(quote_text)
            section['text_chunks'] = []  # Clear since it's now counted as quote/hint
        
        # Process subsections
        for subsection in section.get('subsections', []):
            if subsection.get('has_table') and subsection['text_chunks']:
                # Text after table is quote/hint
                quote_text = ' '.join(subsection['text_chunks'])
                subsection['quote_hint_length'] = len(quote_text)
                subsection['text_chunks'] = []  # Clear since it's now counted as quote/hint
    
    for part in report:
        for section in part['sections']:
            finalize_section_text(section)

    return report


def generate_report(report, html_file_path):
    """
    Print a report of counts and details, and save to CSV files.
    """
    # Get base filename for CSV files
    base_name = os.path.splitext(os.path.basename(html_file_path))[0]
    summary_csv = f"{base_name}_summary.csv"
    breakdown_csv = f"{base_name}_breakdown.csv"
    
    # First, calculate unfinished status for all entries
    for part in report:
        for sec in part['sections']:
            if not sec['tables']:
                text = ' '.join(sec['text_chunks'])
                if 'TODO' in text:
                    sec['unfinished'] = True
            for sub in sec.get('subsections', []):
                if not sub['tables']:
                    text = ' '.join(sub['text_chunks'])
                    if 'TODO' in text:
                        sub['unfinished'] = True

    # Prepare summary data
    summary_data = []
    for part in report:
        sec_count = len(part['sections'])
        unfinished_sec_count = sum(1 for sec in part['sections'] if sec.get('unfinished'))
        sub_count = sum(len(sec.get('subsections', [])) for sec in part['sections'])
        unfinished_sub_count = sum(sum(1 for sub in sec.get('subsections', []) if sub.get('unfinished')) for sec in part['sections'])

        if sec_count > 0 or sub_count > 0:
            summary_data.append({
                'Part': part['part'],
                'Sections': sec_count,
                'Sections_Unfinished': unfinished_sec_count,
                'Subsections': sub_count,
                'Subsections_Unfinished': unfinished_sub_count
            })

    # Write summary CSV
    with open(summary_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Part', 'Sections', 'Sections_Unfinished', 'Subsections', 'Subsections_Unfinished']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_data)

    # Summary per part (stdout)
    print("Part | #Sections | #Subsections")
    print("-----|-----------|--------------")
    for row in summary_data:
        sec_str = f"{row['Sections']} ({row['Sections_Unfinished']})"
        sub_str = f"{row['Subsections']} ({row['Subsections_Unfinished']})"
        print(f"{row['Part']:<50} | {sec_str:<9} | {sub_str:<12}")

    # Prepare breakdown data
    breakdown_data = []
    
    def collect_entry_data(part_name, entry, number_prefix=""):
        # Determine terms or text length
        intro_length = entry.get('intro_length', 0) if entry.get('intro_length', 0) > 0 else '-'
        quote_hint_length = entry.get('quote_hint_length', 0) if entry.get('quote_hint_length', 0) > 0 else '-'
        
        if entry['tables']:
            terms_count = sum(entry['tables'])
            text_length = '-'
        else:
            terms_count = '-'
            text = ' '.join(entry['text_chunks'])
            text_length = len(text)
            if 'TODO' in text:
                entry['unfinished'] = True
        status = 'Unfinished' if entry.get('unfinished') else 'Done'
        
        breakdown_data.append({
            'Part': part_name,
            'Number': number_prefix,
            'Title': entry['title'],
            'Level': f"h{entry['level']}",
            'Terms_Count': terms_count,
            'Intro_Length': intro_length,
            'Text_Length': text_length,
            'Quote_Hint_Length': quote_hint_length,
            'Status': status
        })

        if 'subsections' in entry:
            for i, sub in enumerate(entry['subsections'], 1):
                collect_entry_data(part_name, sub, number_prefix=f"{number_prefix}.{i}")

    for part_idx, part in enumerate(report, 1):
        for i, sec in enumerate(part['sections'], 1):
            collect_entry_data(part['part'], sec, number_prefix=f"{part_idx-1}.{i}")

    # Write breakdown CSV
    with open(breakdown_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Part', 'Number', 'Title', 'Level', 'Terms_Count', 'Intro_Length', 'Text_Length', 'Quote_Hint_Length', 'Status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(breakdown_data)

    print("\nDetailed breakdown:\n")
    print("Part | No. | Title | Level | Terms Count | Intro Length | Text Length | Quote/Hint Length | Status")
    print("-----|-----|-------|-------|-------------|--------------|-------------|------------------|--------")

    def print_entry(part_name, entry, number_prefix=""):
        # Determine terms or text length
        intro_length = entry.get('intro_length', 0) if entry.get('intro_length', 0) > 0 else '-'
        quote_hint_length = entry.get('quote_hint_length', 0) if entry.get('quote_hint_length', 0) > 0 else '-'
        
        if entry['tables']:
            terms_count = sum(entry['tables'])
            text_length = '-'
        else:
            terms_count = '-'
            text = ' '.join(entry['text_chunks'])
            text_length = len(text)
            if 'TODO' in text:
                entry['unfinished'] = True
        status = 'Unfinished' if entry.get('unfinished') else 'Done'
        print(f"{part_name} | {number_prefix} | {entry['title']} | h{entry['level']} | {terms_count} | {intro_length} | {text_length} | {quote_hint_length} | {status}")

        if 'subsections' in entry:
            for i, sub in enumerate(entry['subsections'], 1):
                print_entry(part_name, sub, number_prefix=f"{number_prefix}.{i}")

    for part_idx, part in enumerate(report, 1):
        for i, sec in enumerate(part['sections'], 1):
            print_entry(part['part'], sec, number_prefix=f"{part_idx-1}.{i}")

    # --- Terms Count Statistics ---
    all_term_counts = [
        entry['Terms_Count']
        for entry in breakdown_data
        if isinstance(entry['Terms_Count'], int)
    ]

    overall_avg = statistics.mean(all_term_counts) if all_term_counts else 0
    overall_stdev = statistics.stdev(all_term_counts) if len(all_term_counts) > 1 else 0

    part_term_counts = {}
    for entry in breakdown_data:
        if isinstance(entry['Terms_Count'], int):
            part_name = entry['Part']
            if part_name not in part_term_counts:
                part_term_counts[part_name] = []
            part_term_counts[part_name].append(entry['Terms_Count'])

    print("\n--- Terms Count Statistics ---")
    print(f"{'Part':<50} | {'Avg Terms/Section':<17} | {'Std Dev'}")
    print(f"{'-'*50}-|-------------------|---------")
    print(f"{'Entire Document':<50} | {overall_avg:<17.2f} | {overall_stdev:.2f}")

    for part_name, counts in sorted(part_term_counts.items()):
        avg = statistics.mean(counts) if counts else 0
        stdev = statistics.stdev(counts) if len(counts) > 1 else 0
        print(f"{part_name:<50} | {avg:<17.2f} | {stdev:.2f}")
    
    print(f"\nCSV files created: {summary_csv}, {breakdown_csv}")


def main():
    parser = argparse.ArgumentParser(description="Analyze IT Dictionary HTML structure")
    parser.add_argument('html_file', help='Path to ITdictionary.html')
    args = parser.parse_args()

    report = parse_document(args.html_file)
    generate_report(report, args.html_file)


if __name__ == '__main__':
    main()
