import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const workflowsDir = join(__dirname, '..', 'workflows');

const API_KEY = process.env.N8N_API_KEY;
const N8N_URL = 'http://localhost:5678';

const newWorkflows = [
  '11_native_space_weather.json',
  '12_native_environmental.json', 
  '15_native_earth_science.json',
  '16_native_analytics.json',
  '17_native_automation.json',
  '30_defense_connector.json'
];

async function importWorkflow(filename) {
  const filepath = join(workflowsDir, filename);
  const workflow = JSON.parse(readFileSync(filepath, 'utf-8'));
  
  // Extract only the fields n8n API accepts
  const payload = {
    name: workflow.name,
    nodes: workflow.nodes,
    connections: workflow.connections,
    settings: { executionOrder: 'v1' }
  };

  try {
    const response = await fetch(`${N8N_URL}/api/v1/workflows`, {
      method: 'POST',
      headers: {
        'X-N8N-API-KEY': API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      const error = await response.text();
      console.error(`FAILED: ${filename} - ${response.status}: ${error}`);
      return null;
    }
    
    const result = await response.json();
    console.log(`SUCCESS: ${filename} -> ID: ${result.id}`);
    return result;
  } catch (err) {
    console.error(`ERROR: ${filename} - ${err.message}`);
    return null;
  }
}

async function main() {
  console.log('Importing new global integration workflows...\n');
  
  for (const filename of newWorkflows) {
    await importWorkflow(filename);
  }
  
  console.log('\nDone!');
}

main();



