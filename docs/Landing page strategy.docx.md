# NatureOS Dual‑Interface Platform – Technical Specification

This document defines a complete architecture and implementation plan for transforming the Mycosoft website into a dual‑interface platform serving both human visitors and autonomous agents. The goal is to provide **immediate, pay‑per‑use access** to NatureOS’s unique environmental intelligence while preserving the existing search experience and current code base. The specification is designed so that it can be handed off to a code generator such as Cursor to scaffold the necessary files without breaking existing functionality.

## 1\. Background and Goals

Mycosoft has built a rich ecosystem around NatureOS: a CREP (Continuous Environmental Picture) dashboard, the MINDEX event graph, Myca (an AI chat agent), and a family of devices feeding real‑time signals. The platform ingests weather, pollution, species observations, air/sea/land traffic, seismic events and more, normalizes them into a unified graph and produces **worldview snapshots** with Merkle roots and geotagged events. Myca uses this worldview to answer questions and provide environmental context.

The company now wants to monetize this data by selling it directly to **autonomous agents** in addition to offering user‑facing dashboards for humans. Agents need to sign up and pay automatically (e.g. via x402 agentic payments), receive API keys or pay‑per‑request credentials, and then call NatureOS for worldviews, MINDEX queries or device feeds. Humans should still be able to chat with Myca, use the CREP map and search pages.

## 2\. High‑Level Architecture

The solution is divided into four layers:

1. **Presentation (Web Front‑End)** – A Next.js/React site that presents a homepage with two clear paths: *Human* and *Agent*. It must retain existing pages (e.g. the search page) and provide navigation to Myca, CREP map and other dashboards. Agents see machine‑readable metadata and endpoints to register, pay and obtain credentials.

