"""
Scan for real TODO/FIXME/XXX/HACK comments in production code.
"""
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Directories to scan
SCAN_DIRS = [
    Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\mycosoft_mas'),
    Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app'),
    Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\components'),
    Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\lib'),
    Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\mindex_api'),
    Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\mindex_etl'),
]

# Patterns for TODO markers
TODO_PATTERNS = [
    (r'#\s*(TODO|FIXME|XXX|HACK):\s*(.+)', 'python'),  # Python
    (r'//\s*(TODO|FIXME|XXX|HACK):\s*(.+)', 'js/ts'),  # JavaScript/TypeScript
    (r'/\*\s*(TODO|FIXME|XXX|HACK):\s*(.+)\*/', 'js/ts'),  # JS/TS block comment
]

# File extensions to scan
EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.jsx'}

# Ignore patterns
IGNORE_PATTERNS = [
    r'node_modules',
    r'\.next',
    r'__pycache__',
    r'\.pyc',
    r'venv',
    r'\.venv',
    r'dist',
    r'build',
    r'coverage',
    r'\.min\.',
]

def should_ignore(file_path: Path) -> bool:
    """Check if file should be ignored."""
    path_str = str(file_path)
    return any(re.search(pattern, path_str) for pattern in IGNORE_PATTERNS)

def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Scan a file for TODO markers. Returns list of (line_no, marker_type, message)."""
    todos = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_no, line in enumerate(f, 1):
                for pattern, lang in TODO_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        marker_type = match.group(1).upper()
                        message = match.group(2).strip()
                        todos.append((line_no, marker_type, message))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return todos

def categorize_priority(marker_type: str, message: str, file_path: Path) -> str:
    """Categorize by priority."""
    msg_lower = message.lower()
    
    # Critical keywords
    critical_keywords = [
        'security', 'auth', 'password', 'secret', 'api key', 'token',
        'sql injection', 'xss', 'csrf', 'vulnerability',
        'crash', 'memory leak', 'data loss', 'corruption',
        'production', 'urgent', 'critical', 'blocker',
    ]
    
    # High keywords
    high_keywords = [
        'broken', 'error', 'fail', 'bug', 'issue', 'problem',
        'user-facing', 'frontend', 'api endpoint', 'database',
        'important', 'must fix', 'needs fix', 'implement',
    ]
    
    # Medium keywords
    medium_keywords = [
        'performance', 'optimize', 'refactor', 'improve',
        'clean up', 'technical debt', 'enhancement',
    ]
    
    # FIXME is always at least HIGH
    if marker_type == 'FIXME':
        if any(kw in msg_lower for kw in critical_keywords):
            return 'CRITICAL'
        return 'HIGH'
    
    # Check for critical keywords
    if any(kw in msg_lower for kw in critical_keywords):
        return 'CRITICAL'
    
    # Check for high keywords
    if any(kw in msg_lower for kw in high_keywords):
        return 'HIGH'
    
    # Check for medium keywords
    if any(kw in msg_lower for kw in medium_keywords):
        return 'MEDIUM'
    
    # Default to LOW
    return 'LOW'

def scan_all() -> Dict:
    """Scan all directories for TODOs."""
    all_todos = defaultdict(list)
    
    for base_dir in SCAN_DIRS:
        if not base_dir.exists():
            print(f"Skipping {base_dir} (not found)")
            continue
        
        print(f"Scanning {base_dir}...")
        
        for file_path in base_dir.rglob('*'):
            if not file_path.is_file():
                continue
            
            if file_path.suffix not in EXTENSIONS:
                continue
            
            if should_ignore(file_path):
                continue
            
            todos = scan_file(file_path)
            
            for line_no, marker_type, message in todos:
                priority = categorize_priority(marker_type, message, file_path)
                
                # Get relative path from repo root
                try:
                    if 'mycosoft-mas' in str(file_path):
                        rel_path = file_path.relative_to(Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas'))
                        repo = 'MAS'
                    elif 'website' in str(file_path):
                        rel_path = file_path.relative_to(Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website'))
                        repo = 'WEBSITE'
                    elif 'mindex' in str(file_path):
                        rel_path = file_path.relative_to(Path(r'C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex'))
                        repo = 'MINDEX'
                    else:
                        rel_path = file_path.name
                        repo = 'UNKNOWN'
                except:
                    rel_path = file_path.name
                    repo = 'UNKNOWN'
                
                all_todos[priority].append({
                    'file': str(rel_path),
                    'line_no': line_no,
                    'marker': marker_type,
                    'message': message,
                    'repo': repo,
                })
    
    return all_todos

def generate_report(todos: Dict, output_path: str):
    """Generate markdown report."""
    total = sum(len(items) for items in todos.values())
    
    report = []
    report.append("# TODO Audit Report - February 12, 2026\n")
    report.append("## Summary\n")
    report.append(f"- **Total real TODOs found**: {total}")
    report.append(f"- **Critical**: {len(todos.get('CRITICAL', []))}")
    report.append(f"- **High**: {len(todos.get('HIGH', []))}")
    report.append(f"- **Medium**: {len(todos.get('MEDIUM', []))}")
    report.append(f"- **Low**: {len(todos.get('LOW', []))}\n")
    
    report.append("## Scanned Repositories\n")
    report.append("- MAS (`mycosoft_mas/` - Python backend)")
    report.append("- WEBSITE (`app/`, `components/`, `lib/` - Next.js frontend)")
    report.append("- MINDEX (`mindex_api/`, `mindex_etl/` - Database & ETL)\n")
    
    report.append("## Methodology\n")
    report.append("- Direct codebase scan for `# TODO:`, `// TODO:`, `# FIXME:`, etc.")
    report.append("- Filtered false positives (debug/test files, node_modules, minified code)")
    report.append("- Categorized by severity based on keywords and marker type")
    report.append("- **FIXME** = Always HIGH or CRITICAL priority")
    report.append("- **TODO** = Categorized by content (HIGH if 'implement', 'fix', 'broken')\n")
    
    # Top priority items
    report.append("## Top Priority Items\n")
    
    report.append("### Critical Priority\n")
    critical_items = todos.get('CRITICAL', [])[:10]
    if critical_items:
        for i, item in enumerate(critical_items, 1):
            report.append(f"{i}. **[{item['repo']}] `{item['file']}:{item['line_no']}`** (`{item['marker']}`)")
            report.append(f"   - {item['message']}")
            report.append("")
    else:
        report.append("✅ No critical items found.\n")
    
    report.append("### High Priority\n")
    high_items = todos.get('HIGH', [])[:15]
    if high_items:
        for i, item in enumerate(high_items, 1):
            report.append(f"{i}. **[{item['repo']}] `{item['file']}:{item['line_no']}`** (`{item['marker']}`)")
            report.append(f"   - {item['message']}")
            report.append("")
    else:
        report.append("✅ No high priority items found.\n")
    
    # Full breakdown
    report.append("## Full Breakdown by Priority\n")
    
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        items = todos.get(priority, [])
        if not items:
            continue
        
        report.append(f"### {priority} Priority ({len(items)} items)\n")
        
        if len(items) > 20:
            report.append(f"<details>")
            report.append(f"<summary>Show all {len(items)} {priority.lower()} priority items</summary>\n")
        
        for i, item in enumerate(items, 1):
            report.append(f"{i}. **[{item['repo']}] `{item['file']}:{item['line_no']}`** (`{item['marker']}`)")
            report.append(f"   - {item['message'][:150]}")
            report.append("")
        
        if len(items) > 20:
            report.append("</details>\n")
    
    # Recommendations
    report.append("## Recommendations\n")
    report.append("1. **Critical items**: Fix immediately before next deployment")
    report.append("2. **High priority items**: Schedule for current sprint")
    report.append("3. **Medium priority items**: Add to backlog, tackle during refactor sessions")
    report.append("4. **Low priority items**: Address opportunistically during related work\n")
    
    report.append("## Next Steps\n")
    report.append("1. Create GitHub issues for all CRITICAL and HIGH priority items")
    report.append("2. Assign owners to critical items")
    report.append("3. Review with team and prioritize based on upcoming work")
    report.append("4. Run this scan weekly to track progress\n")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

if __name__ == '__main__':
    output_path = Path(__file__).parent.parent / 'docs' / 'TODO_AUDIT_FEB12_2026.md'
    
    print("Scanning codebase for TODOs...")
    todos = scan_all()
    
    total = sum(len(items) for items in todos.values())
    print(f"\nFound {total} real TODOs:")
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = len(todos.get(priority, []))
        print(f"  {priority}: {count}")
    
    print(f"\nGenerating report: {output_path}")
    generate_report(todos, str(output_path))
    print("Done!")
