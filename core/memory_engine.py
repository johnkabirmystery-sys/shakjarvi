import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/memory/jarvis_memory.db")

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. User Facts & Preferences
        # 1. User Facts & Preferences
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            workspace TEXT DEFAULT 'personal',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        cursor.execute("PRAGMA table_info(user_facts)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "workspace" not in cols:
            cursor.execute("ALTER TABLE user_facts ADD COLUMN workspace TEXT DEFAULT 'personal'")

        # 2. Researched Knowledge Vault
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            category TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_url TEXT,
            summary TEXT NOT NULL,
            details TEXT,
            tags TEXT,
            workspace TEXT DEFAULT 'general',
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("PRAGMA table_info(knowledge_vault)")
        k_cols = [r["name"] for r in cursor.fetchall()]
        if "workspace" not in k_cols:
            cursor.execute("ALTER TABLE knowledge_vault ADD COLUMN workspace TEXT DEFAULT 'general'")

        # 3. Evolution Metrics & Stats
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolution_stats (
            id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            knowledge_nodes INTEGER DEFAULT 0,
            research_cycles INTEGER DEFAULT 0,
            days_active INTEGER DEFAULT 1,
            first_boot_time TEXT,
            last_research_time TEXT
        )
        """)

        # Initialize evolution stats row if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM evolution_stats")
        if cursor.fetchone()["cnt"] == 0:
            now_iso = datetime.now().isoformat()
            cursor.execute("""
            INSERT INTO evolution_stats (id, level, knowledge_nodes, research_cycles, days_active, first_boot_time, last_research_time)
            VALUES (1, 1, 0, 0, 1, ?, ?)
            """, (now_iso, now_iso))

        # Seed initial core facts if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM user_facts")
        if cursor.fetchone()["cnt"] == 0:
            now = datetime.now().isoformat()
            initial_facts = [
                ("identity", "Creator & Master", "Sir Shakil", now, now),
                ("protocol", "Prime Directive", "Devoted exclusively to fulfilling Sir Shakil's goals and instructions", now, now),
                ("environment", "Host Machine", "Windows 11 Pro 64-bit Workstation", now, now),
                ("preferences", "Interface Style", "Futuristic Stark Industries Arc Reactor HUD", now, now)
            ]
            cursor.executemany("""
            INSERT INTO user_facts (category, key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, initial_facts)

        # Seed initial knowledge nodes if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_vault")
        if cursor.fetchone()["cnt"] == 0:
            now = datetime.now().isoformat()
            seed_knowledge = [
                (
                    "Autonomous Windows Control",
                    "Windows Automation",
                    "system",
                    "local",
                    "Direct control of Windows processes, master audio endpoint volume via Pycaw, and UI screenshot captures.",
                    "Allows J.A.R.V.I.S. to operate Windows seamlessly without user intervention.",
                    "windows, automation, pycaw",
                    now
                ),
                (
                    "High-Frequency Telemetry",
                    "System Diagnostics",
                    "system",
                    "local",
                    "Real-time 2Hz metrics gathering for 16 CPU cores, RAM consumption, and network I/O speeds.",
                    "Provides telemetry data feeding the Arc Reactor HUD dials.",
                    "telemetry, diagnostics, psutil",
                    now
                ),
                (
                    "Neural Voice Synthesis Architecture",
                    "Speech AI",
                    "research",
                    "edge-tts",
                    "Microsoft Neural Voice (en-GB-RyanNeural) cached via MD5 hash lookups for zero-latency playback.",
                    "Gives J.A.R.V.I.S. his signature Paul Bettany British cadence.",
                    "tts, voice, edge-tts, audio",
                    now
                )
            ]
            cursor.executemany("""
            INSERT INTO knowledge_vault (topic, category, source_type, source_url, summary, details, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, seed_knowledge)

        # Seed Wealth & Tech Monetization Nodes if not present
        wealth_seeds = [
            (
                "AI Automation Agency (AAA) Monetization Blueprint",
                "Wealth Strategy",
                "core_strategy",
                "strategic_vault",
                "Build and deploy custom multi-agent automation systems, AI customer service bots, and CRM scraping workflows for businesses on $2,500 - $8,000/mo retainers.",
                "1. Target high-margin niches: real estate, law firms, dental clinics, e-commerce. 2. Implement automated lead intake, booking, and database enrichment. 3. Zero marginal cost once pipeline is deployed.",
                "monetization, wealth, ai agency, b2b, retainers"
            ),
            (
                "Micro-SaaS & Developer API Recurring Revenue Engine",
                "Tech Monetization",
                "core_strategy",
                "strategic_vault",
                "Develop targeted, single-purpose SaaS or API tools (e.g. data scrapers, format converters, AI summarizers) monetized via Stripe subscriptions.",
                "1. Identify underserved developer / marketer pain points. 2. Build MVP using FastAPI + React. 3. Implement programmatic SEO to drive organic Google search traffic at $0 customer acquisition cost.",
                "saas, recurring revenue, stripe, micro-saas, tech"
            ),
            (
                "Viral Tech Marketing & High-Converting Direct Response Funnels",
                "Growth Marketing",
                "core_strategy",
                "strategic_vault",
                "Leverage value-first algorithmic distribution on X/Twitter, LinkedIn, and YouTube, combined with cold email outreach funnels to convert attention into paying clients.",
                "1. Use 'Hook -> Proof -> Insight -> Action' copywriting framework. 2. Offer high-value free lead magnets (code templates, cheat sheets). 3. Drive traffic to a frictionless one-click checkout or booking call.",
                "marketing, viral, copywriting, funnels, sales"
            ),
            (
                "Digital Product & Tech Asset Arbitrage",
                "Revenue Generation",
                "core_strategy",
                "strategic_vault",
                "Package boilerplate code, automation scripts, scrapers, and prompt engineering libraries into digital products sold on Gumroad, ProductHunt, and GitHub Sponsors.",
                "1. Build once, sell infinitely with 95%+ profit margins. 2. Create interactive demos. 3. Partner with tech creators for 30% affiliate revenue share.",
                "digital products, passive income, arbitrage, gumroad"
            )
        ]

        now = datetime.now().isoformat()
        for t, c, s_type, s_url, summ, det, tg in wealth_seeds:
            cursor.execute("SELECT id FROM knowledge_vault WHERE topic = ?", (t,))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO knowledge_vault (topic, category, source_type, source_url, summary, details, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (t, c, s_type, s_url, summ, det, tg, now))

        # Ensure Prime Wealth Directive is in user_facts
        cursor.execute("SELECT id FROM user_facts WHERE key = 'Wealth & Strategic Objective'")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO user_facts (category, key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, ("strategy", "Wealth & Strategic Objective", "Execute high-ROI digital monetization, SaaS development, automated marketing funnels, and technical product assets to earn money for Sir Shakil.", now, now))

        # Recount knowledge nodes
        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_vault")
        k_count = cursor.fetchone()["cnt"]
        cursor.execute("UPDATE evolution_stats SET knowledge_nodes = ?, level = ? WHERE id = 1", (k_count, max(1, k_count // 2)))

        conn.commit()

# --- User Facts CRUD ---
def save_fact(category: str, key: str, value: str, workspace: str = "personal") -> dict:
    init_db()
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_facts (category, key, value, workspace, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            category = excluded.category,
            value = excluded.value,
            workspace = excluded.workspace,
            updated_at = excluded.updated_at
        """, (category.strip(), key.strip(), value.strip(), workspace or "personal", now, now))
        conn.commit()
    return {"success": True, "message": f"Fact '{key}' committed to long-term memory, Sir Shakil."}

def delete_fact(fact_id: int) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_facts WHERE id = ?", (fact_id,))
        conn.commit()
    return {"success": True, "message": "Fact purged from memory."}

def get_all_facts(workspace: Optional[str] = None) -> list:
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        if workspace and workspace != "all":
            cursor.execute("""
            SELECT id, category, key, value, workspace, updated_at 
            FROM user_facts 
            WHERE workspace = ? OR (workspace IN ('general', 'personal') AND category IN ('identity', 'protocol', 'preference'))
            ORDER BY category, key
            """, (workspace,))
        else:
            cursor.execute("SELECT id, category, key, value, workspace, updated_at FROM user_facts ORDER BY category, key")
        return [dict(row) for row in cursor.fetchall()]

def get_facts_for_prompt(workspace: Optional[str] = None) -> str:
    facts = get_all_facts(workspace=workspace)
    if not facts:
        return "No specific personal facts recorded yet."
    lines = []
    for f in facts:
        lines.append(f"- [{f['category'].upper()}] {f['key']}: {f['value']}")
    return "\n".join(lines)

# --- Knowledge Vault CRUD ---
def save_knowledge_node(topic: str, category: str, source_type: str, source_url: str, summary: str, details: str = "", tags: str = "") -> dict:
    init_db()
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO knowledge_vault (topic, category, source_type, source_url, summary, details, tags, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (topic.strip(), category.strip(), source_type.strip(), source_url.strip() if source_url else "", summary.strip(), details.strip(), tags.strip(), now))
        node_id = cursor.lastrowid
        
        # Update evolution count & level
        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_vault")
        cnt = cursor.fetchone()["cnt"]
        new_level = max(1, cnt // 2)
        cursor.execute("UPDATE evolution_stats SET knowledge_nodes = ?, level = ? WHERE id = 1", (cnt, new_level))
        conn.commit()
        
    return {
        "success": True,
        "node_id": node_id,
        "message": f"Knowledge node '{topic}' assimilated into J.A.R.V.I.S. neural vault.",
        "total_nodes": cnt,
        "level": new_level
    }

def search_knowledge(query: str, limit: int = 5) -> list:
    init_db()
    q = f"%{query.strip()}%"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, topic, category, source_type, source_url, summary, details, tags, created_at
        FROM knowledge_vault
        WHERE topic LIKE ? OR summary LIKE ? OR tags LIKE ? OR details LIKE ?
        ORDER BY id DESC LIMIT ?
        """, (q, q, q, q, limit))
        return [dict(row) for row in cursor.fetchall()]

def get_all_knowledge(limit: int = 60) -> list:
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, topic, category, source_type, source_url, summary, details, tags, created_at
        FROM knowledge_vault
        ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_top_knowledge_for_prompt() -> str:
    nodes = get_all_knowledge(limit=5)
    if not nodes:
        return "No recent technical nodes cataloged."
    lines = []
    for n in nodes:
        lines.append(f"- [{n['category']}] {n['topic']}: {n['summary']}")
    return "\n".join(lines)

# --- Evolution Metrics ---
def get_evolution_stats() -> dict:
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evolution_stats WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return {"level": 1, "knowledge_nodes": 0, "research_cycles": 0, "days_active": 1}
        data = dict(row)
        
        # Calculate days active from first_boot_time
        try:
            boot_dt = datetime.fromisoformat(data["first_boot_time"])
            days = max(1, (datetime.now() - boot_dt).days + 1)
            data["days_active"] = days
        except Exception:
            data["days_active"] = 1
            
        return data

def record_research_cycle() -> dict:
    init_db()
    now_iso = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE evolution_stats
        SET research_cycles = research_cycles + 1,
            last_research_time = ?
        WHERE id = 1
        """, (now_iso,))
        conn.commit()
    return get_evolution_stats()

# Auto initialize
init_db()
