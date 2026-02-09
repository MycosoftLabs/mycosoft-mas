# Autonomous Experiments System Documentation
**Date:** February 6, 2026  
**Version:** 2.0  
**Status:** Production Ready

---

## Overview

The Autonomous Experiments System enables AI-driven closed-loop scientific experimentation. Starting from a hypothesis, the system automatically generates experiment protocols, executes them, adapts based on results, and validates findings with minimal human intervention.

---

## Key Concepts

### Closed-Loop Experimentation
```
Hypothesis → Protocol Generation → Execution → Measurement → Analysis → Adaptation → Validation
     ↑                                                                                    |
     └────────────────────────── Feedback Loop ───────────────────────────────────────────┘
```

### AI-Driven Adaptations
The system automatically adjusts experiments based on:
- Unexpected measurement variance
- Suboptimal growth conditions
- Equipment calibration drift
- Statistical significance thresholds

---

## Dashboard (`autonomous-experiment-dashboard.tsx`)

### Summary Cards
- **Total Experiments**: All autonomous experiments
- **Running**: Currently executing
- **Completed**: Successfully finished
- **Auto-Adaptations**: AI adjustments made

### Experiment List
- Browse all autonomous experiments
- Status badges (planning, running, paused, completed, failed)
- Progress bars for active experiments
- Click to view details

### Experiment Details
Three tabs for comprehensive experiment information:

1. **Steps Tab**
   - Visual step progress
   - Step type icons (setup, execute, measure, analyze, decide)
   - Status indicators (completed, running, pending)
   - Duration tracking

2. **Adaptations Tab**
   - List of AI-made adjustments
   - Reason for each adaptation
   - Parameter changes made

3. **Results Tab**
   - Final experiment outcomes
   - Statistical analysis
   - Hypothesis validation status

---

## Experiment Lifecycle

### Stages
1. **Planning**: AI generates protocol from hypothesis
2. **Running**: Executing experiment steps
3. **Paused**: Temporarily halted (user or AI initiated)
4. **Completed**: All steps finished, hypothesis validated
5. **Failed**: Experiment could not complete

### Step Types
| Type | Icon | Description |
|------|------|-------------|
| Setup | 🧪 | Environment and sample preparation |
| Execute | ⚡ | Apply treatment or intervention |
| Measure | ⏱️ | Data collection and recording |
| Analyze | 🧠 | Statistical analysis and processing |
| Decide | 💡 | Hypothesis validation decision |

---

## API Endpoints

### Autonomous Experiments
```
GET  /api/autonomous/experiments           → List experiments
POST /api/autonomous/experiments           → Create from hypothesis
POST /api/autonomous/experiments/{id}/start → Start experiment
POST /api/autonomous/experiments/{id}/pause → Pause experiment
POST /api/autonomous/experiments/{id}/stop  → Stop experiment
POST /api/autonomous/experiments/{id}/reset → Reset experiment
```

### Backend (MAS)
```
GET  /autonomous/experiments               → All experiments with steps
POST /autonomous/experiments               → Generate protocol from hypothesis
POST /autonomous/experiments/{id}/{action} → Control experiment
GET  /autonomous/experiments/{id}/steps    → Get step details
GET  /autonomous/experiments/{id}/adaptations → Get adaptation log
```

---

## Data Hook

**File:** `hooks/scientific/use-autonomous.ts`

```typescript
const { 
  experiments,        // Array of autonomous experiments
  steps,              // Steps for selected experiment
  isLive,             // API connectivity status
  isLoading,          // Loading state
  createExperiment,   // Function to create from hypothesis
  controlExperiment,  // Function to control (start/pause/stop/reset)
  getSteps,           // Function to get experiment steps
  refresh             // Manual refresh function
} = useAutonomousExperiments()
```

**Refresh Interval:** 5 seconds

---

## Data Types

