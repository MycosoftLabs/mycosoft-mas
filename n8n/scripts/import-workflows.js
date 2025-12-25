#!/usr/bin/env node
/**
 * n8n Workflow Import Script
 * 
 * Imports all MAS workflows into n8n via the API.
 * 
 * Environment Variables:
 *   N8N_API_URL - n8n API URL (default: http://localhost:5678)
 *   N8N_API_KEY - n8n API key
 * 
 * Usage:
 *   node import-workflows.js
 *   node import-workflows.js --dry-run
 */

const fs = require('fs');
const path = require('path');

const N8N_API_URL = process.env.N8N_API_URL || 'http://localhost:5678';
const N8N_API_KEY = process.env.N8N_API_KEY || '';

const DRY_RUN = process.argv.includes('--dry-run');

const WORKFLOWS_DIR = path.join(__dirname, '..', 'workflows');

// Workflow import order (dependencies first)
const WORKFLOW_ORDER = [
  // Core workflows
  '14_audit_logger.json',
  '13_generic_connector.json',
  
  // Native category handlers
  '03_native_ai.json',
  '04_native_comms.json',
  '05_native_devtools.json',
  '06_native_data_storage.json',
  '07_native_finance.json',
  '08_native_productivity.json',
  '09_native_utility.json',
  '10_native_security.json',
  
  // New global integration workflows
  '11_native_space_weather.json',
  '12_native_environmental.json',
  '15_native_earth_science.json',
  '16_native_analytics.json',
  '17_native_automation.json',
  
  // Operations workflows
  '20_ops_proxmox.json',
  '21_ops_unifi.json',
  '22_ops_nas_health.json',
  '23_ops_gpu_job.json',
  '24_ops_uart_ingest.json',
  
  // Defense (restricted)
  '30_defense_connector.json',
  
  // Router and command API
  '02_router_integration_dispatch.json',
  '01_myca_command_api.json',
  '01b_myca_event_intake.json',
];

async function importWorkflow(filePath) {
  const fileName = path.basename(filePath);
  
  try {
    const workflowData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    
    if (DRY_RUN) {
      console.log(`[DRY RUN] Would import: ${fileName} - "${workflowData.name}"`);
      return { success: true, name: workflowData.name, id: null };
    }
    
    const response = await fetch(`${N8N_API_URL}/api/v1/workflows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-N8N-API-KEY': N8N_API_KEY,
      },
      body: JSON.stringify(workflowData),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const result = await response.json();
    console.log(`✓ Imported: ${fileName} -> ID: ${result.id} ("${result.name}")`);
    return { success: true, name: result.name, id: result.id };
    
  } catch (error) {
    console.error(`✗ Failed: ${fileName} - ${error.message}`);
    return { success: false, name: fileName, error: error.message };
  }
}

async function getAllWorkflowFiles() {
  const files = fs.readdirSync(WORKFLOWS_DIR);
  const jsonFiles = files.filter(f => f.endsWith('.json') && !f.includes('\\'));
  
  // Order workflows according to WORKFLOW_ORDER, then add any remaining
  const orderedFiles = [];
  
  for (const orderFile of WORKFLOW_ORDER) {
    if (jsonFiles.includes(orderFile)) {
      orderedFiles.push(orderFile);
    }
  }
  
  // Add remaining files not in the order list
  for (const file of jsonFiles) {
    if (!orderedFiles.includes(file)) {
      orderedFiles.push(file);
    }
  }
  
  return orderedFiles.map(f => path.join(WORKFLOWS_DIR, f));
}

async function main() {
  console.log('='.repeat(60));
  console.log('n8n Workflow Import Script');
  console.log('='.repeat(60));
  console.log(`n8n API URL: ${N8N_API_URL}`);
  console.log(`API Key: ${N8N_API_KEY ? '[SET]' : '[NOT SET]'}`);
  console.log(`Mode: ${DRY_RUN ? 'DRY RUN' : 'LIVE IMPORT'}`);
  console.log('='.repeat(60));
  
  if (!N8N_API_KEY && !DRY_RUN) {
    console.error('\nERROR: N8N_API_KEY environment variable is required for import.');
    console.error('Set it with: export N8N_API_KEY=your_api_key');
    console.error('Or run with --dry-run to preview.');
    process.exit(1);
  }
  
  const workflowFiles = await getAllWorkflowFiles();
  console.log(`\nFound ${workflowFiles.length} workflow files to import.\n`);
  
  const results = {
    success: [],
    failed: [],
  };
  
  for (const file of workflowFiles) {
    const result = await importWorkflow(file);
    if (result.success) {
      results.success.push(result);
    } else {
      results.failed.push(result);
    }
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('Import Summary');
  console.log('='.repeat(60));
  console.log(`Successful: ${results.success.length}`);
  console.log(`Failed: ${results.failed.length}`);
  
  if (results.failed.length > 0) {
    console.log('\nFailed imports:');
    results.failed.forEach(f => console.log(`  - ${f.name}: ${f.error}`));
  }
  
  // Generate workflow ID mapping
  if (!DRY_RUN && results.success.length > 0) {
    console.log('\n' + '='.repeat(60));
    console.log('Environment Variables for Router');
    console.log('='.repeat(60));
    console.log('# Add these to your .env file:\n');
    
    const mapping = {
      'native_ai': 'WORKFLOW_ID_NATIVE_AI',
      'native_comms': 'WORKFLOW_ID_NATIVE_COMMS',
      'native_data': 'WORKFLOW_ID_NATIVE_DATA',
      'native_devtools': 'WORKFLOW_ID_NATIVE_DEVTOOLS',
      'native_productivity': 'WORKFLOW_ID_NATIVE_PRODUCTIVITY',
      'native_finance': 'WORKFLOW_ID_NATIVE_FINANCE',
      'native_ops': 'WORKFLOW_ID_NATIVE_OPS',
      'native_security': 'WORKFLOW_ID_NATIVE_SECURITY',
      'native_utility': 'WORKFLOW_ID_NATIVE_UTILITY',
      'space_weather': 'WORKFLOW_ID_NATIVE_SPACE_WEATHER',
      'environmental': 'WORKFLOW_ID_NATIVE_ENVIRONMENTAL',
      'earth_science': 'WORKFLOW_ID_NATIVE_EARTH_SCIENCE',
      'analytics': 'WORKFLOW_ID_NATIVE_ANALYTICS',
      'automation': 'WORKFLOW_ID_NATIVE_AUTOMATION',
      'generic': 'WORKFLOW_ID_GENERIC_CONNECTOR',
      'defense': 'WORKFLOW_ID_DEFENSE_CONNECTOR',
      'audit': 'AUDIT_LOGGER_WORKFLOW_ID',
    };
    
    results.success.forEach(w => {
      const nameLower = w.name.toLowerCase();
      for (const [key, envVar] of Object.entries(mapping)) {
        if (nameLower.includes(key)) {
          console.log(`${envVar}=${w.id}`);
          break;
        }
      }
    });
  }
}

main().catch(console.error);
