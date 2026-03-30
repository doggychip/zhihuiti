import { useState, useRef, useMemo, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Text, Billboard, Stars, Float, Trail } from "@react-three/drei";
import * as THREE from "three";
import { motion, AnimatePresence } from "framer-motion";

// ═══════════════════════════════════════════════════════════════════
// DATA — Theories & Dynamics from zhihuiti
// ═══════════════════════════════════════════════════════════════════

const THEORIES = {
  darwinian: {
    label: "Darwinian Selection",
    icon: "🧬",
    description: "Survival of the fittest — pure competition, aggressive culling",
    color: "#ef4444",
    cull: 0.5, promote: 0.8,
    messaging: false, lending: false,
    position: [-4, 2, 0],
  },
  mutualist: {
    label: "Symbiotic Mutualism",
    icon: "🤝",
    description: "Cooperation amplifies both — messaging, lending, gentle culling",
    color: "#22c55e",
    cull: 0.1, promote: 0.7,
    messaging: true, lending: true,
    position: [4, 2, 0],
  },
  hybrid: {
    label: "Hybrid Equilibrium",
    icon: "⚡",
    description: "Default zhihuiti — competition + cooperation balanced",
    color: "#a855f7",
    cull: 0.3, promote: 0.8,
    messaging: true, lending: true,
    position: [0, -3, 2],
  },
  elitist: {
    label: "Elite Meritocracy",
    icon: "👑",
    description: "Only the top performers survive — extreme selection pressure",
    color: "#eab308",
    cull: 0.6, promote: 0.9,
    messaging: false, lending: false,
    position: [0, 3, -3],
  },
};

const DYNAMICS = [
  { id: "replicator", label: "Replicator Dynamics", icon: "🔄", color: "#f97316", desc: "Strategy frequencies evolve by fitness — above-mean strategies spread" },
  { id: "thermodynamics", label: "Statistical Mechanics", icon: "🌡️", color: "#3b82f6", desc: "Temperature + entropy of the token economy" },
  { id: "bellman", label: "Bellman Control", icon: "🎯", color: "#22c55e", desc: "Value functions guide agent migration between realms" },
  { id: "criticality", label: "Self-Organized Criticality", icon: "⚡", color: "#eab308", desc: "Phase transitions & wealth avalanches at critical points" },
  { id: "info_geometry", label: "Information Geometry", icon: "📐", color: "#a855f7", desc: "Fisher information + KL divergence on wealth manifold" },
];

// Pre-generate some collision results for visualization
const COLLISION_HISTORY = [
  { a: "darwinian", b: "mutualist", scoreA: 0.72, scoreB: 0.81, goal: "Market analysis" },
  { a: "hybrid", b: "elitist", scoreA: 0.85, scoreB: 0.78, goal: "Code review" },
  { a: "darwinian", b: "hybrid", scoreA: 0.65, scoreB: 0.79, goal: "Research synthesis" },
  { a: "mutualist", b: "elitist", scoreA: 0.77, scoreB: 0.69, goal: "Risk assessment" },
  { a: "darwinian", b: "elitist", scoreA: 0.71, scoreB: 0.74, goal: "Trade execution" },
  { a: "mutualist", b: "hybrid", scoreA: 0.82, scoreB: 0.84, goal: "Strategic planning" },
];


// ═══════════════════════════════════════════════════════════════════
// 3D COMPONENTS
// ═══════════════════════════════════════════════════════════════════

