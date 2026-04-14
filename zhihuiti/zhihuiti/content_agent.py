"""Cross-domain content agent — East meets West wisdom engine.

Generates continuous content exploring intersections between:
- Western: neuroscience, quantum mechanics, physics, psychology
- Eastern: meditation, Buddhism (Mahamudra), Hinduism, Taoism, yoga

Content is stored persistently and served via API.
Each piece is scored by the 3-layer inspection system.
Top content gets promoted; weak content gets culled.

Usage:
  GET /api/content/feed          — latest content feed
  GET /api/content/:id           — single content piece
  GET /api/content/topics        — available topic categories
  POST /api/content/generate     — trigger new content generation
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ── Content Data Structures ──────────────────────────────────────────────

@dataclass
class ContentPiece:
    """A generated content piece bridging East and West."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    body: str = ""                     # Main content in accessible language
    west_topic: str = ""               # e.g., "mirror neurons", "quantum entanglement"
    east_topic: str = ""               # e.g., "Mahamudra", "vipassana meditation"
    cross_insight: str = ""            # The bridging insight
    video_recommendations: list[dict] = field(default_factory=list)  # [{title, description, search_query}]
    tags: list[str] = field(default_factory=list)
    score: float = 0.0                 # From 3-layer inspection
    agent_id: str = ""                 # Which agent generated it
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Topic Registry ───────────────────────────────────────────────────────

TOPIC_PAIRS = [
    # Neuroscience × Meditation
    {
        "west": "镜像神经元 (Mirror neurons)",
        "east": "佛教慈悲观修 (Buddhist compassion meditation)",
        "bridge": "Mirror neurons fire when observing others' actions — compassion meditation literally rewires these circuits, expanding empathy at a neural level.",
        "tags": ["neuroscience", "buddhism", "compassion", "mirror_neurons"],
    },
    {
        "west": "默认模式网络 DMN (Default Mode Network)",
        "east": "打坐冥想 (Sitting meditation / Zazen)",
        "bridge": "The DMN is your brain's 'monkey mind'. fMRI studies show experienced meditators can quiet the DMN at will — what monks called 'stopping thoughts' for 2500 years.",
        "tags": ["neuroscience", "meditation", "dmn", "zen"],
    },
    {
        "west": "神经可塑性 (Neuroplasticity)",
        "east": "大手印 (Mahamudra / Great Seal)",
        "bridge": "Neuroplasticity proves the brain reshapes itself through repeated practice. Mahamudra's progressive stages mirror this: recognition → familiarization → stability. Same mechanism, different language.",
        "tags": ["neuroscience", "mahamudra", "buddhism", "neuroplasticity"],
    },
    {
        "west": "量子纠缠 (Quantum entanglement)",
        "east": "印度教梵我合一 (Hindu Brahman-Atman unity)",
        "bridge": "Quantum entanglement shows particles connected across any distance, acting as one. The Upanishads described this 3000 years ago: 'Tat tvam asi' — you are that. All is interconnected.",
        "tags": ["quantum", "hinduism", "entanglement", "vedanta"],
    },
    {
        "west": "量子观测者效应 (Observer effect in quantum mechanics)",
        "east": "内观禅修 (Vipassana / Insight meditation)",
        "bridge": "In quantum physics, observation changes the outcome. In Vipassana, observing your thoughts without judgment changes their nature. The observer is never separate from the observed.",
        "tags": ["quantum", "vipassana", "buddhism", "observer_effect"],
    },
    {
        "west": "脑波同步 (Brainwave synchronization / Gamma waves)",
        "east": "藏传佛教长期修行者 (Tibetan Buddhist long-term practitioners)",
        "bridge": "Richard Davidson's lab found Tibetan monks produce gamma brainwaves 800% stronger than novices. Decades of meditation literally builds a different brain.",
        "tags": ["neuroscience", "tibetan_buddhism", "gamma_waves", "davidson"],
    },
    {
        "west": "肠脑轴 (Gut-brain axis / Enteric nervous system)",
        "east": "丹田 / 脉轮系统 (Dantian / Chakra system)",
        "bridge": "Science discovered the gut has 500 million neurons — a 'second brain'. Yogis and qigong masters always knew: the lower dantian (belly center) is a seat of intelligence, not just digestion.",
        "tags": ["neuroscience", "yoga", "chakra", "gut_brain", "qigong"],
    },
    {
        "west": "心流状态 (Flow state psychology — Csikszentmihalyi)",
        "east": "道家无为 (Taoist Wu Wei / Effortless action)",
        "bridge": "Flow state: complete absorption where self disappears and performance peaks. Wu Wei: acting without forcing, like water flowing downhill. Same state, discovered 2000 years apart.",
        "tags": ["psychology", "taoism", "flow", "wu_wei"],
    },
    {
        "west": "表观遗传学 (Epigenetics — gene expression by environment)",
        "east": "业力 / 因果 (Karma — actions shape future conditions)",
        "bridge": "Epigenetics shows your choices (diet, stress, meditation) change which genes activate, affecting your children too. Karma said the same: actions create imprints that ripple across generations.",
        "tags": ["epigenetics", "buddhism", "hinduism", "karma"],
    },
    {
        "west": "迷走神经与多层迷走神经理论 (Vagus nerve / Polyvagal theory)",
        "east": "瑜伽呼吸法 (Pranayama / Yogic breathing)",
        "bridge": "Polyvagal theory shows the vagus nerve controls fight/flight/freeze. Pranayama breathing directly stimulates the vagus nerve, shifting the body from stress to calm. Ancient yogis hacked the nervous system.",
        "tags": ["neuroscience", "yoga", "pranayama", "vagus_nerve", "polyvagal"],
    },
    {
        "west": "濒死体验研究 (Near-death experience research — van Lommel)",
        "east": "藏传佛教中阴法 (Tibetan Bardo Thodol / Book of the Dead)",
        "bridge": "NDE research documents consistent experiences: light, peace, life review, tunnel. The Tibetan Book of the Dead mapped these exact stages 1200 years ago as 'bardos' between death and rebirth.",
        "tags": ["consciousness", "tibetan_buddhism", "nde", "bardo"],
    },
    {
        "west": "弦理论与多维空间 (String theory — extra dimensions)",
        "east": "佛教三千大千世界 (Buddhist cosmology — countless world systems)",
        "bridge": "String theory requires 10-11 dimensions. Buddhist cosmology describes infinite world systems layered within each other. Both point to reality being far larger than our senses perceive.",
        "tags": ["physics", "buddhism", "string_theory", "cosmology"],
    },
    {
        "west": "注意力科学 (Attention science — selective/sustained attention)",
        "east": "止观双修 (Shamatha-Vipassana — calm abiding + insight)",
        "bridge": "Cognitive science studies two attention modes: focused (selective) and open (monitoring). Shamatha trains focused attention; Vipassana trains open monitoring. Buddhism had the attention science framework all along.",
        "tags": ["cognitive_science", "buddhism", "attention", "shamatha", "vipassana"],
    },
    {
        "west": "安慰剂效应 (Placebo effect — belief changes biology)",
        "east": "密宗观想法 (Tantric visualization practices)",
        "bridge": "Placebo research proves belief alone can heal. Tantric visualization — vividly imagining deities, light, healing — works the same mechanism. Mind shapes matter, both traditions agree.",
        "tags": ["medicine", "tantra", "placebo", "visualization"],
    },
    {
        "west": "混沌理论与蝴蝶效应 (Chaos theory / Butterfly effect)",
        "east": "因陀罗网 (Indra's Net — interconnected reality)",
        "bridge": "Chaos theory: tiny changes cascade into massive effects. Indra's Net: every jewel reflects every other jewel. Both describe a universe where everything is connected and small actions ripple everywhere.",
        "tags": ["physics", "buddhism", "hinduism", "chaos_theory", "indras_net"],
    },
]

