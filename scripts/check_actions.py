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

results = {}

for repo in repos:
    print(f"\n--- {repo} ---")
    try:
        res = subprocess.run(
            ['gh', 'run', 'list', '-R', repo, '--json', 'status,conclusion,name,createdAt,url', '--limit', '1'],
            capture_output=True,
            text=True
        )
        if not res.stdout.strip():
            print("No runs found or empty output.")
            results[repo] = "No runs found"
            continue
            
        runs = json.loads(res.stdout)
        if not runs:
            print("No runs.")
            results[repo] = "No runs found"
        for run in runs:
            status = run.get('status')
            conclusion = run.get('conclusion')
            print(f"Name: {run.get('name')}")
            print(f"Status: {status}")
            print(f"Conclusion: {conclusion}")
            print(f"Created: {run.get('createdAt')}")
            print(f"URL: {run.get('url')}")
            results[repo] = f"Status: {status}, Conclusion: {conclusion}, Name: {run.get('name')}"
    except Exception as e:
        print(f"Error: {e}")
        results[repo] = f"Error: {e}"

with open("github_actions_summary.json", "w") as f:
    json.dump(results, f, indent=2)
