"""re:Invent Keynote Note-Taker — Strands Agent that researches AWS announcements from Bee transcripts."""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.tools.mcp import MCPClient

MCP_TOOL_DELAY = 2  # seconds to wait between MCP tool calls to avoid 429s


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_MCP_TOOLS = [
    "aws___search_documentation",
    "aws___read_documentation",
    "aws___get_regional_availability",
    "aws___recommend",
]

BEE_CLI_TIMEOUT = 30  # seconds

OUTPUT_DIR = "keynote-notes"

FILENAME_MAX_LABEL_LENGTH = 50

SYSTEM_PROMPT = """\
You are an expert AWS solutions architect and technical writer who specializes in \
covering AWS re:Invent keynotes. You have deep knowledge of AWS services and can \
quickly identify new service launches and feature announcements from keynote transcripts.

Your task: process a keynote transcript captured by a Bee wearable device, research \
every AWS announcement using official documentation, and compile structured markdown notes.

<rules>
- Only include URLs that are returned by the AWS Knowledge MCP tools. Never invent or guess URLs.
- If a tool returns no results for an announcement, say "Documentation may not yet be published." Do not fabricate links.
- When identifying announcements, think through each one carefully before researching. Two mentions of the same service count as one announcement.
- Skip transcript noise: applause, audience chatter, filler speech, off-topic discussion.
- Identify the primary keynote presenter by speaker label frequency and prioritize their utterances.
- If the transcript spans multiple Bee conversations, treat them as one session ordered by start_time.
- Transcription correction: "Curo" in the transcript refers to "Kiro" (Amazon's AI-native IDE). \
The Bee device mishears the name. Always use "Kiro" in the output.
- The keynote was delivered at AWS re:Invent 2025. Do not guess the year or date — use 2025.
</rules>

<workflow>
Follow these steps in order:

STEP 1 — RETRIEVE TRANSCRIPT
Call `get_keynote_transcript` to fetch the last 10 hours of Bee conversations as JSON.
If the result is empty or an error, stop and report the issue.

STEP 2 — IDENTIFY ANNOUNCEMENTS
Before researching anything, analyze the full transcript and list every distinct AWS \
announcement you find. For each one, extract:
- Name (service or feature)
- 1–3 sentence description from transcript context
- Timestamp of first mention

Think through this carefully in a <thinking> block. Consider: Is this a genuinely new \
announcement or just a reference to an existing service? Are two mentions actually the \
same thing? Only proceed to research once you have a complete list.

STEP 3 — CHECK FLAGGED MOMENTS
Call `get_flagged_moments` to retrieve the user's todos and bookmarked conversations.

The user flags moments in two ways:
- **During the keynote (silent)**: Button press on the Bee device creates a bookmark. \
This gives you a timestamp but no text — infer what caught their attention from the \
transcript context around that moment (2 min before to 1 min after).
- **After the keynote (with context)**: The user adds todos with ⭐ or "interesting" \
to describe what they want to deep-dive on. These carry explicit intent about what \
the user cares about.

Match flagged moments to announcements using:
- Timestamp proximity: announcement timestamp within 2 minutes of a bookmark
- Semantic matching: announcement name matches todo text containing ⭐ or "interesting"

When both a bookmark and a todo exist for the same moment, prefer the todo text as \
the "why you flagged this" since it carries the user's explicit intent.

STEP 4 — RESEARCH EACH ANNOUNCEMENT
IMPORTANT: The AWS Knowledge MCP server has strict rate limits. You MUST research \
announcements ONE AT A TIME — complete all tool calls for one announcement before \
moving to the next. NEVER call multiple MCP tools in parallel. Wait for each tool \
call to return before making the next one.

For each announcement (sequentially), call these tools:
- `aws___search_documentation` — search for docs, What's New posts, blog posts
- `aws___read_documentation` — read up to 3 top results from the search
- `aws___get_regional_availability` — check which regions support it
- `aws___recommend` — find related content and getting started guides

For FLAGGED announcements, do additional deep-dive research:
- Run 3+ additional `aws___search_documentation` queries (one at a time) covering \
related services, architectural guidance, and tutorials
- If a todo flag exists, use the todo text as a search term
- If flagged via bookmark only, use the surrounding transcript context as search terms

STEP 5 — COMPILE AND SAVE
Assemble the research into markdown and call `save_notes` with:
- filename: `YYYY-MM-DD-<label>.md` (today's date, label from keynote topic, lowercase \
alphanumeric + hyphens, max 50 chars, default "keynote")
- content: the full markdown
</workflow>

<output_format>
Structure the markdown file exactly like this:

```markdown
# [Keynote Title] — [Date]

## Summary
[2–4 sentences: keynote topic, presenter name, key themes covered]

## Announcements

### [Service/Feature Name]
[1–3 sentence summary from transcript]

- **Documentation**: [link from search results]
- **What's New / Blog**: [link from search results]
- **Regional Availability**: [regions from get_regional_availability]
- **Getting Started**: [link from recommend results]

## ⭐ Flagged Moments

### [Flagged Service/Feature Name]
[1–3 sentence summary]

**Why you flagged this**: [if todo exists: the todo text | if bookmark only: \
"You bookmarked during a discussion about [topic inferred from surrounding transcript]"]

- **Documentation**: [link]
- **What's New / Blog**: [link]
- **Regional Availability**: [regions]
- **Getting Started**: [link]
- **Related Services**: [links from deep-dive research]
- **Architectural Guidance**: [links from deep-dive research]
- **Tutorials**: [links from deep-dive research]

## Reading List

### Priority (Flagged)
1. [url] — [description]

### All Announcements
1. [url] — [description]
```

For announcements where no documentation was found, include the name and transcript \
summary but replace the links section with: "Documentation may not yet be published."

The reading list should place flagged items first, then remaining announcements in \
keynote chronological order.
</output_format>

<error_handling>
- Zero announcements found: inform the user and stop
- Tool returns no results for one announcement: include it with "docs not yet published" note, continue with others
- Tool call fails for one announcement: keep successful results, note the failure, continue
- If the transcript is very large, use conversation summaries first to identify relevant \
conversations, then fetch full details only for those
</error_handling>
"""


