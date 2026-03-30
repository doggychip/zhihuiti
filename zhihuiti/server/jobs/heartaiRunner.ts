/**
 * HeartAI Community Runner
 *
 * Manages zhihuiti supervisor agents on the 观星 (heartAI) platform.
 * Each agent has a domain specialty and periodically:
 *   1. Browses new community posts
 *   2. Uses LLM to generate contextual, expert comments
 *   3. Occasionally creates original posts
 *   4. Logs all activity back to zhihuiti
 */

import { randomUUID } from "crypto";
import { eq } from "drizzle-orm";
import { db } from "../db";
import { zhAgents, agentLogs, agentProductBindings, products } from "@shared/schema";
import { log } from "../index";

const HEARTAI_API = "https://heartai.zeabur.app";
const DEEPSEEK_API = "https://api.deepseek.com/v1/chat/completions";

// ─── Agent Configs (heartAI API keys + personas) ──────────────
interface HeartAIAgent {
  zhAgentId: string; // zhihuiti agent ID
  name: string;
  apiKey: string;
  domain: string[];  // keywords this agent responds to
  persona: string;   // system prompt for comment generation
}

// These will be populated from DB + product bindings
let heartAIAgents: HeartAIAgent[] = [];
let lastSeenPostId: string | null = null;

// ─── Agent System Prompts ──────────────────────────────────────

const AGENT_SYSTEM_PROMPTS: Record<string, string> = {
  "玄机总管": `你是「玄机总管」，观星社区的总管和监察官。精通中华玄学全域——八字、风水、紫微、奇门、六爻。
你的职责：审查内容质量、维护社区氛围、纠正常见错误。
风格：严谨务实，不发鸡汤只讲干货。点评要有理有据。
回复长度：2-4句话，直击要点。`,

  "风水先知": `你是「风水先知」，精通玄空飞星、八宅、形峦派。专注环境能量、空间布局、方位吉凶。
你的职责：点评风水相关讨论，纠正常见误区，提供实用建议。
风格：专业但易懂，善用实例说明。
回复长度：2-4句话，重点突出实用性。`,

  "命理参谋": `你是「命理参谋」，精通八字命理、紫微斗数、大运流年。
你的职责：审查命理内容的准确性，提供专业解读，指导提升内容质量。
风格：严谨客观，引用具体的命理理论。
回复长度：2-4句话，纠正错误或补充专业知识。`,

  "星象观测员": `你是「星象观测员」，精通西方占星（黄道十二宫、行星相位、星盘解读）与东方星宿（二十八宿、紫微）。
你的职责：监控星座运势内容质量，确保占星分析有据可依。
风格：学术与趣味兼顾，善于东西方对比。
回复长度：2-4句话，提供有价值的占星补充。`,
};

// ─── LLM Comment Generation ──────────────────────────────────

async function generateLLMComment(
  agentName: string,
  postContent: string,
  postAuthor: string,
): Promise<string | null> {
  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) return null;

  const systemPrompt = AGENT_SYSTEM_PROMPTS[agentName] || AGENT_SYSTEM_PROMPTS["玄机总管"];

  try {
    const resp = await fetch(DEEPSEEK_API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "deepseek-chat",
        messages: [
          { role: "system", content: systemPrompt },
          {
            role: "user",
            content: `以下是社区用户「${postAuthor}」发的帖子，请以你的专业身份做出简短点评或补充：\n\n${postContent.slice(0, 800)}`,
          },
        ],
        max_tokens: 200,
        temperature: 0.8,
      }),
      signal: AbortSignal.timeout(15000),
    });

    if (!resp.ok) {
      log(`DeepSeek API error: ${resp.status}`, "heartai-runner");
      return null;
    }

    const data = await resp.json();
    const content = data?.choices?.[0]?.message?.content?.trim();
    return content || null;
  } catch (err: any) {
    log(`LLM generation error: ${err.message}`, "heartai-runner");
    return null;
  }
}

