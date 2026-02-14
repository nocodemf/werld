"""
NativeBrain — a self-training neural network native to the computational world.

This is NOT a pre-trained model.  It starts with RANDOM WEIGHTS — a true
blank slate with zero knowledge of any world.  It has the ARCHITECTURE for:
  - Pattern recognition (mapping state features to representations)
  - Outcome prediction (what will happen if I do action X?)
  - Action selection (which action best reduces my drives?)

But all knowledge must be EARNED through experience in the simulation.

Reward System (multi-channel):
  The brain receives reward through multiple independent channels —
  like separate neurotransmitter systems.  Each measures a different
  aspect of the agent's state change.  None tells the agent WHAT to
  value; together they provide a rich learning signal.

  Channels:
    - Energy delta: how much energy changed (scaled)
    - Entropy delta: how much entropy changed (scaled)
    - Survival: penalty for dying, small bonus for living
    - Novelty: bonus for encountering genuinely new states
    - Baseline subtraction: expected reward is subtracted so
      surprising outcomes generate stronger learning signals

Architecture:
    StateFeatures(N) → Hidden(H, tanh) → ActionScores(A, linear)

Pure Python, zero dependencies.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple, Dict, Optional, Set, Any

import config as cfg

# ── Feature encoding ─────────────────────────────────────────────────────────

# Input features (all normalised to roughly 0-1):
#  0: energy_deficit (0=full, 1=empty)
#  1: entropy_pressure (0=fresh, 1=lethal)
#  2: local_energy (node energy / 100)
#  3: best_neighbor_energy (max neighbor node energy / 100)
#  4: avg_neighbor_energy (mean neighbor node energy / 100)
#  5: agents_nearby / 5
#  6: node_degree / 8   ← graph topology awareness
#  7: num_signals / 10
#  8: age / 500
#  9: energy_ratio (energy / max_energy)
# 10: entropy_ratio (entropy / lethal)
# 11: was_last_harvest (0 or 1)
# 12: was_last_move (0 or 1)
# 13: was_last_maintain (0 or 1)
# 14: signal_avg_energy (avg sender energy from received signals)
# 15: signal_avg_entropy (avg sender entropy from received signals)

INPUT_SIZE = 16


def encode_state(
    energy_deficit: float,
    entropy_pressure: float,
    local_energy: float,
    best_neighbor_energy: float,
    avg_neighbor_energy: float,
    agents_nearby: int,
    node_degree: int,
    num_signals: int,
    age: int,
    energy: float,
    max_energy: float,
    entropy: float,
    last_action_id: int,
    signal_avg_energy: float = 0.0,
    signal_avg_entropy: float = 0.0,
) -> List[float]:
    """
    Encode an agent's current perception into a fixed-size feature vector.
    All values normalised to roughly [0, 1].
    """
    return [
        min(1.0, max(0.0, energy_deficit)),
        min(1.0, max(0.0, entropy_pressure)),
        min(1.0, local_energy / 100.0),
        min(1.0, best_neighbor_energy / 100.0),
        min(1.0, avg_neighbor_energy / 100.0),
        min(1.0, agents_nearby / 5.0),
        min(1.0, node_degree / 8.0),
        min(1.0, num_signals / 10.0),
        min(1.0, age / 500.0),
        min(1.0, energy / max(max_energy, 1.0)),
        min(1.0, entropy / cfg.LETHAL_ENTROPY),
        1.0 if last_action_id == 4 else 0.0,     # harvest
        1.0 if last_action_id in (0, 1, 2, 3) else 0.0,  # move
        1.0 if last_action_id == 7 else 0.0,     # maintain
        min(1.0, max(0.0, signal_avg_energy)),
        min(1.0, max(0.0, signal_avg_entropy)),
    ]


# ── Reward computation ───────────────────────────────────────────────────────

def compute_reward(
    energy_before: float,
    energy_after: float,
    max_energy: float,
    entropy_before: float,
    entropy_after: float,
    is_alive: bool,
    is_novel_state: bool,
) -> float:
    """
    Multi-channel reward signal.  This is the agent's "nervous system" —
    it provides a MECHANISM for learning, not a VALUE JUDGMENT about what
    to learn.  The channels are:

      1. Energy delta (scaled): did I gain or lose energy?
      2. Entropy delta (scaled): did my entropy increase or decrease?
      3. Survival: am I still alive?
      4. Novelty: is this a genuinely new situation?

    Total reward is roughly in [-7, 4] — a much stronger signal than
    the previous ~0.01 range.
    """
    # Channel 1: Energy change (positive = gained energy)
    max_e = max(max_energy, 1.0)
    energy_channel = (energy_after - energy_before) / max_e

    # Channel 2: Entropy change (positive = entropy decreased = good)
    lethal = max(cfg.LETHAL_ENTROPY, 1.0)
    entropy_channel = (entropy_before - entropy_after) / lethal

    # Channel 3: Survival
    survival_channel = cfg.REWARD_SURVIVAL_PENALTY if not is_alive else cfg.REWARD_SURVIVAL_BONUS

    # Channel 4: Novelty
    novelty_channel = cfg.REWARD_NOVELTY_BONUS if is_novel_state else 0.0

    # Combine with configured weights
    reward = (
        energy_channel * cfg.REWARD_ENERGY_SCALE
        + entropy_channel * cfg.REWARD_ENTROPY_SCALE
        + survival_channel
        + novelty_channel
    )

    return reward


# ── Pure-Python linear algebra ──────────────────────────────────────────────

def _rand_matrix(rows: int, cols: int, rng: random.Random, scale: float = 0.3) -> List[List[float]]:
    """Xavier-like initialisation — small random weights."""
    s = scale / math.sqrt(rows + cols)
    return [[rng.gauss(0, s) for _ in range(cols)] for _ in range(rows)]


def _rand_vector(size: int, rng: random.Random, scale: float = 0.01) -> List[float]:
    return [rng.gauss(0, scale) for _ in range(size)]


def _zeros(size: int) -> List[float]:
    return [0.0] * size


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _mat_vec(mat: List[List[float]], vec: List[float]) -> List[float]:
    """Matrix-vector multiply: mat[rows][cols] × vec[cols] → result[rows]."""
    return [_dot(row, vec) for row in mat]


def _tanh(x: float) -> float:
    x = max(-10.0, min(10.0, x))
    return math.tanh(x)


def _tanh_vec(vec: List[float]) -> List[float]:
    return [_tanh(x) for x in vec]


def _tanh_deriv(tanh_output: float) -> float:
    return 1.0 - tanh_output * tanh_output


def _add_vec(a: List[float], b: List[float]) -> List[float]:
    return [x + y for x, y in zip(a, b)]


def _softmax(scores: List[float]) -> List[float]:
    max_s = max(scores)
    exps = [math.exp(min(s - max_s, 20.0)) for s in scores]
    total = sum(exps)
    if total == 0:
        n = len(scores)
        return [1.0 / n] * n
    return [e / total for e in exps]


# ── Experience tuple ─────────────────────────────────────────────────────────

class Experience:
    """A single (state, action, reward, next_state) transition."""
    __slots__ = ("state", "action", "reward", "next_state")

    def __init__(
        self,
        state: List[float],
        action: int,
        reward: float,
        next_state: Optional[List[float]] = None,
    ) -> None:
        self.state = state
        self.action = action
        self.reward = reward
        self.next_state = next_state


# ── The Brain ────────────────────────────────────────────────────────────────

class NativeBrain:
    """
    A self-training neural network.  Starts BLANK — learns only from
    its own experiences in the simulation world.

    Architecture:
        Input[16] → Hidden[H] (tanh) → Output[num_actions] (linear)

    Training:
        Online Q-learning from experience replay buffer with:
        - Multi-channel reward signal (energy, entropy, survival, novelty)
        - Reward baseline subtraction (prediction error emphasis)
        - Higher learning rate for stronger weight updates
    """

    def __init__(
        self,
        num_actions: int,
        hidden_size: int = cfg.BRAIN_HIDDEN_SIZE,
        learning_rate: float = cfg.BRAIN_LEARNING_RATE,
        gamma: float = cfg.BRAIN_GAMMA,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.rng = rng or random.Random()
        self.num_actions = num_actions
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.gamma = gamma

        # ── Weights (randomly initialised — NO pre-training) ──────────
        self.W1: List[List[float]] = _rand_matrix(hidden_size, INPUT_SIZE, self.rng)
        self.b1: List[float] = _zeros(hidden_size)
        self.W2: List[List[float]] = _rand_matrix(num_actions, hidden_size, self.rng)
        self.b2: List[float] = _zeros(num_actions)

        # ── Experience replay buffer ──────────────────────────────────
        self.experience_buffer: List[Experience] = []
        self.max_buffer_size: int = cfg.BRAIN_BUFFER_SIZE
        self.train_batch_size: int = cfg.BRAIN_TRAIN_BATCH
        self.train_every: int = cfg.BRAIN_TRAIN_EVERY
        self._experience_since_train: int = 0

        # ── Reward baseline (for prediction error) ───────────────────
        self.reward_baseline: float = 0.0
        self.baseline_alpha: float = cfg.REWARD_BASELINE_ALPHA

        # ── Novelty tracking (visited state hashes) ──────────────────
        self.visited_states: Set[int] = set()
        self.max_visited: int = 2000  # Bounded to prevent memory bloat

        # Stats
        self.total_trains: int = 0
        self.total_experiences: int = 0

    # ── Novelty detection ─────────────────────────────────────────────

    def check_novelty(self, state: List[float]) -> bool:
        """
        Check if a state is novel (never seen before).
        Discretises the state into a hash for comparison.
        """
        # Coarse discretization: round each feature to 1 decimal
        state_hash = hash(tuple(round(f, 1) for f in state))
        if state_hash not in self.visited_states:
            self.visited_states.add(state_hash)
            # Bounded: if too many states tracked, remove oldest-ish
            if len(self.visited_states) > self.max_visited:
                # Remove a random element (approximate LRU)
                self.visited_states.pop()
            return True
        return False

    # ── Forward pass ─────────────────────────────────────────────────────

    def forward(self, state: List[float]) -> Tuple[List[float], List[float]]:
        """
        Forward pass.  Returns (hidden_activations, q_values).
        hidden is needed for backprop.
        """
        raw_h = _add_vec(_mat_vec(self.W1, state), self.b1)
        hidden = _tanh_vec(raw_h)
        q_values = _add_vec(_mat_vec(self.W2, hidden), self.b2)
        return hidden, q_values

    def get_q_values(self, state: List[float]) -> List[float]:
        """Get Q-values for all actions given a state."""
        _, q = self.forward(state)
        return q

    # ── Action selection ─────────────────────────────────────────────────

    def choose_action(
        self,
        state: List[float],
        exploration_rate: float = 0.2,
        num_compound_actions: int = 0,
    ) -> int:
        """
        Choose an action using the brain's current knowledge.
        Uses epsilon-greedy with softmax for the exploit portion.
        """
        total_actions = self.num_actions + num_compound_actions

        # Epsilon-greedy: explore randomly sometimes
        if self.rng.random() < exploration_rate:
            return self.rng.randint(0, total_actions - 1)

        # Exploit: use learned Q-values
        _, q_values = self.forward(state)

        # Extend q_values for compound actions
        while len(q_values) < total_actions:
            q_values.append(self.rng.gauss(0, 0.1))

        # Softmax selection
        probs = _softmax(q_values[:total_actions])
        r = self.rng.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i
        return total_actions - 1

    # ── Learning ─────────────────────────────────────────────────────────

    def record_experience(
        self,
        state: List[float],
        action: int,
        reward: float,
        next_state: Optional[List[float]] = None,
    ) -> None:
        """
        Record an experience with baseline subtraction.
        The reward stored is (actual - baseline), emphasising surprises.
        """
        # Prediction error: how surprising was this reward?
        surprise_reward = reward - self.reward_baseline

        # Update baseline with exponential moving average
        self.reward_baseline = (
            self.reward_baseline * (1.0 - self.baseline_alpha)
            + reward * self.baseline_alpha
        )

        exp = Experience(state, action, surprise_reward, next_state)
        self.experience_buffer.append(exp)
        self.total_experiences += 1
        self._experience_since_train += 1

        # Bounded buffer — drop oldest
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer = self.experience_buffer[-self.max_buffer_size:]

        # Auto-train
        if self._experience_since_train >= self.train_every:
            self.train()

    def train(self) -> None:
        """Self-train from experience replay."""
        if len(self.experience_buffer) < 4:
            return

        batch_size = min(self.train_batch_size, len(self.experience_buffer))
        batch = self.rng.sample(self.experience_buffer, batch_size)

        for exp in batch:
            self._train_one(exp)

        self.total_trains += 1
        self._experience_since_train = 0

    def _train_one(self, exp: Experience) -> None:
        """
        Train on a single experience using Q-learning + backprop.

        target = reward                              (if terminal)
        target = reward + gamma * max(Q(s', a'))     (otherwise)
        """
        state = exp.state
        action = exp.action
        reward = exp.reward

        # Forward pass
        hidden, q_values = self.forward(state)

        # Compute target
        if exp.next_state is not None:
            next_q = self.get_q_values(exp.next_state)
            max_next_q = max(next_q[:self.num_actions])
            target = reward + self.gamma * max_next_q
        else:
            target = reward

        # Skip if action index out of range
        if action >= len(q_values):
            return

        # Error
        error = target - q_values[action]

        # Clamp gradient to prevent explosion
        error = max(-3.0, min(3.0, error))

        # ── Backpropagation ──────────────────────────────────────────
        lr = self.learning_rate

        # Output layer: dW2[action] = error * hidden, db2[action] = error
        for j in range(self.hidden_size):
            self.W2[action][j] += lr * error * hidden[j]
        self.b2[action] += lr * error

        # Hidden layer: dh[j] = error * W2[action][j] * tanh'(h[j])
        dh = [0.0] * self.hidden_size
        for j in range(self.hidden_size):
            dh[j] = error * self.W2[action][j] * _tanh_deriv(hidden[j])

        # Input layer: dW1[j][i] = dh[j] * state[i], db1[j] = dh[j]
        for j in range(self.hidden_size):
            if abs(dh[j]) < 1e-8:
                continue
            for i in range(len(state)):
                self.W1[j][i] += lr * dh[j] * state[i]
            self.b1[j] += lr * dh[j]

    # ── Serialisation ────────────────────────────────────────────────────

    def serialise(self) -> Dict[str, Any]:
        """Serialise brain weights and state for checkpointing."""
        return {
            "num_actions": self.num_actions,
            "hidden_size": self.hidden_size,
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "W1": [list(row) for row in self.W1],
            "b1": list(self.b1),
            "W2": [list(row) for row in self.W2],
            "b2": list(self.b2),
            "total_trains": self.total_trains,
            "total_experiences": self.total_experiences,
            "reward_baseline": self.reward_baseline,
        }

    @classmethod
    def deserialise(cls, data: Dict[str, Any], rng: random.Random) -> "NativeBrain":
        """Restore a brain from serialised data."""
        brain = cls(
            num_actions=data["num_actions"],
            hidden_size=data["hidden_size"],
            learning_rate=data["learning_rate"],
            gamma=data["gamma"],
            rng=rng,
        )
        brain.W1 = [list(row) for row in data["W1"]]
        brain.b1 = list(data["b1"])
        brain.W2 = [list(row) for row in data["W2"]]
        brain.b2 = list(data["b2"])
        brain.total_trains = data.get("total_trains", 0)
        brain.total_experiences = data.get("total_experiences", 0)
        brain.reward_baseline = data.get("reward_baseline", 0.0)
        return brain

    # ── Inheritance (cultural transfer) ──────────────────────────────────

    @classmethod
    def inherit(
        cls,
        parent_a: "NativeBrain",
        parent_b: "NativeBrain",
        num_actions: int,
        learning_rate: float,
        knowledge_transfer: float,
        rng: random.Random,
    ) -> "NativeBrain":
        """
        Create a child brain by blending parent weights.

        knowledge_transfer (0-1): EVOLVABLE trait controlling how much
        parent knowledge the child inherits.
          0.0 = completely random (fresh start)
          1.0 = full copy of averaged parents
          0.5 = 50% parent blend + 50% random noise

        This is computational cultural inheritance.
        """
        child = cls(
            num_actions=num_actions,
            hidden_size=parent_a.hidden_size,
            learning_rate=learning_rate,
            rng=rng,
        )

        kt = max(0.0, min(1.0, knowledge_transfer))

        # W1: blend parents + child's random init
        for i in range(child.hidden_size):
            for j in range(INPUT_SIZE):
                parent_w = (
                    parent_a.W1[i][j] if rng.random() < 0.5
                    else parent_b.W1[i][j]
                )
                child.W1[i][j] = kt * parent_w + (1.0 - kt) * child.W1[i][j]
                child.W1[i][j] += rng.gauss(0, 0.02)

        # b1
        for i in range(child.hidden_size):
            parent_b1 = (
                parent_a.b1[i] if rng.random() < 0.5
                else parent_b.b1[i]
            )
            child.b1[i] = kt * parent_b1 + (1.0 - kt) * child.b1[i]

        # W2
        min_actions = min(len(parent_a.W2), len(parent_b.W2), num_actions)
        for i in range(min_actions):
            for j in range(child.hidden_size):
                parent_w = (
                    parent_a.W2[i][j] if rng.random() < 0.5
                    else parent_b.W2[i][j]
                )
                child.W2[i][j] = kt * parent_w + (1.0 - kt) * child.W2[i][j]
                child.W2[i][j] += rng.gauss(0, 0.02)

        # b2
        for i in range(min_actions):
            parent_b2 = (
                parent_a.b2[i] if rng.random() < 0.5
                else parent_b.b2[i]
            )
            child.b2[i] = kt * parent_b2 + (1.0 - kt) * child.b2[i]

        # Inherit reward baseline (start with parents' sense of "normal")
        child.reward_baseline = (parent_a.reward_baseline + parent_b.reward_baseline) / 2.0

        return child

    # ── Info ─────────────────────────────────────────────────────────────

    def weight_magnitude(self) -> float:
        """Total absolute weight magnitude — measures how much has been learned."""
        total = 0.0
        for row in self.W1:
            total += sum(abs(w) for w in row)
        for row in self.W2:
            total += sum(abs(w) for w in row)
        total += sum(abs(w) for w in self.b1)
        total += sum(abs(w) for w in self.b2)
        return total

    def __repr__(self) -> str:
        return (
            f"NativeBrain(actions={self.num_actions}, hidden={self.hidden_size}, "
            f"exp={self.total_experiences}, trains={self.total_trains})"
        )