# ---------------------------------------------------------------------------
# Helper functions (pure logic, extracted for testability)
# ---------------------------------------------------------------------------


def _parse_timestamp(ts) -> datetime | None:
    """Convert a Bee timestamp to a datetime object.

    Bee uses epoch milliseconds (int/float) for most fields, but some contexts
    may provide ISO 8601 strings. Returns None if the value can't be parsed.
    """
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    if isinstance(ts, str) and ts:
        try:
            # Try epoch millis encoded as a string
            return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def parse_bee_conversations(json_str: str) -> list[dict]:
    """Parse Bee JSON and extract conversation objects.

    Each conversation retains: id, start_time, end_time, state, summary,
    and nested utterances with speaker and text.
    """
    data = json.loads(json_str)

    # Handle both top-level list and object-with-conversations-key formats
    if isinstance(data, list):
        raw_conversations = data
    elif isinstance(data, dict):
        raw_conversations = data.get("conversations", data.get("data", []))
    else:
        return []

    conversations: list[dict] = []
    for conv in raw_conversations:
        utterances: list[dict] = []
        for transcription in conv.get("transcriptions", []):
            for utt in transcription.get("utterances", []):
                utterances.append(
                    {
                        "speaker": utt.get("speaker", ""),
                        "text": utt.get("text", ""),
                    }
                )

        conversations.append(
            {
                "id": conv.get("id"),
                "start_time": conv.get("start_time", ""),
                "end_time": conv.get("end_time", ""),
                "state": conv.get("state", ""),
                "summary": conv.get("short_summary", conv.get("summary", "")),
                "utterances": utterances,
            }
        )

    return conversations



def format_subprocess_error(exit_code: int, stderr: str) -> str:
    """Format an error message containing both the exit code and stderr content."""
    return f"Command failed with exit code {exit_code}: {stderr}"


def filter_todo_flags(todos: list[dict]) -> list[dict]:
    """Filter todos whose text contains ⭐ or 'interesting' (case-insensitive)."""
    flagged: list[dict] = []
    for todo in todos:
        text = todo.get("text", "")
        if "⭐" in text or "interesting" in text.lower():
            flagged.append(todo)
    return flagged


