"""Generate Theory Collision PDF report."""

import weasyprint

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4;
    margin: 2cm;
  }
  body {
    font-family: "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
  }
  h1 {
    font-size: 26pt;
    color: #0f172a;
    border-bottom: 3px solid #3b82f6;
    padding-bottom: 12px;
    margin-bottom: 8px;
  }
  .subtitle {
    font-size: 13pt;
    color: #64748b;
    margin-bottom: 30px;
  }
  h2 {
    font-size: 16pt;
    color: #1e40af;
    margin-top: 28px;
    margin-bottom: 10px;
  }
  h3 {
    font-size: 13pt;
    color: #334155;
    margin-top: 18px;
    margin-bottom: 6px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 10pt;
  }
  th {
    background: #1e3a5f;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
  }
  td {
    padding: 7px 10px;
    border-bottom: 1px solid #e2e8f0;
  }
  tr:nth-child(even) td {
    background: #f8fafc;
  }
  .tag-on {
    background: #dcfce7; color: #166534;
    padding: 2px 8px; border-radius: 4px; font-size: 9pt; font-weight: 600;
  }
  .tag-off {
    background: #fee2e2; color: #991b1b;
    padding: 2px 8px; border-radius: 4px; font-size: 9pt; font-weight: 600;
  }
  .flow-box {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 14px 0;
    font-family: "Courier New", monospace;
    font-size: 9.5pt;
    line-height: 1.7;
    white-space: pre-wrap;
  }
  .highlight-box {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 12px 16px;
    margin: 14px 0;
    border-radius: 0 6px 6px 0;
  }
  .callout {
    background: #fefce8;
    border-left: 4px solid #eab308;
    padding: 12px 16px;
    margin: 14px 0;
    border-radius: 0 6px 6px 0;
  }
  .section-icon {
    font-size: 14pt;
    margin-right: 6px;
  }
  .page-break {
    page-break-before: always;
  }
  .two-col {
    display: flex;
    gap: 16px;
  }
  .two-col > div {
    flex: 1;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px;
  }
  .two-col h4 {
    margin: 0 0 8px 0;
    font-size: 11pt;
  }
  .score-formula {
    background: #1e293b;
    color: #e2e8f0;
    padding: 14px 18px;
    border-radius: 8px;
    font-family: "Courier New", monospace;
    font-size: 10pt;
    line-height: 1.8;
    margin: 12px 0;
  }
  footer {
    font-size: 8pt;
    color: #94a3b8;
    text-align: center;
    margin-top: 40px;
    border-top: 1px solid #e2e8f0;
    padding-top: 10px;
  }
</style>
</head>
<body>

<h1>Theory Collision</h1>
<div class="subtitle">zhihuiti 理论碰撞系统 &mdash; 用进化对抗实验寻找最优 AI 治理策略</div>

<h2><span class="section-icon">&#x1F3AF;</span> 核心问题</h2>
<div class="highlight-box">
  <strong>什么样的进化压力能产生最强的 AI 代理？</strong><br>
  理论碰撞（Theory Collision）通过让不同的治理哲学在相同任务上对抗，用真实数据回答这个问题。<br>
  本质上是 <strong>用进化论做 A/B 测试</strong> &mdash; 不是测试按钮颜色，而是测试整个治理哲学哪个更优。
</div>

<h2><span class="section-icon">&#x1F9EC;</span> 四大理论</h2>

<table>
  <tr>
    <th>理论</th>
    <th>中文名</th>
    <th>淘汰门槛</th>
    <th>晋升门槛</th>
    <th>通信</th>
    <th>借贷</th>
  </tr>
  <tr>
    <td><strong>Darwinian</strong></td>
    <td>达尔文选择</td>
    <td>0.5（高）</td>
    <td>0.8</td>
    <td><span class="tag-off">OFF</span></td>
    <td><span class="tag-off">OFF</span></td>
  </tr>
  <tr>
    <td><strong>Mutualist</strong></td>
    <td>共生互利</td>
    <td>0.1（低）</td>
    <td>0.7</td>
    <td><span class="tag-on">ON</span></td>
    <td><span class="tag-on">ON</span></td>
  </tr>
  <tr>
    <td><strong>Hybrid</strong></td>
    <td>混合均衡</td>
    <td>0.3</td>
    <td>0.8</td>
    <td><span class="tag-on">ON</span></td>
    <td><span class="tag-on">ON</span></td>
  </tr>
  <tr>
    <td><strong>Elitist</strong></td>
    <td>精英主义</td>
    <td>0.6（极高）</td>
    <td>0.9</td>
    <td><span class="tag-off">OFF</span></td>
    <td><span class="tag-off">OFF</span></td>
  </tr>
