#!/bin/bash
# Setup zhihuiti as MCP sub-agent provider for any project.
#
# Usage:
#   cd /path/to/your-project
#   bash /path/to/zhihuiti/scripts/setup-zhihuiti-mcp.sh
#
# This adds zhihuiti's MCP server to your project's Claude Code settings,
# giving Claude access to zhihuiti's agent swarm as sub-agents:
#   - zhihuiti_execute_goal: decompose + auction + parallel execution
#   - zhihuiti_execute_task: single agent with specific role
#   - zhihuiti_list_agents: see alive agents with scores
#   - zhihuiti_system_status: economy + agent health
#   - zhihuiti_find_analogies: cross-domain theory search
#   - zhihuiti_crypto_diagnose: market pattern detection
#   - criticai_status/analyze: CriticAI monitoring
#
# Prerequisites:
#   pip install -e /path/to/zhihuiti/zhihuiti
#   export OPENROUTER_API_KEY=sk-or-...

set -e

SETTINGS_DIR=".claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"

# Detect zhihuiti installation
ZHIHUITI_DB="${ZHIHUITI_DB:-$HOME/.zhihuiti/zhihuiti.db}"

echo "Setting up zhihuiti MCP agent provider..."

# Create .claude directory if needed
mkdir -p "$SETTINGS_DIR"

# Create or update settings.json
if [ -f "$SETTINGS_FILE" ]; then
    # Merge into existing settings using python
    python3 -c "
import json, sys

with open('$SETTINGS_FILE') as f:
    settings = json.load(f)

settings.setdefault('mcpServers', {})
settings['mcpServers']['zhihuiti'] = {
    'command': 'python',
    'args': ['-m', 'zhihuiti.mcp_server'],
    'env': {
        'ZHIHUITI_DB': '$ZHIHUITI_DB',
        'ZHIHUITI_TOOLS': 'true'
    }
}

with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')

print(f'  Updated {\"$SETTINGS_FILE\"} with zhihuiti MCP server')
"
else
    cat > "$SETTINGS_FILE" << 'EOF'
{
  "mcpServers": {
    "zhihuiti": {
      "command": "python",
      "args": ["-m", "zhihuiti.mcp_server"],
      "env": {
        "ZHIHUITI_DB": "~/.zhihuiti/zhihuiti.db",
        "ZHIHUITI_TOOLS": "true"
      }
    }
  }
}
EOF
    echo "  Created $SETTINGS_FILE with zhihuiti MCP server"
fi

# Create shared DB directory
mkdir -p "$(dirname "$ZHIHUITI_DB")"

echo ""
echo "Done! zhihuiti agents are now available in this project."
echo ""
echo "Available tools in Claude Code:"
echo "  zhihuiti_execute_goal  — Full multi-agent pipeline (decompose → auction → execute → score)"
echo "  zhihuiti_execute_task  — Single agent task (researcher/analyst/coder/trader/strategist)"
echo "  zhihuiti_list_agents   — List alive agents with scores and budgets"
echo "  zhihuiti_system_status — Economy and system health"
echo "  + 10 more tools (theory graph, crypto oracle, CriticAI)"
echo ""
echo "All agents share state via: $ZHIHUITI_DB"
