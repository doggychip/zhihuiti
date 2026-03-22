import { useState, useRef, useCallback, type ReactNode } from "react";

interface ResizableWidgetProps {
  children: ReactNode;
  defaultHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function ResizableWidget({
  children,
  defaultHeight,
  minHeight = 40,
  maxHeight = 800,
  className = "",
  style = {},
}: ResizableWidgetProps) {
  const [height, setHeight] = useState<number | undefined>(defaultHeight);
  const dragRef = useRef<{ startY: number; startH: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startH = height ?? containerRef.current?.offsetHeight ?? 100;
    dragRef.current = { startY: e.clientY, startH };

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = ev.clientY - dragRef.current.startY;
      const newH = Math.min(maxHeight, Math.max(minHeight, dragRef.current.startH + delta));
      setHeight(newH);
    };

    const onMouseUp = () => {
      dragRef.current = null;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  }, [height, minHeight, maxHeight]);

  return (
    <div
      ref={containerRef}
      className={`relative ${className}`}
      style={{
        ...style,
        ...(height !== undefined ? { height, overflow: "auto" } : {}),
      }}
    >
      {children}
      {/* Resize handle at bottom */}
      <div
        onMouseDown={onMouseDown}
        style={{
          position: "sticky",
          bottom: 0,
          left: 0,
          right: 0,
          height: 7,
          cursor: "row-resize",
          background: "transparent",
          zIndex: 5,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(167,139,250,0.25)";
          e.currentTarget.querySelector<HTMLElement>(".resize-grip")!.style.opacity = "1";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.querySelector<HTMLElement>(".resize-grip")!.style.opacity = "0";
        }}
      >
        <div
          className="resize-grip"
          style={{
            width: 32,
            height: 3,
            borderRadius: 2,
            background: "rgba(167,139,250,0.5)",
            opacity: 0,
            transition: "opacity 0.15s ease",
          }}
        />
      </div>
    </div>
  );
}
