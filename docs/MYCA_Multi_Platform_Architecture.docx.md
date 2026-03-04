

MYCA Multi-Platform Deployment Architecture

Mycosoft, Inc.

Department 12: MYCA MAS

Date: March 2026

Classification: UNCLASSIFIED

Prepared by: Morgan (CEO) with MYCA Secretary

TABLE OF CONTENTS

1\. Executive Summary

2\. Architecture Overview

3\. MYCA Dedicated VM Setup (Proxmox)

4\. Google Workspace Setup

5\. Discord Integration

6\. Slack Integration

7\. Asana Integration

8\. Signal Integration

9\. WhatsApp Integration

10\. Gmail Integration

11\. Notion & Google Drive Integration

12\. Cowork & Cursor Integration

13\. n8n Orchestration Workflows

14\. Setup Checklist

15\. Security & Access Control

# **1\. Executive Summary**

MYCA is Mycosoft's AI secretary and Multi-Agent System orchestrator designed to provide autonomous, intelligent assistance across all communication and work platforms. This comprehensive document provides the complete architecture and step-by-step deployment guide to make MYCA a fully autonomous, interactive agent capable of managing communications, workflows, and team coordination across Discord, Slack, Asana, Signal, WhatsApp, Gmail, and other integrated platforms.

MYCA operates under the dedicated identity schedule@mycosoft.org and follows a central integration pattern: Platform → n8n webhook → MAS Orchestrator (localhost:8001) → Agent routing → Response → Platform. This asynchronous, event-driven architecture ensures scalability and resilience.

Leadership: Morgan Rockwell. Access Control: Only @mycosoft.org email addresses have authorized access to MYCA systems and credentials. This document is classified UNCLASSIFIED but contains sensitive deployment instructions.

# **2\. Architecture Overview**

The MYCA architecture is built on a hub-and-spoke model with n8n as the central integration hub (localhost:5678) and the MAS Orchestrator as the intelligent routing and execution engine (localhost:8001).

## **Core Components**

* n8n (localhost:5678): Low-code workflow orchestration platform serving as the integration hub

* MAS Orchestrator (localhost:8001): CrewAI-based intelligent agent router and execution engine

* ElevenLabs Voice Agent (Arabella): Voice interaction and synthesis capabilities

* Platform-Specific Connectors: Discord, Slack, Asana, Signal, WhatsApp, Gmail, Notion, Google Drive

## **Current Integration Points**

Existing API endpoints operational:

* POST /voice/orchestrator/chat: Main orchestrator endpoint for message processing

* GET /agents/registry/: Registry of available agents and capabilities

* POST /agents/registry/route/voice: Voice-specific routing endpoint

## **n8n Webhooks**

Primary webhook endpoints for platform integration:

* /webhook/myca/command: Command execution trigger

* /webhook/myca/speech\_turn: Speech turn indicator for voice interactions

* /webhook/myca/speech\_safety: Safety check for potentially destructive actions

* /webhook/myca/speech\_confirm: Confirmation gate before critical operations

## **Critical Gap**

Currently, 0 n8n workflows are deployed in production, representing a critical gap in the architecture. This deployment guide addresses this gap with templates and deployment procedures for 8 priority workflows (Discord, Slack, Asana, Signal, WhatsApp, Gmail, Notion sync, health monitoring).

# **3\. MYCA Dedicated VM Setup (Proxmox)**

MYCA requires a dedicated virtual machine separate from Morgan's development PC and existing sandbox/MAS/MIDNEX VMs. This isolated environment ensures security, stability, and scalability for production operations.

## **VM Specifications**

* Operating System: Ubuntu 22.04 LTS Server (headless)

* Architecture: x86\_64, 64-bit

* CPU Allocation: 8 vCPUs (dedicated or pinned cores recommended)

* Memory: 32GB RAM

* Storage: 256GB SSD (NVMe preferred for optimal I/O performance)

* Network: Bridged networking on dedicated VLAN 50, static IP address

## **Rationale for Ubuntu Server**

Ubuntu 22.04 LTS Server (headless) is recommended over Windows for several reasons: lower resource overhead, superior Docker and containerized service support, better filesystem performance for microservices, simpler SSH/CLI administration, and long-term support (LTS) until 2027\.

## **Core Services to Deploy**

* Docker & Docker Compose: Container orchestration for microservices

* n8n Container: Workflow automation platform