function TheoryNode({ theory, id, isSelected, isColliding, onClick, collisionTarget }) {
  const meshRef = useRef();
  const glowRef = useRef();
  const pos = theory.position;

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.position.y = pos[1] + Math.sin(t * 0.5 + pos[0]) * 0.15;
      const scale = isSelected ? 1.3 : isColliding ? 1.15 : 1.0;
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.05);
    }
    if (glowRef.current) {
      glowRef.current.material.opacity = 0.15 + Math.sin(t * 2) * 0.05 + (isColliding ? 0.15 : 0);
    }
  });

  return (
    <group ref={meshRef} position={pos} onClick={(e) => { e.stopPropagation(); onClick(id); }}>
      {/* Outer glow */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[0.9, 32, 32]} />
        <meshBasicMaterial color={theory.color} transparent opacity={0.15} />
      </mesh>

      {/* Core sphere */}
      <mesh>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color={theory.color}
          emissive={theory.color}
          emissiveIntensity={isColliding ? 1.2 : isSelected ? 0.8 : 0.4}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>

      {/* Inner bright core */}
      <mesh>
        <sphereGeometry args={[0.2, 16, 16]} />
        <meshBasicMaterial color="white" transparent opacity={0.6} />
      </mesh>

      {/* Label */}
      <Billboard position={[0, 1.1, 0]}>
        <Text fontSize={0.22} color="white" anchorX="center" anchorY="bottom" font={undefined}>
          {theory.icon} {theory.label}
        </Text>
        <Text fontSize={0.12} color="rgba(255,255,255,0.4)" anchorX="center" anchorY="top" position={[0, -0.05, 0]} font={undefined}>
          cull:{theory.cull} promote:{theory.promote}
        </Text>
      </Billboard>
    </group>
  );
}


