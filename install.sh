#!/usr/bin/env bash
# zhihuiti — one-click install for Claude Code Desktop integration
# Usage: curl -s <repo>/install.sh | bash
#   or:  ./install.sh

set -euo pipefail

REPO_URL="https://github.com/doggychip/zhihuiti.git"
INSTALL_DIR="${ZHIHUITI_HOME:-$HOME/zhihuiti}"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
DATA_DIR="$INSTALL_DIR/zhihuiti/data"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[zhihuiti]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Step 1: Check Python ──
info "Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    fail "Python 3.10+ is required. Install from https://python.org"
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    fail "Python 3.10+ required, found $PY_VERSION"
fi
ok "Python $PY_VERSION ($PYTHON)"

# ── Step 2: Check git ──
if ! command -v git &>/dev/null; then
    fail "git is required. Install from https://git-scm.com"
fi
ok "git found"

# ── Step 3: Clone or update repo ──
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing repo at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || warn "Pull failed, using existing code"
    ok "Repo updated"
else
    info "Cloning to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || fail "Clone failed. Check your access to $REPO_URL"
    ok "Cloned"
fi

# ── Step 4: Install Python package ──
info "Installing zhihuiti Python package..."
cd "$INSTALL_DIR/zhihuiti"
$PYTHON -m pip install -e . --quiet 2>/dev/null || $PYTHON -m pip install -e . 2>&1
ok "zhihuiti installed"

# ── Step 5: Create data directory ──
mkdir -p "$DATA_DIR"
ok "Data directory: $DATA_DIR"

# ── Step 6: Verify MCP server ──
info "Testing MCP server..."
RESULT=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
    | $PYTHON -c "
import sys
msg = sys.stdin.read()
sys.stdout.write(f'Content-Length: {len(msg)}\r\n\r\n{msg}')
sys.stdout.flush()
" | timeout 5 $PYTHON -m zhihuiti.mcp_server 2>/dev/null \
    | $PYTHON -c "
import sys, re, json
data = sys.stdin.read()
for m in re.findall(r'\{.*\}', data, re.DOTALL):
    try:
        obj = json.loads(m)
        if 'result' in obj:
            print('OK')
            break
    except: pass
" 2>/dev/null || echo "")

if [ "$RESULT" = "OK" ]; then
    ok "MCP server works"
else
    warn "MCP server test inconclusive (may still work with Claude Code)"
fi

# ── Step 7: Configure Claude Code ──
info "Configuring Claude Code Desktop..."

MCP_CONFIG=$(cat <<JSONEOF
{
    "command": "$PYTHON",
    "args": ["-m", "zhihuiti.mcp_server"],
    "cwd": "$INSTALL_DIR/zhihuiti",
    "env": {
        "ZHIHUITI_DB": "$DATA_DIR/zhihuiti.db"
    }
}
JSONEOF
)

mkdir -p "$HOME/.claude"

if [ -f "$CLAUDE_SETTINGS" ]; then
    # Merge into existing settings
    HAS_MCP=$($PYTHON -c "
import json
with open('$CLAUDE_SETTINGS') as f:
    d = json.load(f)
print('yes' if 'mcpServers' in d else 'no')
" 2>/dev/null || echo "no")

    $PYTHON -c "
import json

with open('$CLAUDE_SETTINGS') as f:
    settings = json.load(f)

settings.setdefault('mcpServers', {})
settings['mcpServers']['zhihuiti'] = json.loads('''$MCP_CONFIG''')

with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
print('merged')
" 2>/dev/null && ok "Merged into existing $CLAUDE_SETTINGS" || {
        warn "Could not merge settings automatically"
        echo ""
        echo "Add this to $CLAUDE_SETTINGS manually:"
        echo ""
        echo "  \"mcpServers\": {"
        echo "    \"zhihuiti\": $MCP_CONFIG"
        echo "  }"
    }
else
    # Create new settings file
    $PYTHON -c "
import json
settings = {
    'mcpServers': {
        'zhihuiti': json.loads('''$MCP_CONFIG''')
    }
}
with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
" 2>/dev/null
    ok "Created $CLAUDE_SETTINGS"
fi

# ── Step 8: API key reminder ──
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} zhihuiti installed successfully!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e " ${CYAN}Location:${NC}    $INSTALL_DIR"
echo -e " ${CYAN}MCP Server:${NC}  $PYTHON -m zhihuiti.mcp_server"
echo -e " ${CYAN}Config:${NC}      $CLAUDE_SETTINGS"
echo ""
echo -e " ${CYAN}Skills available in project directory:${NC}"
echo "   /oracle    — crypto market analysis"
echo "   /agents    — multi-agent system management"
echo "   /theory    — 378-theory knowledge graph"
echo "   /diagnose  — universal time series diagnosis"
echo ""
echo -e " ${YELLOW}Optional: set LLM API key for agent features:${NC}"
echo "   export OPENROUTER_API_KEY=sk-or-v1-xxx"
echo "   export DEEPSEEK_API_KEY=sk-xxx"
echo ""
echo -e " ${GREEN}Restart Claude Code Desktop to activate.${NC}"