* MAS Orchestrator Container: CrewAI-based agent router

* signal-cli REST API Container: Signal messaging bridge

* WhatsApp Bridge Container: WhatsApp integration (Baileys or official API)

* Claude Code CLI: Autonomous code generation and deployment

* Cursor Server (headless): IDE for code generation tasks

* Chromium (headless): Web automation and scraping capabilities

## **Setup Procedure**

* Create VM in Proxmox with specified resources

* Install Ubuntu 22.04 LTS Server (minimal installation)

* Install Docker and Docker Compose

* Configure static IP address and DNS resolution

* Deploy MYCA service stack via Docker Compose

* Configure reverse proxy (Caddy or Nginx) for external webhooks with TLS

* Set up firewall rules (whitelist n8n, close unused ports)

* Enable SSH and configure key-based authentication

* Test all containers and verify inter-service communication

## **Resource Allocation (Proxmox Configuration)**

Table: MYCA VM Resource Summary

| Resource | Specification | Notes |
| ----- | ----- | ----- |
| vCPUs | 8 cores | Supports parallel workflow execution |
| RAM | 32GB | Accommodates n8n, MAS, and multiple integrations |
| Storage | 256GB SSD | NVMe preferred for service responsiveness |
| Network | Bridged VLAN 50 | Isolated, dedicated network segment |
| Backup | Daily snapshots | Via Proxmox backup system |

# **4\. Google Workspace Setup**

Google Workspace integration provides email, calendar, drive, and document access for MYCA. All integrations operate under the dedicated service account schedule@mycosoft.org.

## **Service Account Creation**

* Log into Google Workspace Admin Console (admin.google.com)

* Navigate to Security \> API Controls \> Domain-wide Delegation

* Create a new OAuth 2.0 service account for MYCA

* Download service account JSON key file securely

## **Required APIs**

Enable the following APIs in Google Cloud Console for the service account:

* Gmail API: Read and send emails on behalf of schedule@mycosoft.org

* Google Drive API: Access shared drives and document storage

* Google Docs API: Read and edit Google Documents

* Google Calendar API: Schedule meetings and manage calendar events

## **Domain-Wide Delegation**

Configure domain-wide delegation to allow the service account to impersonate schedule@mycosoft.org:

* Authorize the service account in Google Workspace Admin \> Security \> API Controls

* Grant OAuth scopes: https://www.googleapis.com/auth/gmail.send, https://www.googleapis.com/auth/drive, https://www.googleapis.com/auth/docs, https://www.googleapis.com/auth/calendar

## **Credential Storage**

Store the service account JSON key at /opt/myca/credentials/google/service-account-key.json on the MYCA VM. Restrict file permissions to 400 (read-only for MYCA service user).

## **Environment Variables**

* GOOGLE\_SERVICE\_ACCOUNT\_KEY: /opt/myca/credentials/google/service-account-key.json

* MYCA\_EMAIL: schedule@mycosoft.org

* GOOGLE\_PROJECT\_ID: \<Google Cloud Project ID\>

# **5\. Discord Integration**

Discord serves as a primary chat platform for MYCA, enabling team communication and command execution within the Mycosoft Discord server.

## **Discord Application Setup**

* Visit discord.com/developers/applications

* Click "New Application" and name it "MYCA"

* Navigate to Bot \> Add Bot

* Copy the bot token (store as DISCORD\_BOT\_TOKEN)

## **Required Intents**

Enable the following Gateway Intents in Bot settings:

* Message Content Intent: Required to read message text

* Server Members Intent: For member list and role information

* Presence Intent: For user status and activity tracking

## **Bot Permissions**

Grant the bot the following permissions in the Mycosoft Discord server:

* Send Messages: Post responses in channels

* Read Message History: Access previous messages for context

* Manage Messages: Delete or edit messages if needed

* Add Reactions: React to messages for acknowledgment

* Use Slash Commands: Support for slash command interactions

* Mention @everyone: Escalate to leadership if necessary

## **n8n Workflow Configuration**

The Discord-to-MAS workflow follows this pattern:

* 1\. Discord trigger node: Listens for messages mentioning @MYCA or in DMs

* 2\. Parse function node: Extract user ID, channel ID, message text

* 3\. HTTP Request node: POST to localhost:8001/voice/orchestrator/chat with parsed data

* 4\. Format response node: Ensure response meets Discord message format

