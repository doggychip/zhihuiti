import { useState, useRef, useCallback, type ReactNode } from "react";

interface ResizableWidgetProps {
  children: ReactNode;
  defaultHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  resizeX?: boolean;
  resizeY?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export function ResizableWidget({
  children,
  defaultHeight,
  minHeight = 40,
  maxHeight = 800,
  defaultWidth,
  minWidth = 60,
  maxWidth = 1200,
  resizeX = true,
  resizeY = true,
  className = "",
  style = {},
}: ResizableWidgetProps) {
  const [height, setHeight] = useState<number | undefined>(defaultHeight);
  const [width, setWidth] = useState<number | undefined>(defaultWidth);
  const dragRef = useRef<{ startX: number; startY: number; startH: number; startW: number; axis: "y" | "x" | "xy" } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const startDrag = useCallback((e: React.MouseEvent, axis: "y" | "x" | "xy") => {
    e.preventDefault();
    e.stopPropagation();
    const startH = height ?? containerRef.current?.offsetHeight ?? 100;
    const startW = width ?? containerRef.current?.offsetWidth ?? 200;
    dragRef.current = { startX: e.clientX, startY: e.clientY, startH, startW, axis };

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const { axis: a, startX, startY, startH: sH, startW: sW } = dragRef.current;
      if (a === "y" || a === "xy") {
        const dy = ev.clientY - startY;
        setHeight(Math.min(maxHeight, Math.max(minHeight, sH + dy)));
      }
      if (a === "x" || a === "xy") {
        const dx = ev.clientX - startX;
        setWidth(Math.min(maxWidth, Math.max(minWidth, sW + dx)));
      }
    };

    const onMouseUp = () => {
      dragRef.current = null;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  }, [height, width, minHeight, maxHeight, minWidth, maxWidth]);

  const gripStyle = (visible: boolean): React.CSSProperties => ({
    background: visible ? "rgba(167,139,250,0.5)" : "rgba(167,139,250,0.5)",
    borderRadius: 2,
    opacity: 0,
    transition: "opacity 0.15s ease",
  });

  return (
    <div
      ref={containerRef}
      className={`relative ${className}`}
      style={{
        ...style,
        ...(height !== undefined ? { height, overflow: "auto" } : {}),
        ...(width !== undefined ? { width } : {}),
      }}
    >
      {children}
      {/* Bottom resize handle */}
      {resizeY && (
        <div
          onMouseDown={e => startDrag(e, "y")}
          style={{ position: "sticky", bottom: 0, left: 0, right: 0, height: 7, cursor: "row-resize", background: "transparent", zIndex: 5, display: "flex", alignItems: "center", justifyContent: "center" }}
          onMouseEnter={e => { e.currentTarget.style.background = "rgba(167,139,250,0.25)"; e.currentTarget.querySelector<HTMLElement>(".grip")!.style.opacity = "1"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.querySelector<HTMLElement>(".grip")!.style.opacity = "0"; }}
        >
          <div className="grip" style={{ ...gripStyle(false), width: 32, height: 3 }} />
        </div>
      )}
      {/* Right resize handle */}
      {resizeX && (
        <div
          onMouseDown={e => startDrag(e, "x")}
          style={{ position: "absolute", top: 0, right: 0, bottom: 0, width: 7, cursor: "col-resize", background: "transparent", zIndex: 5, display: "flex", alignItems: "center", justifyContent: "center" }}
          onMouseEnter={e => { e.currentTarget.style.background = "rgba(167,139,250,0.25)"; e.currentTarget.querySelector<HTMLElement>(".grip")!.style.opacity = "1"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.querySelector<HTMLElement>(".grip")!.style.opacity = "0"; }}
        >
          <div className="grip" style={{ ...gripStyle(false), width: 3, height: 32 }} />
        </div>
      )}
      {/* Corner resize handle */}
      {resizeX && resizeY && (
        <div
          onMouseDown={e => startDrag(e, "xy")}
          style={{ position: "absolute", bottom: 0, right: 0, width: 12, height: 12, cursor: "nwse-resize", zIndex: 6 }}
          onMouseEnter={e => { e.currentTarget.style.background = "rgba(167,139,250,0.35)"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
        />
      )}
    </div>
  );
}