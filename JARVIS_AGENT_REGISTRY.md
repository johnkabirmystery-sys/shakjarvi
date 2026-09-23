# J.A.R.V.I.S. SPECIALIST AGENT REGISTRY & ON-DEMAND ARCHITECTURE

**System**: J.A.R.V.I.S. Desktop AI Operating System  
**Principal User**: Sir Shakil Ahmed Chowdhury  
**Platform**: Windows 11, Python 3.14.7 64-bit  
**Status**: On-Demand Modular Architecture  

---

## 1. On-Demand vs. Always-Active Architecture

To preserve system memory, CPU cycles, and network bandwidth on Sir Shakil's workstation, J.A.R.V.I.S. **does not** run 9 background agents concurrently. 

Instead, specialist agents are structured as **lightweight on-demand modules** that:
1. Load into execution memory only when their specific intent is triggered.
2. Share a single unified resource guard, model client (`omniroute_client`), and logging pipeline.
3. Terminate immediately upon task verification and return structured results to the orchestrator.

---

## 2. Specialist Agent Catalog

```
                    ┌────────────────────────┐
                    │  Master Orchestrator   │
                    └───────────┬────────────┘
                                │ (On-Demand Dispatch)
         ┌───────────────┬──────┴────────┬───────────────┐
         ▼               ▼               ▼               ▼
┌────────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│ Research Agent ││ Coding Agent ││   QA Agent   ││Marketing Agt │
└────────────────┘└──────────────┘└──────────────┘└──────────────┘
         ▼               ▼               ▼               ▼
┌────────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│   SEO Agent    ││Lead Gen Agent││WordPress Agt ││Business Anal.│
└────────────────┘└──────────────┘└──────────────┘└──────────────┘
                                 ▼
                         ┌──────────────┐
                         │ System Agent │
                         └──────────────┘
```

### 1. Research Agent (`specialist: research_agent`)
* **Role**: Autonomous deep online information synthesis and competitive intelligence.
* **Capabilities**: Live web search queries, Chrome browser page text extraction, topic summarization, fact validation.
* **Tools Used**: `browser_controller.browse_url_and_extract`, `research_engine.conduct_deep_research`.
* **Output**: Executive Briefing, Source URLs, Key Findings, Knowledge Vault Node.

### 2. Coding Agent (`specialist: coding_agent`)
* **Role**: Software engineering, script authoring, refactoring, and backend API development.
* **Capabilities**: Python, FastAPI, JavaScript, HTML/CSS generation, syntax validation.
* **Output Delivery Protocol**: Full code formatted in markdown code blocks; auto-compiled and saved to `C:\Users\Qbits\Desktop\Jarvis_Created_Files` for Sir Shakil's review without reciting code syntax over voice.

### 3. QA Agent (`specialist: qa_agent`)
* **Role**: Bug auditing, regression testing, and code quality verification.
* **Capabilities**: Running unit tests (`pytest`, `unittest`, custom diagnostics), verifying HTTP endpoints, auditing WebSocket telemetry frames.
* **Output**: Pass/Fail metrics, stack trace isolation, regression impact report.

### 4. Marketing Agent (`specialist: marketing_agent`)
* **Role**: High-ticket client acquisition, funnel architecture, and multi-channel copywriting.
* **Capabilities**: Alex Hormozi $100M Grand Slam Offers, 12-step Video Sales Letters (VSL), 5-part email nurture funnels, high-urgency SMS blasts, Meta 3:2:2 DCT ads, Google PMax copy.
* **Tools Used**: `core/marketing_engine.py`.

### 5. SEO Agent (`specialist: seo_agent`)
* **Role**: Organic visibility, search intent mapping, and Eventbrite ranking.
* **Capabilities**: Eventbrite title/description SEO optimization, keyword density calculation, schema markup guidance, metadata tag generation.

### 6. Lead Generation Agent (`specialist: leadgen_agent`)
* **Role**: B2B client prospect discovery and qualification.
* **Capabilities**: Agency prospect discovery, email format verification, outreach targeting criteria (MEDDIC/BANT).
* **Permission Gate**: Read-only research permitted; **transmitting cold emails or messages requires explicit approval**.

### 7. WordPress Agent (`specialist: wordpress_agent`)
* **Role**: Website auditing, performance tuning, and CMS implementation.
* **Capabilities**: Core Web Vitals assessment, plugin conflict diagnosis, REST API endpoint integration, theme PHP/CSS inspection.

### 8. Business Analyst (`specialist: business_analyst`)
* **Role**: Financial modeling, monetization blueprints, and operational scenario planning.
* **Capabilities**: LTV/CAC ratio calculation, ticket tier pricing models, monthly retainer economics, micro-SaaS pricing cascades.

### 9. System Agent (`specialist: system_agent`)
* **Role**: Workstation health, background services, and Jarvis diagnostics.
* **Capabilities**: Real-time per-core CPU load, RAM allocation, process termination, network bandwidth, audio device inspection.
* **Tools Used**: `core/telemetry.py`, `core/pc_controller.py`.

---

## 3. Resource & Concurrency Guard Rules

1. **Max Active Concurrency**: At any moment, at most **2 subtasks** can execute concurrently across all specialists.
2. **Zero Redundant Infrastructure**: Specialist agents do not spin up their own WebSocket servers, database connections, or API clients. All agents execute through `MasterOrchestrator.execute_task()`.
3. **Execution Timeouts**: Every specialist task enforces a strict timeout (maximum 60 seconds) to prevent frozen network calls or hung subprocesses.