### Autonomous Experiment
```typescript
interface AutoExperiment {
  id: string
  name: string
  hypothesis: string          // Original hypothesis text
  status: 'planning' | 'running' | 'paused' | 'completed' | 'failed'
  currentStep: number         // Index of current step
  totalSteps: number          // Total steps in protocol
  progress: number            // 0-100 percentage
  startedAt?: string          // ISO timestamp
  adaptations: number         // Number of AI adaptations
}
```

### Experiment Step
```typescript
interface ExperimentStep {
  id: string
  name: string
  type: 'setup' | 'execute' | 'measure' | 'analyze' | 'decide'
  status: 'pending' | 'running' | 'completed' | 'failed'
  duration?: number           // seconds (when completed)
}
```

### Adaptation
```typescript
interface Adaptation {
  id: string
  type: string                // e.g., "temperature_adjustment"
  reason: string              // Why adaptation was made
  parameters: Record<string, any>  // What was changed
  timestamp: string           // When it occurred
}
```

---

## Creating an Experiment

### From Hypothesis
```typescript
const { createExperiment } = useAutonomousExperiments()

// User enters hypothesis
const hypothesis = "Electrical stimulation at 0.5Hz increases P. ostreatus growth rate by 15-20%"

// AI generates full experiment protocol
await createExperiment(hypothesis)
```

### What the AI Generates
1. **Experiment Name**: Descriptive title
2. **Protocol Steps**: Ordered list of actions
3. **Parameters**: Environmental conditions, timing, measurements
4. **Success Criteria**: Statistical thresholds for validation
5. **Fallback Plans**: What to do if steps fail

---

## User Actions

| Action | Description | Feedback |
|--------|-------------|----------|
| Create | Generate experiment from hypothesis | Loading toast → Success/Error |
| Start | Begin or resume experiment | Toast notification |
| Pause | Pause running experiment | Toast notification |
| Stop | Terminate experiment | Toast notification |
| Reset | Reset to initial state | Toast notification |
| Refresh | Reload experiment data | Animated spinner |

---

## Example Workflow

```tsx
import { AutonomousExperimentDashboard } from '@/components/autonomous/autonomous-experiment-dashboard'

export function AutonomousPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1>Autonomous Research</h1>
        <p>AI-driven closed-loop experimentation</p>
      </div>
      <AutonomousExperimentDashboard />
    </div>
  )
}
```

---

## AI Adaptation Examples

### Temperature Adjustment
```
Reason: Detected suboptimal growth rate
Action: Adjusted incubator temperature from 25°C to 24°C
Impact: Growth rate normalized within 2 hours
```

### Extended Measurement Period
```
Reason: High variance in initial measurements
Action: Extended data collection by 2 hours
Impact: Achieved statistical significance
```

### Calibration Correction
```
Reason: Spectrometer drift detected
Action: Triggered auto-calibration routine
Impact: Measurement accuracy restored
```

---

## Best Practices

1. **Clear Hypotheses**: Write specific, testable hypotheses
2. **Realistic Parameters**: Use achievable conditions
3. **Monitor Adaptations**: Review AI decisions
4. **Validate Results**: Cross-check with manual experiments
5. **Document Learnings**: Update knowledge base

---

## Future Enhancements

1. **Multi-Hypothesis Testing**
   - Test multiple hypotheses in parallel
   - Cross-reference results
   - Identify correlations

2. **Learning from History**
   - Use past experiment data
   - Improve protocol generation
   - Predict outcomes

3. **Human-in-the-Loop**
   - Request approval for major adaptations
   - Allow parameter overrides
   - Collaborative decision making

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Experiment stuck | Check equipment connectivity |
| Too many adaptations | Review environmental stability |
| Failed steps | Check step-specific requirements |
| Low confidence | Increase sample size or duration |

---

## Related Documentation
- [Scientific Systems Overview](./SCIENTIFIC_SYSTEMS_COMPLETE_FEB06_2026.md)
- [Hypothesis Engine](./HYPOTHESIS_ENGINE.md)
- [Experiment Tracker](./EXPERIMENT_TRACKING.md)