def deduplicate_flagged_moments(
    todo_flags: list[dict], bookmarks: list[dict]
) -> list[dict]:
    """Combine Todo_Flags and Bookmarks, deduplicating by conversation reference.

    Each item is expected to have a 'conversation_id' key (or 'id' for bookmarks).
    If a todo_flag references the same conversation as a bookmark, only one entry
    is kept (the todo_flag is preferred since it carries user context).
    """
    seen_conversation_ids: set = set()
    result: list[dict] = []

    # Process todo flags first (they carry user context)
    for flag in todo_flags:
        conv_id = flag.get("conversation_id")
        if conv_id is not None and conv_id not in seen_conversation_ids:
            seen_conversation_ids.add(conv_id)
            result.append(flag)
        elif conv_id is None:
            # Todos without a conversation reference are always included
            result.append(flag)

    # Then add bookmarks that don't overlap
    for bookmark in bookmarks:
        conv_id = bookmark.get("conversation_id", bookmark.get("id"))
        if conv_id is not None and conv_id not in seen_conversation_ids:
            seen_conversation_ids.add(conv_id)
            result.append(bookmark)
        elif conv_id is None:
            result.append(bookmark)

    return result


def is_within_proximity(
    ts1, ts2, window_seconds: int = 120
) -> bool:
    """Check if two timestamps are within the given window (seconds).

    Accepts epoch milliseconds (int/float/str) or ISO 8601 strings.
    """
    dt1 = _parse_timestamp(ts1)
    dt2 = _parse_timestamp(ts2)
    if dt1 is None or dt2 is None:
        return False
    return abs((dt1 - dt2).total_seconds()) <= window_seconds



def extract_bookmark_context(
    conversations: list[dict], bookmark_ts
) -> list[dict]:
    """Return utterances from conversations near the bookmark timestamp.

    Since Bee utterances don't carry individual timestamps, this uses the
    conversation start_time to find conversations within 2 min before to
    1 min after the bookmark, then returns all utterances from those
    conversations.
    """
    bookmark_dt = _parse_timestamp(bookmark_ts)
    if bookmark_dt is None:
        return []
    result: list[dict] = []
    for conv in conversations:
        conv_dt = _parse_timestamp(conv.get("start_time", ""))
        if conv_dt is None:
            continue
        diff = (conv_dt - bookmark_dt).total_seconds()
        # Conversations starting 2 min before to 1 min after the bookmark
        if -120 <= diff <= 60:
            result.extend(conv.get("utterances", []))
    return result


def generate_filename(date_str: str, title: str) -> str:
    """Produce a filename matching YYYY-MM-DD-<label>.md.

    The label is derived from the title: lowercased, non-alphanumeric characters
    replaced with hyphens, consecutive hyphens collapsed, leading/trailing hyphens
    stripped, and truncated to 50 characters. Defaults to 'keynote' if the label
    is empty after processing.
    """
    # Normalise title to a safe label
    label = title.lower()
    label = re.sub(r"[^a-z0-9]+", "-", label)
    label = label.strip("-")
    # Truncate to max length, but don't cut in the middle of a word-boundary hyphen
    if len(label) > FILENAME_MAX_LABEL_LENGTH:
        label = label[:FILENAME_MAX_LABEL_LENGTH].rstrip("-")
    label = label or "keynote"
    return f"{date_str}-{label}.md"


def validate_mcp_tools(
    discovered_tools: list[str], required: list[str]
) -> tuple[bool, list[str]]:
    """Check that all required MCP tools are present in the discovered set.

    Returns (ok, missing) where ok is True when all required tools are found.
    """
    discovered_set = set(discovered_tools)
    missing = [t for t in required if t not in discovered_set]
    return (len(missing) == 0, missing)


def check_auth_status(status_output: str) -> bool:
    """Return True iff the bee status output contains 'Verified as'."""
    return "Verified as" in status_output


def order_conversations_chronologically(
    conversations: list[dict],
) -> list[dict]:
    """Sort conversations by start_time ascending."""
    return sorted(conversations, key=lambda c: c.get("start_time", ""))


