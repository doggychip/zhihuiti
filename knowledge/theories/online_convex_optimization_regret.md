# Online Convex Optimization / Regret

**Domain:** Machine Learning

**Equation:** `Regret_T = Σ f_t(x_t) − min_x Σ f_t(x);  FTRL: x_t = argmin[Σ f_s(x) + R(x)];  OGD: x_{t+1} = Π(x_t − η∇f_t)`

**Update Form:** follow_the_regularized_leader

**Optimization:** minimize_regret

**Fixed Points:** no_regret_strategy

## Patterns

- dual_variables
- energy_minimization
- exploration_exploitation
- gradient_descent
- variational_principle

## Operators

- adaptive_learning_rate
- gradient
- projection
- regret_bound
- regularizer
