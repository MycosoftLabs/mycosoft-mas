# Analysis of Candidate GitHub Projects for Mycosoft Integration

The following table groups the repositories you provided by the main categories relevant to Mycosoft’s products. For each project I summarised its purpose, key capabilities and potential integration points for Mycosoft (website, applications, dashboards or developer tools). Citations come from the projects’ README files or official documentation.

## 1\. Core platform / Website foundation

| Project | Summary & capabilities | Potential Mycosoft integration |
| :---- | :---- | :---- |
| **MycosoftLabs/website** | This is the active codebase of the new Mycosoft website and dashboard. It is a Next.js application providing several core dashboards: **CREP** (real‑time environmental awareness), **NatureOS** (Earth systems monitoring), **MycoBrain** (IoT device management), species database and phylogenetic **Ancestry Tools**[\[1\]](https://github.com/MycosoftLabs/website/blob/main/README.md#L9-L15). The repo includes a detailed project structure with Next.js App Router pages (dashboard, natureos, devices) and React components for each section[\[2\]](https://github.com/MycosoftLabs/website/blob/main/README.md#L35-L56). Docker‑compose scripts manage services such as PostgreSQL, Redis and various data collectors[\[3\]](https://github.com/MycosoftLabs/website/blob/main/README.md#L71-L84). | Serves as the base for Mycosoft.com and the sandbox site. Additional UI/UX components can be integrated here. Provides a foundation for dashboards and device integration. |
| **vercel‑labs/json‑render** | json‑render is a library that allows AI to output structured JSON and translate it into UI elements. It limits AI to a catalog of predefined components, making the output guard‑railed and predictable[\[4\]](https://github.com/vercel-labs/json-render#:~:text=Predictable). Developers define a catalog with zod schemas and register components; the AI then generates dashboards or widgets by emitting JSON that the library renders. It includes rich UI features like conditional visibility rules and confirmation dialogs. | Allows Mycosoft to let AI agents (e.g., MYCA) build widgets/dashboards from natural language prompts while ensuring UI consistency. Could be used inside the website or internal dashboards to permit dynamic, AI‑generated interfaces. |
| **itshover/itshover** | Animated icon library built with React and motion/react that provides over 186 icons covering UI essentials, social logos, tech logos and actions[\[5\]](https://github.com/itshover/itshover/blob/main/README.md#L42-L51). Icons animate on hover, are provided as drop‑in React components and can be customized in stroke width and colors[\[6\]](https://github.com/itshover/itshover/blob/main/README.md#L9-L13). | Enhances the website and dashboards with modern, animated icons. Icons can be integrated into Next.js pages or dashboards for better UX and to indicate interactive elements. |
| **NeXTs/Clusterize.js** | A tiny vanilla‑JS plugin for displaying very large datasets in tables or lists. It works by splitting the list into clusters and rendering only elements for the current scroll position, while adding extra rows to maintain the correct scroll height[\[7\]](https://clusterize.js.org/#:~:text=). | Suitable for Mycosoft dashboards (e.g., mindex, NatureOS, species database) where large tables need to scroll efficiently without DOM bloat. Useful for the ancestry database and real‑time data tables. |
| **perspective‑dev/perspective** | Perspective is an interactive analytics and data‑visualisation component that can handle large or streaming datasets. It includes a fast, memory‑efficient query engine (written in C++ and compiled to WebAssembly) and a framework‑agnostic custom element for UI[\[8\]](https://github.com/perspective-dev/perspective/blob/master/README.md#L17-L34). It provides Python, Rust and JavaScript clients and integrates with JupyterLab[\[9\]](https://github.com/perspective-dev/perspective/blob/master/README.md#L35-L37). | Can provide user‑configurable data grids or dashboards on Mycosoft’s site. Could power interactive views of simulation results or environmental datasets with pivoting, sorting and streaming updates. |
| **metafizzy/packery** | Packery is a JavaScript library that creates gapless, draggable grid layouts using a bin‑packing algorithm[\[10\]](https://packery.metafizzy.co/#:~:text=What%20is%20Packery%3F). Items can be stamped in place, fit in specific spots or dragged around, making it ideal for dashboards where users rearrange widgets[\[10\]](https://packery.metafizzy.co/#:~:text=What%20is%20Packery%3F). | Provides the draggable, customizable dashboard grid the user described. Users could arrange simulation widgets or data panels in the CREP/NatureOS dashboards. Combining with user‑type templates would allow different default layouts by customer type. |
| **originalankur/maptoposter** | Python CLI script to generate minimalist map posters for any city. Supports 17 themes and allows distance radius selection[\[11\]](https://github.com/originalankur/maptoposter/blob/main/README.md#L89-L110). Uses OSM data via OSMnx and Matplotlib; outputs images with optional custom themes[\[12\]](https://github.com/originalankur/maptoposter/blob/main/README.md#L117-L137). | For Earth simulator: could produce map images with custom styles that feed into AI models or appear in customer‑facing dashboards. Images could be combined with data overlays (e.g., species distribution) then pipelined to MycoBrain or MYCA for pattern recognition. |
| **yorkeccak/history** | “History” is an open‑source app that displays an interactive 3D globe where users click anywhere to trigger an AI‑driven research process. It leverages the Valyu DeepResearch API to pull data from historical databases, archives, exploration logs and real‑time sources, running for up to 10 minutes and providing fully cited research[\[13\]](https://github.com/yorkeccak/history/blob/main/README.md#L19-L30). The front end uses Mapbox GL JS in a Next.js/React app, and the results show timelines and citations[\[14\]](https://github.com/yorkeccak/history/blob/main/README.md#L53-L68). | Inspiration for Mycosoft’s Earth simulator or CREP interface: the 3D globe and research pipeline could inform ways to present environmental or historical context for fungal species or climate data. Integration may involve similar interactive globe UI or summarising remote research results. |

## 2\. Simulation and game‑engine tools

| Project | Summary & capabilities | Potential integration |
| :---- | :---- | :---- |
| **Facepunch/sbox‑public** | s\&box is a modern game engine built on Valve’s Source 2 and .NET. It provides a modern, intuitive editor for creating games and allows building the engine from source[\[15\]](https://github.com/Facepunch/sbox-public#:~:text=s%26box). It is aimed at developers who want to compile and extend the engine; Visual Studio and .NET 10 SDK are required. | Could power Mycosoft’s mushroom or compound simulators by providing a 3D simulation environment, realistic physics and an extensible editor. The Source 2 engine supports high‑fidelity visuals, which may enhance user engagement in the science simulators. |
| **pixlcore/xyOps** | xyOps is a job‑scheduling, workflow‑automation, server monitoring and incident‑response platform. It combines job scheduling beyond cron with real‑time monitoring, custom alerts and incident response. It has a graphical workflow editor connecting events, triggers, actions and monitors[\[16\]](https://github.com/pixlcore/xyops#:~:text=xyOps%E2%84%A2). The system is built for developers and operations teams, providing scalability and a developer‑friendly design[\[17\]](https://github.com/pixlcore/xyops#:~:text=Features%20at%20a%20Glance). | Useful for Mycosoft’s deployment and CI/CD pipeline. Could automate data collectors, schedule simulations, monitor servers and handle alerts from IoT devices. Integrates operations for all back‑end services. |
| **midudev/disable‑cloudflare‑cli (Cloudflare Proxy Manager)** | CLI tool to list Cloudflare zones, view DNS records and enable/disable the Cloudflare proxy (orange cloud). Provides interactive selection of domains, multi‑language support and visual indicators[\[18\]](https://github.com/midudev/disable-cloudflare-cli/blob/main/README.md#L5-L16). | Helpful for devops staff working on the sandbox site or production (mycosoft.com). Allows quick toggling of Cloudflare proxy settings while troubleshooting or setting up direct connections for services. |
| **port‑killer** | Cross‑platform desktop app for port management. Auto‑discovers listening ports, allows one‑click process termination, includes search/filter, favorites and notifications[\[19\]](https://github.com/productdevbook/port-killer/blob/master/README.md#L46-L56). Integrates with Kubernetes port forwarding and Cloudflare Tunnels[\[20\]](https://github.com/productdevbook/port-killer/blob/master/README.md#L57-L66), and has native UI on macOS and Windows. | Valuable on the dev machine and MycoBrain devices. Manages local ports, kills processes occupying serial ports used by IoT devices, monitors Kubernetes port forwards and Cloudflare tunnels. Eases development on machines with multiple services. |
| **kriuchkov/tock (time‑tracker)** | tock is a CLI time‑tracking tool with an interactive terminal UI. It stores activities in plaintext and provides features like iCal export, productivity analysis (deep work score, chronotype, context switching metrics)[\[21\]](https://github.com/kriuchkov/tock/blob/master/README.md#L12-L24)[\[22\]](https://github.com/kriuchkov/tock/blob/master/README.md#L453-L465). Users can start/stop tasks, view calendars, generate reports and integrate with TimeWarrior. | Helps Mycosoft developers track time spent on tasks and projects. Integration into the Mycosoft shell or cursor environment could improve productivity measurement and provide analytics for management. |
| **tock/tock (Tock OS)** | An embedded operating system written in Rust, designed for running multiple concurrent applications on Cortex‑M and RISC‑V microcontrollers with memory protection and safety[\[23\]](https://github.com/tock/tock/blob/master/README.md#L7-L17). It isolates apps using MPUs and the Rust type system. | May be useful if Mycosoft develops firmware for field devices (e.g., MycoBrain sensors) requiring secure multitasking. Otherwise outside main scope. |
| **itssamuelrowe/Zen** | A nascent general‑purpose programming language with a compiler implemented in this repository. The README provides examples and instructions but notes that the language is under development[\[24\]](https://github.com/itssamuelrowe/Zen/blob/main/README.md#L2-L10). | Not directly relevant to Mycosoft’s immediate needs; interesting for experimentation but not production‑ready. |

## 3\. Developer tools & shell integration

| Project | Summary & capabilities | Potential integration |
| :---- | :---- | :---- |
| **CodeOne45/vex‑tui** | Terminal‑based spreadsheet editor built in Go. Provides editing of Excel/CSV files, formulas, insertion/deletion of rows/columns, copy/paste, undo/redo, live data visualisation and theme customization[\[25\]](https://github.com/CodeOne45/vex-tui#:~:text=Vex%20). Supports exporting to CSV/JSON and includes a formula engine and charting. | Can be integrated into the Mycosoft shell (on the sandbox site) to let developers and analysts view and edit tabular data within a terminal, similar to Excel but CLI‑native. Beneficial for handling simulation outputs or database extracts via cursor. |
| **drclcomputers/GoSheet** | Feature‑rich terminal spreadsheet application built with Go and tview. Offers multiple sheets, 104 built‑in functions, rich cell formatting, undo/redo, smart navigation and Excel‑like data validation[\[26\]](https://github.com/drclcomputers/GoSheet/blob/main/README.md#L20-L33)[\[27\]](https://github.com/drclcomputers/GoSheet/blob/main/README.md#L36-L61). Supports numerous file formats (native GSheet, JSON, Excel, CSV, PDF, HTML) with import/export capabilities[\[28\]](https://github.com/drclcomputers/GoSheet/blob/main/README.md#L31-L32). | Provides an even more comprehensive spreadsheet environment than Vex TUI. Could be offered to internal staff and customers via the MycoBrain shell for data entry, analysis and reporting. Useful for dashboards requiring spreadsheet interactions. |
| **ComposioHQ/open‑claude‑cowork** | Open‑source desktop chat application that uses the Claude Agent SDK and Composio tool router to build AI agents with access to 500+ tools[\[29\]](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md#L25-L42). Supports multiple providers (Claude, Opencode), persistent chat sessions, multi‑chat, streaming responses and tool‑call visualization[\[30\]](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md#L36-L49). Built with Electron and Node/Express[\[31\]](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md#L52-L60). | Could serve as a local coworking interface for Mycosoft staff to interact with AI agents (including MYCA) and access integrated tools (Gmail, Slack, GitHub). Provides an example of multi‑provider agent integration with streaming and session management. |
| **xyOps** | Already covered under simulation but relevant for developer tools: provides job scheduling, workflow automation and server monitoring. | Use to automate dev tasks, schedule data processing, and monitor simulation services. |
| **midudev/disable‑cloudflare‑cli** | CLI to manage Cloudflare DNS proxy settings; see above. | Integrate into shell for devs performing Cloudflare operations. |
| **nodemailer/nodemailer** | Popular Node.js module for sending emails. The README directs users to [nodemailer.com](https://nodemailer.com) for full docs and notes that it allows sending emails as easily as cake[\[32\]](https://github.com/nodemailer/nodemailer/blob/master/README.md#L2-L15). | If the Mycosoft platform needs to send notification emails (e.g., sign‑up confirmations, report delivery), Nodemailer can be integrated into the Node back‑end services. It supports OAuth and multiple transport methods. |
| **sharp (lovell/sharp)** | High‑speed Node‑API module for image processing. Converts images to JPEG/PNG/WebP/AVIF, performs resizing, rotation, extraction and compositing, and is 4–5× faster than ImageMagick due to libvips[\[33\]](https://github.com/lovell/sharp/blob/main/README.md#L5-L21). | Ideal for processing fungal images or environmental maps: resizing, cropping and converting images before storing them in the species database or rendering them on the website. Ensures images are optimized without bloat. |
| **Lulzx/zpdf** | PDF text‑extraction library written in Zig. Provides memory‑mapped reading, supports multiple decompression filters and font encodings, and can extract structure trees for logical reading order[\[34\]](https://github.com/Lulzx/zpdf/blob/main/README.md#L5-L15). Benchmarks show it is several times faster than MuPDF for extraction[\[35\]](https://github.com/Lulzx/zpdf/blob/main/README.md#L20-L25). | Useful for your requirement to scrape research papers and convert them to Markdown. zpdf can extract text from PDFs efficiently; the extracted text can then be parsed into Markdown and stored in Mycosoft’s knowledge base or species pages. |
| **TONL (tonl‑dev/tonl)** | Token‑Optimized Notation Language: a compact, human‑readable data format that reduces JSON size by \~32–45 % and token costs for LLM prompts[\[36\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L58-L68). Provides query, modification, indexing and streaming APIs with TypeScript and CLI support[\[37\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L71-L101). The CLI offers interactive dashboards, file comparison, themes and full schema validation[\[38\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L154-L206)[\[39\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L326-L334). | Could be adopted internally for storing large datasets (e.g., species or simulation data) in a compact form, reducing costs when sending structured data to LLMs (MYCA). The interactive CLI and API could help devs query and manipulate data. |

## 4\. Image, data and research utilities

| Project | Summary & capabilities | Potential integration |
| :---- | :---- | :---- |
| **maptoposter** | See above; generates stylized city map posters in various themes[\[11\]](https://github.com/originalankur/maptoposter/blob/main/README.md#L89-L110). | Use to create map images for Earth simulator or combine with data overlays for pattern‑detection pipelines. |
| **history** | See above; interactive globe with AI research. | Inspiration for Earth simulator UI and research integration. |
| **zpdf** | See above. | Use for PDF scraping and converting research papers to text for Mycosoft’s knowledge base. |
| **sharp** | See above. | Use for resizing and optimizing images (fungal photos, device images) before serving them. |
| **Clusterize.js, perspective** | Already noted under website improvements. | Use to handle large data tables and visualizations in dashboards. |

## 5\. Miscellaneous / potential out‑of‑scope projects

| Project | Reason it may be less relevant |
| :---- | :---- |
| **Zen (programming language)** | Still under development; not directly related to Mycosoft’s objectives beyond experimentation[\[24\]](https://github.com/itssamuelrowe/Zen/blob/main/README.md#L2-L10). |
| **Tock OS** | Embedded OS for microcontrollers; relevant only if Mycosoft develops firmware for sensors or devices[\[23\]](https://github.com/tock/tock/blob/master/README.md#L7-L17). |
| **kriuchkov/tock (time tracker)** | Already summarised; relevant if time‑tracking features are desired. |
| **originalankur/maptoposter** | Already summarised under image utilities. |

## Recommendations and integration ideas

1. **Dashboard & UI enhancements** – Integrate itshover icons for animated UI elements, Clusterize.js for smooth scrolling of large tables (species lists, simulation data), perspective for real‑time analytics dashboards, and packery to let users customise the layout of dashboards or apps. json‑render can be used with MYCA to dynamically generate widgets from natural‑language prompts.

2. **Simulation & visualisation** – Use sbox-public to develop interactive 3D simulation environments (e.g., mushroom growth or compound interactions). Adopt features from history (interactive globe) for Earth simulator or environment monitoring. maptoposter can generate map backgrounds for simulations and feed images into AI pattern detection pipelines.

3. **Backend & devops** – Employ xyOps for job scheduling, monitoring and incident response across Mycosoft’s services. Integrate disable-cloudflare-cli and port-killer into the devops toolkit for managing DNS proxies and local ports. Use nodemailer for sending emails and sharp to optimise images. TONL can compress large datasets, reducing token costs when sending data to AI.

4. **Terminal & developer productivity** – Provide terminal spreadsheet capabilities with vex-tui or GoSheet inside the Mycosoft shell for staff and customer use. Offer tock for time tracking and analysis of developer productivity. open-claude-cowork demonstrates how to build agent‑based chat applications integrated with many tools; it may serve as a template for MYCA’s coworking interface.

5. **Research ingestion** – Use zpdf for high‑performance PDF text extraction to ingest research papers into Mycosoft’s knowledge base (mindex) and convert them to Markdown for consumption by AI models. Combine with TONL and json‑render to feed the information into user‑facing dashboards and AI training pipelines.

These integrations will enhance Mycosoft’s website and applications, improve internal developer workflows, provide powerful data processing capabilities and help deliver a richer experience for end‑users.

---

[\[1\]](https://github.com/MycosoftLabs/website/blob/main/README.md#L9-L15) [\[2\]](https://github.com/MycosoftLabs/website/blob/main/README.md#L35-L56) [\[3\]](https://github.com/MycosoftLabs/website/blob/main/README.md#L71-L84) README.md

[https://github.com/MycosoftLabs/website/blob/main/README.md](https://github.com/MycosoftLabs/website/blob/main/README.md)

[\[4\]](https://github.com/vercel-labs/json-render#:~:text=Predictable) GitHub \- vercel-labs/json-render: AI → JSON → UI

[https://github.com/vercel-labs/json-render](https://github.com/vercel-labs/json-render)

[\[5\]](https://github.com/itshover/itshover/blob/main/README.md#L42-L51) [\[6\]](https://github.com/itshover/itshover/blob/main/README.md#L9-L13) README.md

[https://github.com/itshover/itshover/blob/main/README.md](https://github.com/itshover/itshover/blob/main/README.md)

[\[7\]](https://clusterize.js.org/#:~:text=) Clusterize.js

[https://clusterize.js.org/](https://clusterize.js.org/)

[\[8\]](https://github.com/perspective-dev/perspective/blob/master/README.md#L17-L34) [\[9\]](https://github.com/perspective-dev/perspective/blob/master/README.md#L35-L37) README.md

[https://github.com/perspective-dev/perspective/blob/master/README.md](https://github.com/perspective-dev/perspective/blob/master/README.md)

[\[10\]](https://packery.metafizzy.co/#:~:text=What%20is%20Packery%3F) Packery

[https://packery.metafizzy.co/](https://packery.metafizzy.co/)

[\[11\]](https://github.com/originalankur/maptoposter/blob/main/README.md#L89-L110) [\[12\]](https://github.com/originalankur/maptoposter/blob/main/README.md#L117-L137) README.md

[https://github.com/originalankur/maptoposter/blob/main/README.md](https://github.com/originalankur/maptoposter/blob/main/README.md)

[\[13\]](https://github.com/yorkeccak/history/blob/main/README.md#L19-L30) [\[14\]](https://github.com/yorkeccak/history/blob/main/README.md#L53-L68) README.md

[https://github.com/yorkeccak/history/blob/main/README.md](https://github.com/yorkeccak/history/blob/main/README.md)

[\[15\]](https://github.com/Facepunch/sbox-public#:~:text=s%26box) GitHub \- Facepunch/sbox-public: s\&box is a modern game engine, built on Valve's Source 2 and the latest .NET technology, it provides a modern intuitive editor for creating games

[https://github.com/Facepunch/sbox-public](https://github.com/Facepunch/sbox-public)

[\[16\]](https://github.com/pixlcore/xyops#:~:text=xyOps%E2%84%A2) [\[17\]](https://github.com/pixlcore/xyops#:~:text=Features%20at%20a%20Glance) GitHub \- pixlcore/xyops: A complete workflow automation and server monitoring system.

[https://github.com/pixlcore/xyops](https://github.com/pixlcore/xyops)

[\[18\]](https://github.com/midudev/disable-cloudflare-cli/blob/main/README.md#L5-L16) README.md

[https://github.com/midudev/disable-cloudflare-cli/blob/main/README.md](https://github.com/midudev/disable-cloudflare-cli/blob/main/README.md)

[\[19\]](https://github.com/productdevbook/port-killer/blob/master/README.md#L46-L56) [\[20\]](https://github.com/productdevbook/port-killer/blob/master/README.md#L57-L66) README.md

[https://github.com/productdevbook/port-killer/blob/master/README.md](https://github.com/productdevbook/port-killer/blob/master/README.md)

[\[21\]](https://github.com/kriuchkov/tock/blob/master/README.md#L12-L24) [\[22\]](https://github.com/kriuchkov/tock/blob/master/README.md#L453-L465) README.md

[https://github.com/kriuchkov/tock/blob/master/README.md](https://github.com/kriuchkov/tock/blob/master/README.md)

[\[23\]](https://github.com/tock/tock/blob/master/README.md#L7-L17) README.md

[https://github.com/tock/tock/blob/master/README.md](https://github.com/tock/tock/blob/master/README.md)

[\[24\]](https://github.com/itssamuelrowe/Zen/blob/main/README.md#L2-L10) README.md

[https://github.com/itssamuelrowe/Zen/blob/main/README.md](https://github.com/itssamuelrowe/Zen/blob/main/README.md)

[\[25\]](https://github.com/CodeOne45/vex-tui#:~:text=Vex%20) GitHub \- CodeOne45/vex-tui: A beautiful, fast, and feature-rich terminal-based Excel and CSV viewer & editor built with Go.

[https://github.com/CodeOne45/vex-tui](https://github.com/CodeOne45/vex-tui)

[\[26\]](https://github.com/drclcomputers/GoSheet/blob/main/README.md#L20-L33) [\[27\]](https://github.com/drclcomputers/GoSheet/blob/main/README.md#L36-L61) [\[28\]](https://github.com/drclcomputers/GoSheet/blob/main/README.md#L31-L32) README.md

[https://github.com/drclcomputers/GoSheet/blob/main/README.md](https://github.com/drclcomputers/GoSheet/blob/main/README.md)

[\[29\]](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md#L25-L42) [\[30\]](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md#L36-L49) [\[31\]](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md#L52-L60) README.md

[https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md](https://github.com/ComposioHQ/open-claude-cowork/blob/main/README.md)

[\[32\]](https://github.com/nodemailer/nodemailer/blob/master/README.md#L2-L15) README.md

[https://github.com/nodemailer/nodemailer/blob/master/README.md](https://github.com/nodemailer/nodemailer/blob/master/README.md)

[\[33\]](https://github.com/lovell/sharp/blob/main/README.md#L5-L21) README.md

[https://github.com/lovell/sharp/blob/main/README.md](https://github.com/lovell/sharp/blob/main/README.md)

[\[34\]](https://github.com/Lulzx/zpdf/blob/main/README.md#L5-L15) [\[35\]](https://github.com/Lulzx/zpdf/blob/main/README.md#L20-L25) README.md

[https://github.com/Lulzx/zpdf/blob/main/README.md](https://github.com/Lulzx/zpdf/blob/main/README.md)

[\[36\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L58-L68) [\[37\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L71-L101) [\[38\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L154-L206) [\[39\]](https://github.com/tonl-dev/tonl/blob/main/README.md#L326-L334) README.md

[https://github.com/tonl-dev/tonl/blob/main/README.md](https://github.com/tonl-dev/tonl/blob/main/README.md)