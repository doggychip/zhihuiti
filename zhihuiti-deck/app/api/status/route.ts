import { NextResponse } from "next/server";

const ORACLE_URL = process.env.ZHIHUITI_ORACLE_URL || "http://localhost:5000";

export async function GET() {
  try {
    const res = await fetch(`${ORACLE_URL}/api/status`, {
      next: { revalidate: 10 },
    });

    if (!res.ok) {
      return NextResponse.json(
        { status: "offline", error: `Oracle returned ${res.status}` },
        { status: 502 },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    // Oracle not reachable — return mock fallback
    return NextResponse.json({
      status: "offline",
      agents: {
        total: 6,
        active: 3,
        idle: 2,
        culled: 1,
      },
      economy: {
        moneySupply: 10000,
        treasuryBalance: 4200,
        totalTaxCollected: 1580,
      },
      uptime: 0,
    });
  }
}
