"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Collapsible section ────────────────────────────────────────────── */

function MethodSection({
  id,
  title,
  open,
  onToggle,
  children,
}: {
  id: string;
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-border/40 last:border-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 py-3.5 text-left cursor-pointer group"
      >
        <ChevronRight
          className={cn(
            "w-3.5 h-3.5 text-muted-foreground transition-transform duration-150",
            open && "rotate-90"
          )}
        />
        <span className="text-[15px] font-semibold text-foreground group-hover:text-foreground/80 transition-colors">
          {title}
        </span>
      </button>
      {open && (
        <div className="pl-5.5 pb-5 text-[13.5px] leading-relaxed text-foreground/85 space-y-3">
          {children}
        </div>
      )}
    </section>
  );
}

/* ── Inline code/param helper ───────────────────────────────────────── */

function P({ children }: { children: React.ReactNode }) {
  return <p>{children}</p>;
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="font-mono text-[12px] bg-muted/60 px-1 py-0.5 rounded text-foreground/90">
      {children}
    </code>
  );
}

function Def({
  term,
  children,
}: {
  term: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-2 py-0.5">
      <span className="font-medium text-foreground shrink-0 w-44">{term}</span>
      <span className="text-muted-foreground">{children}</span>
    </div>
  );
}

function TraitRow({
  name,
  range,
  desc,
}: {
  name: string;
  range: string;
  desc: string;
}) {
  return (
    <tr className="border-b border-border/30 last:border-0">
      <td className="py-1.5 pr-3 font-mono text-[12px] text-foreground/90">{name}</td>
      <td className="py-1.5 pr-3 font-mono text-[12px] text-muted-foreground">{range}</td>
      <td className="py-1.5 text-[12.5px] text-muted-foreground">{desc}</td>
    </tr>
  );
}

/* ── Main component ─────────────────────────────────────────────────── */

