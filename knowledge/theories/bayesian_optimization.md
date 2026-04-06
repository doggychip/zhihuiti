# Bayesian Optimization

**Domain:** Optimization

**Equation:** `x_{n+1} = argmax α(x; D_n);  α_EI(x) = E[max(f(x)−f*,0)];  f ~ GP(μ,k);  p(f|D) ∝ p(D|f)p(f)`

**Update Form:** acquisition_maximization

**Optimization:** maximize_acquisition_function

**Fixed Points:** global_optimum

## Patterns

- bayesian_inference
- energy_minimization
- exploration_exploitation
- information_gain
- optimal_inference
- variational_principle

## Operators

- acquisition_function
- gaussian_process
- gradient
- kernel_evaluation
- posterior_update
