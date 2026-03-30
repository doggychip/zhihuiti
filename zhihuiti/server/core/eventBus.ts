type EventCallback = (data: any) => void;

const listeners: Map<string, EventCallback[]> = new Map();

export type EventName =
  | "agent.created"
  | "agent.started"
  | "agent.paused"
  | "agent.stopped"
  | "agent.trade"
  | "agent.error"
  | "strategy.executed";

export function on(event: EventName, callback: EventCallback): void {
  if (!listeners.has(event)) {
    listeners.set(event, []);
  }
  listeners.get(event)!.push(callback);
}

export function off(event: EventName, callback: EventCallback): void {
  const cbs = listeners.get(event);
  if (!cbs) return;
  const idx = cbs.indexOf(callback);
  if (idx !== -1) cbs.splice(idx, 1);
}

export function emit(event: EventName, data?: any): void {
  const cbs = listeners.get(event);
  if (!cbs) return;
  for (const cb of cbs) {
    try {
      cb(data);
    } catch (err) {
      console.error(`[eventBus] Error in listener for ${event}:`, err);
    }
  }
}
