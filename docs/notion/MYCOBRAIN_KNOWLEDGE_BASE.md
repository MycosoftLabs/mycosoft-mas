# MycoBrain Knowledge Base Structure for Notion

This document outlines the recommended Notion knowledge base structure for MycoBrain integration documentation.

## Database: "MycoBrain Knowledge Base"

### Page Templates

#### 1. Hardware Specifications

**Title:** `Hardware Specifications - MycoBrain V1`

**Properties:**
- **Type**: Select (Hardware)
- **Version**: Text (e.g., "V1.0")
- **Status**: Select (Active, Deprecated, Planned)
- **Last Updated**: Date

**Content Sections:**
- Overview
- Schematics (embedded images/files)
- Pin Mappings (table)
- BOM (Bill of Materials) table
- Power Requirements
- Physical Dimensions

**Relations:**
- Links to firmware pages
- Links to protocol reference
- Links to integration guides

---

#### 2. Firmware Documentation

**Title:** `Firmware - Side-A [Version]`

**Properties:**
- **Type**: Select (Firmware)
- **Component**: Select (Side-A, Side-B, Gateway)
- **Version**: Text
- **Status**: Select (Stable, Beta, Deprecated)
- **Release Date**: Date
- **GitHub Release**: URL

**Content Sections:**
- Changelog
- Build Instructions
- Flash Instructions
- Known Issues
- Configuration Options

**Relations:**
- Links to hardware specs
- Links to protocol reference
- Links to related firmware versions

---

#### 3. Protocol Reference

**Title:** `MDP v1 Protocol Reference`

**Properties:**
- **Type**: Select (Protocol)
- **Version**: Text ("v1")
- **Status**: Select (Active, Deprecated)
- **Last Updated**: Date

**Content Sections:**
- Frame Structure
- Message Types (TELEMETRY, COMMAND, EVENT, ACK)
- COBS Encoding Algorithm
- CRC16 Calculation
- Sequence Numbers
- Timestamps
- Code Examples (embedded code blocks)
- Error Handling

**Relations:**
- Links to firmware pages
- Links to integration guides
- Links to troubleshooting pages

---

#### 4. Integration Guides

**Title:** `Integration Guide - MINDEX`

**Properties:**
- **Type**: Select (Integration)
- **System**: Select (MINDEX, NatureOS, MAS)
- **Status**: Select (Complete, In Progress, Planned)
- **Last Updated**: Date

**Content Sections:**
- Overview
- Prerequisites
- Setup Instructions
- API Methods
- Code Examples
- Schema Mapping
- Authentication
- Troubleshooting

**Relations:**
- Links to protocol reference
- Links to device registration pages
- Links to troubleshooting FAQ

---

#### 5. Device Registration

**Title:** `Device Registration - [Device ID]`

**Properties:**
- **Type**: Select (Device)
- **Device ID**: Text
- **Serial Number**: Text
- **Status**: Select (Active, Offline, Error, Maintenance)
- **Location**: Text
- **Registered Date**: Date
- **Firmware Version**: Text

**Content Sections:**
- Device Information
- Registration Steps
- API Keys
- MINDEX Registration
- NatureOS Registration
- Connection Details
- Telemetry Configuration

**Relations:**
- Links to integration guides
- Links to troubleshooting pages

---

#### 6. Troubleshooting FAQ

**Title:** `Troubleshooting - [Issue Category]`

**Properties:**
- **Type**: Select (Troubleshooting)
- **Category**: Select (Connection, Telemetry, Commands, Firmware, Hardware)
- **Severity**: Select (Critical, High, Medium, Low)
- **Status**: Select (Resolved, In Progress, Open)
- **Last Updated**: Date

**Content Sections:**
- Problem Description
- Symptoms
- Root Cause
- Solution Steps
- Prevention
- Related Issues

**Relations:**
- Links to relevant hardware/firmware pages
- Links to integration guides

---

#### 7. Hard-Won Lessons

**Title:** `Hard-Won Lesson - [Topic]`

