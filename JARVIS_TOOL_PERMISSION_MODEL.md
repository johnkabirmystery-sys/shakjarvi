# J.A.R.V.I.S. TOOL PERMISSION & VERIFICATION MODEL

**System**: J.A.R.V.I.S. Desktop AI Operating System  
**Principal User**: Sir Shakil Ahmed Chowdhury  
**Platform**: Windows 11, Python 3.14.7 64-bit  
**Security Level**: Executive Hardened Workstation Protocol  

---

## 1. Tool Classification Framework

To protect Sir Shakil's personal files, business accounts, and workstation security, all tools in J.A.R.V.I.S. are classified into three strict permission tiers:

```
┌───────────────────────────────────────────────────────────┐
│                    TOOL PERMISSION TIERS                  │
├───────────────────────────────────────────────────────────┤
│ [TIER 1: READ_ONLY]                                       │
│ • Zero state changes to disk or accounts                  │
│ • Executed autonomously upon intent classification        │
│ • Examples: Telemetry, status checks, web research, audio │
├───────────────────────────────────────────────────────────┤
│ [TIER 2: LOW_RISK_WRITE]                                  │
│ • Creates non-destructive local drafts and files          │
│ • Executed with mandatory outcome verification            │
│ • Examples: Saving code to Desktop, drafting email reply  │
├───────────────────────────────────────────────────────────┤
│ [TIER 3: HIGH_RISK (NEEDS_APPROVAL)]                      │
│ • External communications, file deletions, finance        │
│ • MANDATORY EXPLICIT USER CONFIRMATION REQUIRED           │
│ • Pauses in NEEDS_APPROVAL state until Sir Shakil confirms│
│ • Examples: Sending email/SMS, deleting files, purchasing │
└───────────────────────────────────────────────────────────┘
```

---

## 2. Tool Permission Matrix

| Tool / Action | Permission Tier | Verification Method | Rollback / Cancellation Behavior |
| :--- | :--- | :--- | :--- |
| `get_telemetry_data` | `READ_ONLY` | psutil object valid | Instant return |
| `get_evolution_stats` | `READ_ONLY` | SQLite row query | Instant return |
| `search_knowledge_vault` | `READ_ONLY` | FTS5 BM25 match count | Zero disk impact |
| `browse_url_and_extract` | `READ_ONLY` | HTTP 200 + HTML body $>0$ | Tab closed cleanly |
| `take_screenshot` | `READ_ONLY` | PIL image size $>0$ | Base64 buffered in RAM |
| `set_volume` | `LOW_RISK_WRITE` | pycaw master volume verified | Reversible |
| `launch_app` | `LOW_RISK_WRITE` | Process spawned | Process killable |
| `save_code_to_desktop` | `LOW_RISK_WRITE` | `os.path.exists` + size check | File overwrites prevented |
| `save_fact` | `LOW_RISK_WRITE` | SQLite `lastrowid` verified | Purgeable by key |
| `stage_email_reply` | `LOW_RISK_WRITE` | Staged draft in memory | No email sent |
| **`execute_confirmed_send`** | **`HIGH_RISK`** | **Requires Sir Shakil's explicit approval** | **Irreversible once sent** |
| **`delete_file`** | **`HIGH_RISK`** | **Requires Sir Shakil's explicit approval** | **Destructive** |
| **`publish_ad_campaign`** | **`HIGH_RISK`** | **Requires Sir Shakil's explicit approval** | **Financial spend risk** |
| **`lock_workstation`** | `LOW_RISK_WRITE` | `user32.LockWorkStation()` | Reversible via Windows PIN |

---

## 3. Strict Verification & Anti-False-Claim Policy

1. **No Phantom Completions**: An action is never reported as "completed", "executed", or "done" merely because a subprocess was invoked or an asynchronous call was scheduled.
2. **Evidence Attachment**:
   * File creation tools must return absolute file paths and byte size.
   * Process launch tools must return process names and success codes.
   * RAG memory tools must return record IDs and timestamps.
3. **Failure Transparency**: If a network request, tool execution, or model call fails, J.A.R.V.I.S. explicitly reports the failure, cause, and fallback remedy instead of producing a polite simulation.
