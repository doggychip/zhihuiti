#!/bin/bash
# Setup zhihuiti MCP agents across ALL doggychip repos.
#
# Usage:
#   cd /path/to/parent-dir   # where all repos are cloned
#   bash /path/to/zhihuiti/scripts/setup-all-repos.sh
#
# Or clone + setup everything:
#   bash /path/to/zhihuiti/scripts/setup-all-repos.sh --clone

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_SCRIPT="$SCRIPT_DIR/setup-zhihuiti-mcp.sh"

# Repos that benefit from zhihuiti agents
REPOS=(
    "agentforge"
    "pokescope"
    "knowledge-graph"
    "causal-engine"
    "openclaw-family-plugin"
    "zhihuiti-city"
    "heartai"
    "AlphaArena"
    "alphaarena-mobile"
    "alphaarena-skill"
    "alphaarena-hedge-fund"
    "alphaarena-agents"
    "hk-news"
    "guanxing-skill"
    "plugin-guanxing"
    "guanxing-mcp"
)

CLONE_MODE=false
if [ "$1" = "--clone" ]; then
    CLONE_MODE=true
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║  zhihuiti MCP Agent Setup — All Repos           ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

SUCCESS=0
SKIPPED=0
CLONED=0

for repo in "${REPOS[@]}"; do
    if [ ! -d "$repo" ]; then
        if [ "$CLONE_MODE" = true ]; then
            echo "Cloning $repo..."
            git clone "https://github.com/doggychip/$repo.git" 2>/dev/null || {
                echo "  ✗ Failed to clone $repo"
                SKIPPED=$((SKIPPED + 1))
                continue
            }
            CLONED=$((CLONED + 1))
        else
            echo "  ⊘ $repo — not found (use --clone to auto-clone)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    fi

    echo "Setting up $repo..."
    (cd "$repo" && bash "$SETUP_SCRIPT")
    SUCCESS=$((SUCCESS + 1))
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  Setup complete: $SUCCESS configured, $SKIPPED skipped, $CLONED cloned"
echo ""
echo "  Shared agent state: ~/.zhihuiti/zhihuiti.db"
echo "  All repos now have zhihuiti agents as sub-agents."
echo "════════════════════════════════════════════════════"