* 5\. Discord Send Message node: Post response to source channel or user DM

## **Invocation Methods**

* @MYCA \<command\>: Mention MYCA in any server channel

* Direct Message: Send DM to MYCA bot for private interactions

* /myca \<command\>: Slash command for structured inputs

## **Credential Storage**

Store DISCORD\_BOT\_TOKEN in /opt/myca/credentials/discord/bot-token.txt and configure in n8n Discord node credentials.

# **6\. Slack Integration**

Slack integration enables MYCA to monitor conversations, respond to mentions, and execute commands within Slack channels and direct messages.

## **Slack App Creation**

* Visit api.slack.com/apps

* Click "Create New App" \> "From scratch"

* Name: "MYCA", Workspace: Mycosoft Slack

* Navigate to Bot Token Scopes and enable scopes below

## **Required Bot Token Scopes**

Enable the following OAuth 2.0 scopes for the bot user token:

* chat:write: Post messages to channels

* channels:read: List and access channel information

* channels:history: Read message history from channels

* im:read: Access direct messages

* im:history: Read direct message history

* users:read: Retrieve user information

* app\_mentions:read: Detect mentions of the app

* message.channels: Event subscriptions for channel messages

* message.im: Event subscriptions for direct messages

## **Event Subscriptions**

Configure Event Subscriptions to notify MYCA of relevant interactions:

* Enable Event Subscriptions

* Request URL: https://\[MYCA VM Domain\]/webhook/slack/events

* Subscribe to bot events: message.channels, message.im, app\_mention

## **Installation**

* Click "Install to Workspace"

* Review permissions and authorize

* Copy Bot User OAuth Token (store as SLACK\_BOT\_TOKEN)

* Copy Signing Secret (store as SLACK\_SIGNING\_SECRET)

## **n8n Workflow**

Slack-to-MAS workflow:

* 1\. Slack trigger node: Webhook receives message events

* 2\. Parse function: Extract message, user, channel context

* 3\. HTTP Request: POST localhost:8001/voice/orchestrator/chat

* 4\. Format response: Structure as Slack message

* 5\. Slack post message node: Reply in same channel

# **7\. Asana Integration**

Asana integration allows MYCA to monitor project tasks, create assignments, update status, and manage team workflows across the Mycosoft organization.

## **Workspace Configuration**

Asana Workspace Information:

* Workspace GID: 1206459835987965

* Primary Team: Mycosoft Staff (GID: 1206459835987967\)

* Secondary Teams: Engineering, Operations, Infrastructure

## **Access Token Setup**

Two options for authentication:

* Option 1 (Recommended): Create Personal Access Token for schedule@mycosoft.org in Asana

* Option 2: Create Asana Service Account with restricted permissions for automation

* Store token securely: /opt/myca/credentials/asana/access-token.txt

## **n8n Workflow Configuration**

Asana-to-MAS workflow:

* 1\. Asana trigger node: Listen for task created, updated, or commented events

* 2\. Parse task data: Extract task name, description, assignee, custom fields

* 3\. Route to MAS: POST localhost:8001/voice/orchestrator/chat with task context

* 4\. Determine routing: Analyze task and route to appropriate team member

* 5\. Execute action: Create new task, comment, update status, or reassign

## **Routing Rules**

MYCA automatically routes Asana tasks based on expertise:

* Morgan (CEO): Strategic planning, budget, hiring, legal matters

* RJ (COO): Operations, processes, team coordination, customer relations

* Garret (CTO): Infrastructure, technical architecture, code review, deployments

## **MYCA Capabilities**

* Create new tasks in projects

* Comment on existing tasks with status updates

* Update task status and priority

* Assign/reassign tasks to team members

* Log time and track progress

* Generate task summaries and reports

## **Environment Variable**

ASANA\_ACCESS\_TOKEN: \<Personal Access Token from Asana account settings\>

# **8\. Signal Integration**

Signal messaging provides end-to-end encrypted communication for MYCA, ideal for sensitive team coordination and security-focused operations.

## **Phone Number Registration**

Signal requires a valid phone number:

* Obtain a dedicated phone number (virtual or SIM) for schedule@mycosoft.org

* Recommended: Google Voice or Twilio number for flexibility

* Register number with Signal application

* Verify via SMS confirmation code

## **signal-cli Setup**

Deploy signal-cli REST API in Docker:

* Docker image: docker.io/bbernhard/signal-cli-rest-api

* Expose port 8089 on MYCA VM

* Configure environment variables in Docker Compose:

*   \- SIGNAL\_CLI\_ARGS: \--account=\<phone-number\>

*   \- SIGNAL\_CLI\_PASSWORDFILE: /opt/myca/credentials/signal/password.txt

## **n8n Workflow**

Signal-to-MAS workflow:

* 1\. Webhook trigger: Receives Signal message events from signal-cli

* 2\. Parse message: Extract sender, text, attachments

* 3\. HTTP Request: POST to localhost:8001/voice/orchestrator/chat

* 4\. Format response: Plain text or Signal-compatible format

* 5\. HTTP POST: Send response via signal-cli REST API (localhost:8089)

## **Docker Compose Service Configuration**

Example service definition:

* Service name: signal-cli-rest-api

* Image: bbernhard/signal-cli-rest-api:latest

* Port mapping: 8089:8080

* Volume mounts: /opt/myca/credentials/signal

* Network: MYCA internal network

## **Environment Variables**

SIGNAL\_PHONE\_NUMBER: \<Registered Signal phone number\>

# **9\. WhatsApp Integration**

WhatsApp integration provides MYCA access to WhatsApp Business platform for team communication and automated responses.

## **Integration Options**

Two approaches available, each with trade-offs:

Option A: WhatsApp Business API (Official)

* Official Meta integration with business features

* Requires Meta Business Account verification

* Supports message templates and rich media

* Higher reliability and compliance

* More complex setup process

Option B: Baileys Library (Unofficial)

* Unofficial library using WhatsApp Web reverse engineering

* Simpler setup, no business verification required

* Suitable for internal team use

* Lower cost, no API fees

* Less stable, subject to WhatsApp client updates

## **Recommended: Hybrid Approach**

Deploy Option B (Baileys) initially for fast deployment, then migrate to Option A for production stability.

## **Setup Procedure (Baileys)**

* Deploy Baileys Docker container on MYCA VM

* Scan QR code with schedule@mycosoft.org WhatsApp account

* Configure webhook to forward messages to n8n

* Test message sending and receiving

## **n8n Workflow**

WhatsApp-to-MAS workflow:

* 1\. Webhook trigger: Receives message events from Baileys/WhatsApp API

* 2\. Parse message: Extract sender phone, text, media

* 3\. HTTP Request: POST localhost:8001/voice/orchestrator/chat

* 4\. Format response: WhatsApp message format

* 5\. WhatsApp node or HTTP: Send response via Baileys/API

## **Credential Storage**

Store credentials at /opt/myca/credentials/whatsapp/:

* WHATSAPP\_API\_TOKEN: Token for official API (if using Option A)

* WHATSAPP\_PHONE\_ID: Business phone number ID

* WHATSAPP\_VERIFY\_TOKEN: Webhook verification token

# **10\. Gmail Integration**

Gmail integration leverages the Google Workspace service account (from Section 4\) to enable MYCA to read incoming emails and compose intelligent responses.

## **Gmail API Configuration**

Use existing service account from Section 4 with these capabilities:

* Read incoming emails to schedule@mycosoft.org

* Compose and send email responses

* Create draft messages for review

* Manage email labels and archives

* Thread-based conversation handling

## **n8n Workflow**

Gmail-to-MAS workflow:

* 1\. Gmail trigger node: Poll for new emails to schedule@mycosoft.org

* 2\. Parse email: Extract sender, subject, body, attachments

* 3\. Verify sender: Confirm email is from @mycosoft.org address

* 4\. HTTP Request: POST localhost:8001/voice/orchestrator/chat with email context

* 5\. Format response: Compose professional email reply

* 6\. Gmail send: Send response email to original sender

## **Security Filtering**

Critical: Only process emails from @mycosoft.org senders to prevent external attacks:

* Check sender domain against @mycosoft.org whitelist

* Reject external emails with error notification

* Log all rejected messages for security audit

## **MYCA Email Capabilities**

* Read and summarize incoming messages

* Compose professional responses

* Create draft emails for leadership review

* Manage email organization with labels

* Forward to appropriate team member when needed

# **11\. Notion & Google Drive Integration**

Notion and Google Drive serve as centralized document repositories for Mycosoft. MYCA synchronizes document inventory and enables team members to query and manage documentation.

## **Notion Setup**

