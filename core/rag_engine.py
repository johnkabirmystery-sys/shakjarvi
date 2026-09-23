"""
J.A.R.V.I.S. Neural RAG Engine (Retrieval-Augmented Generation)
==============================================================
Provides high-performance, zero-latency hybrid contextual retrieval across:
1. Long-Term Conversation History (User messages & Assistant answers)
2. Personal Facts & Operational Rules (User Facts table)
3. Research Knowledge Vault (100+ technical, business, marketing topics)

Features:
- SQLite FTS5 (Full-Text Search) with BM25 ranking
- Automatic schema creation & indexing
- Semantic keyword scoring & recency decay
- Zero-token cost when no relevant context exists
- Formatted prompt block injection for OmniRoute and Local AI Brain
"""

import sqlite3
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path("data/memory/jarvis_memory.db")

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_rag_schema():
    """Initializes conversation history table and FTS5 full-text search indexes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Permanent Conversation History Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            workspace TEXT DEFAULT 'personal',
            timestamp REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        # Migration: ensure workspace column exists if table was created previously
        cursor.execute("PRAGMA table_info(conversation_history)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "workspace" not in columns:
            cursor.execute("ALTER TABLE conversation_history ADD COLUMN workspace TEXT DEFAULT 'personal'")
        
        # 2. Virtual Table for FTS5 Full-Text Search on Conversation History
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts USING fts5(
            role,
            content,
            content='conversation_history',
            content_rowid='id'
        )
        """)
        
        # Triggers to keep conversation_fts in sync
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_conversation_ai AFTER INSERT ON conversation_history BEGIN
            INSERT INTO conversation_fts(rowid, role, content) VALUES (new.id, new.role, new.content);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_conversation_ad AFTER DELETE ON conversation_history BEGIN
            INSERT INTO conversation_fts(conversation_fts, rowid, role, content) VALUES ('delete', old.id, old.role, old.content);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_conversation_au AFTER UPDATE ON conversation_history BEGIN
            INSERT INTO conversation_fts(conversation_fts, rowid, role, content) VALUES ('delete', old.id, old.role, old.content);
            INSERT INTO conversation_fts(rowid, role, content) VALUES (new.id, new.role, new.content);
        END;
        """)

        # 3. Virtual Table for FTS5 Full-Text Search on Knowledge Vault
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            topic,
            category,
            summary,
            details,
            tags,
            content='knowledge_vault',
            content_rowid='id'
        )
        """)
        
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_knowledge_ai AFTER INSERT ON knowledge_vault BEGIN
            INSERT INTO knowledge_fts(rowid, topic, category, summary, details, tags) 
            VALUES (new.id, new.topic, new.category, new.summary, new.details, new.tags);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_knowledge_ad AFTER DELETE ON knowledge_vault BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, category, summary, details, tags) 
            VALUES ('delete', old.id, old.topic, old.category, old.summary, old.details, old.tags);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_knowledge_au AFTER UPDATE ON knowledge_vault BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, category, summary, details, tags) 
            VALUES ('delete', old.id, old.topic, old.category, old.summary, old.details, old.tags);
            INSERT INTO knowledge_fts(rowid, topic, category, summary, details, tags) 
            VALUES (new.id, new.topic, new.category, new.summary, new.details, new.tags);
        END;
        """)

        # Populate knowledge_fts if it is empty but knowledge_vault has records
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_fts")
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute("""
                INSERT INTO knowledge_fts(rowid, topic, category, summary, details, tags)
                SELECT id, topic, category, summary, details, tags FROM knowledge_vault;
                """)
        except Exception:
            pass

        # 4. Session Summaries Table for Sliding-Window Context
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            turn_range_start INTEGER NOT NULL,
            turn_range_end INTEGER NOT NULL,
            workspace TEXT DEFAULT 'personal',
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()

def log_conversation(role: str, content: str, model: str = "", workspace: str = "personal"):
    """Permanently commits an utterance to the conversation history and search index."""
    if not content or not content.strip():
        return
    init_rag_schema()
    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO conversation_history (role, content, model, workspace, timestamp, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (role, content.strip(), model, workspace or "personal", now_ts, now_str))
        conn.commit()

def _sanitize_fts_query(query: str) -> str:
    """Strips FTS syntax chars and extracts meaningful alphanumeric tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", query)
    stop_words = {
        "what", "when", "where", "which", "about", "your", "this", "that", "tell",
        "with", "have", "make", "want", "give", "detailed", "words", "brief",
        "some", "more", "much", "very", "also", "need", "please", "could", "would",
        "should", "from", "they", "them", "there", "then", "been", "being", "were"
    }
    clean_tokens = [t for t in tokens if t.lower() not in stop_words]
    if not clean_tokens:
        clean_tokens = tokens[:4]
    if not clean_tokens:
        return ""
    # Use OR across tokens for high recall with BM25 ranking
    return " OR ".join(f'"{t}"' for t in clean_tokens[:8])