2. **API Gateway and Payment Layer** – A Node.js/Express gateway that routes all API requests, enforces authentication and implements **usage‑based billing**. When payment is required, the gateway returns an HTTP 402 response with a payment request formatted per the x402 specification. The request includes the maximum amount, asset type (USDC, ETH, etc.), payment address, network and a nonce[\[1\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,identifier%20for%20this%20payment%20request). Clients sign and submit payment authorizations using EIP‑712 signatures[\[2\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Authorization%20When%20submitting%20payment%2C,standard%2C%20enabling%20clear%20and%20secure).

3. **Data & Intelligence Services** – Services for worldview generation (CREP ingestion, Merkle‑root snapshots), MINDEX queries, Myca inference and device streams. These are implemented as microservices behind the API gateway. Each service exposes REST/GraphQL endpoints with pay‑per‑request wrappers. Agents can subscribe to streaming endpoints for continuous worldviews.

4. **Billing & Monitoring** – A usage metering component that records the number of requests, data volume and features used per agent. When thresholds are exceeded, it triggers the payment layer to issue 402 responses prompting additional payment.

The system must support multiple payment methods. For crypto payments, integrate the **x402 protocol** (see the payment request and authorization specification) to enable fully autonomous payments[\[3\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,standard%2C%20enabling%20clear%20and%20secure). For traditional payments, support Stripe/PayPal APIs and set up a fallback pre‑paid balance mechanism.

## 3\. Front‑End Specification

### 3.1 Homepage Redesign

The existing homepage currently hosts a search interface. We will move the search UI to its own /search route (if not already) and designate the new homepage as a **landing page**. The landing page features two call‑to‑action panels:

* **Human Experience:** Presents a hero section introducing NatureOS, Myca chat and CREP dashboard. Provides buttons such as *“Chat with Myca”*, *“View the CREP Map”* and *“Explore NatureOS”*. The site continues to use existing React components and styling. The search page remains accessible via navigation.

* **Agent Interface:** Provides machine‑readable metadata (JSON‑LD embedded in \<script type="application/ld+json"\>) describing available endpoints and pricing tiers. The UI includes sections like *“Register your agent”*, *“Obtain API key or CLI”* and *“View Pricing”*. Each call‑to‑action points to machine‑friendly endpoints (see Section 4). Include documentation links for CLI usage and MCP access.

To avoid accidentally hiding endpoints from scrapers, ensure the agent interface is linked from the root and indexable (e.g. \<a href="/agent"\>Agent Access\</a\>). For human visitors, interactive elements must degrade gracefully if JavaScript is disabled.

### 3.2 Agent Detection

Agents will generally not render JavaScript; they will parse HTML/JSON. Provide both a human‑friendly UI and a machine‑readable JSON description. Use one or more of the following mechanisms to detect agents:

* **User‑Agent header:** Provide guidelines in the docs for agents to include a custom user‑agent (e.g. NatureOS-Agent), but do not rely solely on this for routing.

* **URL parameters or path:** Provide an /agent path that returns pure JSON endpoints and documentation. Agents that land on the homepage can follow the link automatically. Humans can also view it.

* **Accept header:** Agents may set Accept: application/json. If the homepage receives such a header, return the JSON description automatically instead of HTML.

### 3.3 Search Page and Existing Routes

The current search functionality remains under /search. Do **not** delete or rename this page. All other existing routes (e.g. /about, /devices, /apps) remain intact. Add navigation entries for the new *Agent* and *Human* experiences.

## 4\. API & Payment Layer

### 4.1 Agent Registration Endpoint

Agents must register to obtain an identifier and initial balance. Endpoint:

POST /api/agents/register

Request body (JSON):

{  
  "name": "string",           // agent name or identifier  
  "owner": "string",          // optional owner contact or organization  
  "paymentMethod": {  
    "type": "x402|stripe|paypal|custom",  
    "details": { ... }         // crypto wallet address or payment token  
  }  
}

Response:

* 201 Created with { "agentId": "uuid", "apiKey": "string", "balance": 0 }.

Agents can specify multiple payment methods. The apiKey is a fallback secret used when x402 cannot be negotiated. For crypto payments, store the wallet address and network.

### 4.2 Payment Workflow (x402)

NatureOS will use the x402 protocol to request payment. When an agent calls a premium endpoint without sufficient balance, the API responds with HTTP **402 Payment Required** containing a JSON payload with the following fields[\[1\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,identifier%20for%20this%20payment%20request):

{  
  "paymentId": "uuid",        // unique request identifier  
  "maxAmountRequired": "0.10",// maximum payment required (e.g. USDC)  
  "assetType": "ERC20",       // token standard  
  "assetAddress": "0x...",    // USDC contract address  
  "paymentAddress": "0x...",  // recipient address (Mycosoft treasury)  
  "network": "base-mainnet",  // blockchain network  
  "expiresAt": "2026-03-12T00:00:00Z",  
  "nonce": "randomString"  
}

Clients must sign a **payment authorization** including all of the above fields and the actual payment amount (≤ maxAmountRequired) with EIP‑712 and return it in a follow‑up POST to /api/payments/authorize[\[2\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Authorization%20When%20submitting%20payment%2C,standard%2C%20enabling%20clear%20and%20secure).

On successful authorization, the gateway credits the agent’s balance and continues processing the original request. Failed or expired payments return 403 Forbidden.

### 4.3 Pricing & Usage Metering

Define service tiers:

| Tier | Access | Price per call |
| ----: | :---- | ----: |
| **Free** | Basic worldviews (daily snapshot, limited resolution) | $0 per call |
| **Standard** | Hourly worldviews, MINDEX search endpoints | $0.05 per request |
| **Premium** | Real‑time worldviews, streaming events, Myca inference API | $0.10 per request or $1/minute stream |
| **Enterprise** | Dedicated bandwidth, custom models, device control | Negotiable |

The billing engine records each request with the agentId, endpoint name, timestamp and bytes transferred. When the accumulated cost approaches zero balance, the gateway automatically triggers an x402 payment request. Traditional payment methods (Stripe/PayPal) are charged in prepaid increments (e.g. $10 blocks).

### 4.4 REST/GraphQL Endpoints

Examples:

1. GET /api/worldview/latest – returns the most recent worldview snapshot (geo‑JSON, Merkle root, timestamp). Requires Standard tier.

2. GET /api/worldview/{timestamp} – returns the snapshot for a given timestamp.

3. POST /api/worldview/stream – opens a server‑sent events (SSE) or WebSocket stream delivering live worldviews. Metered per minute.

4. GET /api/mindex/search – query MINDEX for events or graph relationships; accepts filters like species, location, timeRange.

5. POST /api/myca/chat – returns answers generated by Myca using the current worldview and the user’s prompt. Parameter stream=true returns streaming tokens.

6. GET /api/devices/{deviceId}/stream – returns real‑time sensor data from Mycorrhizae devices. Available to Premium tier.

All endpoints check the agentId/apiKey from the Authorization header. If the agent has insufficient balance, respond with 402 Payment Required.

## 5\. Data & Intelligence Services

### 5.1 CREP Ingestion & Normalization

* **Sources:** Weather APIs, pollution sensors, flight/ship tracking, iNaturalist species observations, seismic databases, NOAA/NASA satellites, lightning/fire detectors.

* **Processor:** A streaming pipeline normalizes each event into a canonical schema with fields: id, source, eventType, geotag, timestamp, payload. Use a graph database (e.g. Neo4j) or time‑series database to store events.

* **Merkle‑Root Worldviews:** For each clock tick (e.g. every minute), compute a Merkle tree over all events in that interval. The Merkle root forms the worldview snapshot. Include the list of event hashes as leaves, plus tags for geolocation and categories. Use a DAG (directed acyclic graph) representation to link snapshots over time.

### 5.2 MINDEX (Memory Index)

MINDEX stores historical events and relationships. Expose a GraphQL API for complex queries, such as “find all pollution events within 10 km of a given point between two timestamps” or “return all species observed on a trail in the last week.” Use a vector index for similarity queries (e.g. nearest neighbors in embedding space). Provide REST wrappers for agents.

### 5.3 Myca Inference Service

Package Myca’s reasoning capabilities as a microservice. The service maintains state (knowledge of current worldview, conversation context) and exposes endpoints for natural‑language queries. For agent access, strip any user‑facing fluff and return structured answers (JSON with fields like answer, sources, confidence). Only pay for compute time used to run the model.

## 6\. CLI and Client Libraries

Provide an official CLI in Node.js or Python to simplify agent integration. Features:

* **Registration & login** – register an agent, store apiKey locally, select payment method.

* **Query commands** – worldview, mindex-search, myca-query, with flags for tier selection.

* **Streaming** – support WebSocket or SSE streaming of worldviews/events.

* **Auto‑payment** – detect 402 responses and perform x402 payments automatically if a crypto wallet is configured. For Stripe/PayPal, prompt for top‑ups.

Example CLI usage:

mycosoft register \--name "WeatherBot" \--wallet 0xABC123  
mycosoft worldview \--latest \--tier standard  
mycosoft mindex-search \--species "Falco peregrinus" \--range "2026-03-01/2026-03-11"

Document the CLI commands in markdown and embed the docs as part of the agent landing page.

## 7\. MCP & Multi‑Agent System

The **MCP (Model Context Payment) Server** coordinates multi‑agent interactions. It allows agents to request context retrieval for other models and pay per context token. Integrate the MCP server behind the API gateway with endpoints such as:

* POST /api/mcp/context – agent provides the target model, input prompt and maximum tokens; returns a 402 if payment is required, otherwise returns the context.

* POST /api/mcp/agent-call – allows agents to invoke each other’s capabilities through the Mycosoft network (e.g. call Myca on behalf of another agent, with proper authentication and billing).

The MCP server interacts with x402 to monetize context retrieval. Use the payment request format described above[\[3\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,standard%2C%20enabling%20clear%20and%20secure).

## 8\. Monitoring, Logging and Compliance

* **Metrics:** collect metrics per agent (requests per endpoint, data volume, latency) using tools like Prometheus. Expose dashboards for internal monitoring.

* **Error Handling:** return clear error codes (400 for bad requests, 401 for invalid API keys, 402 for payment required, 403 for expired or invalid payment, 429 for rate limits).

* **Regulatory compliance:** follow data protection laws (e.g. GDPR, CCPA). Provide a privacy notice and ensure personal data in MINDEX and CREP is anonymized or aggregated.

* **Security:** all endpoints use HTTPS. Sign API responses if necessary. Use rate limiting and bot detection to prevent abuse.

## 9\. Development and Testing Plan

1. **Merge Pending Pull Requests:** ensure all open PRs (e.g. from Claude and Cursor) are merged. Do not overwrite existing pages or delete files.

2. **Create Branches:** create a feature branch dual-interface-platform. Scaffold new directories:

├── pages/  
│   ├── index.tsx          \# new homepage with human/agent split  
│   ├── agent.tsx          \# agent landing page (JSON and UI)  
│   ├── search.tsx         \# existing search page (unchanged)  
│   └── ...  
├── api/  
│   ├── agents/register.ts \# registration handler  
│   ├── payments/authorize.ts  
│   ├── worldview/latest.ts  
│   ├── worldview/stream.ts  
│   ├── mindex/search.ts  
│   ├── myca/chat.ts  
│   └── mcp/context.ts  
└── lib/  
    ├── billing.ts         \# usage metering and x402 integration  
    ├── crep.ts            \# CREP ingestion & snapshot logic  
    ├── mindex.ts          \# MINDEX query wrappers  
    ├── myca.ts            \# Myca inference wrappers  
    └── security.ts        \# auth & rate limiting

1. **Implement Payment Integration:** create a module lib/billing.ts with functions:

2. checkBalance(agentId, cost) – returns true/false.

3. issuePaymentRequest(agentId, cost) – returns the x402 payment payload with fields described above[\[3\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,standard%2C%20enabling%20clear%20and%20secure).

4. authorizePayment(paymentId, signature) – validates EIP‑712 signature and credits balance.

5. charge(agentId, cost) – deducts cost from balance.

6. **Develop API Handlers:** each handler imports checkBalance and charge. If balance is insufficient, respond 402 with payment payload. Otherwise, perform the underlying service call (e.g. fetch latest worldview) and return data.

7. **Write Tests:** for each endpoint, write unit tests covering registration, payment flows, error conditions and rate limits. Use mock wallets for x402 (see whitepaper for test tools[\[4\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=The%20x402%20toolkit%20includes%20a,without%20connecting%20to%20production%20blockchains)).

8. **Documentation:** generate API reference using tools like Swagger/OpenAPI. Create a README for the CLI and add markdown documentation pages under /docs or embed them into the agent landing page.

9. **Deploy & Monitor:** deploy the services with auto‑scaling (e.g. Kubernetes). Set up logging and monitoring dashboards. Test payment flows on testnets (e.g. Base Goerli) before mainnet.

## 10\. Future Considerations

* **Predictive Upselling:** implement analytics to predict when an agent will exceed its quota and proactively send a 402 request with a recommendation to upgrade.

* **Sandbox Mode:** provide a sandbox environment where agents can test the APIs with fictitious data and free tokens before committing to pay.

* **Partnerships with Agent Platforms:** integrate with popular agent ecosystems (e.g. OpenAI’s function calling, LangChain, or AgentHub) so that they can easily discover and use NatureOS via plugin manifests.

## 11\. References

* x402 Whitepaper – Payment request and authorization fields, example server and client implementations[\[5\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,settlement%20through%20various%20methods%3A%2010). The payment request must include fields like maxAmountRequired, assetType, assetAddress, paymentAddress, network, expiresAt and nonce[\[1\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,identifier%20for%20this%20payment%20request). Payment authorization requires signing these fields using EIP‑712 and including the actual payment amount and timestamp[\[2\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Authorization%20When%20submitting%20payment%2C,standard%2C%20enabling%20clear%20and%20secure).

* The whitepaper also provides example Node.js middleware (@x402/express-middleware) and client libraries (@x402/client) for integrating x402 into Express and browser environments[\[6\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=%2F%2F%20Install%20with%3A%20npm%20install,the%20x402%20client%20library%3A%2011). These can be adapted into NatureOS’s billing layer.

---

This specification ensures a seamless dual‑interface experience, a robust API & payment infrastructure and a clear path for agents to discover, register, pay and scale their use of NatureOS. With careful adherence to the x402 protocol and respect for existing code, the company can quickly attract both human users and autonomous agents while maintaining system integrity.

---

[\[1\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,identifier%20for%20this%20payment%20request) [\[2\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Authorization%20When%20submitting%20payment%2C,standard%2C%20enabling%20clear%20and%20secure) [\[3\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,standard%2C%20enabling%20clear%20and%20secure) [\[4\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=The%20x402%20toolkit%20includes%20a,without%20connecting%20to%20production%20blockchains) [\[5\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=Payment%20Request%20Format%20When%20an,settlement%20through%20various%20methods%3A%2010) [\[6\]](https://www.x402.org/x402-whitepaper.pdf#:~:text=%2F%2F%20Install%20with%3A%20npm%20install,the%20x402%20client%20library%3A%2011) x402: The Payment Protocol for Agentic Commerce

[https://www.x402.org/x402-whitepaper.pdf](https://www.x402.org/x402-whitepaper.pdf)