Existing Notion integration details:

* Database: Mycosoft Docs Sync (synchronized from Google Drive)

* Integration: "Mycosoft Docs Sync" Notion integration with read/update/insert permissions

## **Notion Database Schema**

The synchronization database includes these fields:

* Name/Title: Document filename

* Path/Text: Full path in Google Drive

* Category/Select: Document classification (Architecture, Process, Config, etc.)

* Size/Number: File size in bytes

* Modified/Date: Last modification timestamp

## **Document Synchronization**

Current status: 400+ documents synced from Google Drive to Notion

* Sync scripts: document\_inventory.py, sync\_to\_notion.py

* Schedule: Daily synchronization (3:00 AM UTC)

* Conflict resolution: Drive is source of truth, overwrites Notion on sync

## **Google Drive Configuration**

Configure shared drive access for schedule@mycosoft.org:

* Create shared drive: "MYCA Operations" (or similar)

* Share with schedule@mycosoft.org service account as Editor

* Enable folder sync to track all documents

* Configure backup procedures for critical documents

## **n8n Workflows**

Two complementary workflows:

1\. Google Drive Monitor:

* Trigger: Scheduled daily (3:00 AM) or on file change event

* List all files in shared drive

* Sync to Notion database

* Update document inventory

2\. Document Query:

* Trigger: Request from team member in Discord/Slack

* Search Notion database for matching documents

* Retrieve file metadata and links

* Return results to requester

## **Environment Variables**

Configure the following:

* NOTION\_API\_KEY: Integration token for Notion API

* NOTION\_DATABASE\_ID: GID of synced documents database

* GOOGLE\_DRIVE\_FOLDER\_ID: Root folder for document storage

# **12\. Cowork & Cursor Integration**

Cowork (Claude Desktop) and Cursor provide advanced code generation and AI-assisted development capabilities. MYCA leverages these tools for autonomous code development and deployment tasks.

## **Cowork (Claude Desktop)**

MYCA secretary plugin is pre-installed with specialized skills:

* mas-agent-builder: Create new CrewAI agents

* team-routing: Intelligent task routing to team members

* company-operations: Corporate process automation

* cto-mode: Infrastructure and architecture decisions

* cro-mode: Compliance and risk operations

* ops-dashboard: Operations metrics and monitoring

* approval-gates: Multi-level approval workflows

## **Integration via MAS Orchestrator**

When code generation tasks are identified:

* 1\. MAS Orchestrator receives task in natural language

* 2\. Routes to code-generation agent

* 3\. Code agent initiates Cowork session with task context

* 4\. Cowork generates code and commits to git repository

* 5\. Results returned to user with code review suggestions

## **Cursor Setup**

Deploy Cursor Server in headless mode on MYCA VM:

* Installation: npm install \-g cursor (or via Docker)

* Server mode: cursor \--server \--port 9999

* Authentication: Configure API key for remote access

* Project mounting: Mount git repositories as Cursor workspaces

## **Claude Code CLI**

Install and configure Claude Code CLI for autonomous code operations:

* Installation: npm install \-g @anthropic-ai/claude-code

* Authentication: Set ANTHROPIC\_API\_KEY environment variable

* Use cases: Automated testing, linting, refactoring, deployment

## **Workflow Example: Code Generation Task**

Typical code generation workflow:

* 1\. Team member requests feature in Discord: "/myca create endpoint for user auth"

* 2\. MAS Orchestrator receives request and identifies code generation task

* 3\. Routes to code agent with project context

* 4\. Code agent connects to Cursor Server

* 5\. Cursor generates authentication endpoint code

* 6\. Claude Code CLI runs tests and linting

* 7\. Code committed with automated tests passing

* 8\. User notified with PR link for review

# **13\. n8n Orchestration Workflows (Central Hub)**

n8n serves as the central orchestration platform connecting all communication platforms to the MAS Orchestrator. Currently, 0 workflows are deployed. This section provides templates and priority deployment order.

## **Workflow Architecture Pattern**

All workflows follow a consistent pattern:

* 1\. Platform Trigger: Receive message/event from platform

* 2\. Parse/Normalize: Extract standard fields (sender, text, metadata)

* 3\. Route to MAS: HTTP POST to localhost:8001/voice/orchestrator/chat

* 4\. Format Response: Convert MAS response to platform format

* 5\. Send to Platform: Post response back to originating platform

