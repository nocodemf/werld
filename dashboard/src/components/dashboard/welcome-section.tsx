"use client";

export default function WelcomeSection() {
  return (
    <div className="max-w-3xl">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Welcome to the Observatory
        </h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          A window into a living, evolving digital world.
        </p>
      </div>

      {/* Sections */}
      <div className="space-y-8 text-[14.5px] leading-relaxed text-foreground/90">
        {/* What is this? */}
        <section>
          <h2 className="text-[15px] font-semibold text-foreground mb-2">
            What is this?
          </h2>
          <p>
            We built a digital world and populated it with tiny artificial creatures &mdash; 
            we call them <em>agents</em>. Each agent has its own brain, its own senses, its own 
            drives. They live on a network of interconnected nodes, competing for energy, 
            avoiding decay, and &mdash; if they&rsquo;re successful enough &mdash; reproducing.
          </p>
          <p className="mt-3">
            No one tells them what to do. There are no rules about how to behave, no 
            instructions about what matters. They figure it out themselves, or they die trying. 
            Over thousands of generations, the population evolves.
          </p>
        </section>

        {/* How does it work? */}
        <section>
          <h2 className="text-[15px] font-semibold text-foreground mb-2">
            How does it work?
          </h2>
          <p>
            Every tick (a single step in time), each agent goes through the same cycle:
          </p>
          <ol className="mt-3 ml-5 space-y-2 list-decimal marker:text-muted-foreground">
            <li>
              <span className="font-medium text-foreground">Perceive</span> &mdash; 
              Sense what&rsquo;s around them: how much energy is nearby, how many other 
              agents are close, chemical trails left by others, even the season.
            </li>
            <li>
              <span className="font-medium text-foreground">Decide</span> &mdash; 
              Feed all of that sensory information into their brain (an evolved neural network) 
              to produce a set of &ldquo;muscle&rdquo; activations &mdash; continuous signals that 
              control movement, harvesting, self-repair, communication, reproduction, and more.
            </li>
            <li>
              <span className="font-medium text-foreground">Act</span> &mdash; 
              The world&rsquo;s physics interprets those signals. An agent might move to a 
              neighboring node, harvest energy, broadcast a signal, attack a rival, or try to 
              reproduce &mdash; all in the same tick.
            </li>
            <li>
              <span className="font-medium text-foreground">Learn</span> &mdash; 
              The agent records what happened in its memory and updates its reflex system. 
              But the real learning happens across generations, through evolution.
            </li>
          </ol>
          <p className="mt-3">
            When two agents reproduce, their child inherits a mix of both parents&rsquo; brains 
            and traits, with small random mutations. Children that survive long enough to 
            reproduce pass on their genes. Those that don&rsquo;t are lost. Natural selection 
            is the only teacher.
          </p>
        </section>

        {/* What makes this different? */}
        <section>
          <h2 className="text-[15px] font-semibold text-foreground mb-2">
            What makes this different?
          </h2>
          <p>
            Nothing about the agents is hardcoded. We didn&rsquo;t tell them to eat when 
            hungry, to avoid danger, or to cooperate with others. Every aspect of their 
            cognition is evolvable:
          </p>
          <ul className="mt-3 ml-5 space-y-1.5 list-disc marker:text-muted-foreground/60">
            <li>Their <span className="font-medium">brains</span> grow and rewire through evolution &mdash; new neurons, new connections, different activation functions.</li>
            <li>Their <span className="font-medium">senses</span> can sharpen or dull &mdash; each sensory channel has evolvable sensitivity.</li>
            <li>Their <span className="font-medium">internal drives</span> (hunger, curiosity, aggression, sociality) are inherited traits, not built-in rules.</li>
            <li>Their <span className="font-medium">memory</span> fades at a rate determined by their genes. How much social encounters matter to them is heritable too.</li>
            <li>Their <span className="font-medium">communication</span> bandwidth and content is brain-driven. If signals carry meaning, it&rsquo;s because evolution discovered that meaning is useful.</li>
            <li>Their <span className="font-medium">motor patterns</span> (learned routines like &ldquo;move then harvest&rdquo;) are self-discovered and inherited.</li>
          </ul>
          <p className="mt-3">
            If agents develop cooperation, language, specialisation, or any form of 
            social structure &mdash; it&rsquo;s because evolution found it, not because 
            we designed it.
          </p>
        </section>

        {/* What are we looking for? */}
        <section>
          <h2 className="text-[15px] font-semibold text-foreground mb-2">
            What are we looking for?
          </h2>
          <p>
            We&rsquo;re watching for emergence &mdash; complex, interesting behaviour that 
            arises from simple rules:
          </p>
          <ul className="mt-3 ml-5 space-y-1.5 list-disc marker:text-muted-foreground/60">
            <li>Do agents specialise? (Some harvest, some explore, some defend?)</li>
            <li>Do communication channels develop meaning?</li>
            <li>Do species diverge with different survival strategies?</li>
            <li>Do brains grow more complex over time? Is there a cost-benefit tradeoff?</li>
            <li>Do social structures form? Territories? Cooperation?</li>
            <li>How far can open-ended evolution take them?</li>
          </ul>
          <p className="mt-3">
            The simulation runs indefinitely. Every 1,000 ticks, a story chapter is 
            automatically written summarising what happened. We&rsquo;re watching this 
            civilisation unfold in real time.
          </p>
        </section>

        {/* Using the dashboard */}
        <section>
          <h2 className="text-[15px] font-semibold text-foreground mb-2">
            Using the Dashboard
          </h2>
          <p className="mb-3">
            The sidebar on the left gives you different views into the simulation:
          </p>
          <div className="grid gap-2">
            {[
              ["Overview", "Key metrics at a glance — population, energy, generation, recent events."],
              ["Story", "A chapter-by-chapter plain-English narrative of what's happened."],
              ["World Map", "Visual map of the network showing where agents are, energy levels, and density."],
              ["Population", "Birth/death dynamics, population trends, generational progress."],
              ["Evolution", "Species diversity, genetic divergence, fitness trajectories."],
              ["Brain", "Neural network complexity — how big and costly agent brains are becoming."],
              ["Intelligence", "What agents are actually doing — effector activations, motor patterns, cortex learning."],
              ["Ecology", "Ecosystem health — energy flow, diversity, homeostasis."],
              ["Resources", "Energy and entropy trends across the world and across agents."],
              ["Comms", "Communication activity — who's broadcasting, how much, signal content."],
              ["Agents", "Individual agent roster — click any agent to inspect its genome and vitals."],
            ].map(([name, desc]) => (
              <div key={name} className="flex gap-3 py-1.5">
                <span className="text-[13px] font-medium text-foreground w-24 shrink-0">
                  {name}
                </span>
                <span className="text-[13px] text-muted-foreground">{desc}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Closing */}
        <section className="pb-8">
          <div className="border-t border-border/50 pt-6 mt-2">
            <p className="text-[13px] text-muted-foreground italic">
              This world has no goal except to exist. What the agents make of it is 
              entirely up to them.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