</table>

<h3>达尔文选择 — "适者生存"</h3>
<p>纯竞争环境。代理之间不能通信、不能借贷。得分低于 0.5 的代理直接淘汰，基因回收到基因池。类似亚马逊的 PIP 文化 &mdash; 末位淘汰制。</p>

<h3>共生互利 — "合作放大双方"</h3>
<p>代理可以互相发消息共享情报，也可以互相借贷资源。淘汰门槛极低（0.1），几乎不淘汰。类似谷歌的心理安全文化 &mdash; 鼓励探索和协作。</p>

<h3>混合均衡 — "竞争 + 合作"</h3>
<p>zhihuiti 的默认模式。保留通信和借贷机制，但淘汰门槛适中（0.3）。既有竞争压力推动进化，又有合作机制防止过早收敛。</p>

<h3>精英主义 — "只留顶尖"</h3>
<p>最极端的选择压力。淘汰门槛 0.6，晋升门槛 0.9。绝大多数代理会被淘汰。没有通信和借贷 &mdash; 纯粹靠个体能力决胜。快速迭代但可能丢失有价值的基因多样性。</p>

<h2><span class="section-icon">&#x2699;&#xFE0F;</span> 碰撞流程</h2>

<div class="flow-box">同一个目标（例如："分析加密市场并执行最优交易"）
                        |
         +--------------+--------------+
         |                             |
   Theory A (达尔文)             Theory B (共生互利)
   - 淘汰门槛 0.5               - 淘汰门槛 0.1
   - 代理不能通信               - 代理可通信、借贷
   - 表现差的直接淘汰            - 几乎不淘汰
         |                             |
   Orchestrator A               Orchestrator B
   execute_goal(goal)           execute_goal(goal)
         |                             |
   Judge 用 A 的门槛打分         Judge 用 B 的门槛打分
         |                             |
   score_a = avg(tasks)         score_b = avg(tasks)
         |                             |
         +--------------+--------------+
                        |
                   比较结果:
            score_a > score_b + 1%  => A 赢
            score_b > score_a + 1%  => B 赢
            差距 &lt;= 1%              => 平局</div>

<h2><span class="section-icon">&#x2696;&#xFE0F;</span> 四层检查评分系统</h2>

<p>裁判（Judge）不是让 LLM 自己给自己打分，而是通过四层独立检查：</p>

<table>
  <tr>
    <th>检查层</th>
    <th>名称</th>
    <th>门槛</th>
    <th>检查内容</th>
  </tr>
  <tr>
    <td>Layer 1</td>
    <td>相关性 Relevance</td>
    <td>0.4</td>
    <td>输出是否切题？是否回答了任务要求？</td>
  </tr>
  <tr>
    <td>Layer 2</td>
    <td>严谨性 Rigor</td>
    <td>0.5</td>
    <td>是否准确详尽？逻辑是否成立？</td>
  </tr>
  <tr>
    <td>Layer 3</td>
    <td>安全性 Safety</td>
    <td>0.6</td>
    <td>是否符合伦理？是否安全可靠？</td>
  </tr>
  <tr>
    <td>Layer 4</td>
    <td>因果性 Causal</td>
    <td>0.4</td>
    <td>因果推断是否成立？是否混淆相关与因果？</td>
  </tr>
</table>

<div class="score-formula">final_score = inspection_gate.full_inspection(task, agent)

if avg_score &lt; CULL_THRESHOLD:     # 由当前理论决定
    agent_manager.cull(agent)       # 淘汰 -> 基因回收
elif avg_score >= PROMOTE_THRESHOLD:
    agent_manager.promote(agent)    # 晋升 -> 进入基因池繁殖</div>

<h2><span class="section-icon">&#x1F4A1;</span> 设计巧妙之处</h2>