CONTENT_GENERATION_PROMPT = """You are a bilingual (中文/English) content creator who bridges Western science and Eastern wisdom.

Your style:
- 接地气 (down to earth) — no academic jargon, speak like a wise friend
- Use analogies from everyday life
- Include specific scientific studies with researchers' names when possible
- Include specific scriptures/texts when referencing Eastern traditions
- Mix Chinese and English naturally (key terms in both languages)
- Be genuinely insightful — not surface-level "oh look they both say X"
- Show HOW the cross-validation works, not just THAT it exists

For video recommendations:
- Suggest specific YouTube search queries that would find relevant content
- Describe what the video should cover
- Include both Chinese and English video suggestions

Output format (JSON):
{
    "title": "catchy bilingual title",
    "body": "main content (500-1000 words, accessible language, mix CN/EN)",
    "west_topic": "specific Western science topic",
    "east_topic": "specific Eastern practice/philosophy",
    "cross_insight": "the key bridging insight in 1-2 sentences",
    "video_recommendations": [
        {"title": "video title", "description": "what it covers", "search_query": "YouTube search query"}
    ],
    "tags": ["tag1", "tag2"]
}"""


# ── Content Store ────────────────────────────────────────────────────────

_content: list[ContentPiece] = []
_content_lock = threading.Lock()
_store_path = Path(os.environ.get("ZHIHUITI_DATA", "/app/data")) / "content_feed.jsonl"


def _load_content():
    global _content
    if _store_path.exists():
        with _content_lock:
            try:
                with open(_store_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            d = json.loads(line)
                            _content.append(ContentPiece(**{
                                k: v for k, v in d.items()
                                if k in ContentPiece.__dataclass_fields__
                            }))
            except Exception:
                pass


def _save_content(piece: ContentPiece):
    _store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_store_path, "a") as f:
        f.write(json.dumps(piece.to_dict(), ensure_ascii=False) + "\n")


def get_feed(limit: int = 20, tag: str = "") -> list[dict]:
    """Get latest content, optionally filtered by tag."""
    with _content_lock:
        items = _content
        if tag:
            items = [c for c in items if tag in c.tags]
        sorted_items = sorted(items, key=lambda c: c.created_at, reverse=True)
        return [c.to_dict() for c in sorted_items[:limit]]


