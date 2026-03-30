# Theory Collision Map — Lovable Integration

## Quick Start

1. Copy these files into your Lovable project:
   - `collision-graph-data.ts` → `src/data/collision-graph-data.ts`
   - `CollisionGraph.tsx` → `src/components/CollisionGraph.tsx`

2. Install d3:
   ```
   npm install d3 @types/d3
   ```

3. Use in any page:
   ```tsx
   import CollisionGraph from "@/components/CollisionGraph";

   export default function CollisionMapPage() {
     return (
       <div style={{ width: "100vw", height: "100vh" }}>
         <CollisionGraph />
       </div>
     );
   }
   ```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `width` | number | window.innerWidth | Canvas width |
| `height` | number | window.innerHeight | Canvas height |
| `minScore` | number | 0.05 | Min collision score to show edges |

## Features

- Force-directed graph with D3.js v7
- Domain-colored nodes with glow effects
- Edge thickness/color by collision strength (deep/significant/resonance/weak)
- Interactive tooltips showing equations, shared patterns, structural bridges
- Threshold slider to filter collisions in real-time
- Link opacity control
- Zoom/pan/drag support
- Dark theme optimized for Lovable

## Lovable Prompt

If you want Lovable AI to set this up, paste:

> Create a new page at /collision-map that renders the CollisionGraph component
> full-screen. Add a route for it in the router. The component uses D3.js for
> a force-directed graph visualization with a dark background (#0a0a1a).
