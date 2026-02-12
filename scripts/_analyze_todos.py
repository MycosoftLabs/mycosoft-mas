"""
Analyze TODOs from gap report and categorize by priority.
Filters false positives and generates prioritized audit report.
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

# False positive patterns
FALSE_POSITIVE_PATTERNS = [
    r'_debug',
    r'_test',
    r'\.min\.js',
    r'\.min\.css',
    r'node_modules',
    r'\.pyc',
    r'__pycache__',
    r'\.git',
    r'dist/',
    r'build/',
    r'coverage/',
    r'\.next/',
    r'venv/',
    r'\.venv/',
]

# Production code patterns (real code to audit)
PRODUCTION_PATTERNS = [
    r'mycosoft_mas/',
    r'app/',
    r'components/',
    r'lib/',
    r'mindex_api/',
    r'mindex_etl/',
    r'firmware/',
]

# Priority keywords for categorization
CRITICAL_KEYWORDS = [
    'security', 'auth', 'password', 'secret', 'api key', 'token',
    'sql injection', 'xss', 'csrf', 'vulnerability',
    'crash', 'memory leak', 'data loss', 'corruption',
    'production', 'urgent', 'critical', 'blocker',
]

HIGH_KEYWORDS = [
    'broken', 'error', 'fail', 'bug', 'issue', 'problem',
    'user-facing', 'frontend', 'api endpoint', 'database',
    'important', 'must fix', 'needs fix',
]

MEDIUM_KEYWORDS = [
    'performance', 'optimize', 'refactor', 'improve',
    'clean up', 'technical debt', 'enhancement',
]

def is_false_positive(file_path: str, line: str) -> bool:
    """Check if this is a false positive."""
    # Check filename patterns
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    
    # Check if it's in production code
    is_production = any(re.search(pattern, file_path) for pattern in PRODUCTION_PATTERNS)
    
    # If it's a debug/test file name (not in pattern but in filename)
    filename = Path(file_path).name.lower()
    if any(word in filename for word in ['debug', 'test', 'tmp', 'temp', '_temp']):
        return True
    
    # If it's minified code (very long line with no spaces)
    if len(line) > 200 and line.count(' ') < 5:
        return True
    
    return not is_production

def categorize_priority(item: Dict) -> str:
    """Categorize item by priority based on content."""
    text = (item.get('message', '') + ' ' + item.get('line', '')).lower()
    kind = item.get('kind', '').upper()
    
    # Critical if marked as BUG or FIXME with critical keywords
    if kind in ['BUG', 'FIXME']:
        if any(keyword in text for keyword in CRITICAL_KEYWORDS):
            return 'CRITICAL'
    
    # High if marked as FIXME or has high keywords
    if kind == 'FIXME' or any(keyword in text for keyword in HIGH_KEYWORDS):
        return 'HIGH'
    
    # Medium if has medium keywords
    if any(keyword in text for keyword in MEDIUM_KEYWORDS):
        return 'MEDIUM'
    
    # Low for everything else (TODO, XXX, HACK without urgency)
    return 'LOW'

def analyze_gap_report(gap_report_path: str) -> Dict:
    """Analyze gap report and categorize TODOs."""
    with open(gap_report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('todos_fixmes', [])
    
    # Filter and categorize
    categorized = defaultdict(list)
    false_positives = 0
    
    for item in items:
        file_path = item.get('file', '')
        line = item.get('line', '')
        
        if is_false_positive(file_path, line):
            false_positives += 1
            continue
        
        priority = categorize_priority(item)
        categorized[priority].append(item)
    
    return {
        'categorized': categorized,
        'false_positives': false_positives,
        'total_items': len(items),
    }

def generate_report(analysis: Dict, output_path: str):
    """Generate markdown report."""
    categorized = analysis['categorized']
    false_positives = analysis['false_positives']
    total_items = analysis['total_items']
    
    report = []
    report.append("# TODO Audit Report - February 12, 2026\n")
    report.append("## Summary\n")
    report.append(f"- **Total items scanned**: {total_items}")
    report.append(f"- **False positives filtered**: {false_positives}")
    report.append(f"- **Real TODOs**: {total_items - false_positives}\n")
    
    report.append("### Priority Breakdown\n")
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = len(categorized.get(priority, []))
        report.append(f"- **{priority}**: {count}")
    report.append("")
    
    # Top 20 critical/high items
    report.append("## Top Priority Items to Fix\n")
    report.append("### Critical Priority\n")
    
    critical_items = categorized.get('CRITICAL', [])[:10]
    if critical_items:
        for i, item in enumerate(critical_items, 1):
            report.append(f"{i}. **{item['file']}:{item['line_no']}** (`{item['kind']}`)")
            report.append(f"   - {item['message']}")
            report.append(f"   - Line: `{item['line'].strip()}`")
            report.append("")
    else:
        report.append("No critical items found.\n")
    
    report.append("### High Priority\n")
    high_items = categorized.get('HIGH', [])[:10]
    if high_items:
        for i, item in enumerate(high_items, 1):
            report.append(f"{i}. **{item['file']}:{item['line_no']}** (`{item['kind']}`)")
            report.append(f"   - {item['message']}")
            report.append(f"   - Line: `{item['line'].strip()}`")
            report.append("")
    else:
        report.append("No high priority items found.\n")
    
    # Full breakdown by category
    report.append("## Full Category Breakdown\n")
    
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        items = categorized.get(priority, [])
        if not items:
            continue
        
        report.append(f"### {priority} Priority ({len(items)} items)\n")
        report.append("<details>")
        report.append(f"<summary>Show all {len(items)} {priority.lower()} priority items</summary>\n")
        
        for i, item in enumerate(items, 1):
            report.append(f"{i}. **{item['file']}:{item['line_no']}** (`{item['kind']}`)")
            report.append(f"   - {item['message'][:200]}")
            report.append("")
        
        report.append("</details>\n")
    
    # Recommendations
    report.append("## Recommendations\n")
    report.append("1. **Critical items** should be fixed immediately before next deployment")
    report.append("2. **High priority items** should be scheduled for this sprint")
    report.append("3. **Medium priority items** can be added to the backlog")
    report.append("4. **Low priority items** can be addressed during code cleanup sessions\n")
    
    report.append("## Next Steps\n")
    report.append("1. Create GitHub issues for all critical and high priority items")
    report.append("2. Assign owners for each critical item")
    report.append("3. Review medium priority items with the team")
    report.append("4. Run this audit weekly to track progress\n")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

if __name__ == '__main__':
    gap_report_path = Path(__file__).parent.parent / '.cursor' / 'gap_report_latest.json'
    output_path = Path(__file__).parent.parent / 'docs' / 'TODO_AUDIT_FEB12_2026.md'
    
    print("Analyzing gap report...")
    analysis = analyze_gap_report(str(gap_report_path))
    
    print(f"\nAnalysis complete:")
    print(f"  Total items: {analysis['total_items']}")
    print(f"  False positives: {analysis['false_positives']}")
    print(f"  Real TODOs: {analysis['total_items'] - analysis['false_positives']}")
    print(f"\nPriority breakdown:")
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = len(analysis['categorized'].get(priority, []))
        print(f"  {priority}: {count}")
    
    print(f"\nGenerating report: {output_path}")
    generate_report(analysis, str(output_path))
    print("Done!")
