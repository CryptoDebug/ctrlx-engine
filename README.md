# CTRLX Bot

Lightweight asynchronous Discord bot built with `discord.py` v2, SQLite, and Google Gemini API integration.  
Designed to run on low-resource environments such as a Raspberry Pi with minimal memory footprint (< 50 MB RAM).

---

## Features

- **Automated Job Board (`#offres-emploi`) :** Fetches and posts qualified software engineering and cybersecurity jobs with Discord forum tags and CTRLX templates.
- **Tech Radar (`#tech-radar`) :** Curated multi-domain tech news stream (Cybersecurity, Dev, Hardware, AI, Web3) with opt-in role mentions.
- **Career & Education Guides (`#conseils-carrière`, `#études-et-formations`) :** Practical deep dives and certification guides.
- **Breaking News Approval Queue (`#only-owners`) :** Interactive Discord Components V2 approval panel for high-severity tech events with channel selection, mention type selection, and modal text editor.
- **Social Media Studio :** Multi-platform post generator (`/social-generate`) formatted for LinkedIn, X (Twitter), and Reddit.
- **SQLite Storage :** Deduplication and metric counters with zero database overhead.

---

## Commands

- `/status` : Displays bot runtime stats, memory usage, CPU load, and post metrics.
- `/social-generate [topic]` : Generates tailored posts for LinkedIn, X, and Reddit with one-click copy buttons.
- `/job-force` : Triggers immediate job retrieval and forum post creation.
- `/radar-force` : Publishes an immediate tech radar news item.
- `/career-force [career|formation]` : Publishes an immediate career guide or study guide.
- `/breaking-test` : Sends a simulation approval card to the staff channel.

---

## Setup

### Requirements

- Python 3.10+
- Google Gemini API Key

### Installation

```bash
git clone https://github.com/yourusername/ctrlx-bot.git
cd ctrlx-bot
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

```env
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_guild_id
GEMINI_API_KEY=your_gemini_api_key

CHANNEL_OFFRES_EMPLOI=1559184778228539406
CHANNEL_CONSEILS_CARRIERE=1559184801754390578
CHANNEL_ETUDES_FORMATIONS=1559184795534368842
CHANNEL_TECH_RADAR=1446854554720272466
CHANNEL_TUTORIALS_COURSES=1424468353006698526
CHANNEL_OFF_TOPIC=1419711392029868175
CHANNEL_TECH_TALK=1504836244700663818
CHANNEL_STAFF_OWNERS=1419118008017620994

ROLE_VEILLE_TECH=1559343282646155365
ROLE_OPPORTUNITES=1559186893189546075

TAG_STAGE=1559184778228539407
TAG_ALTERNANCE=1559184778228539408
TAG_CDI_CDD=1559184778228539409
TAG_FREELANCE=1559184778228539410

TAG_TUTO_TOOLS=1559219065120362499
TAG_TUTO_OSINT=1559219065120362500
TAG_TUTO_CYBER=1559219065111707726
TAG_TUTO_DEV=1559192290864660539
TAG_TUTO_IA=1559192290877116446
```

### Running

```bash
python main.py
```

### Systemd Deployment (Raspberry Pi / Linux)

```bash
sudo cp ctrlx.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ctrlx
sudo systemctl start ctrlx
```
