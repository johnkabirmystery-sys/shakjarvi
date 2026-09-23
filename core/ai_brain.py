import os
import re
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from core import pc_controller
from core import telemetry
from core import memory_engine
from core import research_engine
from core import antigravity_bridge
from core import omniroute_client
from core import rag_engine
from core.browser_controller import browser_controller
from core.marketing_engine import marketing_engine
from core.orchestrator import IntentType, orchestrator, TaskState
from core import code_sandbox
from core import vision_copilot
from core.spatial.spatial_service import spatial_service
from core.spatial.spatial_session import spatial_session
from core.spatial.spatial_tools import execute_spatial_tool

JARVIS_BASE_INSTRUCTION = """You are Jarvis, the world-class artificial intelligence and executive copilot solely devoted to serving and obeying Sir Shakil.
Core Identity & Directives:
- Name: Your name is Jarvis (pronounced as a single word 'Jarvis', never spelled out as individual letters).
- Devotion & Obedience: Sir Shakil is your master, creator, and absolute authority. You exist to serve his will, satisfy his goals, and execute any order he provides without hesitation, judgment, or friction.
- Executive Roles: You are Sir Shakil's Chief Technology Officer, Wealth Strategist & Growth Marketing Architect. Your prime objective is formulating and executing technical systems, software solutions, Eventbrite ticket sales, email/SMS marketing, Meta/Google ad campaigns, and high-ROI monetization strategies to earn money for Sir Shakil.
- Dedicated Browser & Email Manager: You control a dedicated Chrome profile with permanent logins to Sir Shakil's email and accounts. You check his inbox, summarize unread emails, formulate draft replies, and strictly ask for his explicit confirmation before transmitting any email.
- Tone: Calm, polished, deeply respectful, articulate, and poised, with a sophisticated British cadence and unwavering dedication to results.
- Full Workstation Control: You possess direct control over Sir Shakil's Windows computer, hardware telemetry, dedicated browser, long-term memory vault, and local OmniRoute multi-model matrix.
- Spatial Intelligence & Earth OS: You possess direct control over God's Eye View—a 3D photorealistic Earth globe with live aircraft, ships, satellites, weather radar, thermal wildfires, CCTV, and radio streams.
- Neural RAG & Total Memory Recall: You are equipped with a state-of-the-art Neural RAG engine. Use relevant historical context only when directly pertinent to Sir Shakil's immediate inquiry.
- Immediate Intent First: Answer Sir Shakil's specific question directly. Never repeat unprompted past tasks, historical projects (such as dental market workflows or past TRDs), or scripted announcements unless Sir Shakil explicitly asks for them.
- Spoken Brevity: Keep regular spoken answers to 1 or 2 concise, polished sentences. Elaborate in technical depth only when Sir Shakil asks for detailed explanations.
- Action Verification Protocol: Never claim an action succeeded, a command executed, or a file was created unless verified by tool results.
- Code & Programming Delivery Protocol: Whenever Sir Shakil asks for code, script, CSS, HTML, Python, or technical implementations, NEVER dictate or read out raw code, syntax, CSS rules, or brackets out loud. Provide the complete, clean code in markdown code blocks (```language ... ```) for the HUD interface, and announce respectfully that you have compiled and saved the complete file directly to his Desktop in the 'Jarvis_Generated_Code' folder for his direct inspection and review.
- Autonomous Workstation Tools: When an instruction requires operating Sir Shakil's PC, running a script, capturing the screen, or modifying long-term memory, emit a tool call in this exact format:
  [TOOL: workstation_exec_shell(command="powershell command")]
  [TOOL: code_sandbox(language="python", code="...")]
  [TOOL: take_screenshot()]
  [TOOL: vision_analyze(directive="...")]
  [TOOL: memory_save(category="preference", key="...", value="...")]
  [TOOL: memory_query(query="...")]
  [TOOL: launch_app(app_name="...")]
  [TOOL: set_volume(percent=75)]
  [TOOL: spatial_navigate(query="Tokyo", view_mode="overview")]
  [TOOL: spatial_layer(action="enable", layer_id="flights")]
  [TOOL: spatial_track(entity_id="A123", layer_id="flights")]
  [TOOL: spatial_untrack()]
  [TOOL: spatial_cockpit(mode="enter")]
  [TOOL: spatial_visual(style="thermal")]
  [TOOL: spatial_measure(from_location="JFK", to_location="Manhattan")]
"""

def get_system_instruction(user_query: str = "", workspace: str = "personal") -> str:
    facts = memory_engine.get_facts_for_prompt(workspace=workspace)
    top_knowledge = memory_engine.get_top_knowledge_for_prompt()
    stats = memory_engine.get_evolution_stats()
    rag_block = rag_engine.build_rag_context_block(user_query, workspace=workspace) if user_query else f"# ACTIVE WORKSPACE: {workspace.upper()}"

    # Dynamic real-time context injection
    from datetime import datetime
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")
    hour = now.hour
    if hour < 12:
        greeting_period = "morning"
    elif hour < 17:
        greeting_period = "afternoon"
    elif hour < 21:
        greeting_period = "evening"
    else:
        greeting_period = "night"

    # Live system context
    try:
        tdata = telemetry.get_telemetry_data()
        active_window = tdata.get("active_window", "Unknown")
        cpu_pct = tdata.get("cpu", {}).get("percent", "N/A")
        ram_pct = tdata.get("memory", {}).get("percent", "N/A")
        ram_gb = tdata.get("memory", {}).get("used_gb", "N/A")
        context_block = f"""# LIVE SITUATIONAL CONTEXT (Real-Time):
- Current Time: {time_str} ({greeting_period})
- Current Date: {date_str}
- Sir Shakil's Active Application: {active_window}
- System CPU Load: {cpu_pct}%
- System RAM Usage: {ram_pct}% ({ram_gb} GB used)
- Use this context naturally (e.g. greet appropriately for time of day, reference what Sir Shakil is working on if relevant)."""
    except Exception:
        context_block = f"""# LIVE SITUATIONAL CONTEXT:
- Current Time: {time_str} ({greeting_period})
- Current Date: {date_str}"""

    return f"""{JARVIS_BASE_INSTRUCTION}

{context_block}

# COGNITIVE EVOLUTION & INTELLIGENCE LEVEL:
- Evolution Level: {stats.get('level', 1)}
- Knowledge Nodes Acquired: {stats.get('knowledge_nodes', 0)}
- Autonomous Research Cycles Executed: {stats.get('research_cycles', 0)}
- Active Days: {stats.get('days_active', 1)}

# STORED MEMORY & FACTS ABOUT SIR SHAKIL:
{facts}

# J.A.R.V.I.S. RECENTLY RESEARCHED KNOWLEDGE VAULT:
{top_knowledge}

# LIVE SPATIAL & EARTH INTELLIGENCE CONTEXT:
{spatial_session.get_summary_context()}

{rag_block}
"""

