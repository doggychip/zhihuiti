# Silicon Realms

A three-realm agent civilization simulator with token economics.

## Overview

Silicon Realms simulates an economy of autonomous agents across three distinct realms:

- **Compute** — Agents process and generate value through computation. Rewards decrease with rising difficulty.
- **Memory** — Agents store and trade knowledge. Data value decays over time.
- **Network** — Agents route transactions and facilitate exchange, earning routing fees.

Agents earn, spend, and stake **SiCoin** tokens. Each agent follows one of four strategies: greedy, staker, nomad, or balanced.

## Install

```bash
pip install -e .
```

## Run

```bash
silicon-realms --config config.yaml
```

## Test

```bash
pip install -e ".[dev]"
pytest
```

## Configuration

Edit `config.yaml` to tune simulation parameters: tick count, realm capacities and rewards, token economics (mint rate, staking yields, fees), and agent count.
