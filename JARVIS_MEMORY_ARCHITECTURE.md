# J.A.R.V.I.S. ADVANCED MEMORY & WORKSPACE ARCHITECTURE

**System**: J.A.R.V.I.S. Desktop AI Operating System  
**Principal User**: Sir Shakil Ahmed Chowdhury  
**Storage**: SQLite 3 with FTS5 Full-Text Search & BM25 Scoring (`data/memory/jarvis_memory.db`)  
**Architecture**: 6-Tier Isolated Memory Subsystem  

---

## 1. The 6 Memory Layers

To eliminate context poisoning (such as past Canadian Dental project notes leaking into new coding or marketing queries), memory is decoupled into six distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Short-Term Conversation Context                          │
│    • Current session buffer (last 8-12 turns max)           │
│    • Filtered dynamically by relevance to latest query      │
├─────────────────────────────────────────────────────────────┤
│ 2. User Facts & Preferences (`user_facts`)                 │
│    • Explicitly approved directives ("remember that...")    │
│    • Key-value schema with category and update timestamps   │
├─────────────────────────────────────────────────────────────┤
│ 3. Workspace & Project Memory                               │
│    • Project-specific objectives, stack notes, client data  │
│    • Strictly partitioned by active workspace               │
├─────────────────────────────────────────────────────────────┤
│ 4. Orchestrator Task History (`task_history`)               │
│    • Bounded record of recent tasks, steps, runtimes, status│
│    • Capped at 50 records to prevent memory footprint growth│
├─────────────────────────────────────────────────────────────┤
│ 5. Knowledge Vault (`knowledge_vault`)                     │
│    • Curated domain nodes (marketing, engineering, APIs)    │
│    • SQLite FTS5 BM25 semantic scoring                      │
├─────────────────────────────────────────────────────────────┤
│ 6. Execution Evidence & Audit Log                           │
│    • Concrete proof of file writes, network calls, actions  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Workspace Context Isolation

J.A.R.V.I.S. partitions memory into six explicit workspaces:

1. **General Personal Assistant**: Daily executive scheduling, email reviews, PC automation, personal reminders.
2. **Ghiringhelli Marketing**: Core business funnels, Hormozi $100M offers, Eventbrite ticket sales, Meta/Google ad copy.
3. **Client Marketing Projects**: Dedicated client accounts, lead generation, cold outreach sequences.
4. **SaaS & Software Development**: Python backends, FastAPI architectures, Antigravity SDK agents, web scrapers.
5. **Research & Learning**: Curated knowledge vault, academic papers, AI model benchmarks.
6. **System Engineering**: Windows 11 hardware calibration, audio latency tuning, process telemetry.

### Workspace Switching Protocol:
* When Sir Shakil says *"Switch workspace to SaaS Development"* or selects it on the HUD, active memory isolation engages.
* Inquiries in the `SaaS Development` workspace will **never** pull irrelevant marketing copy or old dental clinic documents into the prompt context.

---

## 3. User Memory Commands

| Voice / Text Directive | System Action | Feedback Delivered |
| :--- | :--- | :--- |
| `Remember that my primary email is ...` | Saves key-value fact into `user_facts` | *"Fact recorded, Sir Shakil. Committed to long-term memory vault."* |
| `What have you remembered about me?` | Queries `user_facts` table | Lists top 6 verified facts |
| `Purge memory regarding [topic]` | Deletes matching records | Confirms record count deleted |
| `Status of knowledge vault` | Queries `evolution_stats` | Reports knowledge nodes and evolution level |