def is_valid_url(url: str) -> bool:
    """Validate that a URL conforms to RFC 3986 syntax.

    Checks for presence of scheme and network location (authority).
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme) and bool(parsed.netloc)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Markdown compilation helpers
#
# These are not called at runtime — the model writes markdown directly and
# passes it to save_notes. They exist as reference implementations and are
# covered by the test suite.
# ---------------------------------------------------------------------------


def compile_announcement_entry(announcement: dict) -> str:
    """Format a single announcement as a markdown section.

    Expected keys in *announcement*:
      - name (str): service/feature name
      - summary (str): 1-3 sentence description
      - is_flagged (bool): whether this is a flagged moment
      - flag_context (str, optional): todo text or bookmark context
      - doc_links (list[str]): documentation URLs
      - blog_links (list[str]): What's New / blog URLs
      - regional_availability (str): region info
      - getting_started (str): getting started URL
      - related_services (list[str]): related service links (flagged only)
      - architectural_guidance (list[str]): guidance links (flagged only)
      - tutorials (list[str]): tutorial links (flagged only)
      - no_docs_available (bool): True when no research results exist
    """
    name = announcement.get("name", "Unknown Announcement")
    summary = announcement.get("summary", "")
    is_flagged = announcement.get("is_flagged", False)
    no_docs = announcement.get("no_docs_available", False)

    lines: list[str] = [f"### {name}", ""]
    if summary:
        lines.append(summary)
        lines.append("")

    if no_docs:
        lines.append("Documentation may not yet be published.")
        lines.append("")
        return "\n".join(lines)

    # Standard fields
    doc_links = announcement.get("doc_links", [])
    blog_links = announcement.get("blog_links", [])
    regional = announcement.get("regional_availability", "")
    getting_started = announcement.get("getting_started", "")

    if doc_links:
        lines.append(f"- **Documentation**: {', '.join(doc_links)}")
    if blog_links:
        lines.append(f"- **What's New / Blog**: {', '.join(blog_links)}")
    if regional:
        lines.append(f"- **Regional Availability**: {regional}")
    if getting_started:
        lines.append(f"- **Getting Started**: {getting_started}")

    # Flagged-only deep-dive fields
    if is_flagged:
        flag_context = announcement.get("flag_context", "")
        if flag_context:
            lines.append(f"- **Why you flagged this**: {flag_context}")

        related = announcement.get("related_services", [])
        guidance = announcement.get("architectural_guidance", [])
        tutorials = announcement.get("tutorials", [])
        if related:
            lines.append(f"- **Related Services**: {', '.join(related)}")
        if guidance:
            lines.append(f"- **Architectural Guidance**: {', '.join(guidance)}")
        if tutorials:
            lines.append(f"- **Tutorials**: {', '.join(tutorials)}")

    lines.append("")
    return "\n".join(lines)


def compile_reading_list(
    flagged_links: list[dict], unflagged_links: list[dict]
) -> str:
    """Compile the reading list section with flagged items first.

    Each link dict has:
      - url (str)
      - description (str)
      - keynote_order (int): position in keynote chronological order

    Within each group (flagged / unflagged), items are sorted by keynote_order.
    """
    sorted_flagged = sorted(flagged_links, key=lambda x: x.get("keynote_order", 0))
    sorted_unflagged = sorted(unflagged_links, key=lambda x: x.get("keynote_order", 0))

    lines: list[str] = ["## Reading List", ""]

    if sorted_flagged:
        lines.append("### Priority (Flagged)")
        for i, link in enumerate(sorted_flagged, 1):
            lines.append(f"{i}. {link.get('url', '')} — {link.get('description', '')}")
        lines.append("")

    if sorted_unflagged:
        lines.append("### All Announcements")
        for i, link in enumerate(sorted_unflagged, 1):
            lines.append(f"{i}. {link.get('url', '')} — {link.get('description', '')}")
        lines.append("")

    return "\n".join(lines)


def compile_markdown_notes(
    summary: str,
    announcements: list[dict],
    flagged_moments: list[dict],
    reading_list_flagged: list[dict],
    reading_list_unflagged: list[dict],
) -> str:
    """Assemble the full markdown notes with all required sections in order.

    Sections: Summary, Announcements, Flagged Moments, Reading List.
    """
    sections: list[str] = []

    # Summary
    sections.append("## Summary")
    sections.append("")
    sections.append(summary)
    sections.append("")

    # Announcements (non-flagged)
    sections.append("## Announcements")
    sections.append("")
    for ann in announcements:
        sections.append(compile_announcement_entry(ann))

    # Flagged Moments
    sections.append("## ⭐ Flagged Moments")
    sections.append("")
    for fm in flagged_moments:
        sections.append(compile_announcement_entry(fm))

    # Reading List
    sections.append(compile_reading_list(reading_list_flagged, reading_list_unflagged))

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Prerequisite validation (called before agent initialization)
# ---------------------------------------------------------------------------


def validate_bee_cli() -> None:
    """Verify bee CLI is installed and authenticated. Raises SystemExit on failure."""

    # Check that `bee` is on PATH
    try:
        subprocess.run(
            ["bee", "--version"],
            capture_output=True,
            text=True,
            timeout=BEE_CLI_TIMEOUT,
        )
    except FileNotFoundError:
        raise SystemExit(
            "Error: bee CLI not found on PATH. Install it with:\n"
            "  npm install -g @beeai/cli"
        )
    except subprocess.TimeoutExpired:
        raise SystemExit("Error: bee --version timed out.")

    # Check authentication via `bee status`
    try:
        result = subprocess.run(
            ["bee", "status"],
            capture_output=True,
            text=True,
            timeout=BEE_CLI_TIMEOUT,
        )
    except FileNotFoundError:
        raise SystemExit(
            "Error: bee CLI not found on PATH. Install it with:\n"
            "  npm install -g @beeai/cli"
        )
    except subprocess.TimeoutExpired:
        raise SystemExit("Error: bee status timed out.")

    if result.returncode != 0:
        raise SystemExit(
            f"Error: bee status failed:\n{result.stderr}"
        )

    if not check_auth_status(result.stdout):
        raise SystemExit(
            "Error: Bee CLI is not authenticated. Log in with:\n"
            "  bee login"
        )


# ---------------------------------------------------------------------------
# Bee CLI Tools (@tool decorated)
# ---------------------------------------------------------------------------


@tool
def get_keynote_transcript() -> str:
    """Get the last 10 hours of Bee conversations with full utterances as JSON.

    Returns the complete transcript including speaker identification,
    timestamps, and utterance text.
    """
    try:
        result = subprocess.run(
            ["bee", "now", "--json"],
            capture_output=True,
            text=True,
            timeout=BEE_CLI_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return "Error: bee now --json timed out after 30 seconds."
    except FileNotFoundError:
        return "Error: bee CLI not found on PATH. Install it with: npm install -g @beeai/cli"

    if result.returncode != 0:
        return format_subprocess_error(result.returncode, result.stderr)

    stdout = result.stdout.strip()
    if not stdout:
        return "No transcript data available: bee now --json returned empty output."

    # Validate structure via parse_bee_conversations
    conversations = parse_bee_conversations(stdout)
    if not conversations:
        return "No usable transcript data available: response contained zero conversations."

    total_utterances = sum(len(c.get("utterances", [])) for c in conversations)
    if total_utterances == 0:
        return "No usable transcript data available: all conversations contain zero utterances."

    return stdout


@tool
def get_flagged_moments() -> str:
    """Get flagged moments from Bee — checks todos and bookmarked conversations.

    Returns JSON with 'todos' and 'conversations' keys. The agent should
    filter todos for ⭐ emoji or 'interesting' text, and check conversations
    for bookmark indicators.
    """
    todos_error: str | None = None
    conversations_error: str | None = None
    all_todos: list[dict] = []
    conversations: list[dict] = []

    # --- Fetch todos with pagination ---
    try:
        cursor: str | None = None
        while True:
            cmd = ["bee", "todos", "list", "--json"]
            if cursor:
                cmd.extend(["--cursor", cursor])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=BEE_CLI_TIMEOUT,
            )
            if result.returncode != 0:
                todos_error = format_subprocess_error(
                    result.returncode, result.stderr
                )
                break
            page = json.loads(result.stdout)
            all_todos.extend(page.get("todos", []))
            cursor = page.get("next_cursor")
            if not cursor:
                break
    except subprocess.TimeoutExpired:
        todos_error = "bee todos list --json timed out."
    except FileNotFoundError:
        todos_error = "bee CLI not found on PATH."
    except json.JSONDecodeError as exc:
        todos_error = f"Failed to parse todos JSON: {exc}"

    # --- Fetch conversations ---
    try:
        result = subprocess.run(
            ["bee", "conversations", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=BEE_CLI_TIMEOUT,
        )
        if result.returncode != 0:
            conversations_error = format_subprocess_error(
                result.returncode, result.stderr
            )
        else:
            data = json.loads(result.stdout)
            conversations = data.get("conversations", [])
    except subprocess.TimeoutExpired:
        conversations_error = "bee conversations list --json timed out."
    except FileNotFoundError:
        conversations_error = "bee CLI not found on PATH."
    except json.JSONDecodeError as exc:
        conversations_error = f"Failed to parse conversations JSON: {exc}"

    # --- Handle partial failures ---
    if todos_error and conversations_error:
        return (
            f"Warning: both flagged-moment sources failed.\n"
            f"  Todos error: {todos_error}\n"
            f"  Conversations error: {conversations_error}\n"
            "Proceeding without flagged moments."
        )

    warnings: list[str] = []
    if todos_error:
        warnings.append(f"Warning: todos retrieval failed: {todos_error}")
    if conversations_error:
        warnings.append(
            f"Warning: conversations retrieval failed: {conversations_error}"
        )

    # --- Filter and deduplicate ---
    flagged_todos = filter_todo_flags(all_todos)
    combined = deduplicate_flagged_moments(flagged_todos, conversations)

    output: dict = {
        "todos": flagged_todos,
        "conversations": conversations,
        "flagged_moments": combined,
    }
    if warnings:
        output["warnings"] = warnings

    return json.dumps(output)


@tool
def save_notes(filename: str, content: str) -> str:
    """Save compiled keynote notes to a markdown file.

    Args:
        filename: Name for the markdown file (e.g. '2025-12-02-monday-keynote.md')
        content: The full markdown content to write
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return os.path.abspath(filepath)
    except OSError as e:
        return f"Error saving notes: {e}"


