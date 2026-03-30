import subprocess, json

repos = [
    'MycosoftLabs/mycosoft-mas',
    'MycosoftLabs/mindex',
    'MycosoftLabs/website',
    'MycosoftLabs/NLM',
    'MycosoftLabs/NatureOS',
    'MycosoftLabs/sdk',
    'MycosoftLabs/mycobrain'
]

report = "# Deployment Status Report\n\nGenerated from recent GitHub Actions workflow runs.\n\n"

for repo in repos:
    report += f"## Repository: {repo}\n\n"
    try:
        res = subprocess.run(
            ['gh', 'run', 'list', '-R', repo, '--json', 'databaseId,status,conclusion,name,createdAt,url', '--limit', '1'],
            capture_output=True, encoding='utf-8'
        )
        
        if not res.stdout.strip():
            report += "No workflow runs found.\n\n"
            continue
            
        runs = json.loads(res.stdout)
        if not runs:
            report += "No workflow runs found.\n\n"
            continue
            
        run = runs[0]
        run_name = run.get('name', 'Unknown')
        run_status = run.get('status', 'Unknown')
        run_conclusion = run.get('conclusion', 'Unknown')
        run_url = run.get('url', 'Unknown')
        run_id = run.get('databaseId')
        
        report += f"**Workflow**: {run_name}\n"
        report += f"**Status**: {run_status}\n"
        report += f"**Conclusion**: {run_conclusion}\n"
        report += f"**URL**: {run_url}\n\n"
        
        if run_conclusion == 'failure' and run_id:
            report += "### Failure Logs\n```text\n"
            log_res = subprocess.run(
                ['gh', 'run', 'view', str(run_id), '-R', repo, '--log-failed'],
                capture_output=True, encoding='utf-8'
            )
            log_out = log_res.stdout.strip()
            if len(log_out) > 3000:
                log_out = log_out[-3000:] + "\n... (truncated)"
            
            report += log_out if log_out else "No specific failure logs available."
            report += "\n```\n\n"
            
    except Exception as e:
        report += f"Error checking repository: {e}\n\n"

with open(r'C:\Users\admin2\.gemini\antigravity\brain\2581027b-c7e4-4b58-813a-14b45579cb14\deployment_status_report.md', 'w', encoding='utf-8') as f:
    f.write(report)
