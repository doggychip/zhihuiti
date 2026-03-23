#!/bin/bash
# Sync zhihuiti frontend code to the Lovable-connected GitHub repo.
#
# Usage:
#   ./scripts/sync-to-lovable.sh
#
# Prerequisites:
#   - The Lovable repo must be cloned at ../pixel-perfect-replica-51aecdac
#     OR pass the path as first argument:
#     ./scripts/sync-to-lovable.sh /path/to/pixel-perfect-replica-51aecdac

set -euo pipefail

LOVABLE_DIR="${1:-../pixel-perfect-replica-51aecdac}"
ZHIHUITI_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$LOVABLE_DIR/.git" ]; then
  echo "Error: $LOVABLE_DIR is not a git repo."
  echo "Clone it first: git clone https://github.com/doggychip/pixel-perfect-replica-51aecdac.git $LOVABLE_DIR"
  exit 1
fi

echo "Syncing zhihuiti frontend → Lovable repo..."
echo "  Source: $ZHIHUITI_DIR"
echo "  Target: $LOVABLE_DIR"

# Clean target (preserve .git and Lovable config)
cd "$LOVABLE_DIR"
find . -maxdepth 1 ! -name '.git' ! -name '.' ! -name '..' -exec rm -rf {} +

# Copy frontend source (Lovable expects src/ at root)
cp -r "$ZHIHUITI_DIR/client/src" "$LOVABLE_DIR/src"
cp "$ZHIHUITI_DIR/client/index.html" "$LOVABLE_DIR/index.html"

# Copy config files
cp "$ZHIHUITI_DIR/tailwind.config.ts" "$LOVABLE_DIR/tailwind.config.ts"
cp "$ZHIHUITI_DIR/postcss.config.js" "$LOVABLE_DIR/postcss.config.js"
cp "$ZHIHUITI_DIR/components.json" "$LOVABLE_DIR/components.json"

# Create Lovable-compatible tsconfig (paths adjusted for root-level src/)
cat > "$LOVABLE_DIR/tsconfig.json" << 'TSEOF'
{
  "include": ["src/**/*"],
  "exclude": ["node_modules", "build", "dist"],
  "compilerOptions": {
    "noEmit": true,
    "module": "ESNext",
    "strict": true,
    "lib": ["esnext", "dom", "dom.iterable"],
    "jsx": "react-jsx",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "allowImportingTsExtensions": true,
    "moduleResolution": "bundler",
    "baseUrl": ".",
    "types": ["vite/client"],
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
TSEOF

# Create Lovable-compatible vite config (src/ at root, not client/src/)
cat > "$LOVABLE_DIR/vite.config.ts" << 'VEOF'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
VEOF

# Create package.json with same deps (frontend only)
cat > "$LOVABLE_DIR/package.json" << 'PEOF'
{
  "name": "zhihuiti-ui",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@hookform/resolvers": "^3.10.0",
    "@radix-ui/react-accordion": "^1.2.4",
    "@radix-ui/react-alert-dialog": "^1.1.7",
    "@radix-ui/react-aspect-ratio": "^1.1.3",
    "@radix-ui/react-avatar": "^1.1.4",
    "@radix-ui/react-checkbox": "^1.1.5",
    "@radix-ui/react-collapsible": "^1.1.4",
    "@radix-ui/react-context-menu": "^2.2.7",
    "@radix-ui/react-dialog": "^1.1.7",
    "@radix-ui/react-dropdown-menu": "^2.1.7",
    "@radix-ui/react-hover-card": "^1.1.7",
    "@radix-ui/react-label": "^2.1.3",
    "@radix-ui/react-menubar": "^1.1.7",
    "@radix-ui/react-navigation-menu": "^1.2.6",
    "@radix-ui/react-popover": "^1.1.7",
    "@radix-ui/react-progress": "^1.1.3",
    "@radix-ui/react-radio-group": "^1.2.4",
    "@radix-ui/react-scroll-area": "^1.2.4",
    "@radix-ui/react-select": "^2.1.7",
    "@radix-ui/react-separator": "^1.1.3",
    "@radix-ui/react-slider": "^1.2.4",
    "@radix-ui/react-slot": "^1.2.0",
    "@radix-ui/react-switch": "^1.1.4",
    "@radix-ui/react-tabs": "^1.1.4",
    "@radix-ui/react-toast": "^1.2.7",
    "@radix-ui/react-toggle": "^1.1.3",
    "@radix-ui/react-toggle-group": "^1.1.3",
    "@radix-ui/react-tooltip": "^1.2.0",
    "@tanstack/react-query": "^5.60.5",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "cmdk": "^1.1.1",
    "date-fns": "^3.6.0",
    "embla-carousel-react": "^8.6.0",
    "input-otp": "^1.4.2",
    "lucide-react": "^0.453.0",
    "react": "^18.3.1",
    "react-day-picker": "^8.10.1",
    "react-dom": "^18.3.1",
    "react-hook-form": "^7.55.0",
    "react-resizable-panels": "^2.1.7",
    "recharts": "^2.15.2",
    "tailwind-merge": "^2.6.0",
    "tailwindcss-animate": "^1.0.7",
    "vaul": "^1.1.2",
    "wouter": "^3.3.5",
    "zod": "^3.24.2"
  },
  "devDependencies": {
    "@tailwindcss/typography": "^0.5.15",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.7.0",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.17",
    "typescript": "5.6.3",
    "vite": "^7.3.0"
  }
}
PEOF

# Fix tailwind content paths (client/src → src)
sed -i 's|./client/index.html|./index.html|g' "$LOVABLE_DIR/tailwind.config.ts"
sed -i 's|./client/src|./src|g' "$LOVABLE_DIR/tailwind.config.ts"

# Fix components.json paths
sed -i 's|client/src/index.css|src/index.css|g' "$LOVABLE_DIR/components.json"

# Remove any @shared imports (backend-only) — replace with inline types if needed
# For now just check if any exist
SHARED_IMPORTS=$(grep -rl "@shared" "$LOVABLE_DIR/src" 2>/dev/null || true)
if [ -n "$SHARED_IMPORTS" ]; then
  echo ""
  echo "WARNING: These files import from @shared (backend types):"
  echo "$SHARED_IMPORTS"
  echo "You may need to copy shared/schema.ts or create type stubs."
fi

echo ""
echo "Done! Now run:"
echo "  cd $LOVABLE_DIR"
echo "  git add -A"
echo "  git commit -m 'sync: import zhihuiti frontend'"
echo "  git push origin main"
echo ""
echo "Lovable will auto-detect the push and sync."