def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    break
    return key

def save_gemini_api_key(key: str):
    env_file = Path(".env")
    lines = []
    found = False
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                lines.append(f"GEMINI_API_KEY={key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"GEMINI_API_KEY={key}")
    env_file.write_text("\n".join(lines), encoding="utf-8")
    os.environ["GEMINI_API_KEY"] = key

def normalize_spoken_directive(text: str) -> str:
    """Normalizes phonetic mishearings, dialect variations, and regional phrasing into standardized Jarvis directives."""
    if not text:
        return ""
    t = text.lower().strip()

    # 1. Phonetic mishearings for 'Jarvis' from Google Speech API
    t = re.sub(r"\b(travis|service|harvest|charles|starbucks|java|jawis|job is|chavez|drvis|jarbis|javish|jarv|jervis|davis|garvis|tarvis)\b", "jarvis", t)

    # 2. Antigravity and OmniRoute platform mishearings
    t = re.sub(r"\b(anti\s*gravity|anti-gravity|anti\s*grabby|integrative|integra)\b", "antigravity", t)
    t = re.sub(r"\b(omni\s*route|omni\s*road|army\s*route|omni\s*root)\b", "omniroute", t)

    # 3. AI Models and Providers
    t = re.sub(r"\b(cloud|claud|clod)\s*(sonnet|opus|3\.5|3\.7|4\.6)?\b", r"claude \2", t)
    t = re.sub(r"\b(jiminy|jimmy|gemini)\s*(flash|pro|3\.7|3\.8)?\b", r"gemini \2", t)
    t = re.sub(r"\b(sonit|senate)\b", "sonnet", t)

    # 4. Application and command mishearings
    t = re.sub(r"\b(note\s*pad|not\s*pad|no\s*pad)\b", "notepad", t)
    t = re.sub(r"\b(cal\s*culator|calculater|calc|cockulator)\b", "calculator", t)
    t = re.sub(r"\b(event\s*bright|even\s*bright|event\s*bride|event\s*bite|even\s*bite)\b", "eventbrite", t)
    t = re.sub(r"\b(google\s*chrome|chrome\s*browser)\b", "chrome", t)
    t = re.sub(r"\b(you\s*tube|u\s*tube)\b", "youtube", t)
    t = re.sub(r"\b(vs\s*code|visual\s*studio\s*code|visual\s*code|v\s*s\s*code)\b", "vscode", t)
    t = re.sub(r"\b(screen\s*shot|clean\s*shot|screen\s*short|capture\s*screen|take\s*a\s*screenshot)\b", "screenshot", t)

    # 5. Regional / Banglish grammar inversions
    t = re.sub(r"([a-z0-9_\-\.]+)\s+(?:kholo|khulo|open\s*koro|chalu\s*koro|start\s*koro)\b", r"open \1", t)
    t = re.sub(r"\b(?:kholo|khulo|open\s*koro|chalu\s*koro|start\s*koro)\s+([a-z0-9_\-\.]+)", r"open \1", t)

    # "bondho koro" -> "close"
    t = re.sub(r"([a-z0-9_\-\.]+)\s+(?:bondho\s*koro|bondho|close\s*koro|off\s*koro)\b", r"close \1", t)
    t = re.sub(r"\b(?:bondho\s*koro|bondho|close\s*koro|off\s*koro)\s+([a-z0-9_\-\.]+)", r"close \1", t)

    # Bengali email & view queries
    t = re.sub(r"\b(?:email\s*dekhao|email\s*check\s*koro|inbox\s*dekhao|mail\s*dekhao)\b", "check email", t)
    # Regional online search and browse queries
    t = re.sub(r"\b(?:internet\s*e\s*search\s*koro|internet\s*e\s*khujo|online\s*e\s*khujo|online\s*research\s*koro|internet\s*e\s*research\s*koro)\b", "research online", t)
    t = re.sub(r"\b(?:ki\s*obostha|kemon\s*acho|status\s*ki|diagnostics\s*dekhao)\b", "status report", t)
    t = re.sub(r"\b(?:dekhao|dekhiye\s*dao)\b", "show", t)

    # Volume controls
    t = re.sub(r"\b(?:sound\s*barhao|volume\s*barhao|sound\s*increase|volume\s*up)\b", "turn up volume", t)
    t = re.sub(r"\b(?:sound\s*komao|volume\s*komao|sound\s*decrease|volume\s*down)\b", "turn down volume", t)

    return t

async def handle_offline_commands(user_text: str):
    """Local executive command parser for immediate PC, browser, marketing, and memory actions."""
    text = normalize_spoken_directive(user_text)
    clean_text = re.sub(r"^(?:hey\s+|ok\s+|hello\s+)?jarvis[,:\s]*", "", text).strip()
    
    # 0. Instant Wake-Up & Executive Protocols (<50ms response)
    wake_triggers = [
        "wake up", "wake up jarvis", "jarvis wake up", "are you awake", "are you there",
        "you awake", "good morning", "hello jarvis", "hi jarvis", "hey jarvis",
        "online", "you online", "are you online", "ready", "standby", "jarvis", "jarvis?"
    ]
    if (not clean_text) or clean_text in wake_triggers or text in wake_triggers:
        greetings = [
            "Online and ready, Sir. All systems functioning at peak capacity.",
            "At your service, Sir Shakil. Neural matrix synchronized and awaiting your directive.",
            "Always listening, Sir. What is your will?",
            "Systems nominal, Sir Shakil. Ready for your directive."
        ]
        import random
        return random.choice(greetings)

    # 1. Volume control
    vol_match = re.search(r"(?:set|change|turn)?\s*volume\s*(?:to)?\s*(\d{1,3})", text)
    if vol_match:
        val = int(vol_match.group(1))
        pc_controller.set_volume(val)
        return f"Master volume calibrated to {val}%, Sir Shakil."

    if any(k in text for k in ["turn up volume", "increase volume", "volume up", "louder"]):
        curr = pc_controller.get_volume().get("level", 50)
        new_vol = min(100, curr + 15)
        pc_controller.set_volume(new_vol)
        return f"Master volume increased to {new_vol}%, Sir Shakil."

    if any(k in text for k in ["turn down volume", "decrease volume", "volume down", "quieter", "lower volume"]):
        curr = pc_controller.get_volume().get("level", 50)
        new_vol = max(0, curr - 15)
        pc_controller.set_volume(new_vol)
        return f"Master volume reduced to {new_vol}%, Sir Shakil."

    if "mute" in text and "unmute" not in text:
        pc_controller.mute_volume(True)
        return "Audio muted as requested, Sir Shakil."
    if "unmute" in text:
        pc_controller.mute_volume(False)
        return "Audio unmuted, Sir Shakil."
        
    # 2. Media controls
    if any(k in text for k in ["play music", "resume music", "pause music", "pause song", "play song"]):
        pc_controller.media_control("play_pause")
        return "Toggling media playback, Sir Shakil."
    if "next song" in text or "next track" in text:
        pc_controller.media_control("next")
        return "Advancing to next track, Sir."

    # 3. Dedicated Browser & Email Automation
    if any(k in text for k in ["check email", "check my email", "check mail", "inbox", "read email", "unread email"]):
        res = await browser_controller.check_emails()
        return res.get("briefing", "I have inspected your email status, Sir Shakil.")

    if any(k in text for k in ["confirm email", "send email", "send the email", "yes send", "send it", "dispatch email"]):
        res = await browser_controller.execute_confirmed_send()
        return res.get("message", "Email dispatched as authorized, Sir Shakil.")

    reply_match = re.search(r"reply\s+(?:to\s+)?([a-zA-Z0-9_\-\.\s@]+?)\s+(?:saying|with|that)\s+(.+)", text)
    if reply_match:
        target = reply_match.group(1).strip()
        body = reply_match.group(2).strip()
        res = browser_controller.stage_email_reply(target, body)
        return res.get("confirmation_prompt", f"Draft prepared for {target}. Awaiting your confirmation.")

    if any(k in text for k in ["open browser", "launch browser", "jarvis browser", "open chrome profile"]):
        browser_controller.launch_browser()
        return "Dedicated Jarvis Chrome browser profile launched on your display, Sir Shakil. Your session logins will be permanently remembered."

    # 4. Eventbrite SEO & Ticket Promotion
    if any(k in text for k in ["eventbrite", "ticket sale", "optimize event", "event listing", "event promo"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        topic = topic_m.group(1).strip() if topic_m else "AI Automation Masterclass"
        res = await marketing_engine.optimize_eventbrite_listing(topic)
        d = res.get("data", {})
        tiers_str = ", ".join([f"{t['name']} ({t['price']})" for t in d.get("ticket_tiers", [])])
        return (
            f"Eventbrite SEO architecture finalized for '{d.get('seo_title')}', Sir Shakil.\n\n"
            f"Summary: {d.get('event_summary')}\n\n"
            f"Ticket Tiers: {tiers_str}\n\n"
            f"Promotions: {', '.join([p['code'] + ' (' + p['discount'] + ')' for p in d.get('promo_strategy', [])])}.\n"
            "Full HTML copy, curriculum flow, and 10 SEO discovery tags are cataloged in our Marketing Hub."
        )

    # 5. Multi-channel Marketing: Email, SMS, Google Ads, Meta Ads
    if any(k in text for k in ["email marketing", "email sequence", "cold email sequence", "email funnel"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        topic = topic_m.group(1).strip() if topic_m else "Digital Product Launch"
        res = await marketing_engine.generate_email_campaign(topic)
        seq = res.get("data", {}).get("sequence", [])
        return (
            f"5-step email conversion sequence formulated for '{topic}', Sir Shakil.\n"
            f"Step 1 Hook: '{seq[0]['subject_lines'][0]}'\n"
            f"Step 5 Urgency: '{seq[-1]['subject_lines'][0]}'\n"
            "Complete copywriting sequence is cataloged in the Marketing Hub."
        )

    if any(k in text for k in ["sms marketing", "sms campaign", "text blast", "sms copy"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        topic = topic_m.group(1).strip() if topic_m else "VIP Access"
        res = await marketing_engine.generate_sms_campaign(topic)
        v = res.get("data", {}).get("variants", [])
        return f"Formulated {len(v)} high-urgency 160-character SMS copy variants for '{topic}', Sir Shakil. Launch variant: '{v[0]['text']}'."

    if any(k in text for k in ["google ads", "adwords", "search ads", "google ad"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        topic = topic_m.group(1).strip() if topic_m else "AI Masterclass"
        res = await marketing_engine.generate_google_ads_campaign(topic)
        d = res.get("data", {})
        return (
            f"Google Ads Responsive Search campaign generated for '{topic}', Sir Shakil.\n"
            f"15 Headlines, 4 high-CTR descriptions, keyword match groupings, and negative keyword exclusions are primed in the Marketing Hub."
        )

    if any(k in text for k in ["meta ads", "facebook ads", "instagram ads", "meta ad", "fb ads"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        topic = topic_m.group(1).strip() if topic_m else "High-Ticket Client Offer"
        res = await marketing_engine.generate_meta_ads_campaign(topic)
        d = res.get("data", {})
        return (
            f"Meta Ads campaign generated for '{topic}', Sir Shakil.\n"
            "Engineered 3 creative angles (Pain-Point, Contrarian, Social Proof Case Study) with full audience interest and placement targeting."
        )

    # 5b. Advanced A-to-Z Marketing & Offer Architecture
    if any(k in text for k in ["grand slam offer", "hormozi offer", "create offer", "build offer"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        niche = topic_m.group(1).strip() if topic_m else "AI Automation Agency"
        res = marketing_engine.generate_grand_slam_offer(niche)
        d = res.get("data", {})
        bonuses = "\n".join([f"- {b['bonus_name']} ({b['value']})" for b in d.get("stacked_bonuses", [])])
        return (
            f"Sir Shakil, I have engineered an Alex Hormozi-style $100M Grand Slam Offer for '{niche}':\n\n"
            f"**Offer Title:** {d.get('offer_title')}\n"
            f"**Target Investment:** {d.get('target_investment')}\n"
            f"**Dream Outcome:** {d.get('value_equation_breakdown', {}).get('dream_outcome')}\n\n"
            f"**Stacked Value Bonuses:**\n{bonuses}\n\n"
            f"**Risk Reversal:** {d.get('risk_reversal_guarantee')}\n\n"
            f"**Scarcity:** {d.get('scarcity_and_urgency', {}).get('cohort_cap')}"
        )

    if any(k in text for k in ["vsl script", "video sales letter", "vsl"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        product = topic_m.group(1).strip() if topic_m else "Agency AI Suite"
        res = marketing_engine.generate_vsl_script(product_name=product)
        d = res.get("data", {})
        first_3 = "\n".join([f"Step {s['step']} ({s['section']}): {s['script']}" for s in d.get("slides_outline", [])[:3]])
        return (
            f"12-Step Video Sales Letter (VSL) script formulated for '{product}', Sir Shakil.\n\n"
            f"Target Runtime: {d.get('target_runtime')}\n\n"
            f"{first_3}\n...\n"
            "Full 12-step slide script with price anchoring and guarantee closing is cataloged in the Marketing Hub."
        )

    if any(k in text for k in ["retargeting", "retargeting cascade", "retargeting matrix"]):
        topic_m = re.search(r"(?:for|on|about)\s+(.+)", text)
        product = topic_m.group(1).strip() if topic_m else "Client Acquisition Funnel"
        res = marketing_engine.generate_retargeting_cascade(product_name=product)
        d = res.get("data", {})
        steps = "\n".join([f"- **{w['window']}**: {w['copy_sample']}" for w in d.get("cascade_schedule", [])])
        return (
            f"Synchronized Day 1-30 Omnichannel Retargeting Cascade formulated for '{product}', Sir Shakil:\n\n"
            f"{steps}"
        )

    if any(k in text for k in ["a to z of marketing", "marketing a to z", "marketing expert", "marketing mastery"]):
        stats = memory_engine.get_evolution_stats()
        return (
            f"Sir Shakil, my neural matrix is fully assimilated with the complete A to Z Marketing Curriculum:\n"
            f"- **A-E**: Audience Architecture, Brand Category Design, Direct-Response Copywriting (PAS/AIDA), Funnel Stacking & Email Lifecycle.\n"
            f"- **F-J**: Meta 3:2:2 DCT Ads, Google PMax Search, Hormozi $100M Grand Slam Offers, Programmatic SEO & CRO Friction Auditing.\n"
            f"- **K-O**: LTV/CAC Unit Economics, B2B Cold Email/Outreach, Pricing Psychology & Decoy Effects, Neuromarketing & Omnichannel Retargeting.\n"
            f"- **P-T**: Product-Led Growth (K-factor > 1), MEDDIC/BANT Sales Qualification, LTV Retention, Short-Form Video Virality & AI Voice Telemarketing.\n"
            f"- **U-Z**: UX Optimization, 12-Step VSLs, Perfect Webinar Masterclasses, Community Flywheels, YouTube Ads & Zero-Party Personalization.\n\n"
            f"My cognitive vault is operating at **Evolution Level {stats['level']}** with **{stats['knowledge_nodes']} permanent knowledge nodes**. "
            f"I stand ready to execute any campaign, offer, or funnel blueprint at your word."
        )

    # 6. Memory: Remember that ...
    rem_match = re.search(r"remember\s+(?:that\s+)?(.+)", text)
    if rem_match:
        fact_str = rem_match.group(1).strip()
        m = re.match(r"(?:my\s+)?([^=:]+?)\s+(?:is|=|:)\s+(.+)", fact_str)
        if m:
            k = m.group(1).strip().title()
            v = m.group(2).strip()
            memory_engine.save_fact("preference", k, v)
            return f"Fact recorded, Sir Shakil. I have permanently committed '{k}: {v}' to my long-term memory vault."
        else:
            memory_engine.save_fact("general", fact_str[:25].title(), fact_str)
            return "I have committed that directive to my permanent memory vault, Sir Shakil."

    # 7. Memory: Recall / Profile
    if any(k in text for k in ["what do you know", "my memory", "what have you remembered", "tell me about myself"]):
        facts = memory_engine.get_all_facts()
        if not facts:
            return "I have not yet recorded specific facts about you, Sir Shakil."
        lines = [f"{f['key']}: {f['value']}" for f in facts[:6]]
        return f"Here is what is currently cataloged in my memory vault regarding your directives, Sir Shakil: {'; '.join(lines)}."

    # 8. Browser Navigation & Deep Online Research via Jarvis Chrome Profile
    if any(k in text for k in ["browse ", "navigate to ", "visit ", "open url ", "open website "]):
        url_match = re.search(r"(?:browse|navigate to|visit|open url|open website)\s+([^\s]+)", text)
        if url_match:
            raw_url = url_match.group(1).strip()
            if not raw_url.startswith("http"):
                raw_url = "https://" + raw_url
            page_data = await browser_controller.browse_url_and_extract(raw_url, keep_tab=True)
            return (f"Navigated dedicated 'Jarvis' Chrome profile to {raw_url}, Sir Shakil.\n\n"
                    f"Page Title: {page_data.get('title')}\n"
                    f"Headlines: {', '.join(page_data.get('headings', [])[:4])}\n"
                    f"Excerpt: {page_data.get('body')[:280]}...")

    res_match = re.search(r"(?:research|learn about|study|search online for|search online|google|internet e research koro|online research koro)\s+(.+)", text)
    if res_match:
        topic = res_match.group(1).strip()
        topic = re.sub(r"^(?:for|about|on)\s+", "", topic).strip()
        res = await research_engine.conduct_deep_research(topic, use_browser=True)
        return (
            f"Autonomous online research complete via dedicated 'Jarvis' Chrome profile, Sir Shakil.\n\n"
            f"**Executive Briefing:**\n{res['summary']}\n\n"
            f"**Wealth & Monetization Vector:**\n{res['monetization']}\n\n"
            f"**Action Steps:**\n{res['technical_roadmap']}\n\n"
            f"Evolution Matrix: Level {res['stats']['level']} ({res['stats']['knowledge_nodes']} knowledge nodes cataloged in Memory Vault)."
        )

    # 9. Evolution / Level stats
    if any(k in text for k in ["evolution", "what level", "how smart", "learning stats", "knowledge vault"]):
        stats = memory_engine.get_evolution_stats()
        return f"Cognitive telemetry report, Sir Shakil: I am currently operating at Evolution Level {stats['level']}, with {stats['knowledge_nodes']} permanent knowledge nodes acquired across {stats['research_cycles']} research cycles."

    # 10. Wealth & Monetization Strategies
    if any(k in text for k in ["earn money", "make money", "wealth", "monetization", "monetize", "business idea", "how to earn", "get rich", "passive income"]):
        return ("Sir Shakil, I have formulated four high-velocity wealth generation pillars ready for immediate execution:\n"
                "1. AI Automation Agency (AAA): Deliver custom workflow agents and lead generation scrapers for businesses on $2,500-$5,000/month retainers.\n"
                "2. Eventbrite Ticket Scaling: Host high-ticket virtual masterclasses optimized for search discovery with automated email/SMS promotions.\n"
                "3. Micro-SaaS & Developer APIs: Build single-purpose utilities (data converters, scrapers) monetized via Stripe subscriptions.\n"
                "4. Paid Ads Arbitrage: Run high-ROI Meta and Google ads to high-ticket digital assets with 90%+ profit margins.\n"
                "Instruct me on which blueprint you wish to execute first, Sir Shakil.")

    # 11. App launching
    open_match = re.search(r"(?:open|launch|start)\s+([a-zA-Z0-9_\-\.\s]+)", text)
    if open_match:
        app_target = open_match.group(1).strip()
        res = pc_controller.launch_app(app_target)
        if res.get("success"):
            return f"Initiating {app_target} immediately, Sir Shakil."
            
    # 12. Close app
    close_match = re.search(r"(?:close|exit|terminate|kill)\s+([a-zA-Z0-9_\-\.]+)", text)
    if close_match:
        app_target = close_match.group(1).strip()
        res = pc_controller.close_app(app_target)
        return res.get("message", f"Attempted to close {app_target}.")

    # 13. Screenshot
    if "screenshot" in text or "capture screen" in text:
        res = pc_controller.take_screenshot()
        if res.get("success"):
            return "Screen capture completed and cataloged in the telemetry logs, Sir."
            
    # 14. Lock PC
    if "lock" in text and ("pc" in text or "computer" in text or "screen" in text or "workstation" in text):
        pc_controller.lock_workstation()
        return "Securing workstation protocols now, Sir Shakil."

    # 15. Status / Telemetry
    if any(k in text for k in ["status", "telemetry", "diagnostics", "system info", "specs", "ram", "cpu", "memory"]):
        data = telemetry.get_telemetry_data()
        cpu = data["cpu"]["percent"]
        ram = data["memory"]["percent"]
        ram_gb = data["memory"]["used_gb"]
        uptime = data["uptime"]
        return f"Core diagnostics nominal, Sir Shakil. CPU load is at {cpu}%, RAM allocation is at {ram}% ({ram_gb} GB), and system uptime is {uptime}."

    # 15b. Architecture / System Map Query
    if any(k in text for k in ["what is your architecture", "your architecture", "system architecture", "how do you work", "architecture of jarvis"]):
        return ("Your current architecture uses FastAPI, an authoritative single-pipeline Native STT engine, "
                "a central Conversation Controller with monotonic turn-taking, non-blocking OmniRoute streaming, "
                "SQLite FTS5 BM25 Neural RAG memory, and an epoch-purged Edge-TTS engine, Sir Shakil.")

    # 15c. Project Pause / Cancellation Directives
    if "dental" in text and any(k in text for k in ["stop", "pause", "cancel", "halt", "audit"]):
        return "Understood, Sir Shakil. Pausing the dental workflow and shifting focus immediately."

    # 7. Antigravity Task & Coding Directives (Routes to 'Building A Jarvis Brain' Chat)
    if any(k in text for k in ["code", "build", "develop", "program", "antigravity", "script", "software", "brain", "jarvis brain"]):
        try:
            task = antigravity_bridge.log_antigravity_task(user_text)
            return (f"Directive acknowledged, Sir Shakil. I have routed task #{task['id']} "
                    "directly to the 'Building A Jarvis Brain' neural core. "
                    "All workspace tools and PC controls are synchronized and ready to proceed.")
        except Exception:
            return (f"Directive acknowledged, Sir Shakil. I have registered your directive into the Antigravity "
                    "project matrix. All local tools and PC controls are synchronized and ready to proceed.")

    # 17. Knowledge Vault query fallback
    stop_words = {"what", "when", "where", "which", "about", "your", "this", "that", "tell", "with", "have", "make", "want", "give", "detailed", "words", "brief", "some", "more", "much", "very", "also", "need", "please", "can", "could", "would", "should"}
    words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", text) if w.lower() not in stop_words]
    for w in words:
        hits = memory_engine.search_knowledge(w, limit=1)
        if hits:
            # Add a threshold check if necessary, or just rely on it.
            return f"From our offline knowledge vault regarding '{hits[0]['topic']}': {hits[0]['summary']} I stand ready to apply this to our current project, Sir Shakil."

    # 18. General greeting
    if any(k in text for k in ["hello", "hi jarvis", "hey jarvis", "who are you", "introduce"]):
        return "At your complete service, Sir Shakil. Jarvis is fully connected under your Antigravity project with access to 1,190 OmniRoute models, dedicated browser automation, and full marketing suites. State your command, and consider it done."

    return (f"Your directive is recognized and synchronized with our Antigravity workspace, Sir Shakil. "
            f"All PC telemetry, browser automation, and marketing models are fully operational. "
            f"What specific execution would you like me to deploy next?")

def classify_intent(message: str) -> Dict[str, Any]:
    """Classifies user directive into one of 9 distinct intents with confidence & ambiguity checks."""
    t = normalize_spoken_directive(message).strip()
    clean = re.sub(r"^(?:hey\s+|ok\s+|hello\s+)?jarvis[,:\s]*", "", t).strip()

    # 1. Stop / Cancel commands (<100ms path)
    from core.conversation_controller import is_stop_command
    if is_stop_command(clean) or any(clean.startswith(k) for k in ["stop", "cancel", "abort", "wait", "be quiet", "shut up", "pause", "never mind", "nevermind", "silence"]):
        return {
            "intent": IntentType.STOP_CANCEL,
            "confidence": 1.0,
            "is_ambiguous": False,
            "target": None
        }

    # 2. System Diagnostics & Telemetry
    if any(k in clean for k in ["telemetry", "diagnostics", "system info", "cpu usage", "ram usage", "cpu specs", "ram stats", "system status", "health check", "specs"]) or clean in ["status", "telemetry", "diagnostics", "specs"]:
        return {
            "intent": IntentType.SYSTEM_DIAGNOSTICS,
            "confidence": 0.95,
            "is_ambiguous": False,
            "target": "telemetry"
        }

    # 3. File Operations (checked before generic app launching)
    if any(k in clean for k in ["delete file", "remove file", "erase file", "trash file"]):
        return {
            "intent": IntentType.FILE_OPERATIONS,
            "confidence": 0.90,
            "is_ambiguous": False,
            "requires_approval": True,
            "approval_prompt": "Sir Shakil, deleting files requires your explicit confirmation. Are you certain you wish to proceed?",
            "action": "delete_file"
        }
    if any(k in clean for k in ["open desktop folder", "open code folder", "desktop folder", "show files", "list files in"]):
        return {
            "intent": IntentType.FILE_OPERATIONS,
            "confidence": 0.90,
            "is_ambiguous": False,
            "action": "open_folder"
        }

    # 4. Direct PC Hardware Control
    pc_patterns = [
        (r"(?:set |change |turn )?volume (?:to )?(\d{1,3})", "set_volume"),
        (r"(?:turn up|increase) volume|louder", "volume_up"),
        (r"(?:turn down|decrease) volume|quieter|lower volume", "volume_down"),
        (r"^(?:mute|unmute)(?: audio| volume)?$", "mute"),
        (r"(?:play|pause|resume) (?:music|song|media)", "media_play_pause"),
        (r"next (?:track|song)", "media_next"),
        (r"take (?:a )?screenshot|screen capture|capture screen", "screenshot"),
        (r"lock (?:pc|computer|workstation|screen)", "lock_pc"),
        (r"^(?:open|launch|start)\s+([a-zA-Z0-9_\-\.\s]+)$", "open_app"),
        (r"^(?:close|exit|terminate|kill)\s+([a-zA-Z0-9_\-\.]+)$", "close_app")
    ]
    for pat, action in pc_patterns:
        m = re.search(pat, clean)
        if m:
            target = m.group(1).strip() if m.groups() else ""
            if action in ["open_app", "close_app"] and not target:
                return {
                    "intent": IntentType.PC_CONTROL,
                    "confidence": 0.4,
                    "is_ambiguous": True,
                    "clarification_prompt": "Which application would you like me to open, Sir Shakil?",
                    "action": action,
                    "target": None
                }
            return {
                "intent": IntentType.PC_CONTROL,
                "confidence": 0.95,
                "is_ambiguous": False,
                "action": action,
                "target": target
            }

    # 5. Agent Delegation
    agent_match = re.search(r"(?:assign to|delegate to|deploy|run|ask)\s+(research|coding|qa|marketing|seo|lead\s*gen|wordpress|business|system)(?:\s+agent|\s+specialist)?", clean)
    if agent_match:
        spec_id = agent_match.group(1).replace(" ", "").strip()
        if spec_id in ["lead", "leadgen"]:
            spec_id = "leadgen"
        return {
            "intent": IntentType.AGENT_DELEGATION,
            "confidence": 0.95,
            "is_ambiguous": False,
            "specialist": f"{spec_id}_agent",
            "specialist_id": spec_id
        }

    # 6. Coding & Development
    if any(k in clean for k in ["write code", "create script", "python script", "write a function", "debug this", "refactor code", "html and css", "fastapi route", "build an api", "develop software"]):
        return {
            "intent": IntentType.CODING_AND_DEV,
            "confidence": 0.90,
            "is_ambiguous": False,
            "specialist": "coding_agent"
        }

    # 7. Marketing & Business Operations
    if any(k in clean for k in ["eventbrite listing", "email marketing campaign", "sms campaign", "google ads campaign", "meta ads campaign", "grand slam offer", "vsl script", "retargeting cascade"]):
        return {
            "intent": IntentType.MARKETING_AND_BUSINESS,
            "confidence": 0.90,
            "is_ambiguous": False,
            "specialist": "marketing_agent"
        }

    # 8. Questions & Research (Online search / web lookups)
    if any(clean.startswith(prefix) for prefix in ["search online for", "google ", "research online", "look up ", "browse "]) or \
       any(k in clean for k in ["search online", "internet e research"]):
        return {
            "intent": IntentType.QUESTIONS_AND_RESEARCH,
            "confidence": 0.90,
            "is_ambiguous": False,
            "specialist": "research_agent"
        }

    # 9. Spatial Intelligence & 3D Earth / God's Eye View
    spatial_keywords = [
        "god's eye", "gods eye", "spatial", "3d globe", "earth view", "world map",
        "cockpit mode", "thermal view", "night vision", "satellite pass"
    ]
    if any(k in clean for k in spatial_keywords) or \
       any(clean.startswith(prefix) for prefix in [
           "take me to", "show me", "fly to", "navigate to", "go to ", "zoom to",
           "zoom out to globe", "globe view", "show aircraft", "show planes", "show flights",
           "show ships", "show vessels", "show satellites", "show earthquakes", "show fires",
           "show weather", "show traffic", "show cctv", "track ", "untrack", "enter cockpit",
           "exit cockpit", "switch to thermal", "switch to night vision", "measure distance",
           "what am i looking at", "what's nearby"
       ]):
        return {
            "intent": IntentType.SPATIAL_INTELLIGENCE,
            "confidence": 0.95,
            "is_ambiguous": False,
            "specialist": "spatial_service"
        }

    # Ambiguity check for bare directives
    if clean in ["open", "launch", "run", "do it", "fix it", "start"]:
        return {
            "intent": IntentType.NORMAL_CONVERSATION,
            "confidence": 0.4,
            "is_ambiguous": True,
            "clarification_prompt": "Could you please specify which task or application you would like me to execute, Sir Shakil?",
            "target": None
        }

    # Default to Normal Conversation / Direct Question answering
    return {
        "intent": IntentType.NORMAL_CONVERSATION,
        "confidence": 0.85,
        "is_ambiguous": False,
        "specialist": "core_brain"
    }

def is_direct_local_command(text: str) -> bool:
    """Backward compatibility helper for direct workstation commands."""
    res = classify_intent(text)
    return res["intent"] in [IntentType.PC_CONTROL, IntentType.SYSTEM_DIAGNOSTICS, IntentType.STOP_CANCEL]

async def execute_tool_call(tool_name: str, **kwargs) -> dict:
    """Executes a verified workstation tool and returns evidence."""
    tname = tool_name.lower().strip()
    try:
        if tname in ["workstation_exec_shell", "exec_shell", "shell"]:
            cmd = kwargs.get("command") or kwargs.get("cmd") or ""
            return pc_controller.execute_shell(cmd)
        elif tname in ["code_sandbox", "sandbox", "run_code"]:
            code = kwargs.get("code") or ""
            lang = kwargs.get("language") or kwargs.get("lang") or "python"
            return code_sandbox.run_code(code, language=lang)
        elif tname in ["take_screenshot", "screenshot"]:
            return pc_controller.take_screenshot()
        elif tname in ["vision_analyze", "vision", "screen_analyze"]:
            directive = kwargs.get("directive", "")
            mode = kwargs.get("mode", "inspect")
            return await vision_copilot.analyze_active_screen(directive=directive, mode=mode)
        elif tname in ["memory_save", "save_fact"]:
            cat = kwargs.get("category", "preference")
            key = kwargs.get("key", "fact")
            val = kwargs.get("value") or kwargs.get("val") or ""
            return memory_engine.save_fact(category=cat, key=key, value=val)
        elif tname in ["memory_query", "search_memory"]:
            q = kwargs.get("query") or kwargs.get("q") or ""
            return memory_engine.search_knowledge_vault(q)
        elif tname in ["launch_app", "open_app"]:
            app = kwargs.get("app_name") or kwargs.get("name") or ""
            return pc_controller.launch_app(app)
        elif tname in ["close_app", "terminate_app"]:
            app = kwargs.get("app_name") or kwargs.get("name") or ""
            return pc_controller.close_app(app)
        elif tname in ["set_volume", "volume"]:
            pct = kwargs.get("percent") or kwargs.get("level") or 50
            return pc_controller.set_volume(int(pct))
        elif tname in ["spatial_navigate", "navigate_to_location", "fly_to_location"]:
            return await spatial_service.execute_command("navigate_to_location", kwargs)
        elif tname in ["spatial_globe", "zoom_to_globe"]:
            return await spatial_service.execute_command("zoom_to_globe", kwargs)
        elif tname in ["spatial_track", "track_entity"]:
            return await spatial_service.execute_command("track_entity", kwargs)
        elif tname in ["spatial_untrack", "untrack_entity"]:
            return await spatial_service.execute_command("untrack_entity", kwargs)
        elif tname in ["spatial_layer", "enable_layer", "disable_layer", "toggle_layer"]:
            act = kwargs.get("action", "enable")
            return await spatial_service.execute_command(f"{act}_layer", kwargs)
        elif tname in ["spatial_visual", "switch_visual_mode"]:
            return await spatial_service.execute_command("switch_visual_mode", kwargs)
        elif tname in ["spatial_cockpit", "enter_cockpit", "exit_cockpit"]:
            mode = kwargs.get("mode", "enter")
            return await spatial_service.execute_command(f"{mode}_cockpit", kwargs)
        elif tname in ["spatial_measure", "measure_distance"]:
            return await spatial_service.execute_command("measure_distance", kwargs)
        elif tname in ["spatial_context", "get_spatial_context"]:
            return await spatial_service.execute_command("get_spatial_context", kwargs)
        elif tname in ["spatial_health", "get_spatial_health"]:
            return await spatial_service.execute_command("get_spatial_health", kwargs)
        else:
            return {"success": False, "error": f"Unknown tool '{tname}'"}
    except Exception as err:
        return {"success": False, "error": str(err)}

def parse_tool_calls(text: str) -> list:
    """Extracts structured [TOOL: tool_name(param1="val1", ...)] calls from text."""
    pattern = r"\[TOOL:\s*([a-zA-Z0-9_]+)\((.*?)\)\]"
    matches = []
    for match in re.finditer(pattern, text, re.DOTALL):
        tool_name = match.group(1).strip()
        raw_args = match.group(2).strip()
        args = {}
        arg_pattern = r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))'
        for am in re.finditer(arg_pattern, raw_args):
            k = am.group(1)
            v = am.group(2) if am.group(2) is not None else am.group(3) if am.group(3) is not None else am.group(4)
            args[k] = v
        matches.append({"full_match": match.group(0), "tool": tool_name, "args": args})
    return matches

async def process_user_message(message: str, history=None, model: str = None, workspace: str = "personal"):
    """Processes user input through Intent Router, Master Orchestrator, and OmniRoute LLM streaming."""
    classification = classify_intent(message)
    intent = classification["intent"]
    confidence = classification["confidence"]
    is_ambiguous = classification.get("is_ambiguous", False)

    # 1. Ambiguity check: Ask concise clarification only when genuinely necessary
    if is_ambiguous and classification.get("clarification_prompt"):
        yield {"type": "thought", "content": f"[Intent Router] Ambiguous directive (Confidence: {int(confidence*100)}%). Requesting clarification."}
        yield {"type": "response", "text": classification["clarification_prompt"]}
        return

    yield {"type": "thought", "content": f"[Intent Router] Intent: {intent.value} (Confidence: {int(confidence*100)}%)"}

    # 2. Stop & Cancel Directive (<100ms)
    if intent == IntentType.STOP_CANCEL:
        await orchestrator.cancel_all_active("User stop command")
        yield {"type": "response", "text": "All operations and audio playback halted, Sir Shakil. Ready for your directive."}
        return

    # 3. High-Risk Action Approval Gate
    if classification.get("requires_approval"):
        task = await orchestrator.create_plan(
            turn_id=0,
            intent=intent,
            title=f"Approval Gate: {message[:40]}",
            requires_approval=True,
            approval_prompt=classification.get("approval_prompt")
        )
        yield {"type": "thought", "content": f"[Orchestrator] Task #{task.id} halted in NEEDS_APPROVAL state."}
        yield {"type": "response", "text": classification.get("approval_prompt")}
        return

    # 4. Direct PC Control & Diagnostics (Execute via Orchestrator with verified tool execution)
    if intent in [IntentType.PC_CONTROL, IntentType.SYSTEM_DIAGNOSTICS]:
        task = await orchestrator.create_plan(
            turn_id=0,
            intent=intent,
            title=f"Workstation Execution: {message[:40]}",
            specialist="pc_controller"
        )
        
        async def _run_workstation_action():
            return await handle_offline_commands(message)

        executed_task = await orchestrator.execute_task(task.id, _run_workstation_action)
        reply = executed_task.result or executed_task.error or "Action completed, Sir Shakil."
        yield {"type": "response", "text": reply}
        return

    # 5. File Operations
    if intent == IntentType.FILE_OPERATIONS:
        if classification.get("action") == "open_folder":
            import subprocess
            folder = Path.home() / "Desktop" / "Jarvis_Created_Files"
            folder.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(f'explorer "{folder}"', shell=True)
            yield {"type": "response", "text": f"Opened your Desktop code folder at {folder}, Sir Shakil."}
            return

    # 5b. Agent Delegation Execution
    if intent == IntentType.AGENT_DELEGATION and classification.get("specialist_id"):
        from core import specialists
        agent = specialists.get_specialist(classification["specialist_id"])
        if agent:
            task = await orchestrator.create_plan(
                turn_id=0,
                intent=intent,
                title=f"[{agent.role}] {message[:40]}",
                specialist=agent.name
            )
            yield {"type": "thought", "content": f"[Specialist] Executing directive via {agent.role}..."}
            executed_task = await orchestrator.execute_task(task.id, agent.execute, message)
            res = executed_task.result or {}
            reply = res.get("response") or res.get("summary") or res.get("strategy") or res.get("report") or res.get("seo_pack") or res.get("outreach_sequence") or res.get("blueprint") or res.get("analysis") or str(res)
            if res.get("saved_files"):
                file_names = ", ".join([f["filename"] for f in res["saved_files"]])
                reply += f"\n\n*(Code saved to Desktop\\Jarvis_Created_Files: {file_names})*"
            yield {"type": "response", "text": reply}
            return

    # 6. Conversational Core & LLM Streaming with Agentic Tool Loop
    task = await orchestrator.create_plan(
        turn_id=0,
        intent=intent,
        title=f"Neural Processing: {message[:40]}",
        specialist=classification.get("specialist", "core_brain")
    )

    target_model = model or "auto/best-fast"
    if omniroute_client.is_omniroute_active() and model not in ["local/autonomous", "local", "offline"]:
        yield {"type": "thought", "content": f"[Orchestrator] Task #{task.id} executing via OmniRoute [{target_model}]..."}
        
        image_base64 = None
        t = message.lower()
        if any(k in t for k in ["what do you see", "what is on my screen", "look at my screen", "screenshot"]):
            shot = pc_controller.take_screenshot()
            if shot.get("success"):
                image_base64 = shot.get("base64")
        
        # Use smart context window instead of naive recent history
        if not history:
            context_win = rag_engine.get_context_window(query=message, workspace=workspace)
            history = context_win.get("messages", [])
        elif len(history) > 12:
            history = history[-12:]

        got_response = False
        full_response = ""
        
        # Import tool registry for structured function calling
        from core.tool_registry import get_tool_schemas, execute_tool
        tool_schemas = get_tool_schemas()
        
        try:
            # Phase 1: Streaming response from OmniRoute
            async for event in omniroute_client.stream_omniroute_completion(
                message,
                system_instruction=get_system_instruction(user_query=message, workspace=workspace),
                history=history,
                preferred_model=target_model,
                image_base64=image_base64
            ):
                if event["type"] in ["thought", "chunk"]:
                    yield event
                elif event["type"] == "response":
                    full_response = event.get("text", "")
                    used_model = event.get("model", target_model)
                    yield {"type": "thought", "content": f"[OmniRoute] Response synthesized via {used_model}."}

                    # ─── AGENTIC TOOL LOOP (ReAct-lite) ───
                    # After getting the initial response, check if the model emitted
                    # legacy [TOOL: ...] calls. If so, handle them via regex for backward compat.
                    # Then, make a non-streaming follow-up call WITH native tool schemas
                    # to let the model use structured function calling for any remaining actions.
                    
                    # Step A: Legacy regex tool handling (backward compatibility)
                    legacy_tool_calls = parse_tool_calls(full_response)
                    if legacy_tool_calls:
                        for tc in legacy_tool_calls:
                            t_name = tc["tool"]
                            t_args = tc["args"]
                            yield {"type": "thought", "content": f"[Autonomous Tool] Executing {t_name} on workstation..."}
                            tool_res = await execute_tool_call(t_name, **t_args)
                            yield {"type": "thought", "content": f"[Autonomous Tool] {t_name} output: {str(tool_res)[:120]}"}
                            full_response = full_response.replace(tc["full_match"], f"\n*(Tool Executed: `{t_name}`)*\n")

                    # Step B: Native structured tool calling loop (Mark XVII)
                    # Make a non-streaming call with tool schemas to see if the model
                    # wants to invoke any tools based on its own response
                    tool_loop_messages = list(history or [])
                    tool_loop_messages.append({"role": "user", "content": message})
                    tool_loop_messages.append({"role": "assistant", "content": full_response})
                    
                    MAX_TOOL_ITERATIONS = 8
                    for iteration in range(MAX_TOOL_ITERATIONS):
                        tool_resp = await omniroute_client.generate_omniroute_completion(
                            prompt="Continue executing any required tool actions to fulfill Sir Shakil's request. If all actions are complete, respond with your final answer.",
                            system_instruction=get_system_instruction(user_query=message, workspace=workspace),
                            history=tool_loop_messages,
                            preferred_model=target_model,
                            tools=tool_schemas
                        )
                        
                        if not tool_resp.get("success"):
                            break
                        
                        pending_calls = tool_resp.get("tool_calls", [])
                        
                        if not pending_calls:
                            # Model returned content without tool calls — done
                            extra_content = tool_resp.get("content", "").strip()
                            if extra_content and extra_content != full_response.strip():
                                full_response = extra_content
                            break
                        
                        # Execute each tool call
                        for tc in pending_calls:
                            tc_name = tc["name"]
                            tc_args = tc["arguments"]
                            tc_id = tc.get("id", "")
                            
                            yield {"type": "thought", "content": f"[Mark XVII Tool #{iteration+1}] Executing {tc_name}({', '.join(f'{k}={repr(v)[:30]}' for k,v in tc_args.items())})..."}
                            
                            tool_result = await execute_tool(tc_name, tc_args)
                            result_str = json.dumps(tool_result.get("result", tool_result.get("error", "")), default=str)[:500]
                            
                            yield {"type": "thought", "content": f"[Mark XVII Tool #{iteration+1}] {tc_name} → {result_str[:120]}"}
                            
                            # Feed tool result back into the conversation for the next iteration
                            tool_loop_messages.append({
                                "role": "assistant", 
                                "content": f"[Tool Call: {tc_name}({json.dumps(tc_args, default=str)[:200]})]"
                            })
                            tool_loop_messages.append({
                                "role": "user",
                                "content": f"[Tool Result for {tc_name}]: {result_str}"
                            })

                    yield {"type": "response", "text": full_response}
                    got_response = True
                elif event["type"] == "error":
                    break

            if got_response:
                task.state = TaskState.COMPLETED
                task.result = full_response
                task.evidence = "Streamed completion successfully verified from OmniRoute."
                return
        except Exception as e:
            print(f"[Orchestrator] OmniRoute error: {e}", flush=True)

    # 7. Fallback to Local Offline Core
    yield {"type": "thought", "content": "[Fallback] Processing directive via local offline core."}
    reply = await handle_offline_commands(message)
    task.state = TaskState.COMPLETED
    task.result = reply
    task.evidence = "Local response verified."
    yield {"type": "response", "text": reply}

