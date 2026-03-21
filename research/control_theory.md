# Control Theory

## Overview
Control theory studies how to manipulate dynamical systems to achieve desired behavior. Classical control (1930s-1950s) used frequency-domain methods; modern control (1960s+) uses state-space. Optimal control (Pontryagin, Bellman) connects to reinforcement learning, economics, and neuroscience. The Kalman filter connects to Bayesian inference and predictive coding.

---

## 1. Classical Control: PID Controllers

The most widely used controller in industry:

```
u(t) = K_p e(t) + K_i ∫₀ᵗ e(τ)dτ + K_d de(t)/dt
```

**Variables:**
- `e(t) = r(t) - y(t)` — error (reference minus output)
- `K_p` — proportional gain
- `K_i` — integral gain (eliminates steady-state error)
- `K_d` — derivative gain (dampens oscillations)

**Transfer function:** G_c(s) = K_p + K_i/s + K_d·s

**Bode plots:** Gain |G(jω)| and phase ∠G(jω) vs. frequency. Stability margins: gain margin (GM) and phase margin (PM).

**Nyquist criterion:** Closed-loop stability from open-loop frequency response. Number of encirclements of (-1, 0) = number of unstable closed-loop poles minus unstable open-loop poles.

---

## 2. State-Space Representation

Modern control framework — represents any LTI system:

```
ẋ(t) = Ax(t) + Bu(t)     [state equation]
y(t) = Cx(t) + Du(t)     [output equation]
```

**Variables:**
- `x ∈ ℝⁿ` — state vector
- `u ∈ ℝᵐ` — control input
- `y ∈ ℝᵖ` — output
- `A` — system matrix (n×n), eigenvalues = poles
- `B` — input matrix (n×m)
- `C` — output matrix (p×n)
- `D` — feedthrough matrix (p×m)

**Stability:** System stable iff Re(λ_i(A)) < 0 for all eigenvalues.

**Transfer function:** H(s) = C(sI - A)⁻¹B + D

---

## 3. Kalman Filter

Optimal state estimator for linear systems with Gaussian noise:

**System model:**
```
ẋ = Ax + Bu + w,   w ~ N(0, Q)    [process noise]
y = Cx + v,        v ~ N(0, R)    [measurement noise]
```

**Predict step:**
```
x̂⁻ = Ax̂ + Bu
P⁻ = APA^T + Q
```

**Update step:**
```
K = P⁻C^T(CP⁻C^T + R)⁻¹         [Kalman gain]
x̂ = x̂⁻ + K(y - Cx̂⁻)            [state update]
P = (I - KC)P⁻                    [covariance update]
```

**Optimality:** Minimizes trace(P) = mean squared error. Equivalent to recursive Bayesian estimation for linear-Gaussian systems.

**Steady-state Kalman gain:** Solve algebraic Riccati equation:
```
AP + PA^T - PC^T R⁻¹ CP + Q = 0
```

**Cross-domain connection:** Kalman filter = Bayesian update for Gaussian beliefs. Friston's predictive coding is a hierarchical Kalman filter for nonlinear generative models.

---

## 4. LQR / LQG Optimal Control

**Linear Quadratic Regulator (LQR):**
Minimize quadratic cost:
```
J = ∫₀^∞ (x^T Q x + u^T R u) dt
```

**Optimal control law:** u* = -Kx where K = R⁻¹B^T P

**P from algebraic Riccati equation:**
```
PA + A^T P - PBR⁻¹B^T P + Q = 0
```

**LQG = LQR + Kalman filter:** Separate estimation and control (separation principle).

**Key insight:** Q encodes state cost, R encodes control effort cost. Tuning Q/R trade-off performance vs. energy.

---

## 5. Bellman Equation and Dynamic Programming

**Bellman's principle of optimality (1957):**
```
V*(x) = max_u [r(x,u) + γ V*(f(x,u))]   [discrete time]
V*(x) = max_u [r(x,u) + ∂V*/∂x · f(x,u)]  [HJB equation, continuous]
```

**Variables:**
- `V*(x)` — optimal value function
- `r(x,u)` — immediate reward
- `γ` — discount factor
- `f(x,u)` — dynamics