function CollisionBeam({ from, to, score, winner, active }) {
  const lineRef = useRef();
  const particlesRef = useRef();

  const posFrom = useMemo(() => new THREE.Vector3(...THEORIES[from].position), [from]);
  const posTo = useMemo(() => new THREE.Vector3(...THEORIES[to].position), [to]);
  const midPoint = useMemo(() => {
    const mid = posFrom.clone().add(posTo).multiplyScalar(0.5);
    mid.y += 1.5;
    return mid;
  }, [posFrom, posTo]);

  const curve = useMemo(
    () => new THREE.QuadraticBezierCurve3(posFrom, midPoint, posTo),
    [posFrom, midPoint, posTo]
  );
  const points = useMemo(() => curve.getPoints(50), [curve]);
  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

  const winnerColor = winner === from ? THEORIES[from].color : THEORIES[to].color;

  // Particle positions along the beam
  const particleCount = 12;
  const particlePositions = useMemo(() => new Float32Array(particleCount * 3), []);
  const particleSizes = useMemo(() => new Float32Array(particleCount).fill(0.06), []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (lineRef.current) {
      lineRef.current.material.opacity = active ? 0.6 + Math.sin(t * 3) * 0.2 : 0.1;
    }
    // Animate particles along curve
    if (particlesRef.current) {
      for (let i = 0; i < particleCount; i++) {
        const progress = ((t * 0.3 + i / particleCount) % 1);
        const point = curve.getPoint(progress);
        particlePositions[i * 3] = point.x;
        particlePositions[i * 3 + 1] = point.y + Math.sin(t * 4 + i) * 0.05;
        particlePositions[i * 3 + 2] = point.z;
      }
      particlesRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <group>
      <line ref={lineRef} geometry={geometry}>
        <lineBasicMaterial color={winnerColor} transparent opacity={0.15} linewidth={1} />
      </line>

      {active && (
        <points ref={particlesRef}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              count={particleCount}
              array={particlePositions}
              itemSize={3}
            />
            <bufferAttribute
              attach="attributes-size"
              count={particleCount}
              array={particleSizes}
              itemSize={1}
            />
          </bufferGeometry>
          <pointsMaterial
            color={winnerColor}
            size={0.08}
            transparent
            opacity={0.8}
            sizeAttenuation
          />
        </points>
      )}
    </group>
  );
}


function DynamicsRing() {
  const groupRef = useRef();

  useFrame(({ clock }) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = clock.getElapsedTime() * 0.08;
    }
  });

  return (
    <group ref={groupRef}>
      {DYNAMICS.map((d, i) => {
        const angle = (i / DYNAMICS.length) * Math.PI * 2;
        const r = 7;
        const x = Math.cos(angle) * r;
        const z = Math.sin(angle) * r;
        return (
          <group key={d.id} position={[x, 0, z]}>
            <Float speed={2} floatIntensity={0.3}>
              <mesh>
                <octahedronGeometry args={[0.25, 0]} />
                <meshStandardMaterial
                  color={d.color}
                  emissive={d.color}
                  emissiveIntensity={0.6}
                  wireframe
                />
              </mesh>
            </Float>
            <Billboard position={[0, 0.6, 0]}>
              <Text fontSize={0.15} color={d.color} anchorX="center" font={undefined}>
                {d.icon} {d.label}
              </Text>
            </Billboard>
          </group>
        );
      })}

      {/* Connecting ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[7, 0.005, 8, 100]} />
        <meshBasicMaterial color="#333" transparent opacity={0.3} />
      </mesh>
    </group>
  );
}


function CollisionExplosion({ position, color, active }) {
  const ref = useRef();
  const count = 30;

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 0.1;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 0.1;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 0.1;
    }
    return arr;
  }, []);

  const velocities = useMemo(() => {
    const arr = [];
    for (let i = 0; i < count; i++) {
      arr.push(new THREE.Vector3(
        (Math.random() - 0.5) * 2,
        (Math.random() - 0.5) * 2,
        (Math.random() - 0.5) * 2,
      ));
    }
    return arr;
  }, []);

  useFrame(({ clock }) => {
    if (!ref.current || !active) return;
    const t = (clock.getElapsedTime() * 2) % 3;
    const posAttr = ref.current.geometry.attributes.position;

    for (let i = 0; i < count; i++) {
      posAttr.array[i * 3] = velocities[i].x * t * 0.5;
      posAttr.array[i * 3 + 1] = velocities[i].y * t * 0.5;
      posAttr.array[i * 3 + 2] = velocities[i].z * t * 0.5;
    }
    posAttr.needsUpdate = true;
    ref.current.material.opacity = Math.max(0, 1 - t / 2);
  });

  if (!active) return null;

  return (
    <points ref={ref} position={position}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color={color} size={0.06} transparent opacity={1} sizeAttenuation />
    </points>
  );
}


function Scene({ selectedTheory, activeCollision, onSelectTheory }) {
  return (
    <>
      <ambientLight intensity={0.2} />
      <pointLight position={[10, 10, 10]} intensity={0.8} color="#6366f1" />
      <pointLight position={[-10, -5, 5]} intensity={0.5} color="#f97316" />
      <pointLight position={[0, -10, -10]} intensity={0.3} color="#22c55e" />

      <Stars radius={50} depth={50} count={2000} factor={3} saturation={0.3} fade speed={0.5} />

      {/* Theory nodes */}
      {Object.entries(THEORIES).map(([id, theory]) => (
        <TheoryNode
          key={id}
          id={id}
          theory={theory}
          isSelected={selectedTheory === id}
          isColliding={activeCollision && (activeCollision.a === id || activeCollision.b === id)}
          onClick={onSelectTheory}
        />
      ))}

      {/* Collision beams */}
      {COLLISION_HISTORY.map((c, i) => (
        <CollisionBeam
          key={i}
          from={c.a}
          to={c.b}
          score={Math.max(c.scoreA, c.scoreB)}
          winner={c.scoreA >= c.scoreB ? c.a : c.b}
          active={activeCollision && activeCollision.a === c.a && activeCollision.b === c.b}
        />
      ))}

      {/* Collision explosion */}
      {activeCollision && (
        <CollisionExplosion
          position={[
            (THEORIES[activeCollision.a].position[0] + THEORIES[activeCollision.b].position[0]) / 2,
            (THEORIES[activeCollision.a].position[1] + THEORIES[activeCollision.b].position[1]) / 2 + 0.75,
            (THEORIES[activeCollision.a].position[2] + THEORIES[activeCollision.b].position[2]) / 2,
          ]}
          color="white"
          active={true}
        />
      )}

      {/* Dynamics orbit ring */}
      <DynamicsRing />

      <OrbitControls
        enablePan={false}
        minDistance={6}
        maxDistance={20}
        autoRotate
        autoRotateSpeed={0.3}
      />
    </>
  );
}


// ═══════════════════════════════════════════════════════════════════
// UI OVERLAY
// ═══════════════════════════════════════════════════════════════════

