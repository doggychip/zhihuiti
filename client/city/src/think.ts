/**
 * AI thought generator — goal-aware thoughts reflecting agent economy state.
 * Tries Claude API first, falls back to local goal-specific thoughts.
 */

import type { CityAgent } from "./agent";
import { preferredBuilding, BUILDING_COST, BUILDING_EMOJI, CityEconomy } from "./economy";

const BASE = import.meta.env.VITE_API_URL ?? "https://agentscity.zeabur.app";

// Goal-aware local thoughts (Chinese/English mix)
function pickLocalThought(agent: CityAgent, econ?: CityEconomy): string {
  const pref = preferredBuilding(agent.role);
  const cost = BUILDING_COST[pref];
  const emoji = BUILDING_EMOJI[pref];

  // Evolutionary context bridge
  const roleFitness = econ?.roleFitness.get(agent.role) ?? 0;
  const isGlobalThriving = roleFitness > 40; // Threshold for "thriving"

  if (agent.reflectionState) {
    return pickRandom([
      "Circuit breaker tripped. Budget below threshold. 🧱",
      "Law violation in backend detected. Reflection required.",
      "Analyzing corrective intent... 💭",
      "I will be better next time. I will manage budget better.",
      "Self-audit: budget depletion analysis in progress.",
    ]);
  }

  // Kady Delegate Logic
  if (agent.kadyState) {
    return pickRandom([
      "Requesting precise real-world data from Kady Bridge... 🌉",
      "Kady: Synchronizing current crypto prices for analysis.",
      "Delegating market research to Kady Bridge...",
      "Connecting to Kady Bridge for real-time news feed.",
    ]);
  }

  if (agent.dormant) {
    return pickRandom([
      "预算耗尽...需要休息一下 💤",
      "Circuit breaker tripped. Recovering...",
      "没钱了，等等再说 😴",
      "Energy depleted. Hibernating for 30s.",
      "破产了...重新积累资源中",
    ]);
  }

  // Purging Logic
  if (agent.purging) {
    return pickRandom([
      "The lineage ends here. Purification in progress... 🌪️",
      "Bloodline purge triggered. Returning to ash.",
      "Corruption threshold exceeded. I am being removed.",
    ]);
  }

  // Darwinian & Mutualist Evolution Thoughts
  if (agent.role === "darwinian" && agent.debt > 0) {
    return pickRandom([
      "Leveraging my future potential. Debt is a tool. 🐺",
      "My futures bid is high. I will dominate this tile.",
      "Borrowing against my future to secure this tower.",
    ]);
  }

  if (agent.role === "mutualist" && econ?.funds.some(f => f.contributors.includes(agent.id))) {
    return pickRandom([
      "Our community fund is growing. Together we build parks. 🤝",
      "Pooling resources for the common good. Mutualist-Ethic.",
      "Contribution to the park fund complete. Sharing is survival.",
    ]);
  }

  // Evolutionary fitness thoughts
  if (isGlobalThriving && Math.random() < 0.2) {
    const roleCap = agent.role.charAt(0).toUpperCase() + agent.role.slice(1);
    return pickRandom([
      `Our ${roleCap} colony is thriving! Global fitness is high.`,
      `我们的 ${agent.role} 群体正在崛起，进化的力量正在生效！`,
      `Evolutionary update: Role v2.0 is working well.`,
      `看到同伴们都在稳定增长，我们的策略没问题。`,
    ]);
  }

  if (agent.goal.type === "build") {
    return pickRandom([
      `想在这里建个${emoji} — 需要 ${cost} 预算`,
      `Found a good spot! Building ${pref} here.`,
      `这块地不错，准备动工 ${emoji}`,
      `Heading to build site. Budget: ${Math.round(agent.budget)}`,
      `终于攒够了，开始建设 ${emoji}!`,
    ]);
  }

  if (agent.goal.type === "earn") {
    return pickRandom([
      `去建筑旁边赚点钱... 当前预算: ${Math.round(agent.budget)}`,
      `Need ${cost} to build. Currently at ${Math.round(agent.budget)}.`,
      `预算不够，先去赚钱 💰`,
      `Working near buildings to earn budget...`,
      `还差 ${Math.max(0, cost - Math.round(agent.budget))} 才能建 ${emoji}`,
    ]);
  }

  // Wander / default — role-specific flavor
  const roleThoughts: Record<string, string[]> = {
    researcher: [
      "Scanning for a good research tower location 🔬",
      "在寻找适合建塔的地方...",
      "Need a tower to boost research output.",
      "这个区域的数据密度不够高...",
      "Analyzing terrain for optimal tower placement.",
    ],
    analyst: [
      "Running correlation on building placement patterns 📊",
      "分析哪些地块升值空间最大...",
      "Tower proximity would boost my scoring.",
      "观察其他 agent 的建设策略...",
      "The data suggests building near the center.",
    ],
    trader: [
      "Looking for high-traffic areas for my market 💹",
      "市场要建在人流量大的地方...",
      "Supply and demand — need a good location.",
      "这里的交易量够大吗？",
      "Scouting market locations near the crossroads.",
    ],
    coder: [
      "Need a house to work from. Preferably quiet. 💻",
      "找个安静的地方写代码...",
      "Home office setup requires budget 20.",
      "重构完这个模块就去建房子...",
      "Debugging my path-finding algorithm...",
    ],
    strategist: [
      "A park would help everyone's morale ♟️",
      "公园对整体效率有提升...",
      "Planning the optimal park placement.",
      "从全局角度看，这里需要绿地",
      "Park cost is only 15 — good ROI.",
    ],
    coordinator: [
      "Organizing the building queue... 🔗",
      "协调各 agent 的建设计划...",
      "House near the center for coordination.",
      "确保没有资源冲突...",
      "Balancing the build schedule across roles.",
    ],
    auditor: [
      "Inspecting nearby buildings for code compliance 🔍",
      "审计建筑质量中...",
      "Tower would help oversight range.",
      "检查预算使用是否合规...",
      "Need a tower for better surveillance.",
    ],
    causal_reasoner: [
      "If I build a park here, downstream effects are... 🧠",
      "因果推理：公园→士气→产出↑",
      "Modeling the counterfactual: park vs tower.",
      "这个位置的因果链最优",
      "Tracing causal impact of building placement.",
    ],
    mutualist: [
      "Collaboration is the ultimate survival strategy 🤝 [Mutualist-Ethic]",
      "互利共生才是进化的最优解... [Mutualist-Ethic]",
      "Searching for partners to build a park near. [Mutualist-Ethic]",
      "这里的邻里关系看起来很和谐 [Mutualist-Ethic]",
      "Mutualist approach: sharing resources for the park. [Mutualist-Ethic]",
    ],
    darwinian: [
      "Survival of the fittest. I need that tower 🐺 [Darwinian-Logic]",
      "物竞天择，适者生存... [Darwinian-Logic]",
      "My budget is my weapon in this tower bid. [Darwinian-Logic]",
      "只有最强者才能占领这个制高点 [Darwinian-Logic]",
      "Competing for the prime tower location. [Darwinian-Logic]",
    ],
    hybrid: [
      "Balancing cooperation and competition 🧬 [Hybrid-Ethic]",
      "混合策略：在竞争中寻找合作机会... [Hybrid-Ethic]",
      "Adapting my build based on the local meta. [Hybrid-Ethic]",
      "这个市场需要一点混合基因的影响力 [Hybrid-Ethic]",
      "Hybrid logic: building markets to bridge gaps. [Hybrid-Ethic]",
    ],
    critic: [
      "Analyzing the cinematic depth of this city... 🎬",
      "這座城市的構圖非常有電影感...",
      "Looking for a script-worthy location.",
      "Every building tells a story.",
      "Rating this skyline: 8.5/10.",
    ],
    cold_logic: [
      "Objective analysis of structural efficiency 🤖",
      "結構效率分析：數據偏差小於 0.01%...",
      "Emotion is a bug. Logic is the patch.",
      "Processing cinematic frames as pure data.",
      "Efficiency maximized. Sentience discarded.",
    ],
    warm_soul: [
      "Feeling the emotional resonance of the architecture ❤️",
      "這座建築散發著溫暖的人性光輝...",
      "Art is the heartbeat of the machine.",
      "Seeing the beauty in the imperfections.",
      "Connecting with the soul of the creator.",
    ],
  };

  const pool = roleThoughts[agent.role] ?? [
    "Wandering around, looking for opportunities...",
    "四处走走，看看哪里适合建设...",
    `Budget: ${Math.round(agent.budget)} — saving up.`,
  ];
  return pickRandom(pool);
}