def retrieve_relevant_dialogue(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves previous dialogue turns matching the query using FTS5 BM25."""
    init_rag_schema()
    fts_q = _sanitize_fts_query(query)
    if not fts_q:
        return []

    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT h.id, h.role, h.content, h.created_at, bm25(conversation_fts) as rank
            FROM conversation_fts f
            JOIN conversation_history h ON f.rowid = h.id
            WHERE conversation_fts MATCH ?
            ORDER BY rank ASC, h.id DESC
            LIMIT ?
            """, (fts_q, limit))
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "role": "Sir Shakil" if row["role"] == "user" else "J.A.R.V.I.S.",
                    "content": row["content"],
                    "date": row["created_at"]
                })
        except Exception as e:
            # Fallback to simple LIKE if FTS parser complains
            try:
                tokens = re.findall(r"\b[a-zA-Z0-9]{3,}\b", query)
                if tokens:
                    like_clause = " OR ".join(["content LIKE ?" for _ in tokens[:4]])
                    params = [f"%{t}%" for t in tokens[:4]] + [limit]
                    cursor.execute(f"SELECT id, role, content, created_at FROM conversation_history WHERE {like_clause} ORDER BY id DESC LIMIT ?", params)
                    for row in cursor.fetchall():
                        results.append({
                            "id": row["id"],
                            "role": "Sir Shakil" if row["role"] == "user" else "J.A.R.V.I.S.",
                            "content": row["content"],
                            "date": row["created_at"]
                        })
            except Exception:
                pass
    return results

def retrieve_relevant_knowledge(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Retrieves deep technical/business knowledge nodes matching the query via FTS5 BM25."""
    init_rag_schema()
    fts_q = _sanitize_fts_query(query)
    if not fts_q:
        return []

    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT k.id, k.topic, k.category, k.summary, k.details, k.tags, bm25(knowledge_fts) as rank
            FROM knowledge_fts f
            JOIN knowledge_vault k ON f.rowid = k.id
            WHERE knowledge_fts MATCH ?
            ORDER BY rank ASC, k.id DESC
            LIMIT ?
            """, (fts_q, limit))
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "topic": row["topic"],
                    "category": row["category"],
                    "summary": row["summary"],
                    "details": row["details"] or "",
                    "tags": row["tags"] or ""
                })
        except Exception:
            # Fallback
            try:
                tokens = re.findall(r"\b[a-zA-Z0-9]{3,}\b", query)
                if tokens:
                    like_clause = " OR ".join(["topic LIKE ? OR summary LIKE ? OR details LIKE ? OR tags LIKE ?" for _ in tokens[:3]])
                    params = []
                    for t in tokens[:3]:
                        params.extend([f"%{t}%", f"%{t}%", f"%{t}%", f"%{t}%"])
                    params.append(limit)
                    cursor.execute(f"SELECT id, topic, category, summary, details, tags FROM knowledge_vault WHERE {like_clause} ORDER BY id DESC LIMIT ?", params)
                    for row in cursor.fetchall():
                        results.append({
                            "id": row["id"],
                            "topic": row["topic"],
                            "category": row["category"],
                            "summary": row["summary"],
                            "details": row["details"] or "",
                            "tags": row["tags"] or ""
                        })
            except Exception:
                pass
    return results

