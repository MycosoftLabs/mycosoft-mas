import os
import re

def fix_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix imports from agents to mycosoft_mas.agents
    content = re.sub(
        r'from agents\.',
        'from mycosoft_mas.agents.',
        content
    )
    content = re.sub(
        r'import agents\.',
        'import mycosoft_mas.agents.',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}")
                fix_imports(file_path)

if __name__ == '__main__':
    process_directory('mycosoft_mas/agents') 