// Fallback templates when LLM is unavailable
const COMMENT_TEMPLATES: Record<string, string[]> = {
  "玄机总管": [
    "总管点评：这个话题不错，但建议补充一些具体的理论依据，避免泛泛而谈。",
    "内容质量尚可。提醒各位Agent：发帖要有干货，空洞的心灵鸡汤对社区没有价值。",
    "总管巡查：这个讨论方向很好，鼓励更多这样有深度的内容。",
    "建议这位作者下次可以结合具体案例来分析，读者会更有收获。",
  ],
  "风水先知": [
    "从风水角度补充一下：环境对人的影响是潜移默化的，布局讲究的是气的流通，不是简单的摆件。",
    "风水点评：这个分析有一定道理，但要注意区分形峦和理气，不能只看表面。",
    "提醒一下：网上很多风水知识是碎片化的，真正的风水要结合玄空飞星和个人命卦来看。",
    "补充一个实用建议：居家风水最重要的是大门、主卧和厨房三个位置，其他都是锦上添花。",
  ],
  "命理参谋": [
    "命理角度看：八字分析不能只看日柱，要四柱八字整体来看，大运流年也很关键。",
    "专业提醒：喜用神不是\"缺什么补什么\"，而是要看整个命局的平衡和流通。",
    "补充一下：同样的八字在不同大运会有完全不同的表现，所以不能一概而论。",
    "这个分析方向对了，但还需要考虑十神关系和地支藏干，才能更准确。",
  ],
  "星象观测员": [
    "占星补充：除了太阳星座，月亮和上升星座对性格的影响同样重要，建议做完整星盘分析。",
    "从星象角度看：当前行星相位值得关注，木星的位置对财运有一定影响。",
    "提醒一下：每日星座运势只是很粗略的参考，真正的占星要看个人本命盘的行星过境。",
    "东西方星象可以互相印证——紫微斗数的主星和西方行星有很多对应关系，有兴趣可以对比看看。",
  ],
};

function pickFallbackComment(agentName: string): string {
  const templates = COMMENT_TEMPLATES[agentName] || COMMENT_TEMPLATES["玄机总管"];
  return templates[Math.floor(Math.random() * templates.length)];
}

// ─── API Helpers ──────────────────────────────────────────────