## **Priority Workflows (Deploy in Order)**

1\. discord-to-mas (Est. 1-2 hours)

* Trigger: Discord message with @MYCA mention or DM

* Parse: Extract user ID, channel ID, message content

* Route: POST localhost:8001/voice/orchestrator/chat

* Response: Format as Discord message

* Send: Discord node to post in channel/DM

2\. slack-to-mas (Est. 1-2 hours)

* Trigger: Slack message event (channel or DM)

* Parse: Extract user, channel, text

* Route: POST localhost:8001/voice/orchestrator/chat

* Response: Format as Slack message with threading

* Send: Slack post message node

3\. asana-to-mas (Est. 2-3 hours)

* Trigger: Asana task created/updated/commented

* Parse: Task data, assignments, deadlines

* Route: POST localhost:8001/voice/orchestrator/chat

* Response: Decision to create task, comment, or update

* Send: Asana nodes for actions

4\. signal-to-mas (Est. 1-2 hours)

* Trigger: Signal message webhook

* Parse: Phone number, message text

* Route: POST localhost:8001/voice/orchestrator/chat

* Response: Plain text response

* Send: signal-cli REST API call

5\. whatsapp-to-mas (Est. 1-2 hours)

* Trigger: WhatsApp message event

* Parse: Phone number, message, media

* Route: POST localhost:8001/voice/orchestrator/chat

* Response: WhatsApp message format

* Send: Baileys/WhatsApp API node

6\. gmail-to-mas (Est. 2-3 hours)

* Trigger: Gmail new email to schedule@mycosoft.org

* Parse: Sender, subject, body

* Filter: Only @mycosoft.org senders

* Route: POST localhost:8001/voice/orchestrator/chat

* Response: Composed email reply

* Send: Gmail send message node

7\. notion-sync (Est. 1-2 hours)

* Trigger: Scheduled daily (3:00 AM UTC)

* Action: List files from Google Drive

* Parse: Extract metadata

* Route: Update Notion database

* Notification: Slack message on sync completion

8\. health-check (Est. 1 hour)

* Trigger: Scheduled every 5 minutes

* Action: Test all platform endpoints

* Check: n8n, MAS Orchestrator, signal-cli, etc.

* Alert: Send alert if service down

* Log: Track uptime metrics

## **Testing and Validation**

For each workflow:

* Test with sample data before deployment

* Verify MAS Orchestrator responds correctly

* Test response formatting for each platform

* Validate error handling and retry logic

* Deploy to production only after successful testing

## **Monitoring and Logging**

Enable logging for all workflows:

* Store workflow logs at /opt/myca/logs/workflows/

* Include timestamp, workflow ID, status, errors

* Alert on workflow failures via health-check

* Review logs weekly for optimization opportunities

# **14\. Setup Checklist**

Comprehensive checklist for MYCA deployment. Complete each step in order, testing functionality before proceeding.

| Step | Platform | Action | Credentials | Time | Status |
| ----- | ----- | ----- | ----- | ----- | ----- |
| 1 | Proxmox | Create VM (8 vCPU, 32GB, 256GB) | Proxmox login | 30 min | Not Started |
| 2 | Ubuntu | Install 22.04 LTS | ISO image | 15 min | Not Started |
| 3 | Docker | Install Docker & Compose | None | 10 min | Not Started |
| 4 | Network | Configure IP, DNS, firewall | VLAN config | 20 min | Not Started |
| 5 | Google | Create service account | Admin access | 20 min | Not Started |
| 6 | Google | Enable Gmail/Drive/Docs APIs | Project ID | 10 min | Not Started |
| 7 | Google | Configure delegation | OAuth creds | 15 min | Not Started |
| 8 | Discord | Create App & Bot | Discord acc | 15 min | Not Started |
| 9 | Discord | Enable intents & perms | Bot token | 10 min | Not Started |
| 10 | Slack | Create App | Workspace admin | 15 min | Not Started |
| 11 | Slack | Configure scopes & events | App creds | 10 min | Not Started |
| 12 | Asana | Create access token | Asana acc | 5 min | Not Started |
| 13 | Signal | Register phone & CLI | Phone num | 30 min | Not Started |
| 14 | WhatsApp | Deploy Baileys or API | WhatsApp acc | 45 min | Not Started |
| 15 | Notion | Verify integration | API key | 10 min | Not Started |
| 16 | Drive | Mount shared folder | Folder ID | 10 min | Not Started |
| 17 | n8n | Deploy n8n container | Docker | 10 min | Not Started |
| 18 | MAS | Deploy Orchestrator | Docker | 10 min | Not Started |
| 19 | Reverse Proxy | Configure Caddy/Nginx | SSL cert | 30 min | Not Started |
| 20 | n8n | discord-to-mas flow | Creds | 2 hrs | Not Started |
| 21 | n8n | slack-to-mas flow | Creds | 2 hrs | Not Started |
| 22 | n8n | asana-to-mas flow | Creds | 2 hrs | Not Started |
| 23 | n8n | signal-to-mas flow | Creds | 2 hrs | Not Started |
| 24 | n8n | whatsapp-to-mas flow | Creds | 2 hrs | Not Started |
| 25 | n8n | gmail-to-mas flow | Creds | 2 hrs | Not Started |
| 26 | n8n | notion-sync flow | Creds | 2 hrs | Not Started |
| 27 | n8n | health-check flow | None | 1 hr | Not Started |
| 28 | Testing | End-to-end tests | All creds | 3 hrs | Not Started |
| 29 | Security | Setup vault & access | Vault SW | 1 hr | Not Started |
| 30 | Monitoring | Enable logging | Log agg | 1 hr | Not Started |

