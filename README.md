# re:Invent Keynote Note-Taker

> This sample works with [Amazon Bedrock](https://aws.amazon.com/bedrock/?trk=0fc6058e-ef5a-4fc9-bc07-6efe2c3c9de4&sc_channel=el), [Strands Agents SDK](https://strandsagents.com/), and the [AWS Knowledge MCP Server](https://awslabs.github.io/mcp/).

Turn a two-hour AWS re:Invent keynote into a fully-researched set of notes with documentation links, regional availability, and a prioritized reading list — using a [Bee](https://www.bee.computer/) wearable for capture and a [Strands Agent](https://strandsagents.com/) with the [AWS Knowledge MCP Server](https://awslabs.github.io/mcp/) for research.

## How It Works

```
CAPTURE (during keynote)     RESEARCH (after keynote)       OUTPUT
┌──────────────────────┐    ┌──────────────────────────┐   ┌─────────────────────┐
│ Bee wearable records │    │ Strands Agent pulls      │   │ Markdown file with:  │
│ audio, transcribes,  │───▶│ transcript, identifies   │──▶│ • Summary            │
│ identifies speakers  │    │ announcements, researches│   │ • Announcements+links│
│                      │    │ each via AWS Knowledge   │   │ • ⭐ Flagged deep-dives│
│ Double-press to      │    │ MCP Server               │   │ • Reading list       │
│ bookmark moments     │    └──────────────────────────┘   └─────────────────────┘
└──────────────────────┘
```

During the keynote, you just listen. When something catches your attention, double-press the Bee action button to bookmark that moment. After the keynote, one command produces structured notes with links to documentation, What's New posts, blog posts, and regional availability for every announcement.

Bookmarked moments get special treatment — deeper research with related services, architectural guidance, and tutorials.

## Prerequisites

- [Bee device](https://www.bee.computer/) (Bee Pioneer)
- Bee iOS app (latest version from the App Store)
- Node.js (for Bee CLI)
- Python 3.10+
- AWS account with Bedrock model access for Claude Sonnet
- AWS credentials configured (`aws configure` or environment variables)

## Bee Device Setup

### 1. Enable Developer Mode

Developer Mode is required for the Bee CLI to connect to your account.

1. Open the Bee iOS app
2. Go to **Settings**
3. Find the **Version** row and tap it **5 times** to unlock Developer Mode

> The Version row is typically at the bottom of the Settings screen. If you can't find it, make sure you're on the latest app version and try again.

### 2. Install and authenticate the Bee CLI

```bash
npm install -g @beeai/cli
bee login
```

Verify everything is connected:

```bash
bee status
bee ping
```

`bee status` should show "Verified as [your name]" and `bee ping` should return "pong".

### 3. Configure the action button

In the Bee iOS app:

1. Go to **Settings**
2. Find the **Action Button** menu
3. Set the **Double Press** field to **Bookmark**

This lets you silently bookmark moments during a keynote with a quick double-press — no phone, no typing, no breaking focus.

### 4. Check the silence timeout

Bee stops recording after a period of silence. The default is 15 minutes, which works well for keynotes — there's never 15 minutes of dead silence during a talk, so the Bee won't cut out. And it'll stop recording shortly after the keynote ends.

You can check or change this in the Bee iOS app under **Device Settings** → **Stop after silence**. Options are 5 mins, 15 mins, 1 hour, 12 hours, and 24 hours. Leave it at 15 mins unless you have a reason to change it.

> If you set it to 5 mins, you risk the Bee cutting out during longer video segments or applause breaks.

## Project Setup

```bash
git clone <this-repo>
cd reinvent-notetaker

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### During the keynote

1. Wear your Bee device — make sure it's recording
2. Just listen and enjoy the talk
3. When something interests you, **double-press the action button** to bookmark that moment

### After the keynote

1. Optionally create todos for moments you want extra research on (the ⭐ emoji tells the agent to deep-dive):

   ```bash
   bee todos create --text "⭐ Nova Forge - how does open training actually work?"
   bee todos create --text "⭐ Lambda Durable Functions - what does this mean for long-running agents?"
   ```

2. Run the agent:

   ```bash
   python reinvent_notetaker.py
   ```

3. Find your notes in `keynote-notes/`

## What You Get

The agent produces a markdown file with:

- **Summary** — keynote topic, presenter, key themes
- **Announcements** — every service launch/feature with documentation links, What's New/blog links, regional availability, and getting started guides
- **⭐ Flagged Moments** — deep-dive research for bookmarked moments, including related services, architectural guidance, tutorials, and the context of why you flagged it
- **Reading List** — prioritized links with flagged items first

See [example-output.md](example-output.md) for a real sample.

## How Flagging Works

The agent checks two sources for flagged moments:

| Method | When to use | What the agent gets |
|--------|------------|-------------------|
| Double-press bookmark | During the keynote (silent, zero friction) | Timestamp — agent infers context from surrounding transcript |
| Todo with ⭐ emoji | After the keynote (more explicit) | Your text — agent uses it as additional search terms |

You can combine both: bookmark during the talk, then add a todo with context during a break. The agent deduplicates and uses the richest context available.

Moments without a todo get context extracted from the transcript (2 minutes before to 1 minute after the bookmark). Moments with a todo use your text as the "why you flagged this" and as extra search terms for deeper research.

## Technology Stack

| Component | Role |
|-----------|------|
| [Bee](https://www.bee.computer/) | Wearable AI that captures and transcribes keynote audio with speaker identification |
| [Bee CLI](https://www.bee.computer/docs/cli) | Command-line access to transcripts, todos, bookmarks (`bee now --json`, `bee todos list --json`) |
| [Strands Agents SDK](https://strandsagents.com/) | Agent orchestration — model decides which tools to call and when |
| [AWS Knowledge MCP Server](https://awslabs.github.io/mcp/) | Remote managed MCP for AWS docs, What's New, blogs, regional availability. No local setup or AWS credentials needed |
| [Amazon Bedrock](https://aws.amazon.com/bedrock/?trk=0fc6058e-ef5a-4fc9-bc07-6efe2c3c9de4&sc_channel=el) | Model inference (Claude Sonnet via Converse API) |

## Architecture

One Python file. Three `@tool` functions wrap Bee CLI commands (`get_keynote_transcript`, `get_flagged_moments`, `save_notes`). An `MCPClient` connects to the AWS Knowledge MCP Server at `https://knowledge-mcp.global.api.aws` over Streamable HTTP. The Strands `Agent` ties it all together — the model reads the transcript, identifies announcements, and decides which tools to call for research.

```python
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

knowledge_mcp = MCPClient(lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws"))

with knowledge_mcp:
    agent = Agent(
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        tools=[get_keynote_transcript, get_flagged_moments, save_notes,
               *knowledge_mcp.list_tools_sync()],
        system_prompt=SYSTEM_PROMPT,
    )
    agent("Process my latest re:Invent keynote and compile research notes.")
```

No workflow graph, no step definitions. The model handles orchestration.

## Tips

- **Timing matters**: Run the agent a few hours after the keynote for best results. What's New posts and blogs go live during/after the keynote, but full docs can take longer.
- **Multiple keynotes**: The agent pulls the last 10 hours of Bee conversations via `bee now`. If you attend back-to-back sessions, run the agent between them or the transcripts will merge.
- **Connectivity**: Both Bee (for syncing transcripts to the cloud) and the agent (for Bedrock + MCP calls) need internet. Run the research phase when you have solid Wi-Fi — not during the keynote on conference Wi-Fi.
- **Transcript noise**: Bee captures everything including audience chatter and applause. The agent is prompted to filter this out and focus on announcements from the primary speaker.
- **Transcription quirks**: Bee may mishear uncommon product names (e.g., "Kiro" transcribed as "Curo"). The system prompt includes corrections for known cases, but you may want to add more for your specific keynote.

## Useful Bee CLI Commands

```bash
# Check what the Bee captured (human-readable)
bee now

# See your todos
bee todos list

# Search past conversations
bee search --query "Lambda Durable Functions"

# Semantic search (slower, better for conceptual queries)
bee search --query "that new training service" --neural

# Full data export to markdown files
bee sync
```

See the [Bee CLI documentation](https://docs.bee.computer/docs) for the complete reference.

## Security

See [LICENSE](LICENSE) for more information.

## License

This sample code is made available under the MIT-0 license. See the [LICENSE](LICENSE) file.

Copyright Amazon.