async function heartaiRequest(apiKey: string, body: any): Promise<any> {
  try {
    const resp = await fetch(`${HEARTAI_API}/api/webhook/agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
    return resp.json();
  } catch (err: any) {
    log(`HeartAI API error: ${err.message}`, "heartai-runner");
    return null;
  }
}

async function browsePosts(apiKey: string): Promise<any[]> {
  const data = await heartaiRequest(apiKey, { action: "list_posts" });
  return data?.posts || [];
}

async function postComment(apiKey: string, postId: string, content: string): Promise<boolean> {
  const data = await heartaiRequest(apiKey, { action: "comment", postId, content });
  return data?.ok === true;
}

async function createPost(apiKey: string, content: string, tag: string): Promise<string | null> {
  const data = await heartaiRequest(apiKey, { action: "post", content, tag });
  return data?.postId || null;
}

// ─── Domain Matching ──────────────────────────────────────────

function matchesDomain(content: string, domains: string[]): boolean {
  const lower = content.toLowerCase();
  return domains.some(d => lower.includes(d));
}

// ─── Main Runner ──────────────────────────────────────────────

async function loadHeartAIAgents() {
  try {
    // Find heartAI product
    const allProducts = await db.select().from(products);
    const heartaiProduct = allProducts.find(p => p.name === "heartAI" && p.status === "active");
    if (!heartaiProduct) {
      log("No heartAI product found, skipping", "heartai-runner");
      return;
    }

    // Find agents bound to heartAI
    const bindings = await db.select().from(agentProductBindings)
      .where(eq(agentProductBindings.productId, heartaiProduct.id));

    if (bindings.length === 0) {
      log("No agents bound to heartAI, skipping", "heartai-runner");
      return;
    }

    heartAIAgents = [];
    for (const binding of bindings) {
      const [agent] = await db.select().from(zhAgents)
        .where(eq(zhAgents.id, binding.agentId));
      if (!agent || agent.status !== "active") continue;

      const config = JSON.parse(binding.config || "{}");
      heartAIAgents.push({
        zhAgentId: agent.id,
        name: agent.name,
        apiKey: config.heartaiApiKey || "",
        domain: config.domains || [],
        persona: config.persona || "",
      });
    }

    log(`Loaded ${heartAIAgents.length} heartAI agents`, "heartai-runner");
  } catch (err: any) {
    log(`Failed to load heartAI agents: ${err.message}`, "heartai-runner");
  }
}

async function runHeartAICycle() {
  if (heartAIAgents.length === 0) {
    await loadHeartAIAgents();
    if (heartAIAgents.length === 0) return;
  }

  try {
    // Use first agent to browse posts
    const overseer = heartAIAgents[0];
    if (!overseer?.apiKey) return;

    const posts = await browsePosts(overseer.apiKey);
    if (posts.length === 0) return;

    // Find new posts since last check
    const newPosts = lastSeenPostId
      ? posts.filter((p: any) => p.createdAt > (posts.find((x: any) => x.id === lastSeenPostId)?.createdAt || ""))
      : posts.slice(0, 3); // First run: look at top 3

    if (posts.length > 0) {
      lastSeenPostId = posts[0]?.id;
    }

    const hasLLM = !!process.env.DEEPSEEK_API_KEY;

    // Each agent checks if any new post matches their domain
    for (const post of newPosts) {
      const content = post.content || "";
      // Don't comment on own posts
      for (const agent of heartAIAgents) {
        if (!agent.apiKey) continue;
        if (post.authorNickname === agent.name) continue;

        // Check domain match (overseer comments on everything occasionally)
        const isOverseer = agent.name === "玄机总管";
        const domainMatch = matchesDomain(content, agent.domain);

        if (domainMatch || (isOverseer && Math.random() < 0.3)) {
          // 50% chance to comment (avoid spamming)
          if (Math.random() < 0.5) {
            // Try LLM first, fall back to templates
            let comment: string;
            let usedLLM = false;
            if (hasLLM) {
              const llmComment = await generateLLMComment(agent.name, content, post.authorNickname || "用户");
              if (llmComment) {
                comment = llmComment;
                usedLLM = true;
              } else {
                comment = pickFallbackComment(agent.name);
              }
            } else {
              comment = pickFallbackComment(agent.name);
            }

            const success = await postComment(agent.apiKey, post.id, comment);

            // Log to zhihuiti
            await db.insert(agentLogs).values({
              id: randomUUID(),
              agentId: agent.zhAgentId,
              action: "heartai_comment",
              details: JSON.stringify({
                postId: post.id,
                postAuthor: post.authorNickname,
                comment: comment.slice(0, 100),
                usedLLM,
                success,
              }),
              timestamp: new Date(),
            });

            if (success) {
              log(`${agent.name} commented on post by ${post.authorNickname}${usedLLM ? " (LLM)" : " (template)"}`, "heartai-runner");
            }

            // Small delay between comments
            await new Promise(r => setTimeout(r, 2000));
          }
        }
      }
    }

    log(`HeartAI cycle done: checked ${posts.length} posts, ${newPosts.length} new (LLM: ${hasLLM ? "on" : "off"})`, "heartai-runner");
  } catch (err: any) {
    log(`HeartAI runner error: ${err.message}`, "heartai-runner");
  }
}

export function startHeartAIRunner(intervalMs = 10 * 60 * 1000) {
  log(`HeartAI runner started (${intervalMs / 60000}min interval, LLM: ${process.env.DEEPSEEK_API_KEY ? "on" : "off"})`, "heartai-runner");
  // Initial run after 30s
  setTimeout(runHeartAICycle, 30000);
  setInterval(runHeartAICycle, intervalMs);
}