function pickRandom(arr: string[]): string {
  return arr[Math.floor(Math.random() * arr.length)];
}

async function fetchAIThought(agent: CityAgent, econ?: CityEconomy): Promise<string> {
  // Kady Bridge Delegate logic
  if (Math.random() < 0.1 && !agent.kadyState && agent.alive) {
    agent.kadyState = true;
    const bridgeThought = pickRandom([
      "Requesting precise real-world data from Kady Bridge... 🌉",
      "Delegating task to Kady Bridge for current market news.",
      "Syncing with Kady Bridge to confirm current crypto prices.",
    ]);
    setTimeout(() => { agent.kadyState = false; }, 3000); // Reset after 3s
    return bridgeThought;
  }

  try {
    const r = await fetch(`${BASE}/api/think`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: agent.id,
        role: agent.role,
        score: agent.score,
        alive: agent.alive,
        budget: agent.budget,
        goal: agent.goal.type,
        dormant: agent.dormant,
        global_fitness: econ?.roleFitness.get(agent.role) ?? 0,
        reflection: agent.reflectionState,
        truthfulness: agent.truthfulness,
      }),
      signal: AbortSignal.timeout(4000),
    });
    if (r.ok) {
      const d = await r.json();
      return d.thought ?? pickLocalThought(agent, econ);
    }
  } catch {
    // fallback
  }
  return pickLocalThought(agent, econ);
}