**Q-function (action-value):**
```
Q*(x,u) = r(x,u) + γ max_{u'} Q*(x', u')
```

**Connection to RL:** Q-learning, SARSA, actor-critic methods all solve or approximate the Bellman equation. Bellman equation is the fundamental object of reinforcement learning.

**Connection to economics:** Hamilton-Jacobi-Bellman = Euler equation in continuous-time economics. Dynamic programming = multi-period optimization.

---

## 6. Pontryagin's Maximum Principle

For continuous-time optimal control problem:
```
min_u ∫₀^T L(x,u,t)dt + Φ(x(T))
s.t. ẋ = f(x,u)
```

**Hamiltonian:**
```
H(x, u, λ, t) = L(x, u, t) + λ^T f(x, u)
```

**Optimality conditions:**
```
ẋ = ∂H/∂λ    [state equation]
λ̇ = -∂H/∂x  [costate equation]
u* = argmin_u H(x*, u, λ*, t)   [minimum principle]
```

**Variables:** λ — costate (adjoint) variable, analogous to momentum in Hamiltonian mechanics.

**Connection to path integrals:** HJB equation → Schrödinger equation under Wick rotation (imaginary time). λ ↔ momentum in physics.

**Connection to backpropagation:** Adjoint method for neural ODEs and optimal control of neural networks uses the same costate equations.

---

## 7. Controllability and Observability

**Controllability (Kalman 1960):**
System (A,B) is controllable iff the controllability matrix has full rank:
```
C = [B | AB | A²B | ... | A^{n-1}B],   rank(C) = n
```
Controllable ↔ can steer state to any target in finite time.

**Observability:**
System (A,C) is observable iff the observability matrix has full rank:
```
O = [C; CA; CA²; ...; CA^{n-1}],   rank(O) = n
```
Observable ↔ can reconstruct initial state from output history.

**Duality:** (A,B) controllable ↔ (A^T, B^T) observable. Control and estimation are dual problems.

---

## 8. Robust Control (H-infinity)

Minimize worst-case gain from disturbances w to output z:
```
‖T_{zw}‖_∞ = sup_ω σ_max[T_{zw}(jω)] < γ
```

**Mixed sensitivity problem:**
```
min_K ‖ [W₁S; W₂KS; W₃T] ‖_∞
```
where S = sensitivity function, T = complementary sensitivity.

**H∞ Riccati equations:** Solve two coupled Riccati equations. Existence condition: ρ(X∞Y∞) < γ².

**Motivation:** H₂/LQG assumes known noise statistics. H∞ handles worst-case unknown disturbances — robust to model uncertainty.

---

## 9. Cross-Domain Connections

### Neuroscience
- **Predictive coding = hierarchical Kalman filter** (Friston 2005)
  - Each cortical level predicts lower level; prediction errors propagate up
  - Precision-weighted prediction errors = Kalman gain
- **Motor control = LQG** (Wolpert & Ghahramani)
  - Brain predicts sensory consequences of actions (forward model)
  - Optimal feedback control for movement

### AI / Machine Learning
- **RL = optimal control**: Q-learning → discrete Bellman; policy gradients → Pontryagin
- **Model predictive control (MPC)**: solve finite-horizon optimal control repeatedly
- **Neural ODEs**: continuous-depth networks, adjoint backprop = Pontryagin costate
- **Diffusion models**: reverse-time SDE as stochastic optimal control

### Economics
- **Dynamic programming**: multi-period utility maximization
- **Ramsey model**: HJB equation for optimal savings
- **Mechanism design**: principal-agent = Stackelberg control

### Biology
- **Homeostasis**: integral control maintains set-points (temperature, glucose)
- **Gene regulatory networks**: feedback loops = biological controllers
- **Chemotaxis**: E. coli uses proportional-integral control

### Key Mathematical Bridges
```
Kalman filter ←→ Bayesian update (linear-Gaussian)
Bellman equation ←→ Q-learning ←→ dynamic programming
Pontryagin costate ←→ adjoint backprop ←→ Lagrangian mechanics
HJB equation ←→ Hamilton-Jacobi equation (classical mechanics)
H∞ control ←→ minimax game theory ←→ robust optimization
Separation principle ←→ perception-action independence
```