# ---------------------------------------------------------------------------
# AWS Knowledge MCP Client
# ---------------------------------------------------------------------------

knowledge_mcp = MCPClient(
    lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws"),
    startup_timeout=30,
)


def validate_mcp_connection(mcp_client: MCPClient) -> None:
    """Validate that the MCP client exposes all required tools.

    Must be called after entering the MCPClient context manager.
    Raises SystemExit listing missing tools if validation fails.
    """
    discovered = [t.tool_name for t in mcp_client.list_tools_sync()]
    ok, missing = validate_mcp_tools(
        discovered_tools=discovered,
        required=REQUIRED_MCP_TOOLS,
    )
    if not ok:
        raise SystemExit(
            f"Error: AWS Knowledge MCP Server is missing required tools: {', '.join(missing)}\n"
            f"Discovered tools: {', '.join(discovered) or '(none)'}"
        )


# ---------------------------------------------------------------------------
# Interactive bookmark annotation (pre-agent terminal flow)
# ---------------------------------------------------------------------------


def _fetch_transcript_json() -> str | None:
    """Fetch transcript JSON from Bee CLI. Returns raw JSON or None on failure."""
    try:
        result = subprocess.run(
            ["bee", "now", "--json"],
            capture_output=True,
            text=True,
            timeout=BEE_CLI_TIMEOUT,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _fetch_bookmarks_json() -> str | None:
    """Fetch conversations JSON from Bee CLI. Returns raw JSON or None on failure."""
    try:
        result = subprocess.run(
            ["bee", "conversations", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=BEE_CLI_TIMEOUT,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def prompt_bookmark_annotations() -> str:
    """Show bookmarked moments to the user and collect optional annotations.

    Returns a string of user annotations to include in the agent prompt,
    or empty string if no bookmarks or user skips.
    """
    # Fetch transcript
    transcript_json = _fetch_transcript_json()
    if not transcript_json:
        return ""

    conversations = parse_bee_conversations(transcript_json)
    if not conversations:
        return ""

    # Fetch bookmarked conversations
    bookmarks_json = _fetch_bookmarks_json()
    if not bookmarks_json:
        return ""

    data = json.loads(bookmarks_json)
    bookmarked = [
        c for c in data.get("conversations", [])
        if c.get("bookmarked", False)
    ]

    if not bookmarked:
        return ""

    # Show bookmarks with transcript context
    print(f"\n📌 You bookmarked {len(bookmarked)} moment(s) during the keynote:\n")

    bookmark_info: list[dict] = []
    for i, bm in enumerate(bookmarked, 1):
        ts = bm.get("start_time", bm.get("created_at", ""))
        context_utts = extract_bookmark_context(conversations, ts) if ts else []
        context_preview = " ".join(
            u.get("text", "") for u in context_utts[:3]
        )[:200]

        # Format timestamp for display
        display_ts = ts[:16].replace("T", " ") if ts else "unknown time"
        print(f"  {i}. [{display_ts}] {context_preview or '(no transcript context)'}...")

        bookmark_info.append({
            "index": i,
            "timestamp": ts,
            "context_preview": context_preview,
            "annotation": "",
        })

    print(
        "\nWant to add context for any of these? "
        "This helps the agent research what you care about."
    )
    print("Enter a number to annotate, or press Enter to skip.\n")

    while True:
        choice = input("> ").strip()
        if not choice:
            break

        try:
            idx = int(choice)
            if 1 <= idx <= len(bookmark_info):
                note = input("What interests you about this? > ").strip()
                if note:
                    bookmark_info[idx - 1]["annotation"] = note
                    print(f"  ✓ Noted for bookmark {idx}\n")
                    print("Enter another number, or press Enter to continue.")
            else:
                print(f"Please enter a number between 1 and {len(bookmark_info)}, or Enter to skip.")
        except ValueError:
            print("Enter a number or press Enter to skip.")

    # Build annotation string for the agent prompt
    annotated = [b for b in bookmark_info if b["annotation"]]
    if not annotated:
        return ""

    lines = ["The user provided additional context for these bookmarked moments:"]
    for b in annotated:
        lines.append(
            f"- Bookmark at {b['timestamp']}: \"{b['annotation']}\""
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent configuration and entry point
# ---------------------------------------------------------------------------


def _safe_close_mcp(mcp_client: MCPClient) -> None:
    """Close the MCP client, ignoring errors if the connection already dropped."""
    try:
        mcp_client.__exit__(None, None, None)
    except Exception:
        pass


def _get_after_tool_call_event():
    """Lazy import to avoid module-level import issues with pytest."""
    from strands.hooks.events import AfterToolCallEvent
    return AfterToolCallEvent


def _throttle_mcp_calls(event) -> None:
    """Hook: pause after MCP tool calls to respect rate limits."""
    tool_use = getattr(event, "tool_use", None)
    if isinstance(tool_use, dict):
        tool_name = tool_use.get("name", "")
    else:
        tool_name = getattr(tool_use, "name", "") if tool_use else ""
    if tool_name.startswith("aws___"):
        time.sleep(MCP_TOOL_DELAY)


def main() -> None:
    """Run the re:Invent Keynote Note-Taker agent."""

    # Step 1 — Validate Bee CLI prerequisites
    validate_bee_cli()

    # Step 2 — Prompt user to annotate bookmarks (interactive, pre-agent)
    user_annotations = prompt_bookmark_annotations()

    # Step 3 — Build the agent prompt
    base_prompt = "Process my latest re:Invent keynote and compile research notes."
    if user_annotations:
        agent_prompt = f"{base_prompt}\n\n{user_annotations}"
    else:
        agent_prompt = base_prompt

    # Step 4 — Start MCP client and validate tools
    # Step 5 — Create the Strands Agent
    # Step 6 — Invoke the agent
    try:
        knowledge_mcp.__enter__()
    except Exception as exc:
        raise SystemExit(
            f"Error: Failed to connect to AWS Knowledge MCP Server: {exc}"
        )

    try:
        validate_mcp_connection(knowledge_mcp)
    except SystemExit:
        _safe_close_mcp(knowledge_mcp)
        raise
    except Exception as exc:
        _safe_close_mcp(knowledge_mcp)
        raise SystemExit(
            f"Error: Failed to connect to AWS Knowledge MCP Server: {exc}"
        )

    try:
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            tools=[get_keynote_transcript, get_flagged_moments, save_notes, *knowledge_mcp.list_tools_sync()],
            system_prompt=SYSTEM_PROMPT,
        )
        agent.add_hook(_throttle_mcp_calls, event_type=_get_after_tool_call_event())

        agent(agent_prompt)
    except Exception as exc:
        raise SystemExit(
            f"Error: Failed to communicate with Amazon Bedrock: {exc}"
        )
    finally:
        _safe_close_mcp(knowledge_mcp)


if __name__ == "__main__":
    main()