def get_piece(content_id: str) -> dict | None:
    with _content_lock:
        for c in _content:
            if c.id == content_id:
                return c.to_dict()
    return None


def generate_content(orch=None, topic_hint: str = "") -> ContentPiece:
    """Generate a new content piece using the LLM.

    If orch is provided, uses the zhihuiti orchestrator (real agents).
    Otherwise uses direct LLM call.
    """
    import random

    # Pick a topic pair as seed
    pair = random.choice(TOPIC_PAIRS)
    if topic_hint:
        # Try to match hint
        for p in TOPIC_PAIRS:
            if topic_hint.lower() in str(p).lower():
                pair = p
                break

    user_prompt = f"""Generate a content piece about this East-West intersection:

Western science: {pair['west']}
Eastern wisdom: {pair['east']}
Bridge insight: {pair['bridge']}

Expand on this bridge with:
1. Specific scientific studies or experiments
2. Specific Eastern texts or practices
3. A personal, relatable example
4. Why this matters for everyday life
5. 2-3 video recommendations (YouTube search queries)

Make it engaging, bilingual (中文 + English), and 接地气."""

    if orch and hasattr(orch, 'llm'):
        # Use the orchestrator's LLM
        try:
            result = orch.llm.chat_json(
                system=CONTENT_GENERATION_PROMPT,
                user=user_prompt,
                temperature=0.8,
            )
        except Exception:
            result = _fallback_content(pair)
    else:
        # Try direct LLM
        try:
            from zhihuiti.llm import LLM
            llm = LLM()
            result = llm.chat_json(
                system=CONTENT_GENERATION_PROMPT,
                user=user_prompt,
                temperature=0.8,
            )
        except Exception:
            result = _fallback_content(pair)

    piece = ContentPiece(
        title=result.get("title", pair["west"] + " × " + pair["east"]),
        body=result.get("body", pair["bridge"]),
        west_topic=result.get("west_topic", pair["west"]),
        east_topic=result.get("east_topic", pair["east"]),
        cross_insight=result.get("cross_insight", pair["bridge"]),
        video_recommendations=result.get("video_recommendations", []),
        tags=result.get("tags", pair["tags"]),
    )

    with _content_lock:
        _content.append(piece)
    _save_content(piece)
    return piece


def _fallback_content(pair: dict) -> dict:
    """Fallback when LLM is unavailable — use the seed topic directly."""
    return {
        "title": f"{pair['west']} × {pair['east']}",
        "body": pair["bridge"],
        "west_topic": pair["west"],
        "east_topic": pair["east"],
        "cross_insight": pair["bridge"],
        "video_recommendations": [
            {"title": f"{pair['west']} explained",
             "description": "Scientific background",
             "search_query": pair["west"].split("(")[0].strip() + " neuroscience"},
            {"title": f"{pair['east']} practice",
             "description": "Eastern practice guide",
             "search_query": pair["east"].split("(")[0].strip() + " meditation guide"},
        ],
        "tags": pair["tags"],
    }


# Content generation goals for the auto-evolve loop
CONTENT_GOALS = [
    "Generate a bilingual content piece about how neuroscience research on mirror neurons validates Buddhist compassion meditation practices. Include specific studies and make it accessible.",
    "Write about the connection between quantum observer effect and Vipassana insight meditation. How does modern physics validate ancient observation practices? Include video recommendations.",
    "Explore how neuroplasticity research proves what Mahamudra practitioners have known for centuries — that the mind can reshape itself through practice. Cite specific fMRI studies.",
    "Create content about the gut-brain axis and how it validates the chakra/dantian energy system. Make it practical — what can people do with this knowledge?",
    "Write about Polyvagal theory and Pranayama breathing. How did ancient yogis discover vagus nerve stimulation thousands of years before Stephen Porges?",
    "Explore how flow state psychology (Csikszentmihalyi) validates the Taoist concept of Wu Wei. Include both scientific and philosophical perspectives.",
    "Write about epigenetics and karma — how modern gene science proves that your choices create biological imprints that affect future generations.",
    "Create content about Default Mode Network research and meditation. What happens in the brain when monks 'stop their thoughts'? Include Davidson's gamma wave findings.",
    "Explore the connection between string theory's extra dimensions and Buddhist cosmology's countless world systems. Make complex physics accessible.",
    "Write about near-death experience research and the Tibetan Book of the Dead. How do modern NDE studies validate ancient bardo descriptions?",
    "Create content about chaos theory (butterfly effect) and Indra's Net — how both Western math and Eastern philosophy describe an interconnected universe.",
    "Explore how placebo effect research validates Tantric visualization practices. Mind shapes matter — what does science say about this?",
    "Write about attention science (selective vs sustained attention) and Shamatha-Vipassana meditation. Buddhism had cognitive science figured out 2500 years ago.",
    "Create a comprehensive piece: what are the TOP 5 scientific discoveries that most strongly validate Eastern contemplative traditions? Rank them by evidence strength.",
    "Write about brainwave synchronization in long-term meditators. Gamma waves, theta states, and what they tell us about consciousness beyond the brain.",
]


# Load on import
_load_content()
