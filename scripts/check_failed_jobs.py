import subprocess, json

runs = {
    'MycosoftLabs/mycosoft-mas': '23393262281',
    'MycosoftLabs/mindex': '23374286419',
    'MycosoftLabs/NatureOS': '23332894441',
    'MycosoftLabs/mycobrain': '23312569984'
}
for repo, run in runs.items():
    print(f'=== {repo} ===')
    res = subprocess.run(['gh', 'run', 'view', run, '-R', repo, '--json', 'jobs'], capture_output=True, text=True, encoding='utf-8')
    try:
        data = json.loads(res.stdout)
        for job in data.get('jobs', []):
            if job.get('conclusion') == 'failure':
                for step in job.get('steps', []):
                    if step.get('conclusion') == 'failure':
                        print(f"Job: {job.get('name')} | Step: {step.get('name')}")
                        
                        # Get log for this specific job to see the error
                        log_res = subprocess.run(['gh', 'run', 'view', '--job', str(job.get('databaseId')), '-R', repo, '--log-failed'], capture_output=True, text=True, encoding='utf-8')
                        lines = log_res.stdout.split('\n')
                        # show last 20 lines of the failed step log
                        print('\n'.join(lines[-20:]))
    except Exception as e:
        print(f'Error parsing output: {e}')