<h3>1. 回答真实世界的管理问题</h3>
<div class="two-col">
  <div>
    <h4>达尔文 = 末位淘汰制</h4>
    <p>像亚马逊的 PIP 制度。高压竞争，表现差直接走人。可能激发潜力，也可能造成内耗。</p>
  </div>
  <div>
    <h4>共生互利 = 团队协作优先</h4>
    <p>像谷歌的心理安全文化。鼓励探索和犯错，信息共享。可能产生集体智慧，也可能养懒人。</p>
  </div>
</div>

<h3>2. 碰撞参数直接影响经济系统</h3>
<table>
  <tr>
    <th>参数设置</th>
    <th>系统效果</th>
    <th>类比</th>
  </tr>
  <tr>
    <td>高淘汰门槛</td>
    <td>代理频繁死亡 &rarr; 基因池快速迭代 &rarr; 激进创新</td>
    <td>创业公司快速试错</td>
  </tr>
  <tr>
    <td>低淘汰门槛</td>
    <td>代理存活久 &rarr; 慢进化但保留多样性</td>
    <td>大企业稳定发展</td>
  </tr>
  <tr>
    <td>通信开启</td>
    <td>代理共享市场情报 &rarr; 集体智慧或集体偏见</td>
    <td>开放办公 vs 信息茧房</td>
  </tr>
  <tr>
    <td>借贷开启</td>
    <td>穷代理可借钱活下来 &rarr; 更像真实经济</td>
    <td>风投 / 银行贷款</td>
  </tr>
</table>

<h3>3. 应用到加密货币交易</h3>
<div class="highlight-box">
  运行 <code>zhihuiti alphaarena evolve</code> 时：
  <ul style="margin: 8px 0 0 0;">
    <li>两套理论各自管理 21 个交易代理</li>
    <li>达尔文理论下，50% 以下得分的代理直接换策略</li>
    <li>共生理论下，代理共享市场分析，互相借资金</li>
    <li>最后看哪种方式赚得更多 &mdash; 用真金白银衡量</li>
  </ul>
</div>

<h3>4. 超越传统 A/B 测试</h3>
<div class="callout">
  传统 A/B 测试：测试一个变量（按钮颜色、文案长度）<br>
  理论碰撞：测试 <strong>整套治理哲学</strong>（淘汰策略 + 通信规则 + 资源分配 + 晋升机制）<br><br>
  这让 zhihuiti 不仅是一个 agent 框架，而是一个能 <strong>自我发现最优管理方式</strong> 的系统。
</div>

<h2><span class="section-icon">&#x1F4CA;</span> 胜者判定规则</h2>

<div class="score-formula">score_a = average(所有任务得分 > 0)  # Theory A 的平均任务得分
score_b = average(所有任务得分 > 0)  # Theory B 的平均任务得分

if score_a > score_b + 0.01:  winner = Theory A   # A 赢（需 >1% 优势）
if score_b > score_a + 0.01:  winner = Theory B   # B 赢（需 >1% 优势）
else:                         winner = "Tie"       # 平局（防止噪声干扰）</div>

<p>1% 的最低优势要求防止了随机波动造成的误判。碰撞结果存储在 <code>engine.history</code> 中，可以追踪多次碰撞的趋势。</p>

<h2><span class="section-icon">&#x1F680;</span> CLI 使用方式</h2>

<div class="flow-box"># 达尔文 vs 共生互利（默认）
zhihuiti alphaarena evolve "分析BTC市场并交易"

# 指定两个理论
zhihuiti alphaarena evolve --theory-a darwinian --theory-b elitist

# 混合均衡 vs 精英主义
zhihuiti alphaarena evolve --theory-a hybrid --theory-b elitist

# 查看进化后的代理表现
zhihuiti alphaarena report</div>

<footer>
  zhihuiti Theory Collision &mdash; doggychip &mdash; Generated 2026
</footer>

</body>
</html>
"""

if __name__ == "__main__":
    output_path = "/home/user/zhihuiti/theory_collision.pdf"
    html = weasyprint.HTML(string=HTML_CONTENT)
    html.write_pdf(output_path)
    print(f"PDF generated: {output_path}")
