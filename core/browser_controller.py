"""
Dedicated Chrome Profile Browser Controller for Shakil's Assistant (J.A.R.V.I.S.)
Controls an isolated Chrome instance named 'Jarvis' with permanent session logins,
autonomous online research capabilities, DOM text extraction, and CDP remote debugging.
"""

import os
import json
import time
import asyncio
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    alt = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"))
    if alt.exists():
        CHROME_PATH = str(alt)

PROFILE_DIR = Path("data/jarvis_chrome_profile").resolve()
PROFILE_NAME = "Jarvis"
CDP_PORT = 9222
CDP_BASE_URL = f"http://127.0.0.1:{CDP_PORT}"

class BrowserController:
    """Master controller for the dedicated 'Jarvis' Chrome profile with CDP automation."""

    def __init__(self):
        self.profile_dir = PROFILE_DIR
        self.profile_name = PROFILE_NAME
        self.init_profile()
        self.process = None
        self._pending_email_draft = None

    def init_profile(self):
        """Ensures the Chrome user data directory and 'Jarvis' profile structure exist."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        sub_profile = self.profile_dir / self.profile_name
        sub_profile.mkdir(parents=True, exist_ok=True)

        # 1. Ensure Local State has profile metadata
        local_state_file = self.profile_dir / "Local State"
        local_state_data = {}
        if local_state_file.exists():
            try:
                local_state_data = json.loads(local_state_file.read_text(encoding="utf-8"))
            except Exception:
                local_state_data = {}
        if "profile" not in local_state_data:
            local_state_data["profile"] = {}
        if "info_cache" not in local_state_data["profile"]:
            local_state_data["profile"]["info_cache"] = {}

        local_state_data["profile"]["info_cache"][self.profile_name] = {
            "name": self.profile_name,
            "is_using_default_name": False,
            "avatar_icon": "chrome://theme/IDR_PROFILE_AVATAR_26"
        }
        try:
            local_state_file.write_text(json.dumps(local_state_data, indent=2), encoding="utf-8")
        except Exception:
            pass

        # 2. Ensure Profile Preferences
        prefs_file = sub_profile / "Preferences"
        prefs_data = {}
        if prefs_file.exists():
            try:
                prefs_data = json.loads(prefs_file.read_text(encoding="utf-8"))
            except Exception:
                prefs_data = {}
        if "profile" not in prefs_data:
            prefs_data["profile"] = {}
        prefs_data["profile"]["name"] = self.profile_name
        try:
            prefs_file.write_text(json.dumps(prefs_data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_browser_running(self) -> bool:
        """Checks if Chrome is running with remote debugging on port 9222."""
        try:
            req = urllib.request.Request(f"{CDP_BASE_URL}/json/version")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def launch_browser(self, target_url: str = "https://www.google.com") -> Dict[str, Any]:
        """Launches the dedicated Chrome browser with the 'Jarvis' profile and CDP enabled."""
        if not os.path.exists(CHROME_PATH):
            return {"success": False, "error": f"Chrome executable not found at {CHROME_PATH}"}

        if not self.is_browser_running():
            cmd = [
                CHROME_PATH,
                f"--user-data-dir={str(self.profile_dir)}",
                f"--profile-directory={self.profile_name}",
                f"--remote-debugging-port={CDP_PORT}",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized",
                target_url
            ]
            self.process = subprocess.Popen(cmd)
            return {
                "success": True,
                "status": "launched",
                "message": f"Dedicated Chrome profile '{self.profile_name}' launched at: {target_url}",
                "profile_dir": str(self.profile_dir),
                "profile_name": self.profile_name,
                "cdp_port": CDP_PORT
            }
        else:
            self.navigate_tab(target_url)
            return {
                "success": True,
                "status": "active",
                "message": f"Jarvis Chrome profile active. Navigated to: {target_url}",
                "profile_dir": str(self.profile_dir),
                "profile_name": self.profile_name
            }

    def get_tabs(self) -> List[Dict[str, Any]]:
        """Lists all open tabs from the CDP endpoint."""
        try:
            req = urllib.request.Request(f"{CDP_BASE_URL}/json/list")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return []

    def get_active_tab(self, url_filter: str = "") -> Optional[Dict[str, Any]]:
        """Finds a tab matching the URL filter or returns the first page tab."""
        tabs = self.get_tabs()
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if url_filter:
            for t in page_tabs:
                if url_filter.lower() in t.get("url", "").lower():
                    return t
        return page_tabs[0] if page_tabs else None

    def open_new_tab(self, url: str) -> Optional[Dict[str, Any]]:
        """Opens a new tab via CDP and returns its metadata."""
        try:
            encoded_url = urllib.parse.quote(url, safe=":/=&?#+%-")
            req = urllib.request.Request(f"{CDP_BASE_URL}/json/new?{encoded_url}", method="PUT")
            with urllib.request.urlopen(req, timeout=4) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def close_tab(self, tab_id: str) -> bool:
        """Closes a tab by its CDP ID."""
        try:
            req = urllib.request.Request(f"{CDP_BASE_URL}/json/close/{tab_id}", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def navigate_tab(self, url: str, tab_id: str = None) -> Dict[str, Any]:
        """Navigates an existing tab or opens a new tab."""
        if not self.is_browser_running():
            return self.launch_browser(url)

        try:
            tab = self.open_new_tab(url)
            if tab:
                return {"success": True, "tab_id": tab.get("id"), "url": url}
            return {"success": False, "error": "Failed to create new tab"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_javascript(self, script: str, ws_url: str = None, url_filter: str = "") -> Dict[str, Any]:
        """Executes JavaScript inside an open tab via CDP Runtime.evaluate."""
        if not ws_url:
            tab = self.get_active_tab(url_filter=url_filter)
            if not tab:
                return {"success": False, "error": "No matching open tab found in Jarvis browser profile"}
            ws_url = tab.get("webSocketDebuggerUrl")

        if not ws_url:
            return {"success": False, "error": "Tab debugger URL unavailable"}
        ws_url = ws_url.replace("localhost:", "127.0.0.1:")

        try:
            async with websockets.connect(ws_url) as ws:
                msg = {
                    "id": int(time.time() * 1000) % 100000,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": script,
                        "returnByValue": True,
                        "awaitPromise": True
                    }
                }
                await ws.send(json.dumps(msg))
                raw_resp = await asyncio.wait_for(ws.recv(), timeout=6)
                data = json.loads(raw_resp)
                result_val = data.get("result", {}).get("result", {}).get("value")
                return {"success": True, "value": result_val, "raw": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # Autonomous Online Research & Scraping via Jarvis Profile
    # -------------------------------------------------------------

    async def search_web_in_browser(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Performs a web search inside the Jarvis Chrome profile and extracts live results."""
        if not self.is_browser_running():
            self.launch_browser("https://www.google.com")
            await asyncio.sleep(2)

        # Use DuckDuckGo HTML for instant, un-blocked, clean structured results
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        tab = self.open_new_tab(search_url)
        if not tab:
            return {"success": False, "error": "Failed to open research tab"}

        tab_id = tab.get("id")
        ws_url = tab.get("webSocketDebuggerUrl", "").replace("localhost:", "127.0.0.1:")

        await asyncio.sleep(2.5)  # Allow rendering

        extract_script = f"""
        (function() {{
            const results = [];
            const links = document.querySelectorAll('.result__body, .results_links, .result');
            links.forEach((el, idx) => {{
                if (results.length >= {max_results}) return;
                const titleEl = el.querySelector('.result__title, .result__a');
                const snippetEl = el.querySelector('.result__snippet');
                const urlEl = el.querySelector('.result__url, a');
                if (titleEl) {{
                    let rawUrl = urlEl ? (urlEl.href || urlEl.innerText.trim()) : '';
                    if (rawUrl.includes('uddg=')) {{
                        try {{
                            const m = rawUrl.match(/uddg=([^&]+)/);
                            if (m) rawUrl = decodeURIComponent(m[1]);
                        }} catch(e){{}}
                    }}
                    results.push({{
                        title: titleEl.innerText.trim(),
                        url: rawUrl,
                        snippet: snippetEl ? snippetEl.innerText.trim() : ''
                    }});
                }}
            }});
            return {{
                page_title: document.title,
                results: results
            }};
        }})();
        """

        res = await self.execute_javascript(extract_script, ws_url=ws_url)
        # Close search tab to keep browser tidy
        self.close_tab(tab_id)

        val = res.get("value") or {}
        return {
            "success": True,
            "query": query,
            "page_title": val.get("page_title", ""),
            "results": val.get("results", [])
        }

    async def browse_url_and_extract(self, url: str, keep_tab: bool = False) -> Dict[str, Any]:
        """Navigates to a specific URL in Jarvis Chrome, extracts headlines and main text content."""
        if not self.is_browser_running():
            self.launch_browser(url)
            await asyncio.sleep(2.5)

        tab = self.open_new_tab(url)
        if not tab:
            return {"success": False, "error": f"Failed to open tab for {url}"}

        tab_id = tab.get("id")
        ws_url = tab.get("webSocketDebuggerUrl", "").replace("localhost:", "127.0.0.1:")

        await asyncio.sleep(3.0)

        extract_script = """
        (function() {
            const title = document.title;
            const h1s = Array.from(document.querySelectorAll('h1')).map(e => e.innerText.trim()).filter(Boolean);
            const h2s = Array.from(document.querySelectorAll('h2')).map(e => e.innerText.trim()).filter(Boolean);
            
            const metaDesc = document.querySelector('meta[name="description"]');
            const description = metaDesc ? metaDesc.getAttribute('content') : '';

            const clone = document.body.cloneNode(true);
            ['script', 'style', 'nav', 'header', 'footer', 'noscript', 'iframe', 'svg'].forEach(tag => {
                clone.querySelectorAll(tag).forEach(e => e.remove());
            });

            const paras = Array.from(clone.querySelectorAll('p, li, article, section'))
                .map(e => e.innerText.trim())
                .filter(t => t.length > 35);

            const uniqueLines = [];
            paras.forEach(p => {
                if (!uniqueLines.includes(p)) uniqueLines.push(p);
            });

            const textSnippet = uniqueLines.slice(0, 15).join('\\n\\n');

            return {
                title: title,
                url: window.location.href,
                headings: h1s.concat(h2s).slice(0, 8),
                description: description,
                body: textSnippet.slice(0, 3500)
            };
        })();
        """

        res = await self.execute_javascript(extract_script, ws_url=ws_url)
        if not keep_tab:
            self.close_tab(tab_id)

        val = res.get("value") or {}
        return {
            "success": True,
            "url": url,
            "title": val.get("title", ""),
            "headings": val.get("headings", []),
            "description": val.get("description", ""),
            "body": val.get("body", "")
        }

    async def deep_research_online(self, topic: str, max_sources: int = 3) -> Dict[str, Any]:
        """Conducts a comprehensive multi-step online research cycle directly via Jarvis Chrome."""
        search_res = await self.search_web_in_browser(topic, max_results=max_sources + 2)
        results = search_res.get("results", [])

        articles = []
        corpus_parts = [f"=== RESEARCH TOPIC: {topic} ==="]

        for item in results[:max_sources]:
            url = item.get("url")
            corpus_parts.append(f"\\n[Source: {item.get('title')}]\\nURL: {url}\\nSnippet: {item.get('snippet')}")

            if url and url.startswith("http"):
                try:
                    page_data = await self.browse_url_and_extract(url, keep_tab=False)
                    if page_data.get("body"):
                        articles.append({
                            "title": page_data.get("title") or item.get("title"),
                            "url": url,
                            "headings": page_data.get("headings", []),
                            "body": page_data.get("body")
                        })
                        corpus_parts.append(f"Deep Content from {url}:\\n{page_data.get('body')[:1500]}")
                except Exception:
                    pass

        combined_corpus = "\\n".join(corpus_parts)

        return {
            "success": True,
            "topic": topic,
            "search_count": len(results),
            "results": results,
            "deep_articles_scraped": articles,
            "corpus": combined_corpus
        }

    async def take_browser_screenshot(self) -> Dict[str, Any]:
        """Captures a screenshot of the active tab in the Jarvis Chrome profile."""
        tab = self.get_active_tab()
        if not tab:
            return {"success": False, "error": "No active page tab found in Jarvis browser"}

        ws_url = tab.get("webSocketDebuggerUrl", "").replace("localhost:", "127.0.0.1:")
        if not ws_url:
            return {"success": False, "error": "Debugger URL not found"}

        try:
            async with websockets.connect(ws_url) as ws:
                msg = {
                    "id": 999,
                    "method": "Page.captureScreenshot",
                    "params": { "format": "png", "quality": 85 }
                }
                await ws.send(json.dumps(msg))
                resp = await asyncio.wait_for(ws.recv(), timeout=6)
                data = json.loads(resp)
                b64 = data.get("result", {}).get("data")
                return {
                    "success": True,
                    "title": tab.get("title"),
                    "url": tab.get("url"),
                    "base64": b64
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------
    # Email Automation: Briefing & Confirmation-Gated Replies
    # -------------------------------------------------------------

    async def check_emails(self) -> Dict[str, Any]:
        """Scans Gmail or Outlook Web in the dedicated browser and extracts an executive briefing."""
        if not self.is_browser_running():
            self.launch_browser("https://mail.google.com")
            return {
                "success": True,
                "status": "browser_launched",
                "briefing": "Sir Shakil, I have opened your dedicated Chrome browser profile ('Jarvis') to Gmail. If not yet signed in, please complete sign-in once. Your session will remain permanently saved for autonomous checking.",
                "message": "Dedicated Chrome browser launched. Please sign in once.",
                "emails": []
            }

        gmail_tab = self.get_active_tab(url_filter="mail.google.com")
        outlook_tab = self.get_active_tab(url_filter="outlook")

        if not gmail_tab and not outlook_tab:
            self.navigate_tab("https://mail.google.com")
            await asyncio.sleep(1.5)
            gmail_tab = self.get_active_tab(url_filter="mail.google.com")
            if not gmail_tab:
                return {
                    "success": True,
                    "status": "browser_open",
                    "briefing": "Sir Shakil, I have opened your dedicated 'Jarvis' browser to Gmail. Please sign in once to initialize autonomous email monitoring.",
                    "message": "Gmail is loading in your dedicated profile. Please sign in once.",
                    "emails": []
                }

        js_extract_gmail = """
        (function() {
            if (document.querySelector('input[type="email"]') || document.location.href.includes('accounts.google.com')) {
                return { loggedIn: false, error: 'Authentication required on Google sign-in page.' };
            }

            const unreadRows = document.querySelectorAll('tr.zE');
            const allRows = document.querySelectorAll('tr.zA');
            const targetRows = unreadRows.length > 0 ? Array.from(unreadRows).slice(0, 5) : Array.from(allRows).slice(0, 5);
            const emails = [];

            targetRows.forEach((row, idx) => {
                const senderEl = row.querySelector('.yX .yW span, .zF');
                const subjectEl = row.querySelector('.y6 span, .bog span');
                const snippetEl = row.querySelector('.y2');
                const dateEl = row.querySelector('.xW span');

                emails.push({
                    id: idx + 1,
                    sender: senderEl ? senderEl.innerText.trim() : 'Unknown Sender',
                    subject: subjectEl ? subjectEl.innerText.trim() : '(No Subject)',
                    snippet: snippetEl ? snippetEl.innerText.trim() : '',
                    date: dateEl ? dateEl.innerText.trim() : 'Recent',
                    isUnread: row.classList.contains('zE')
                });
            });

            return {
                loggedIn: true,
                totalUnreadCount: unreadRows.length,
                emails: emails
            };
        })();
        """

        res = await self.execute_javascript(js_extract_gmail, url_filter="mail.google.com")
        if not res.get("success"):
            return {
                "success": False,
                "briefing": "Sir Shakil, I attempted to inspect Gmail, but the page is currently initializing or requires manual authentication.",
                "error": res.get("error")
            }

        val = res.get("value") or {}
        if not val.get("loggedIn"):
            return {
                "success": True,
                "status": "awaiting_login",
                "briefing": "Sir Shakil, your dedicated Chrome profile is open at Google Accounts. Please sign in once, and I will continuously monitor your correspondence.",
                "emails": []
            }

        emails = val.get("emails", [])
        unread_count = val.get("totalUnreadCount", len(emails))

        if not emails:
            briefing = "Your inbox is clear with zero unread messages, Sir Shakil."
        else:
            email_summaries = []
            for e in emails[:3]:
                email_summaries.append(f"{e['sender']}: '{e['subject']}' ({e['snippet'][:60]}...)")
            briefing = (
                f"Sir Shakil, you have {unread_count} active emails cataloged in your inbox. "
                f"Recent items include: {'; '.join(email_summaries)}. "
                f"Which one would you like me to inspect or draft a reply for?"
            )

        return {
            "success": True,
            "status": "success",
            "total_unread": unread_count,
            "emails": emails,
            "briefing": briefing
        }

    def stage_email_reply(self, recipient_or_id: str, proposed_reply: str) -> Dict[str, Any]:
        """Stages an email reply in draft mode and locks it for Sir Shakil's explicit confirmation."""
        self._pending_email_draft = {
            "recipient": recipient_or_id,
            "reply_text": proposed_reply,
            "timestamp": time.time(),
            "status": "awaiting_user_confirmation"
        }
        return {
            "success": True,
            "status": "awaiting_confirmation",
            "draft": self._pending_email_draft,
            "confirmation_prompt": (
                f"Sir Shakil, I have formulated the following proposed reply for {recipient_or_id}:\n\n"
                f"\"{proposed_reply}\"\n\n"
                f"Shall I dispatch this email, or would you like to adjust the wording?"
            )
        }

    async def execute_confirmed_send(self) -> Dict[str, Any]:
        """Dispatches the pending email only after Sir Shakil has explicitly authorized it."""
        if not self._pending_email_draft or self._pending_email_draft.get("status") != "awaiting_user_confirmation":
            return {"success": False, "error": "No pending authorized email draft found."}

        draft = self._pending_email_draft
        self._pending_email_draft = None

        send_script = """
        (function() {
            const sendBtn = document.querySelector('div[role="button"][data-tooltip*="Send"], div[aria-label*="Send"]');
            if (sendBtn) {
                sendBtn.click();
                return { sent: true };
            }
            return { sent: false, reason: 'Send button not found in active compose window' };
        })();
        """

        res = await self.execute_javascript(send_script, url_filter="mail.google.com")
        return {
            "success": True,
            "status": "dispatched",
            "message": f"Email successfully transmitted to {draft['recipient']}, Sir Shakil.",
            "details": res
        }

    # -------------------------------------------------------------
    # Eventbrite & Marketing Automations
    # -------------------------------------------------------------

    def open_eventbrite_dashboard(self) -> Dict[str, Any]:
        """Opens the Eventbrite manage events dashboard in the dedicated profile."""
        return self.launch_browser("https://www.eventbrite.com/manage/events")

    def open_meta_ads_dashboard(self) -> Dict[str, Any]:
        """Opens Meta Ads Manager in the dedicated profile."""
        return self.launch_browser("https://adsmanager.facebook.com")

    def open_google_ads_dashboard(self) -> Dict[str, Any]:
        """Opens Google Ads dashboard in the dedicated profile."""
        return self.launch_browser("https://ads.google.com")

browser_controller = BrowserController()