function TheoryPanel({ theory, id, collisions }) {
  const wins = collisions.filter(c =>
    (c.a === id && c.scoreA > c.scoreB) || (c.b === id && c.scoreB > c.scoreA)
  ).length;
  const total = collisions.filter(c => c.a === id || c.b === id).length;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="absolute top-20 right-4 w-72 rounded-xl p-4 backdrop-blur-xl"
      style={{
        background: "rgba(10,10,20,0.85)",
        border: `1px solid ${theory.color}40`,
        boxShadow: `0 0 30px ${theory.color}20`,
      }}
    >
      <div className="text-lg font-bold mb-1" style={{ color: theory.color }}>
        {theory.icon} {theory.label}
      </div>
      <div className="text-xs text-gray-400 mb-3">{theory.description}</div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Cull Threshold</span>
          <span className="font-mono" style={{ color: "#ef4444" }}>{theory.cull}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Promote Threshold</span>
          <span className="font-mono" style={{ color: "#22c55e" }}>{theory.promote}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Messaging</span>
          <span>{theory.messaging ? "✅" : "❌"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Lending</span>
          <span>{theory.lending ? "✅" : "❌"}</span>
        </div>

        {/* Threshold bar */}
        <div className="pt-2">
          <div className="text-xs text-gray-500 mb-1">Selection Pressure</div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${theory.cull * 100}%`,
                background: `linear-gradient(90deg, transparent, ${theory.color})`,
              }}
            />
          </div>
        </div>

        {/* Win rate */}
        <div className="pt-2 border-t border-white/10">
          <div className="flex justify-between">
            <span className="text-gray-500">Win Rate</span>
            <span className="font-mono font-bold" style={{ color: theory.color }}>
              {total > 0 ? `${((wins / total) * 100).toFixed(0)}%` : "N/A"} ({wins}/{total})
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}


function CollisionPanel({ onCollide, activeCollision }) {
  const [theoryA, setTheoryA] = useState("darwinian");
  const [theoryB, setTheoryB] = useState("mutualist");

  return (
    <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-4 pointer-events-none">
      {/* Collision controls */}
      <div
        className="rounded-xl p-4 backdrop-blur-xl pointer-events-auto"
        style={{
          background: "rgba(10,10,20,0.85)",
          border: "1px solid rgba(168,85,247,0.3)",
          boxShadow: "0 0 40px rgba(168,85,247,0.1)",
        }}
      >
        <div className="text-xs uppercase tracking-widest mb-3" style={{ color: "#a855f7" }}>
          💥 Theory Collider
        </div>
        <div className="flex items-center gap-3">
          <select
            value={theoryA}
            onChange={(e) => setTheoryA(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none cursor-pointer"
          >
            {Object.entries(THEORIES).map(([id, t]) => (
              <option key={id} value={id} style={{ background: "#1a1a2e" }}>
                {t.icon} {t.label}
              </option>
            ))}
          </select>

          <button
            onClick={() => onCollide(theoryA, theoryB)}
            className="px-5 py-2 rounded-lg font-bold text-sm transition-all hover:scale-105 active:scale-95 cursor-pointer"
            style={{
              background: activeCollision
                ? "rgba(168,85,247,0.3)"
                : "linear-gradient(135deg, #ec4899, #a855f7, #6366f1)",
              color: "white",
              boxShadow: "0 0 20px rgba(168,85,247,0.3)",
            }}
          >
            {activeCollision ? "⏳ Colliding..." : "💥 COLLIDE"}
          </button>

          <select
            value={theoryB}
            onChange={(e) => setTheoryB(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white outline-none cursor-pointer"
          >
            {Object.entries(THEORIES).map(([id, t]) => (
              <option key={id} value={id} style={{ background: "#1a1a2e" }}>
                {t.icon} {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* Recent collision result */}
        {activeCollision && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 flex items-center justify-between text-sm"
          >
            <span style={{ color: THEORIES[activeCollision.a].color }}>
              {THEORIES[activeCollision.a].icon} {activeCollision.scoreA.toFixed(3)}
            </span>
            <span className="text-gray-500 text-xs">vs</span>
            <span style={{ color: THEORIES[activeCollision.b].color }}>
              {activeCollision.scoreB.toFixed(3)} {THEORIES[activeCollision.b].icon}
            </span>
            <span
              className="ml-3 px-2 py-0.5 rounded text-xs font-bold"
              style={{
                color: "white",
                background: activeCollision.scoreA >= activeCollision.scoreB
                  ? THEORIES[activeCollision.a].color
                  : THEORIES[activeCollision.b].color,
              }}
            >
              {activeCollision.scoreA >= activeCollision.scoreB
                ? THEORIES[activeCollision.a].label
                : THEORIES[activeCollision.b].label} wins
            </span>
          </motion.div>
        )}
      </div>

      {/* Dynamics legend */}
      <div
        className="rounded-xl p-3 backdrop-blur-xl pointer-events-auto"
        style={{
          background: "rgba(10,10,20,0.85)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="text-[10px] uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>
          5 Theoretical Dynamics (orbiting)
        </div>
        {DYNAMICS.map((d) => (
          <div key={d.id} className="flex items-center gap-2 py-0.5 text-xs group cursor-default" title={d.desc}>
            <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
            <span style={{ color: "rgba(255,255,255,0.5)" }}>{d.icon} {d.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}


function HistoryBar({ collisions, onSelect }) {
  return (
    <div className="absolute top-4 left-4 flex gap-2">
      {collisions.map((c, i) => {
        const winnerColor = c.scoreA >= c.scoreB ? THEORIES[c.a].color : THEORIES[c.b].color;
        return (
          <button
            key={i}
            onClick={() => onSelect(c)}
            className="px-3 py-1.5 rounded-lg text-xs backdrop-blur-xl transition-all hover:scale-105 cursor-pointer"
            style={{
              background: "rgba(10,10,20,0.7)",
              border: `1px solid ${winnerColor}40`,
            }}
            title={c.goal}
          >
            <span style={{ color: THEORIES[c.a].color }}>{THEORIES[c.a].icon}</span>
            <span className="mx-1 text-gray-600">vs</span>
            <span style={{ color: THEORIES[c.b].color }}>{THEORIES[c.b].icon}</span>
          </button>
        );
      })}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// APP
// ═══════════════════════════════════════════════════════════════════

export default function App() {
  const [selectedTheory, setSelectedTheory] = useState(null);
  const [activeCollision, setActiveCollision] = useState(null);
  const [collisions, setCollisions] = useState(COLLISION_HISTORY);

  const handleCollide = useCallback((a, b) => {
    if (a === b) return;

    // Simulate a collision result
    const scoreA = 0.5 + Math.random() * 0.4;
    const scoreB = 0.5 + Math.random() * 0.4;
    const result = { a, b, scoreA: +scoreA.toFixed(3), scoreB: +scoreB.toFixed(3), goal: "Live collision" };

    setActiveCollision(result);
    setCollisions(prev => [...prev, result]);

    // Clear active state after animation
    setTimeout(() => setActiveCollision(null), 4000);
  }, []);

  const handleSelectCollision = useCallback((c) => {
    setActiveCollision(c);
    setTimeout(() => setActiveCollision(null), 4000);
  }, []);

  return (
    <div className="w-full h-full relative">
      {/* 3D Scene */}
      <Canvas camera={{ position: [0, 3, 12], fov: 55 }} dpr={[1, 2]}>
        <Scene
          selectedTheory={selectedTheory}
          activeCollision={activeCollision}
          onSelectTheory={setSelectedTheory}
        />
      </Canvas>

      {/* Header */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 text-center pointer-events-none">
        <div className="text-xl font-bold tracking-wide" style={{ color: "rgba(255,255,255,0.9)" }}>
          <span style={{ background: "linear-gradient(135deg, #a855f7, #ec4899)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Theory Collider
          </span>
        </div>
        <div className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
          zhihuiti 智慧体 — How do governance theories perform when they collide?
        </div>
      </div>

      {/* Collision history bar */}
      <HistoryBar collisions={collisions.slice(-8)} onSelect={handleSelectCollision} />

      {/* Theory detail panel */}
      <AnimatePresence>
        {selectedTheory && THEORIES[selectedTheory] && (
          <TheoryPanel
            theory={THEORIES[selectedTheory]}
            id={selectedTheory}
            collisions={collisions}
          />
        )}
      </AnimatePresence>

      {/* Bottom controls */}
      <CollisionPanel onCollide={handleCollide} activeCollision={activeCollision} />
    </div>
  );
}
