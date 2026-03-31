# Attention Mechanism (Transformers)

**Domain:** Machine Learning

**Equation:** `Attn(Q,K,V) = softmax(QK^T/√d)V;  softmax(zᵢ) = exp(zᵢ)/Σⱼ exp(zⱼ);  MultiHead = Concat(head₁,...,headₕ)W`

**Update Form:** weighted_value_aggregation

**Optimization:** minimize_cross_entropy_loss

**Fixed Points:** learned_attention_patterns

## Patterns

- compositional_structure
- energy_based
- energy_entropy_tradeoff
- gradient_descent
- information_gain
- mean_field
- pairwise_coupling

## Operators

- composition
- dot_product
- expectation
- gradient
- projection
- softmax