**Properties:**
- **Type**: Select (Lesson)
- **Category**: Select (Protocol, Hardware, Firmware, Integration)
- **Impact**: Select (Critical, High, Medium, Low)
- **Date Learned**: Date

**Content Sections:**
- Lesson Summary
- Context
- What Went Wrong
- Solution
- Prevention
- Related Documentation

**Example Topics:**
- "Always use COBS framing"
- "I²C pins can freeze if not handled correctly"
- "Telemetry is best-effort, commands are reliable"
- "Sequence numbers for idempotency"

---

#### 8. Code Examples

**Title:** `Code Example - [Use Case]`

**Properties:**
- **Type**: Select (Code Example)
- **Language**: Select (Python, C++, JavaScript)
- **Use Case**: Select (Device Connection, Telemetry Ingestion, Command Sending)
- **Last Updated**: Date

**Content Sections:**
- Use Case Description
- Prerequisites
- Code (embedded code blocks)
- Explanation
- Related Documentation

---

#### 9. Roadmap

**Title:** `MycoBrain Integration Roadmap`

**Properties:**
- **Type**: Select (Roadmap)
- **Milestone**: Select (Planned, In Progress, Completed, Blocked)
- **Priority**: Select (Critical, High, Medium, Low)
- **Target Date**: Date
- **Owner**: Person

**Content Sections:**
- Milestone Description
- Dependencies
- Progress Updates
- Blockers
- Related Tasks

**Example Milestones:**
- "Finish MINDEX ingestion agent"
- "Add MycoBrain widget to NatureOS"
- "Complete protocol library documentation"
- "Website integration page"

---

## Database Views

### 1. By Type
Group pages by Type property for easy navigation.

### 2. By Status
Filter pages by Status to see active vs. deprecated content.

### 3. Recent Updates
Sort by Last Updated to see recently modified pages.

### 4. Integration Status
Filter by Type=Integration and Status to track integration progress.

### 5. Troubleshooting Index
Filter by Type=Troubleshooting, grouped by Category.

---

## Relations and Tags

### Relations
- Each page can link to related pages using Notion relations
- Example: Protocol Reference page links to all firmware pages
- Example: Integration Guide links to relevant device registrations

### Tags
Use tags for:
- **Device Types**: Side-A, Side-B, Gateway
- **Systems**: MINDEX, NatureOS, MAS
- **Languages**: Python, C++, JavaScript
- **Topics**: Protocol, Hardware, Firmware, Integration

---

## Embedded Content

### Code Snippets
Use Notion code blocks with syntax highlighting:
- Python examples for MAS integration
- C++ examples for firmware
- JSON examples for protocol messages

### Diagrams
Embed images/diagrams:
- Hardware schematics
- Protocol flow diagrams
- System architecture diagrams

### GitHub Integration
Link to GitHub:
- Repository pages
- Issues
- Pull requests
- Releases

### External Links
- Mycosoft website pages
- API documentation
- Datasheets

---

## Maintenance

### Regular Updates
- Update Last Updated date when modifying content
- Review and update status fields
- Archive deprecated content
- Add new lessons learned

### Content Review
- Monthly review of troubleshooting pages
- Quarterly review of integration guides
- Update roadmap as milestones complete

### Team Collaboration
- Assign owners to roadmap items
- Use comments for questions/discussions
- Link related pages for context

---

## Example Page Structure

### Page: "MDP v1 Protocol Reference"

**Content:**

```markdown
# MDP v1 Protocol Reference

## Overview
MDP v1 is the communication protocol for MycoBrain devices...

## Frame Structure
[Diagram embedded]

## Message Types

### TELEMETRY (0x01)
[Code example embedded]

### COMMAND (0x02)
[Code example embedded]

## COBS Encoding
[Algorithm explanation]

## Related Pages
- [Hardware Specifications - MycoBrain V1]
- [Firmware - Side-A v1.0]
- [Integration Guide - MAS]
```

---

This structure provides a comprehensive knowledge base that:
- Organizes information by type and category
- Links related content for easy navigation
- Tracks status and progress
- Includes code examples and troubleshooting
- Maintains a living roadmap
