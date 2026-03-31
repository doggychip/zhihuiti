import { registerStrategy } from "../core/strategyEngine";
import { trendFollowing, multiPairMomentum, strongTrend } from "./momentum";
import { bollingerBounce, contrarian } from "./meanReversion";
import { rsiStrategy, macdCross, ichimokuSimple } from "./indicator";
import { momentumPlusRsi, adaptiveSizing, fibonacciLevels } from "./hybrid";
import { randomWalk } from "./random";

export function registerAllStrategies(): void {
  // Momentum
  registerStrategy("momentum", trendFollowing);
  registerStrategy("momentum_multi", multiPairMomentum);
  registerStrategy("momentum_strong", strongTrend);

  // Mean reversion
  registerStrategy("mean_reversion", bollingerBounce);
  registerStrategy("mean_reversion_contrarian", contrarian);

  // Indicator
  registerStrategy("indicator", rsiStrategy);
  registerStrategy("indicator_macd", macdCross);
  registerStrategy("indicator_ichimoku", ichimokuSimple);

  // Hybrid
  registerStrategy("hybrid", momentumPlusRsi);
  registerStrategy("hybrid_adaptive", adaptiveSizing);
  registerStrategy("hybrid_fibonacci", fibonacciLevels);

  // Custom / random
  registerStrategy("custom", randomWalk);
}