export default function MethodsSection() {
  const [openSections, setOpenSections] = useState<Set<string>>(
    new Set(["architecture"])
  );

  const toggle = (id: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => {
    setOpenSections(new Set([
      "architecture", "brain", "sensory", "motor", "genome",
      "cortex", "memory", "macros", "comms", "selection", "physics",
    ]));
  };

  const collapseAll = () => setOpenSections(new Set());

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Methods
        </h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Technical reference for the simulation architecture and algorithms.
        </p>
        <div className="flex gap-3 mt-3">
          <button
            onClick={expandAll}
            className="text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            Expand all
          </button>
          <span className="text-[11px] text-muted-foreground/40">|</span>
          <button
            onClick={collapseAll}
            className="text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            Collapse all
          </button>
        </div>
      </div>

      {/* Sections */}
      <div className="border-t border-border/40">
        {/* ── Architecture ──────────────────────────────────────── */}
        <MethodSection
          id="architecture"
          title="Architecture Overview"
          open={openSections.has("architecture")}
          onToggle={() => toggle("architecture")}
        >
          <P>
            The simulation runs as a pure Python process with no ML framework dependencies.
            The world is a <strong>Watts-Strogatz small-world graph</strong> &mdash; 800 nodes
            with an average degree of 4 and a rewiring probability of 0.15. There is no grid,
            no Cartesian coordinate system. Connectivity <em>is</em> the spatial structure.
          </P>
          <P>
            Each node holds energy (regenerated per tick, modulated by seasons) and pheromone
            (deposited by visiting agents, decaying over time). Agents live on nodes and can
            traverse edges to reach neighboring nodes.
          </P>
          <P>
            The core loop processes one <strong>tick</strong> per iteration. For every alive
            agent, the tick executes:
          </P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="1. Upkeep">Deduct tick_cost + brain metabolic cost from energy; accumulate entropy</Def>
            <Def term="2. Perceive">BFS within sense_range hops &rarr; 64-channel sensory vector</Def>
            <Def term="3. Decide">NEAT brain forward pass &rarr; 23 continuous effector outputs</Def>
            <Def term="4. Act">Physics engine interprets effectors into world effects</Def>
            <Def term="5. Learn">Cortex reinforcement, episodic memory, motor pattern tracking</Def>
          </div>
          <P>
            After all agents act, system-level resolution runs: signal propagation (BFS),
            forking/reproduction, death collection, pheromone decay, and periodic logging.
          </P>
          <P>
            Persistence uses <strong>SQLite</strong> for time-series data (population stats,
            brain stats, species stats, events) and <strong>gzipped JSON checkpoints</strong>
            for full simulation snapshots. Milestone checkpoints are saved permanently every
            10,000 ticks.
          </P>
        </MethodSection>

        {/* ── Brain ─────────────────────────────────────────────── */}
        <MethodSection
          id="brain"
          title="Brain: NEAT Neural Networks"
          open={openSections.has("brain")}
          onToggle={() => toggle("brain")}
        >
          <P>
            Agent brains use <strong>NEAT</strong> (NeuroEvolution of Augmenting Topologies).
            Unlike fixed-topology networks, NEAT evolves both the <em>structure</em> and
            <em>weights</em> of the neural network simultaneously.
          </P>
          <P>
            Each brain is defined by its genome&rsquo;s <strong>node genes</strong> and
            <strong> connection genes</strong>. Node genes specify neuron type
            (<Code>input</Code>, <Code>hidden</Code>, <Code>output</Code>),
            bias, and activation function. Connection genes specify source, target,
            weight, and an enabled/disabled flag.
          </P>
          <P>
            <strong>Structural mutations</strong> grow the network over generations:
          </P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="Add connection (15%)">Create a new weighted connection between two nodes</Def>
            <Def term="Add node (3%)">Split an existing connection, inserting a new hidden neuron</Def>
            <Def term="Mutate weight (80%)">Gaussian perturbation of an existing connection weight</Def>
            <Def term="Toggle connection (5%)">Enable or disable an existing connection</Def>
            <Def term="Mutate bias (30%)">Gaussian perturbation of a node&rsquo;s bias</Def>
            <Def term="Mutate activation (2%)">Change a node&rsquo;s activation function (tanh, relu, sigmoid, identity, sin, abs, step)</Def>
          </div>
          <P>
            <strong>Crossover</strong> aligns parent genomes by innovation number (a global
            counter incremented whenever a new structural mutation occurs). Matching genes are
            randomly inherited from either parent. Excess and disjoint genes come from the
            fitter parent.
          </P>
          <P>
            <strong>Speciation</strong> groups agents by genetic distance (excess genes,
            disjoint genes, weight difference). This protects topological innovation by
            preventing novel structures from being competed away before they have time to
            be optimised.
          </P>
          <P>
            <strong>Metabolic cost</strong> creates selection pressure against unnecessary
            complexity. Each tick, the brain costs:
          </P>
          <div className="ml-4 font-mono text-[12px] text-muted-foreground py-1">
            neurons &times; 0.005 + connections &times; 0.002 + sensory_excess &times; 0.001 + broadcast_width &times; 0.003
          </div>
          <P>
            There is <strong>no reward function</strong>. The brain does not learn via
            gradient descent or reinforcement learning. It evolves via natural selection:
            agents with brains that produce better survival behaviour reproduce more.
          </P>
        </MethodSection>

        {/* ── Sensory ───────────────────────────────────────────── */}
        <MethodSection
          id="sensory"
          title="Sensory System (64 Channels)"
          open={openSections.has("sensory")}
          onToggle={() => toggle("sensory")}
        >
          <P>
            Each agent perceives the world through a <strong>64-dimensional sensory
            vector</strong> fed into the brain&rsquo;s input layer. The first 45 channels
            carry core information; the remaining 19 are <strong>latent channels</strong> that
            start dormant and can be &ldquo;discovered&rdquo; by evolution.
          </P>
          <P><strong>Core channels (0-44):</strong></P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="0-12: Proprioceptive">Energy/entropy levels, age, brain complexity, energy/entropy deltas, compound action count</Def>
            <Def term="13-22: Exteroceptive">Local energy, neighbor energy, node degree, agent counts, hub detection, 2nd-hop energy</Def>
            <Def term="23-32: Social">Signal count, 4 signal channel averages, kin presence, last action flags</Def>
            <Def term="33-35: Pheromone">Local, best neighbor, average neighbor pheromone levels</Def>
            <Def term="36-40: Environmental">Season phase (sin/cos), season regen, circadian clock, last action type</Def>
            <Def term="41-44: Stochastic">Constant bias (1.0), uniform noise, gaussian noise, age-modulated pulse</Def>
          </div>
          <P><strong>Latent channels (45-63):</strong></P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="45-48: Effector echo">Last tick&rsquo;s locomotion and motor activations (proprioceptive motor feedback)</Def>
            <Def term="49-52: Broadcast echo">Last tick&rsquo;s own broadcast channel values (self-monitoring)</Def>
            <Def term="53-56: Derivatives">Rate of change of energy, entropy, local energy, nearby population</Def>
            <Def term="57-60: Cross-products">Compound features: energy&times;entropy, local_energy&times;agents, pheromone&times;season, age&times;entropy</Def>
            <Def term="61-63: Memory readouts">Average recent drive delta, action variety, memory fullness</Def>
          </div>
          <P>
            <strong>Evolvable perception:</strong> Every channel has a heritable <Code>gain</Code> and <Code>offset</Code>.
            The processed value is <Code>raw &times; gain + offset</Code>. Core channels
            default to gain=1.0; latent channels default to gain=0.01 (effectively silent).
            Evolution &ldquo;turns on&rdquo; a latent channel by evolving its gain upward.
            This mechanism lets agents expand their sensory field without changing the
            brain&rsquo;s I/O dimensionality.
          </P>
          <P>
            Sensory sensitivity has a metabolic cost: the total deviation of gains from 1.0
            is multiplied by <Code>SENSORY_COST</Code> (0.001) and added to the brain&rsquo;s
            energy drain per tick.
          </P>
        </MethodSection>

        {/* ── Motor ─────────────────────────────────────────────── */}
        <MethodSection
          id="motor"
          title="Motor System (23 Effectors)"
          open={openSections.has("motor")}
          onToggle={() => toggle("motor")}
        >
          <P>
            The brain produces <strong>23 continuous output values</strong> each tick &mdash;
            7 motor effectors plus up to 16 broadcast channels. Multiple effectors can fire
            simultaneously; there are no discrete &ldquo;choose one action&rdquo; constraints.
          </P>
          <P><strong>Motor effectors (0-6):</strong></P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="0: Locomotion direction">Continuous value mapped to neighbor index</Def>
            <Def term="1: Locomotion intensity">0-1 movement commitment</Def>
            <Def term="2: Harvest">0-1 energy extraction from current node</Def>
            <Def term="3: Social interaction">Signed: negative = attack, positive = energy transfer</Def>
            <Def term="4: Maintenance">0-1 self-repair (reduces entropy)</Def>
            <Def term="5: Reproduction">Above threshold (0.7) triggers fork attempt</Def>
            <Def term="6: Signal">Above threshold triggers broadcast</Def>
          </div>
          <P><strong>Broadcast channels (7-22):</strong></P>
          <P>
            Up to 16 evolved signal content channels. The genome trait <Code>broadcast_width</Code> (1-16)
            controls how many channels are active; the rest are zeroed. Only active channels
            incur metabolic cost. The brain decides what to encode in each channel &mdash;
            there is no predefined meaning.
          </P>
          <P>
            The physics engine (<Code>interpret_effectors</Code>) reads these activations
            simultaneously. An agent can move, harvest, and signal in the same tick. Each
            effector has a minimum intensity threshold (<Code>ACTION_INTENSITY_THRESHOLD</Code> = 0.3)
            and an energy cost scaled by intensity.
          </P>
        </MethodSection>

        {/* ── Genome ────────────────────────────────────────────── */}
        <MethodSection
          id="genome"
          title="Genome and Inheritance (29 Traits)"
          open={openSections.has("genome")}
          onToggle={() => toggle("genome")}
        >
          <P>
            Each agent&rsquo;s genome is a three-part heritable blueprint:
          </P>
          <div className="ml-4 space-y-1 text-[13px] mb-3">
            <Def term="1. Trait vector">29 numeric values governing physical capacities, drives, and cognitive architecture</Def>
            <Def term="2. NEAT topology">Node genes + connection genes with global innovation numbers</Def>
            <Def term="3. Sensory genes">Per-channel gain and offset for all 64 sensory inputs</Def>
          </div>
          <P><strong>Full trait table:</strong></P>
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border/50">
                  <th className="py-1.5 pr-3 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Trait</th>
                  <th className="py-1.5 pr-3 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Range</th>
                  <th className="py-1.5 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Description</th>
                </tr>
              </thead>
              <tbody>
                <TraitRow name="tick_cost" range="0.3 - 2.0" desc="Energy cost per tick to exist" />
                <TraitRow name="max_energy" range="100 - 250" desc="Maximum energy capacity" />
                <TraitRow name="entropy_resistance" range="0.5 - 2.0" desc="Resistance to entropy accumulation" />
                <TraitRow name="sense_range" range="1 - 4" desc="Perception range in graph hops" />
                <TraitRow name="signal_range" range="1 - 5" desc="Signal broadcast range in hops" />
                <TraitRow name="signal_width" range="2 - 8" desc="Signal encoding width" />
                <TraitRow name="learning_rate" range="0.01 - 0.5" desc="Cortex weight update speed" />
                <TraitRow name="exploration_factor" range="0.05 - 0.5" desc="Random action probability" />
                <TraitRow name="mutation_rate" range="0.01 - 0.3" desc="Offspring genome mutation magnitude" />
                <TraitRow name="knowledge_transfer" range="0.0 - 1.0" desc="Brain weight inheritance fraction" />
                <TraitRow name="cortex_capacity" range="50 - 500" desc="Max entries in cortex weight table" />
                <TraitRow name="memory_capacity" range="10 - 100" desc="Episodic memory buffer size" />
                <TraitRow name="fork_threshold" range="40 - 80" desc="Energy needed to reproduce" />
                <TraitRow name="macro_discovery_rate" range="0.01 - 0.2" desc="Chance of discovering motor patterns" />
                <TraitRow name="cultural_transfer" range="0.1 - 0.8" desc="Motor pattern inheritance fidelity" />
                <TraitRow name="harvest_drive" range="0.0 - 1.0" desc="Bias toward energy extraction when hungry" />
                <TraitRow name="maintain_drive" range="0.0 - 1.0" desc="Bias toward self-repair when entropic" />
                <TraitRow name="explore_drive" range="0.0 - 1.0" desc="Bias toward movement" />
                <TraitRow name="social_drive" range="-1.0 - 1.0" desc="Negative = aggression, positive = cooperation" />
                <TraitRow name="reproduce_drive" range="0.0 - 1.0" desc="Bias toward forking when energy surplus" />
                <TraitRow name="signal_drive" range="0.0 - 1.0" desc="Bias toward broadcasting" />
                <TraitRow name="broadcast_width" range="1 - 16" desc="Active broadcast channels (rest zeroed)" />
                <TraitRow name="cortex_reliance" range="0.0 - 1.0" desc="Probability cortex fires when brain active" />
                <TraitRow name="cortex_resolution" range="2 - 6" desc="Perceptual binning resolution in state hash" />
                <TraitRow name="memory_decay" range="0.80 - 0.99" desc="Memory importance decay rate per tick" />
                <TraitRow name="memory_social_weight" range="0.0 - 2.0" desc="Social encounter importance boost" />
                <TraitRow name="macro_capacity" range="5 - 50" desc="Max compound actions per agent" />
                <TraitRow name="macro_pattern_length" range="2 - 8" desc="Max length of discovered patterns" />
              </tbody>
            </table>
          </div>
          <P>
            <strong>Crossover:</strong> On reproduction, traits are randomly inherited per-trait
            from either parent. NEAT genes are aligned by innovation number &mdash; matching
            genes are randomly chosen, excess/disjoint genes come from the fitter parent.
            Sensory gains and offsets crossover per-channel (uniform).
          </P>
          <P>
            <strong>Mutation:</strong> Traits are perturbed within their configured ranges.
            Integer traits (like <Code>broadcast_width</Code>) are rounded after mutation.
            NEAT structural mutations add nodes/connections. Sensory gains undergo gaussian
            perturbation (30% per channel).
          </P>
        </MethodSection>

        {/* ── Cortex ────────────────────────────────────────────── */}
        <MethodSection
          id="cortex"
          title="Cortex (Associative Reflex System)"
          open={openSections.has("cortex")}
          onToggle={() => toggle("cortex")}
        >
          <P>
            The cortex is a <strong>secondary decision system</strong> &mdash; a fast, simple
            lookup table mapping perceived states to action weights. It serves as a reflex
            backup to the NEAT brain.
          </P>
          <P>
            It works by discretising the agent&rsquo;s perception into a coarse
            <strong> state hash</strong> (energy bucket, entropy bucket, local energy, agents
            nearby, node degree, signal count) and looking up weights for each possible action.
            Action selection uses softmax with genome-driven drive modulation and exploration noise.
          </P>
          <P>
            <strong>Evolvable architecture:</strong>
          </P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="cortex_reliance (0-1)">Probability the cortex fires each tick when the brain is active. Agents can evolve this to 0.0 to become pure brain-driven creatures, or keep it high for reflex backup.</Def>
            <Def term="cortex_resolution (2-6)">Bins per perceptual dimension in the state hash. Higher = finer discrimination but slower generalisation and more memory usage.</Def>
          </div>
          <P>
            <strong>Drive modulation</strong> uses heritable genome traits instead of hardcoded
            biases. The 6 drive traits (<Code>harvest_drive</Code>, <Code>maintain_drive</Code>,
            <Code>explore_drive</Code>, <Code>social_drive</Code>, <Code>reproduce_drive</Code>,
            <Code>signal_drive</Code>) determine how internal conditions bias action selection.
            Different species evolve different drive profiles through natural selection.
          </P>
          <P>
            The cortex learns within a single lifetime via experience-based reinforcement
            (weight updates based on drive-before vs drive-after delta), but this is secondary
            to the cross-generational learning that happens through evolution.
          </P>
        </MethodSection>

        {/* ── Memory ────────────────────────────────────────────── */}
        <MethodSection
          id="memory"
          title="Episodic Memory"
          open={openSections.has("memory")}
          onToggle={() => toggle("memory")}
        >
          <P>
            Each agent maintains a bounded buffer of <strong>episodic memories</strong> &mdash;
            records of past actions, their context, and their outcomes. The buffer size is
            governed by <Code>memory_capacity</Code> (10-100).
          </P>
          <P>
            Each episode records: tick, action taken, node position, energy/entropy before
            and after, drive improvement, which other agents were present, and how many
            signals were received.
          </P>
          <P>
            <strong>Importance scoring:</strong> Each memory has an importance value =
            <Code>|drive_delta| + social_weight &times; (1 if agents were present)</Code>.
            The <Code>memory_social_weight</Code> trait (0-2) is heritable &mdash; social
            species evolve high values, making social encounters more memorable.
          </P>
          <P>
            <strong>Evolvable decay:</strong> Every tick, all memory importance values are
            multiplied by <Code>memory_decay</Code> (0.80-0.99). Memories below a threshold
            are pruned. Species that evolve low decay rates forget quickly but are more
            responsive to recent events; high decay rates preserve long-term knowledge.
          </P>
          <P>
            Memory contents feed into the sensory system via latent channels 61-63 (average
            recent drive delta, action variety, memory fullness ratio), creating a feedback
            loop between experience and perception.
          </P>
        </MethodSection>

        {/* ── Motor Patterns ────────────────────────────────────── */}
        <MethodSection
          id="macros"
          title="Motor Patterns (Compound Actions)"
          open={openSections.has("macros")}
          onToggle={() => toggle("macros")}
        >
          <P>
            Agents can discover <strong>motor patterns</strong> &mdash; repeating sequences
            of effector activations that reliably improve drives. When an agent executes the
            same beneficial pattern multiple times, it gets promoted to a reusable compound
            action that the cortex can trigger as a single unit.
          </P>
          <P>
            The <Code>SequenceTracker</Code> bins continuous effector outputs into coarse
            action buckets and scans for patterns of length 2 to <Code>macro_pattern_length</Code> (evolvable, 2-8).
            A pattern must be repeated at least <Code>COMPOUND_SUCCESS_THRESHOLD</Code> (3)
            times with net positive drive improvement to be promoted.
          </P>
          <P>
            <strong>Genome-gated thresholds:</strong>
          </P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="macro_capacity (5-50)">Maximum compound actions an agent can hold. Replaces the old fixed limit.</Def>
            <Def term="macro_pattern_length (2-8)">Maximum sequence length for pattern detection. Longer patterns = more complex routines.</Def>
            <Def term="macro_discovery_rate (0.01-0.2)">Probability of promoting a qualified pattern. Already evolvable since early phases.</Def>
          </div>
          <P>
            Motor patterns are <strong>inheritable</strong>: offspring receive a subset of
            their parents&rsquo; patterns (controlled by <Code>cultural_transfer</Code> trait),
            with possible mutations (swap, add, remove, or change a step). This is the
            computational equivalent of learned tool use being passed between generations.
          </P>
        </MethodSection>

        {/* ── Communication ─────────────────────────────────────── */}
        <MethodSection
          id="comms"
          title="Communication System"
          open={openSections.has("comms")}
          onToggle={() => toggle("comms")}
        >
          <P>
            Communication is <strong>fully unstructured</strong>. When an agent&rsquo;s signal
            effector (channel 6) exceeds the activation threshold, the brain&rsquo;s broadcast
            channels (7-22) are propagated as a signal vector to all agents within
            <Code>signal_range</Code> hops via BFS on the graph.
          </P>
          <P>
            There is no predefined encoding. The brain decides what values to put in each
            channel. If channel 0 comes to &ldquo;mean&rdquo; something about energy levels,
            it&rsquo;s because evolution discovered that encoding is useful for survival.
          </P>
          <P>
            <strong>Variable bandwidth:</strong> The <Code>broadcast_width</Code> trait (1-16)
            controls how many channels are active per agent. Channels beyond the agent&rsquo;s
            width are zeroed. Only active channels cost energy, creating selection pressure
            against unused bandwidth. Some species may evolve narrow, efficient signals;
            others may evolve rich, multi-channel broadcasts.
          </P>
          <P>
            <strong>Signal propagation:</strong> Uses BFS on the graph substrate. Signal range
            is measured in hops, not distance. Signals include noise inversely proportional to
            intensity &mdash; faint signals are noisier than strong ones. Receivers aggregate
            all incoming signals by channel-wise averaging.
          </P>
          <P>
            Agents also leave <strong>pheromone</strong> traces on visited nodes &mdash; a
            form of indirect, stigmergic communication. Pheromone decays at 2% per tick and
            is sensed through channels 33-35.
          </P>
        </MethodSection>

        {/* ── Natural Selection ─────────────────────────────────── */}
        <MethodSection
          id="selection"
          title="Natural Selection (No Reward Function)"
          open={openSections.has("selection")}
          onToggle={() => toggle("selection")}
        >
          <P>
            The simulation uses <strong>pure natural selection</strong> as the sole optimisation
            mechanism. There is no reward function, no fitness function, no gradient descent,
            no reinforcement learning signal.
          </P>
          <P>
            The evolutionary loop is simple:
          </P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="1. Variation">Offspring genomes are created via crossover + mutation. NEAT structural mutations add/remove neurons and connections. Trait values are perturbed.</Def>
            <Def term="2. Selection">Agents that accumulate enough energy and survive long enough can reproduce. Those that die before reproducing leave no offspring.</Def>
            <Def term="3. Inheritance">Children receive mixed traits from both parents, mixed brain topology, mixed sensory genes, and a subset of motor patterns.</Def>
          </div>
          <P>
            <strong>Speciation</strong> (NEAT-style) groups genetically similar agents together.
            Within-species competition is normalised by species size (<Code>NEAT_FITNESS_SHARING</Code>),
            protecting novel topological innovations from being outcompeted before they&rsquo;re
            optimised.
          </P>
          <P>
            <strong>Metabolic cost</strong> acts as a counter-pressure to complexity. Bigger
            brains, more sensory channels, and wider broadcast bandwidth all cost energy per
            tick. Evolution must find the sweet spot: complex enough to survive, simple enough
            to afford.
          </P>
          <P>
            An <strong>extinction safeguard</strong> auto-spawns mutant agents if population
            drops to 1, preventing total extinction from terminating the simulation.
          </P>
        </MethodSection>

        {/* ── Environmental Physics ─────────────────────────────── */}
        <MethodSection
          id="physics"
          title="Environmental Physics"
          open={openSections.has("physics")}
          onToggle={() => toggle("physics")}
        >
          <P>
            The &ldquo;laws of physics&rdquo; in the simulation are fixed environmental
            constraints. They define the world the agents live in but do not constrain how
            agents choose to behave within it.
          </P>
          <P><strong>Energy:</strong></P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="Regeneration">Each node regenerates energy per tick (base rate 1.0), modulated by seasonal cycles</Def>
            <Def term="Harvesting">Agents extract energy from their current node (capped by available energy)</Def>
            <Def term="Costs">Existence costs tick_cost per tick; actions cost additional energy scaled by intensity; brain complexity costs energy per tick</Def>
            <Def term="Death">Energy reaching 0 kills the agent</Def>
          </div>
          <P><strong>Entropy:</strong></P>
          <div className="ml-4 space-y-1 text-[13px]">
            <Def term="Accumulation">Entropy increases by base_rate + age_factor &times; age each tick</Def>
            <Def term="Reduction">The maintenance effector reduces entropy (costs energy)</Def>
            <Def term="Lethality">Entropy reaching 100 kills the agent (entropy_resistance modulates rate)</Def>
          </div>
          <P><strong>Seasons:</strong></P>
          <P>
            Energy regeneration follows a sinusoidal cycle with period <Code>SEASON_PERIOD</Code> (200 ticks)
            and amplitude <Code>SEASON_AMPLITUDE</Code> (0.6). This creates periodic environmental
            pressure &mdash; agents must adapt their behaviour to boom and bust cycles.
            Season phase is sensed through channels 36-38.
          </P>
          <P><strong>Pheromones:</strong></P>
          <P>
            Agents deposit pheromone on visited nodes proportional to their energy fraction.
            Pheromone decays at 2% per tick (capped at 10.0 per node). This enables indirect
            communication: successful agents leave trails that others can follow. It&rsquo;s
            up to evolution whether agents evolve to use this information.
          </P>
        </MethodSection>
      </div>

      {/* Footer */}
      <div className="border-t border-border/50 mt-6 pt-6 pb-8">
        <p className="text-[12px] text-muted-foreground">
          For the complete implementation reference including database schema, checkpoint
          format, and API routes, see the project&rsquo;s <Code>claude.md</Code> file.
        </p>
      </div>
    </div>
  );
}

