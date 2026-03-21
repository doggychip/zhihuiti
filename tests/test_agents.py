import random
from silicon_realms.models import Agent, Realm, SimState
from silicon_realms.agents import create_agents, agent_decide, agent_act


def make_state():
    config = {
        "economy": {"initial_supply": 3000, "transfer_fee": 0.01, "stake_min": 10, "stake_reward_rate": 0.03},
        "agents": {"initial_count": 9},
        "realms": {
            "compute": {"capacity": 50, "base_reward": 10, "difficulty_growth": 0.02},
            "memory": {"capacity": 40, "base_reward": 8, "decay_rate": 0.01},
            "network": {"capacity": 30, "base_reward": 12, "routing_fee": 0.05},
        },
    }
    state = SimState(rng=random.Random(42), config=config)
    for name, params in config["realms"].items():
        state.realms[name] = Realm(name=name, capacity=params["capacity"], base_reward=params["base_reward"], params=params)
    return state, config


def test_create_agents():
    state, config = make_state()
    create_agents(config, state)
    assert len(state.agents) == 9
    realms_used = {a.realm for a in state.agents.values()}
    assert len(realms_used) == 3  # all three realms populated


def test_agent_decide_returns_valid_action():
    state, config = make_state()
    create_agents(config, state)
    valid = {"work", "stake", "unstake", "migrate", "rest"}
    for agent in state.agents.values():
        action = agent_decide(state, agent)
        assert action in valid


def test_agent_rest_recharges():
    state, config = make_state()
    create_agents(config, state)
    agent = list(state.agents.values())[0]
    agent.energy = 0
    agent.balance = 10.0
    state.total_supply = 10.0
    agent_act(state, agent, "rest")
    assert agent.energy > 0
