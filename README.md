# IT Dictionary Statistics Analyzer

## Purpose

This tool analyzes the structure and content statistics of the IT Dictionary book to ensure that all parts are similar in size and content distribution. It provides detailed metrics on sections, subsections, term counts, text lengths, and completion status to help maintain consistency across the book's different parts.

## Requirements

- **Python**: Tested on Python 3.10.12
- **Dependencies**: `beautifulsoup4` (install with `pip install beautifulsoup4`)
- **Input**: IT Dictionary book content exported in HTML format

## Usage

```bash
python3 analyze_it_dictionary.py <path_to_html_file>
```

Example:
```bash
python3 analyze_it_dictionary.py ITdictionary.html
```

## Output Files and STDOUT

The script generates both console output and CSV files:

### Console Output (STDOUT)
1. **Summary Table**: Overview of sections and subsections per part with unfinished counts
2. **Detailed Breakdown**: Complete hierarchical listing of all sections and subsections with statistics

### Generated CSV Files
- **`<filename>_summary.csv`**: Summary statistics per part
- **`<filename>_breakdown.csv`**: Detailed breakdown of all sections and subsections

## Statistics Description

### Summary Statistics (per Part)
- **Sections**: Total number of h2 sections
- **Sections_Unfinished**: Number of sections marked as unfinished (containing "TODO")
- **Subsections**: Total number of h3 subsections  
- **Subsections_Unfinished**: Number of subsections marked as unfinished

### Detailed Statistics (per Section/Subsection)
- **Number**: Hierarchical numbering using PART.SECTION[.SUBSECTION] format (e.g., 1.1, 1.2, 2.1, 2.2.1)
- **Title**: Section or subsection title
- **Level**: Header level (h2 for sections, h3 for subsections)
- **Terms Count**: Number of terms in tables (excluding header row), or `-` if no table
- **Intro Length**: Character count of introductory text before tables, or `-` if no intro text
- **Text Length**: Character count of text content for sections without tables, or `-` if has table
- **Quote/Hint Length**: Character count of explanatory text after tables, or `-` if no post-table text
- **Status**: `Done` or `Unfinished` (based on presence of "TODO" in text)

### Numbering Strategy
The tool uses a **PART.SECTION[.SUBSECTION]** numbering format:
- **Sections**: Numbered as `PART.SECTION` (e.g., 1.1, 1.2, 2.1, 2.2)
- **Subsections**: Numbered as `PART.SECTION.SUBSECTION` (e.g., 1.1.1, 1.1.2, 2.1.1)
- **Parts without content sections** (like "Table of Contents") are skipped in the numbering
- Only parts containing actual content sections (h2 elements) contribute to the part numbering
- This ensures consistent numbering that reflects the actual content structure

### Structure Recognition
The analyzer recognizes the following HTML structure:
- **Parts**: Identified by `<h1>` tags
- **Sections**: Identified by `<h2>` tags
- **Subsections**: Identified by `<h3>` tags
- **Tables**: Term definitions with row counting (header excluded)
- **Text Content**: Paragraphs (`<p>`) categorized as intro, content, or quote/hint based on position relative to tables