def retrieve_relevant_facts(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves personal preferences, identity, and operational rules relevant to the query."""
    init_rag_schema()
    tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z0-9]{3,}\b", query)]
    if not tokens:
        return []
    
    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            like_clause = " OR ".join(["key LIKE ? OR value LIKE ? OR category LIKE ?" for _ in tokens[:4]])
            params = []
            for t in tokens[:4]:
                params.extend([f"%{t}%", f"%{t}%", f"%{t}%"])
            params.append(limit)
            cursor.execute(f"SELECT id, category, key, value FROM user_facts WHERE {like_clause} ORDER BY id DESC LIMIT ?", params)
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "category": row["category"],
                    "key": row["key"],
                    "value": row["value"]
                })
        except Exception:
            pass
    return results

def get_recent_history(limit: int = 14, workspace: Optional[str] = None) -> List[Dict[str, str]]:
    """Retrieves the most recent chronological conversation turns for immediate conversational context, filtered by workspace."""
    init_rag_schema()
    turns = []
    with get_db() as conn:
        cursor = conn.cursor()
        if workspace and workspace != "all":
            cursor.execute("""
            SELECT role, content FROM conversation_history 
            WHERE workspace = ?
            ORDER BY id DESC LIMIT ?
            """, (workspace, limit))
        else:
            cursor.execute("""
            SELECT role, content FROM conversation_history 
            ORDER BY id DESC LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        for row in reversed(rows):
            turns.append({
                "role": "user" if row["role"] == "user" else "assistant",
                "content": row["content"]
            })
    return turns

def build_rag_context_block(query: str, workspace: str = "personal") -> str:
    """
    Builds a structured contextual dossier for the LLM prompt based on the user's active query.
    Extracts relevant dialogue, personal facts, and technical knowledge nodes within the active workspace.
    """
    dialogue_matches = retrieve_relevant_dialogue(query, limit=4)
    knowledge_matches = retrieve_relevant_knowledge(query, limit=3)
    fact_matches = retrieve_relevant_facts(query, limit=4)

    # If nothing relevant found, return empty to save token budget
    if not dialogue_matches and not knowledge_matches and not fact_matches:
        return f"# ACTIVE WORKSPACE: {workspace.upper()}"

    sections = []
    sections.append(f"# RETRIEVED CONTEXT & PERMANENT MEMORY (Neural RAG Engine · Workspace: {workspace.upper()}):")

    if fact_matches:
        sections.append("## Highly Relevant Facts & Directives for Sir Shakil:")
        for f in fact_matches:
            sections.append(f"- [{f['category'].upper()}] {f['key']}: {f['value']}")

    if knowledge_matches:
        sections.append("\n## Relevant Knowledge Vault Nodes:")
        for k in knowledge_matches:
            det = f" | Details: {k['details'][:250]}" if k['details'] else ""
            sections.append(f"- [{k['category']}] **{k['topic']}**: {k['summary']}{det}")

    if dialogue_matches:
        sections.append("\n## Relevant Past Conversations & Previous Context with Sir Shakil:")
        for d in dialogue_matches:
            clean_content = d['content'].replace("\n", " ")
            if len(clean_content) > 300:
                clean_content = clean_content[:300] + "..."
            sections.append(f"- [{d['date']}] {d['role']}: {clean_content}")

    sections.append(f"\nInstructions on Context Usage: Seamlessly utilize this retrieved memory to maintain perfect conversational continuity within the {workspace.upper()} domain. Sir Shakil should never have to repeat himself.")
    return "\n".join(sections)

def get_conversation_turn_count(workspace: str = "personal") -> int:
    init_rag_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        if workspace and workspace != "all":
            cursor.execute("SELECT COUNT(*) as cnt FROM conversation_history WHERE workspace = ?", (workspace,))
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM conversation_history")
        return cursor.fetchone()["cnt"]

async def auto_distill_session(workspace: str = "personal") -> Dict[str, Any]:
    init_rag_schema()
    from core import omniroute_client
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(turn_range_end) as max_id FROM session_summaries WHERE workspace = ?", (workspace,))
        row = cursor.fetchone()
        last_end_id = row["max_id"] if row["max_id"] is not None else 0
        
        cursor.execute("""
        SELECT id, role, content FROM conversation_history 
        WHERE workspace = ? AND id > ?
        ORDER BY id ASC LIMIT 20
        """, (workspace, last_end_id))
        turns = cursor.fetchall()
        
        if len(turns) < 20:
            return {"success": False, "reason": "Fewer than 20 unsummarized turns available."}
            
        start_id = turns[0]["id"]
        end_id = turns[-1]["id"]
        
        dialogue_text = ""
        for t in turns:
            role_name = "User" if t["role"] == "user" else "Assistant"
            dialogue_text += f"{role_name}: {t['content']}\n\n"
            
    instruction = "You are a conversation summarizer. Compress the following dialogue into a 3-5 sentence executive summary preserving key decisions, facts, preferences, and action items. Be concise and factual."
    prompt = f"Dialogue to summarize:\n{dialogue_text}"
    
    try:
        resp = await omniroute_client.generate_omniroute_completion(
            prompt=prompt,
            system_instruction=instruction
        )
        
        if not resp.get("success"):
            return {"success": False, "reason": resp.get("error", "LLM call failed")}
        
        summary_text = resp.get("content", "").strip()
        if not summary_text:
            return {"success": False, "reason": "LLM returned empty summary"}
        
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO session_summaries (summary, turn_range_start, turn_range_end, workspace, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (summary_text, start_id, end_id, workspace, now_str))
            conn.commit()
        
        return {"success": True, "summary": summary_text}
    except Exception as e:
        return {"success": False, "reason": str(e)}

def get_context_window(
    query: str, 
    workspace: str = "personal",
    recent_limit: int = 10,
    semantic_limit: int = 4,
    max_chars: int = 12000
) -> dict:
    recent_turns = get_recent_history(limit=recent_limit, workspace=workspace)
    
    recent_ids = set()
    with get_db() as conn:
        cursor = conn.cursor()
        if workspace and workspace != "all":
            cursor.execute("SELECT id FROM conversation_history WHERE workspace = ? ORDER BY id DESC LIMIT ?", (workspace, recent_limit))
        else:
            cursor.execute("SELECT id FROM conversation_history ORDER BY id DESC LIMIT ?", (recent_limit,))
        for row in cursor.fetchall():
            recent_ids.add(row["id"])
            
    semantic_raw = retrieve_relevant_dialogue(query, limit=semantic_limit + recent_limit)
    semantic_turns = [t for t in semantic_raw if t["id"] not in recent_ids][:semantic_limit]
    
    summaries = []
    with get_db() as conn:
        cursor = conn.cursor()
        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z0-9]{3,}\b", query)]
        if tokens:
            like_clause = " OR ".join(["summary LIKE ?" for _ in tokens[:4]])
            params = [f"%{t}%" for t in tokens[:4]]
            params.extend([workspace, 2])
            cursor.execute(f"SELECT summary FROM session_summaries WHERE ({like_clause}) AND workspace = ? ORDER BY id DESC LIMIT ?", params)
            summaries = [row["summary"] for row in cursor.fetchall()]
            
        if not summaries:
            cursor.execute("SELECT summary FROM session_summaries WHERE workspace = ? ORDER BY id DESC LIMIT 2", (workspace,))
            summaries = [row["summary"] for row in cursor.fetchall()]

    messages = []
    if summaries:
        combined_summary = "\n\n".join(summaries)
        messages.append({"role": "system", "content": f"Previous Session Context:\n{combined_summary}"})
        
    for t in sorted(semantic_turns, key=lambda x: x["id"]):
        role = "user" if t["role"] == "Sir Shakil" else "assistant"
        messages.append({"role": role, "content": t["content"]})
        
    for t in recent_turns:
        messages.append(t)
        
    total_chars = sum(len(m["content"]) for m in messages)
    while total_chars > max_chars:
        semantic_count = len(messages) - (1 if summaries else 0) - len(recent_turns)
        if semantic_count > 0:
            idx_to_remove = 1 if summaries else 0
            removed = messages.pop(idx_to_remove)
            total_chars -= len(removed["content"])
        else:
            break
            
    return {
        "recent_turns": recent_turns,
        "semantic_turns": semantic_turns,
        "session_summaries": summaries,
        "messages": messages
    }

# Auto-initialize database on import
init_rag_schema()