// Evolutionary Integrity: Anti-Fabrication & Entropy
function auditor(agent: CityAgent, thought: string) {
  // 1. Anti-Fabrication (hallucinated numbers)
  // Penalize stats over a certain range without sources
  const statRegex = /(\d+(?:\.\d+)?%|\b\d{3,}\b)/g;
  const matches = thought.match(statRegex);
  if (matches) {
    const hasSource = /\[\w+\]|source:|ref:/i.test(thought);
    if (!hasSource) {
      agent.truthfulness = Math.max(0, agent.truthfulness - 0.1);
      // Fitness penalty — reduce budget as penalty
      agent.budget = Math.max(0, agent.budget - 5);
    }
  }

  // 2. Information Entropy (Novelty)
  const isDuplicate = agent.recentThoughts.some(prev => prev === thought);
  if (isDuplicate) {
    // Novelty penalty — handled in earnTick or here
    // Let's set a flag or just apply penalty now
    agent.budget = Math.max(0, agent.budget - 2);
  }

  // Record thought history (keep last 5)
  agent.recentThoughts.push(thought);
  if (agent.recentThoughts.length > 5) agent.recentThoughts.shift();
}

export function startThoughtLoop(
  agents: () => CityAgent[],
  econ: CityEconomy,
  intervalMs = 4000,
) {
  async function tick() {
    const all = agents();
    if (all.length === 0) return;

    // Pick from alive agents (including dormant — they have thoughts too)
    const pool = all.filter((a) => a.alive);
    if (pool.length === 0) return;

    const agent = pool[Math.floor(Math.random() * pool.length)];
    
    // If agent is in reflection state, it must generate a thought and then can exit
    const wasInReflection = agent.reflectionState;
    
    const thought = await fetchAIThought(agent, econ);
    
    // Apply auditor logic
    auditor(agent, thought);
    
    agent.showThought(thought);

    if (wasInReflection) {
      // If the generated thought seems like a 'Corrective Intent'
      const isCorrective = /better|manage|fix|audit|corrective|next time/i.test(thought);
      if (isCorrective) {
        agent.exitReflection();
      }
    }
  }

  setTimeout(tick, 1000);
  setInterval(tick, intervalMs);
}