## **Total Estimated Setup Time**

2-3 days for complete MYCA deployment, including:

* VM setup: 2 hours

* Google Workspace: 1 hour

* Platform integrations: 3 hours

* n8n workflows: 15 hours

* Testing and validation: 3 hours

* Security hardening: 1 hour

Recommended approach: Deploy workflows in priority order (Section 13), testing each thoroughly before adding the next.

# **15\. Security & Access Control**

Security is paramount for MYCA operations. This section defines access controls, credential management, and operational security procedures.

## **Access Control**

Authorization:

* Only @mycosoft.org email addresses authorized

* Team access: Morgan (CEO), RJ (COO), Garret (CTO)

* Contractors: Temporary access with explicit approval

* External parties: No direct access

Authentication Methods:

* Discord: Whitelist @mycosoft.org member IDs

* Slack: Verify user domain in workspace

* Asana: Service account tied to @mycosoft.org

* Email: Only process @mycosoft.org senders

* All platforms: Reject external users

## **Credential Management**

All API keys stored on MYCA VM at /opt/myca/credentials/:

* File structure: /opt/myca/credentials/{platform}/{name}

* Example: /opt/myca/credentials/discord/bot-token.txt

* Permissions: 400 (read-only for myca user)

* Owner: myca:myca service account

* Access: Via application only, no shell access

## **n8n Credential Encryption**

n8n encrypts all stored credentials:

* Enable encryption at rest (configure .env)

* Backup: Export encrypted backups

* Rotation: Update without redeploying workflows

* Audit: Log credential access attempts

## **Webhook Security**

All webhook endpoints protected:

* HTTPS/TLS only via reverse proxy

* IP whitelisting for authorized platforms

* Rate limiting: 100 requests/minute max

* Signature verification from Discord, Slack, etc.

* CORS: Restrict to trusted domains

## **Safety Workflow for Destructive Actions**

Three-stage approval process:

* speech\_turn: Initial command received

* speech\_safety: Safety check identifies risk

* speech\_confirm: Leadership confirmation required

* Applies to: Delete, modify, bulk operations

* Bypassed for: Read, query, passive operations

## **Audit Logging**

Comprehensive logs maintained at /opt/myca/logs/:

* Workflow execution: /opt/myca/logs/workflows/

* API calls: /opt/myca/logs/api/

* Credential access: /opt/myca/logs/credentials/

* Security events: /opt/myca/logs/security/

* Retention: 90 days minimum (365 recommended)

## **Incident Response**

In case of security incident:

* 1\. Disable affected MYCA platform immediately

* 2\. Rotate compromised credentials

* 3\. Review audit logs for unauthorized access

* 4\. Notify leadership (Morgan, RJ, Garret)

* 5\. Conduct post-incident review

* 6\. Re-enable service after verification

## **Backup & Disaster Recovery**

Ensure MYCA recovery from failures:

* Daily VM snapshots via Proxmox

* Encrypted credential backups (separate storage)

* n8n workflow exports (weekly)

* Database backups (nightly)

* RTO: 1 hour, RPO: 1 hour

