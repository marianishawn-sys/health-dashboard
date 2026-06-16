# Loop Engineering for a Hybrid Self-Hosted Master Orchestrator with Desktop Claude Sub-Orchestrators and Claude Code

**A deep, evidence-backed, step-by-step engineering manual.**

Status: research deliverable · Compiled 2026-06-16 · Target system: a self-hosted **master agent orchestrator** coordinating multiple **desktop Claude sub-orchestrators** that drive **Claude Code** workers, applied first to this repository's *Nutrition Concierge* concierge/coach loop.

---

## How to read this document

This report is organised around the four questions you asked, in order:

1. **What loop engineering is** — Part I (philosophy + foundations + the academic and industrial evidence base).
2. **How to design it** — Part II (topologies, termination, context management, memory, error handling, guardrails).
3. **How to facilitate it** — Part III (observability, evaluation, cost/latency budgets, checkpoints, reliability).
4. **How to utilize it** — Part IV (the concrete hybrid architecture: master orchestrator ⇄ desktop sub-orchestrators ⇄ Claude Code, mapped onto your existing drop-box loop) and Part V (a phased build plan).

Every claim that carries weight is cited inline with a bracketed reference `[n]` resolving to the **Bibliography** (§ References). Numbers that could not be byte-verified against a primary page in the research pass are tagged **`⚑secondary`** and reconciled in the **Claims Confidence Ledger** (Appendix D). Read that ledger before you quote a number in a board deck.

A note on intellectual honesty up front: a large fraction of the public "agent loop" literature is hype. This report deliberately gives equal billing to the **counter-evidence** — the cases where loops and multi-agent systems *underperform* — because an engineering manual that only tells you when things work will get you a large cloud bill and a fragile system. The single most important number in this entire document is the cost multiplier in §1.6, and the single most important design rule is the single-writer principle in §11.3.

---

# PART I — WHAT LOOP ENGINEERING IS

## 1. The core idea

### 1.1 Definition

**Loop engineering** is the discipline of designing, instrumenting, and operating the *iterative control cycle* that an LLM-based agent runs — the cycle in which the model repeatedly perceives state, decides, acts on its environment, and observes the consequences until a stopping condition fires. Where *prompt engineering* optimises a single model call and *context engineering* optimises the token state of that call (§4), **loop engineering optimises the cycle itself**: its topology, its termination, its budget, its memory, its failure handling, and its coordination with other loops.

The canonical loop, as Anthropic documents it for Claude Code and the Claude Agent SDK, is:

> **gather context → take action → verify work → repeat.** [2]

Anthropic explicitly generalises this loop beyond coding — "deep research, video creation, note-taking, and other applications" [2]. That generalisation is exactly why it applies to a *nutrition concierge*: planning meals, reconciling a pantry, and chasing grocery deals is the same loop with different tools.

### 1.2 The atom: the augmented LLM

The smallest unit of an agentic system is not "a prompt" — it is an **augmented LLM**: a model enhanced with **retrieval, tools, and memory**, able to generate its own queries, select tools, and decide what to retain [1].

> "The basic building block of agentic systems is an LLM enhanced with augmentations such as retrieval, tools, and memory. Current models can actively use these capabilities—generating their own search queries, selecting appropriate tools, and determining what information to retain." — Anthropic, *Building Effective Agents* [1]

A loop is just an augmented LLM placed under feedback: the output of one turn becomes part of the input of the next, mediated by the environment.

### 1.3 Workflows vs. agents — the first design fork

Anthropic draws the foundational distinction you must internalise before building anything [1]:

> "**Workflows** are systems where LLMs and tools are orchestrated through **predefined code paths**."
>
> "**Agents** … are systems where LLMs **dynamically direct their own processes and tool usage**, maintaining control over how they accomplish tasks." [1]

- A **workflow** is a *fixed loop or DAG you write in code*. The control flow is yours; the model fills in the blanks. Predictable, cheap, testable.
- An **agent** is a *loop the model drives*. The model decides how many iterations, which tools, in what order. Flexible, expensive, harder to test.

> "Agents can handle sophisticated tasks, but their implementation is often straightforward. They are typically just **LLMs using tools based on environmental feedback** … Once the task is clear, agents plan and operate independently, potentially returning to the human for further information or judgement." [1]

**Loop engineering is the art of choosing, for each part of your system, how much of the loop to hand to the model and how much to keep in deterministic code.** This is not a binary; production systems are *mosaics* of workflow loops with agentic loops embedded at the leaves.

### 1.4 The simplicity principle (the most ignored advice in the field)

Anthropic's headline recommendation:

> "find the simplest solution possible, and only increas[e] complexity when needed … This might mean **not building agentic systems at all**. Agentic systems often trade latency and cost for better task performance." [1]

> "Workflows offer predictability and consistency for well-defined tasks, whereas agents are the better option when flexibility and model-driven decision-making are needed at scale. For many applications, however, **optimizing single LLM calls with retrieval and in-context examples is usually enough**." [1]

Translate this into a hard rule for your build: **every loop you add must justify the latency and token cost it incurs over the next-simplest alternative.** Most of your concierge's behaviour (logging a food, decrementing pantry stock) should remain deterministic app code — *not* an agent loop. Reserve loops for the genuinely open-ended parts: research ("find this week's best protein deals"), planning ("build a 7-day plan that hits my macros from what's on sale"), and reconciliation ("the pantry scan disagrees with the diary — fix it").

### 1.5 The loop pattern catalogue

There are six canonical compositions. The first five are *workflow* patterns (you write the control flow); the sixth is the *autonomous agent* loop (the model writes it). All definitions are Anthropic's [1].

| # | Pattern | Definition (Anthropic) | Use when | In your system |
|---|---------|------------------------|----------|----------------|
| 1 | **Prompt chaining** | "Decomposes a task into a sequence of steps, where each LLM call processes the output of the previous one" with optional programmatic "gate" checks [1] | Task cleanly splits into fixed subtasks; trade latency for accuracy | Recipe parse → macro lookup → ingredient-registry match |
| 2 | **Routing** | "Classifies an input and directs it to a specialized followup task" [1] | Distinct categories handled better separately | A desktop sub-orchestrator classifies an inbound request → groceries vs. meal-plan vs. deals |
| 3 | **Parallelization** | *Sectioning* ("independent subtasks run in parallel") and *Voting* ("running the same task multiple times to get diverse outputs") [1] | Subtasks independent, or you want consensus | Scan three flyers in parallel (sectioning); three macro estimates → median (voting) |
| 4 | **Orchestrator–workers** | "A central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results … subtasks aren't pre-defined, but determined by the orchestrator" [1] | Can't predict the subtasks up front | **The master orchestrator tier** (Part IV) |
| 5 | **Evaluator–optimizer** | "One LLM call generates a response while another provides evaluation and feedback in a loop" [1] | Clear eval criteria + iterative refinement adds measurable value | The **verify** step: a critic checks a proposed meal plan against macro targets and budget, returns fixes |
| 6 | **Autonomous agent** | The model "plan[s] and operate[s] independently," gaining "**ground truth** from the environment at each step," pausing "for human feedback at checkpoints," terminating on completion or "a maximum number of iterations" [1] | Open-ended tasks, unpredictable step count | A Claude Code worker turned loose on "reconcile the pantry with last week's diary" |

Reference implementations for all of these are in the Anthropic cookbook [3].

### 1.6 The academic spine of the loop

Three papers are the load-bearing theory under the "repeat" in the loop:

- **ReAct** (Yao et al., ICLR 2023) — interleave **Thought → Action → Observation**. This is the literal shape of an agentic turn. The headline, well-corroborated result: on the interactive benchmarks **ALFWorld and WebShop, ReAct beat imitation/RL methods by an absolute success rate of 34% and 10% respectively, with only one or two in-context examples** [4]. ReAct's mechanism is that acting on the environment supplies *ground truth* that "overcomes issues of hallucination and error propagation prevalent in chain-of-thought reasoning" [4]. This is the academic justification for Anthropic's "gain ground truth at each step" rule [1].
- **Reflexion** (Shinn et al., 2023) — add a *self-critique* memory: the agent "verbally reflect[s] on task feedback … and maintain[s] reflective text in an episodic memory buffer to induce better decision-making in subsequent trials" [5]. This is the academic form of the evaluator-optimizer loop. Reported gains: ~**+20 points on HotPotQA** and notable AlfWorld improvement over iterative trials [5] **`⚑secondary`** (exact figures vary by summary — see Appendix D).
- **Self-Consistency** (Wang et al., 2022) — sample multiple reasoning paths, take the **majority vote** [6]. This is the academic form of Anthropic's "Voting" parallelization variant [1].

**Why this matters for design:** these three give you three orthogonal knobs to *spend tokens for quality* — iterate (ReAct), reflect (Reflexion), and vote (Self-Consistency). Every one of them trades tokens/latency for accuracy, which is the central economic tension of §1.7.

### 1.7 The master equation: loops are token engines

This is the most important quantitative idea in the report. **A loop re-bills its accumulated history on every cycle.** Each turn = (read full transcript) → (model call) → (tool call) → (append result) → repeat. The transcript grows, so cost grows *super-linearly* in turns unless you actively manage context (Part II).

Anthropic quantified the consequence directly from their production multi-agent research system:

> "Agents typically use about **4× more tokens** than chat interactions, and **multi-agent systems use about 15× more tokens** than chats." [7]

And — the single most useful empirical finding in the agent literature —

> "**Token usage by itself explains 80% of the variance**" in performance on their evaluation [7][8].

A fuller decomposition reported alongside it: three factors — token usage (~80%), number of tool calls (~10%), and model choice (~5%) — explain ~95% of performance variance [8] **`⚑secondary`** (the 80% is firmly attested; the 10/5 split is from secondary analyses).

The payoff side: a multi-agent system with **Claude Opus 4 as lead + Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by 90.2%** on their internal research eval [7].

**The loop engineer's prime directive follows immediately:**

> Quality is bought with tokens. Loops, sub-agents, reflection, and voting are all *mechanisms for spending more tokens in a structured way*. Therefore every architectural decision is, at bottom, a decision about **where to spend tokens and where to refuse to** — and the only loops worth building are those whose output value exceeds their token cost (≈4× for single agents, ≈15× for multi-agent vs. a plain chat call) [7].

This directive governs Parts II–IV.

---

# PART II — HOW TO DESIGN A LOOP

Design is six decisions, taken in order. Skipping any one of them is how loops become runaway cost centres or silent corruption engines.

## 2. Decision 1 — Choose the topology

Pick the *simplest* topology that fits, per §1.4. A decision procedure:

1. **Is the control flow predictable?** → use a **workflow** pattern (chaining/routing/parallelization). Keep the loop in your code.
2. **Are the subtasks unpredictable but decomposable by one coordinator?** → **orchestrator–workers** (§1.5 #4). One brain decomposes, many hands execute.
3. **Is there a clear quality bar and refinement helps?** → wrap the executor in an **evaluator–optimizer** loop (§1.5 #5).
4. **Is the task genuinely open-ended with an unknowable step count?** → a single **autonomous agent** loop with hard stopping conditions (§3).

**When to go multi-agent — and when not to.** This is contested, and you should treat both sides as evidence:

- **For (Anthropic):** multi-agent wins on tasks with "heavy parallelization, information that exceeds single context windows, and interfacing with numerous complex tools" [7]. Their system used two levels of parallelism — the lead spawns **3–5 subagents in parallel**, each running **3+ tools in parallel** — "reducing research time by **up to 90%** for complex queries" [7] **`⚑secondary`** (the "up to 90%" time figure is from the post, corroborated across summaries).
- **Against (Cognition, "Don't Build Multi-Agents"):** parallel *writer* agents make conflicting implicit decisions. Their two principles: **"Share context"** and **"Actions carry implicit decisions, and conflicting decisions carry bad results"** [9]. Their refined 2026 position: the only reliably-working pattern is **single-writer** — "there is only one writer, and only intelligence is bundled"; read-only sub-agents (search, exploration) are fine, parallel writers are not [10].
- **Against (empirical, MAST / UC Berkeley):** an analysis of 200+ execution traces across 7 multi-agent frameworks produced a failure taxonomy in which **41.8% of failures are specification/system-design issues, 36.9% are inter-agent misalignment, and 21.3% are task-verification failures** [11]. Conclusion: most multi-agent failure is *architectural*, not model-quality — i.e. it is *your loop design* that fails, not Claude.
- **Against (benchmarks):** on strongly-sequential tasks (GAIA) a single agent can beat multi-agent because decomposition risks information loss; on focused coding (SWE-bench) "no architecture achieves better results than the other" [12] **`⚑secondary`**. Anthropic themselves note **coding is "less parallelizable"** because it needs shared context and tight sequential dependencies [7].

**Synthesis / design rule:** Use multi-agent for **breadth-first, read-heavy** work (research, deal-hunting, scanning many sources) and **single-agent or single-writer** for **depth-first, write-heavy** work (editing the data file, modifying `index.html`). This maps cleanly onto your system in Part IV.

## 3. Decision 2 — Define termination (stopping conditions)

A loop without a hard stop is an unbounded liability. Anthropic's rule:

> "The task often terminates upon completion, but it's also common to include **stopping conditions (such as a maximum number of iterations)** to maintain control." [1]

Engineer **four independent stop conditions**, any of which halts the loop:

1. **Goal satisfied** — an explicit success predicate (e.g., "the meal plan covers 7 days and every day is within ±10 g protein of target"). Prefer an *evaluator* (§1.5 #5) returning a pass/fail, not the actor's own say-so.
2. **Iteration ceiling** — `max_turns` / max iterations. In Claude Code/SDK this is a first-class control [13].
3. **Budget ceiling** — a token/cost cap. Use `max_tokens` per response and, where available, **Task Budgets** (`task_budget`, beta) where the model sees a running countdown and self-moderates (min 20K tokens) [14].
4. **Wall-clock / no-progress** — a deadline, plus a *no-progress* detector (N consecutive turns with no state change → abort). The "ground truth at each step" principle [1] gives you the signal: if ground truth doesn't change across turns, the loop is spinning.

**Anti-pattern:** letting the model decide it's done with no external check. Combine with §10 (evaluation) so "done" is *verified*, not *asserted*.

## 4. Decision 3 — Engineer the context (keeping the loop coherent over many turns)

This is where most long loops die. **Context engineering** is "answering the broader question of 'what configuration of context is most likely to generate our model's desired behavior?'" — curating "the set of tokens included when sampling," not just writing a prompt [15].

The governing constraint is the **finite attention budget**:

> "Good context engineering means finding the **smallest possible set of high-signal tokens** that maximize the likelihood of some desired outcome, given that LLMs are constrained by a finite attention budget." [15]

And the failure mode you are fighting is **context rot** — documented in Anthropic's own product docs, not just marketing:

> "As token count grows, **accuracy and recall degrade, a phenomenon known as context rot**. This makes curating what's in context just as important as how much space is available." [16]

Independent quantification (Chroma, 18 models incl. Claude 4 Opus/Sonnet): performance "varies significantly as input length changes, even on simple tasks," with reported accuracy losses on the order of **20–50% from ~10k → 100k+ tokens** on needle-in-haystack tasks [17] **`⚑secondary`** (direction robust; exact band from secondary summaries).

**The practical implication:** a bigger context window is *not* a substitute for context engineering. Current Claude models ship a **1M-token window** (Opus 4.8/4.7/4.6, Sonnet 4.6, Fable/Mythos 5) at **standard pricing** — "a 900k-token request is billed at the same per-token rate as a 9k-token request" [18][19] — and 200K on older models [16]. But filling that window degrades quality *and* re-bills on every loop turn. **Treat context as a curated working set, not a bucket.**

The five techniques, in order of how often you'll reach for them:

### 4.1 Compaction (summarise older context near the limit)

Anthropic ships server-side **compaction**: it "automatically summariz[es] older context when approaching the context window limit … replacing stale content with concise summaries" [20]. Mechanics that matter for design:

- Default **trigger at 150,000 input tokens**; configurable minimum **50,000** [20].
- It emits a `<summary>` capturing "state, next steps, learnings" and **drops all message blocks prior to the compaction point**, continuing from the summary [20].
- Claude Code's interactive *auto-compact* is the same idea applied to a coding session — it summarises history "preserving architectural decisions and unresolved bugs while discarding redundant tool outputs" [15] **`⚑secondary`** (auto-compact internals are partly community-reverse-engineered — Appendix D).

**Design rule:** assume compaction *will* happen on any long loop. Put anything the loop must not forget (the plan, the budget, the success predicate) into **durable memory** (§4.3), not the transcript — because the transcript is exactly what compaction throws away.

### 4.2 Context editing (cheap pruning)

Lighter than compaction: **tool-result clearing** and **thinking-block clearing** remove stale tool outputs without a model call ("microcompact") [16]. Use these aggressively in tool-heavy loops (pantry scans, flyer OCR) where each tool result is large and only momentarily relevant.

### 4.3 External memory / structured note-taking (the durability primitive)

The **memory tool** lets Claude "create, read, update, and delete files that persist between sessions … allowing it to build knowledge over time **without keeping everything in the context window**" [21]. Its auto-injected system prompt is the philosophy in one line:

> "ASSUME INTERRUPTION: Your context window might be reset at any moment, so **you risk losing any progress that is not recorded in your memory directory**." [21]

This is the mechanism behind the production pattern Anthropic uses for long research runs: the lead agent **saves its plan to memory** precisely because, "if the context window exceeds 200,000 tokens it will be truncated and it is important to retain the plan" [7]. For multi-hour coding, Anthropic's long-running-agent harness uses an **initializer** that writes a `feature-list.json` and an init script, then a coding agent woken repeatedly to make incremental progress, run tests, leave a `claude-progress.txt` note, and commit [22].

**This is the most important pattern for your system.** Your concierge already does a primitive version of it (the Drive data file is durable memory; `coach-*.json` files are notes). Part IV upgrades it.

### 4.4 Just-in-time retrieval (don't pre-load — fetch on demand)

Rather than stuffing everything in up front, keep "lightweight identifiers (file paths, stored queries, web links)" and "dynamically load data into context at runtime using tools" [15]. Claude Code's native style is **agentic search** — running `grep`/`find`/`tail` to load only the relevant slice of a file rather than ingesting whole documents [2][15]. Design your tools so the agent can *query* your data (pantry, diary, deals) rather than receiving a giant JSON blob each turn.

### 4.5 Sub-agent context isolation (the multiplier)

Give expensive exploration its **own context window** and return only a distilled summary:

> "Each subagent might explore extensively, using tens of thousands of tokens or more, but returns only a condensed, distilled summary of its work (often **1,000–2,000 tokens**)." [15]

This is *the* reason multi-agent can outperform: it parallelises *context*, not just compute — "by distributing work across agents with separate context windows, the architecture adds capacity for parallel reasoning that single agents simply cannot match" [7]. Each Claude Code subagent "runs in its own context window with a custom system prompt, specific tool access, and independent permissions" [23].

### 4.6 Context awareness

Current Claude models (Sonnet 4.6, Haiku 4.5) **track their own remaining token budget** during a conversation, via injected markers like `<budget:token_budget>1000000</budget:token_budget>` and per-tool-call `Token usage: 35000/1000000` warnings [16]. Anthropic's analogy: "lacking context awareness is like competing in a cooking show without a clock" [16]. You don't have to build this — but you should *prompt your agents to respect it* ("when your remaining budget drops below X, write a checkpoint and stop").

## 5. Decision 4 — State and memory architecture

Separate three tiers explicitly; conflating them is a top source of bugs:

| Tier | Lives in | Lifetime | Holds | Mechanism |
|------|----------|----------|-------|-----------|
| **Working memory** | the context window | one loop run (until compaction) | current reasoning, recent tool results | the transcript |
| **Episodic / task memory** | external files | a task across sessions | the plan, progress log, success predicate, learnings | memory tool [21] / `claude-progress.txt` [22] |
| **Durable system state** | your database | forever | the *truth* (pantry, diary, recipes) | your Drive `dashboard-data.json` |

**Rule:** the loop reads from all three but **writes durable state through exactly one path** (the single-writer principle, §11.3). Working and episodic memory are scratch; durable state is sacred.

## 6. Decision 5 — Error handling and retries

> "**Errors compound in stateful execution, so checkpoints and retries are essential.**" [7]

Engineer for compounding failure:

1. **Idempotency** — every action must be safe to repeat, because retries *will* repeat it. (Your codebase already does this: the coach-ingest merge **skips a food/recipe whose name already exists** and skips an already-listed unchecked coach grocery item — `index.html` `ingestCoachFiles`. That is idempotent-merge, the correct pattern.)
2. **At-least-once delivery with retry-on-error** — also already in your code: the ingest loop **does not delete a file on error** ("leave file for retry on next load"). This is textbook durable-queue behaviour. Generalise it (Part IV).
3. **Bounded retries with backoff** — the Anthropic SDKs auto-retry 429/5xx with exponential backoff (default `max_retries=2`) [14]; your own git/Drive operations should mirror this (your task brief already mandates 2s/4s/8s/16s backoff).
4. **Adapt-on-failure** — let the agent "adapt when tools fail" rather than hard-crashing [7]; surface the tool error back into the loop as an observation (ReAct ground truth [4]).
5. **Checkpoints** — write resumable state at every meaningful boundary so a crashed multi-hour run resumes in "seconds," not from scratch [21][22].

## 7. Decision 6 — Guardrails

Three layers, all from primary guidance:

1. **Stopping conditions** (§3) — the guardrail against runaway loops [1].
2. **Human-in-the-loop checkpoints** — "build checkpoints where agents pause for human review, **particularly important before they carry out irreversible actions**, like approving financial transactions or deleting data" [1]. In your system: any *destructive* data edit (clearing the diary, deleting recipes) must pause for confirmation; additive proposals (new recipe, grocery item) can flow autonomously.
3. **Sandboxing + permission gating** — "extensive testing in sandboxed environments, along with the appropriate guardrails" [1]. Concretely (Part IV): Claude Code permission modes (`plan`, `acceptEdits`, `dontAsk`, `bypassPermissions`) [24], `permissions.allow`/`deny` rules that *merge across scopes with `deny` winning* [25], and `PreToolUse` hooks that can `allow|deny|ask` a tool call deterministically [26].

---

# PART III — HOW TO FACILITATE A LOOP

Designing a loop is half the job. *Facilitating* it — making it observable, evaluable, affordable, and reliable in production — is the half that determines whether it survives contact with reality. "Agents run for a long time, errors compound" [7]; facilitation is how you keep that from being fatal.

## 8. Observability and tracing

You cannot debug what you cannot see, and an agentic loop is a black box by default. Standardise on the **OpenTelemetry GenAI semantic conventions** so your traces are portable across tools [27]. The attributes you must emit per step:

- `gen_ai.operation.name` — `chat`, `execute_tool`, `invoke_agent`, `retrieval`, etc. [27]
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` — "SHOULD include all types of input tokens, including cached tokens" [27]. **This is your cost telemetry; without it you are flying blind on the §1.7 prime directive.**
- `gen_ai.request.model`, `gen_ai.tool.name`, `gen_ai.tool.call.id` [27].
- Span naming: inference → `{operation} {model}`; tool → `execute_tool {tool_name}` [27].

**Tooling (2026):** for a *self-hosted* master orchestrator, **Langfuse** is the natural fit — open-source (MIT), self-hosting first-class, built on OpenTelemetry, framework-agnostic; it captures prompts, responses, token usage, latency, and intermediate steps (tool calls, retrieval) [28]. **LangSmith** is the proprietary SaaS alternative with deep tracing/cost dashboards [29]; prefer it only if you don't need data to stay on your hardware. Given your "hybrid self-hosted" requirement, **default to self-hosted Langfuse**.

What to log at minimum, per loop turn: token usage (input/output/cache), every tool call + result size, the model used, agent-invocation boundaries (parent→subagent), and the decision/stop reason. Anthropic's production lesson: **full tracing was "essential for diagnosing failures, monitoring agent decision patterns"** — while deliberately *not* storing sensitive user content, monitoring "high-level decision patterns … while maintaining user privacy" [7]. For a *health* app this privacy posture is mandatory, not optional.

## 9. Cost and latency budgets (the economics)

### 9.1 Current Claude pricing (verified 2026-06-16, per million tokens) [19]

| Model | Input | Output | 5-min cache write | 1-hr cache write | Cache **read** (hit) |
|-------|------:|-------:|------------------:|-----------------:|---------------------:|
| **Claude Opus 4.8** | $5 | $25 | $6.25 | $10 | **$0.50** |
| Claude Opus 4.7 / 4.6 / 4.5 | $5 | $25 | $6.25 | $10 | $0.50 |
| **Claude Sonnet 4.6** (and 4.5) | $3 | $15 | $3.75 | $6 | **$0.30** |
| **Claude Haiku 4.5** | $1 | $5 | $1.25 | $2 | **$0.10** |
| Claude Fable 5 | $10 | $50 | $12.50 | $20 | $1.00 |
| Claude Opus 4.1 *(deprecated)* | $15 | $75 | $18.75 | $30 | $1.50 |

Key facts that change your loop math:

- **1M context is standard-priced** on Opus 4.8/4.7/4.6 and Sonnet 4.6 — no long-context surcharge any more (it existed historically for the Sonnet 4/4.5 beta and is **gone** on current models) [18][19] **`⚑secondary`** for the *historical* premium figure; the *current* "no surcharge" is primary [19].
- **Batch API: −50%** on input *and* output [19]. Use it for every non-interactive loop (overnight planning, deal sweeps).
- **Prompt caching multipliers:** 5-min write **1.25×**, 1-hr write **2×**, **cache read 0.1× (90% off)** [19]. "Caching pays off after just one cache read for the 5-minute duration … or after two cache reads for the 1-hour duration" [19]. Anthropic's own announcement: caching "reduces costs by up to 90% and reduces latency by up to 85% for long prompts" [30].
- **Tokenizer change:** "Opus 4.7 and later use a new tokenizer … may use up to **35% more tokens** for the same fixed text" [19]. Re-baseline any cost estimate when you move to 4.7/4.8.
- **Web search:** $10 per 1,000 searches + tokens [19]. **Code execution:** 1,550 free container-hours/month/org, then $0.05/hour [19]. **Managed Agents runtime:** $0.08 per session-hour while `running` [19].

### 9.2 Worked cost model for your system

The §1.7 multipliers make the budget tractable. Anchor examples from the pricing page [19]:

- 10,000 support-ticket classifications on **Haiku 4.5** (~3,700 tok each) ≈ **$37 total**.
- A 1-hour **Opus 4.8** coding session (50K in / 15K out) ≈ **$0.705**, dropping to **~$0.525** with 40K of input served from cache [19].

Apply to a nutrition concierge: a nightly *deal-sweep + meal-plan* run that does, say, 30 agent turns averaging 20K cached-input + 2K output on **Sonnet 4.6** with a stable cached system prefix:
`30 × (20K × $0.30/M cache-read + 2K × $15/M out)` ≈ `30 × ($0.006 + $0.030)` ≈ **$1.08/night** ≈ **~$33/month** — *if* you cache the prefix and tier to Sonnet. Run the same on Opus without caching and you are at 5–10× that. **The caching + model-tiering decisions are the difference between a $33 and a $300 monthly bill.**

### 9.3 Budget enforcement (not just estimation)

Estimating is useless without enforcement. Enforce at three levels:

1. **Per response:** `max_tokens`.
2. **Per task:** `task_budget` (beta) — the model sees a countdown and self-moderates, min 20K [14].
3. **Per loop / per night:** your orchestrator tracks cumulative `total_cost_usd` (Claude Code headless emits this in `--output-format json` [13]) and trips the §3 budget stop.

### 9.4 Latency

Honest gap: hard per-step latency benchmarks for Claude agent loops are not publicly published in primary sources [research gap, Appendix D]. What *is* established: **parallelism cuts wall-clock time** (parallel subagents + parallel tool calls → "up to 90%" research-time reduction [7]); **caching cuts latency up to 85% on long prompts** [30]; and **LLM-as-judge evals run ~15s each** [31] **`⚑secondary`**. Design for latency by parallelising independent work (§2) and caching stable prefixes — and *measure your own* step latency via §8 telemetry, since you cannot borrow someone else's number.

## 10. Evaluation (proving the loop works)

Anthropic's evaluation philosophy, from two posts, is counterintuitive and worth following exactly:

1. **Evaluate the outcome, not the path.** "Evaluat[e] the final outcome — did the user get correct information — and **not penalizing intermediate steps**" [31]. For non-deterministic multi-agent loops they "do not check whether the agents followed a 'correct' sequence of tool calls" because there *is* no single correct path [7]. Score the **end state of the environment**, not the trajectory.
2. **Start tiny.** "You don't need 1,000 eval tasks to start — beginning with **20–50 real conversation failures** from production has large effects" [31]; "a small sample of about **20 queries**" was often enough to see a change's impact [7]. Build your first eval set from *real* concierge failures, not imagined ones.
3. **LLM-as-judge, with a rubric.** A single LLM call scoring **0.0–1.0** against a rubric (factual accuracy, completeness, source quality, tool efficiency) "proved most consistent with human judgment" [7]; cost "about **$0.06 per evaluation**, ~15 seconds" [31] **`⚑secondary`**. Let the judge answer **"Unknown"** when evidence is insufficient [31].
4. **Keep humans in the loop for what judges miss.** Human testers caught a bias (agents "preferred SEO-optimized content over higher-quality but lower-ranked sources") that the LLM judge missed [7]. Treat evals as "scientific instruments," not scorecards [31].

**For your concierge**, concrete evals: "does the generated plan hit macro targets within tolerance?" (rule-based grader — deterministic, cheap, run on every plan), "are the deals real and unexpired?" (rule-based + web check), "is the recipe parse faithful to the source text?" (LLM-judge). Wire these as the *evaluator* in your evaluator-optimizer loops (§1.5 #5) so eval is not a separate batch job but part of the loop's verify step.

## 11. Reliability engineering

Four primitives, all primary-sourced:

1. **Checkpoints + retries** are "essential" because errors compound in stateful runs [7] (§6).
2. **Resumability** — capture `session_id` and resume (`--resume`/`--continue` in Claude Code [13]; `resume=session_id` in the SDK [13]) so a long loop survives a crash.
3. **Rainbow deployments** — when you ship a new version of a long-running loop, shift traffic gradually with both versions live, because "highly stateful agent webs run almost continuously and standard deployment approaches could break running agents mid-process" [7].
4. **Deterministic vs. stochastic control** — the *path* is non-deterministic; gate on **outcomes** (§10) and wrap stochastic agent steps in deterministic code (workflows, hooks, validators) wherever correctness matters. This is the same idea as §1.3, applied to reliability.

---

# PART IV — HOW TO UTILIZE IT: THE HYBRID ARCHITECTURE

This part maps everything above onto your specific target: a **hybrid self-hosted master agent orchestrator** coordinating **desktop Claude sub-orchestrators** that drive **Claude Code**, applied first to the Nutrition Concierge in this repo.

## 12. Where you are today (the existing loop)

Your repo already runs a real, if primitive, agentic loop. Naming it precisely matters, because you are going to *extend* it, not replace it:

- A **Health Concierge Orchestrator** running on Claude.ai writes typed `coach-*.json` files into a Google Drive folder (`My Drive / 04 - Personal / Health Concierge`) [`coach-templates/README.md`].
- The PWA, on open, runs `ingestCoachFiles()` — a **drain-and-delete** loop: search for `coach-*.json`, ingest in a fixed order (**additions → recipes → mealplan**, so dependencies resolve), **idempotently merge** (skip dupes by name), then **delete each file** — *except on error, where it leaves the file for retry* [`index.html:584–716`].
- Five message types form a **typed contract**: `additions`, `recipes`, `mealplan`, `grocery`, `deals` (the last is a *full replace*; the rest *append/merge*) [`coach-templates/README.md`].

In loop-engineering terms you already have: a **message bus** (the Drive folder), a **typed event contract** (the `type` field), **at-least-once delivery with retry** (don't-delete-on-error), **idempotent merge** (name-dedupe), and **provenance tagging** (`source:"coach"`). This is a solid foundation. What it lacks: a *driving* loop (it's pull-on-open, not continuous), *multiple* coordinated agents, *budget/observability*, and *verification*.

## 13. The target topology (three tiers)

Map the canonical patterns (§1.5) onto three tiers, respecting the single-writer principle throughout:

```
                          ┌───────────────────────────────────────┐
                          │   TIER 1 — MASTER ORCHESTRATOR         │
                          │   (self-hosted, headless, continuous)  │
                          │   Pattern: orchestrator–workers (§1.5#4)│
                          │   • owns the goal queue + schedule      │
                          │   • decomposes goals → tasks            │
                          │   • enforces budgets + stop conditions  │
                          │   • writes PLAN to durable memory       │
                          │   • emits/consumes typed events         │
                          └───────────────┬───────────────────────┘
                                          │  typed event bus
                                          │  (generalised coach-*.json /
                                          │   MCP / message queue)
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
   ┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
   │ TIER 2 — DESKTOP   │    │ TIER 2 — DESKTOP   │    │ TIER 2 — DESKTOP   │
   │ CLAUDE SUB-ORCH.   │    │ CLAUDE SUB-ORCH.   │    │ CLAUDE SUB-ORCH.   │
   │ (Claude Desktop,   │    │  …                 │    │  …                 │
   │  MCP host)         │    │ Pattern: routing   │    │ human-in-the-loop  │
   │ • human-facing     │    │  (§1.5#2)          │    │  checkpoints (§7)  │
   │ • routes + approves │    └─────────┬──────────┘    └────────────────────┘
   └─────────┬──────────┘              │
             ▼                          ▼
   ┌────────────────────┐    ┌────────────────────┐
   │ TIER 3 — CLAUDE    │    │ TIER 3 — CLAUDE    │   Pattern per worker:
   │ CODE WORKER        │    │ CODE WORKER        │   ReAct autonomous loop (§1.6)
   │ (headless claude -p)│    │  …                 │   + evaluator–optimizer verify
   │ • read-heavy: own   │    │ • write-heavy:     │     (§1.5#5)
   │   context, returns  │    │   SINGLE WRITER to │
   │   distilled summary │    │   the data file    │
   └────────────────────┘    └────────────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │ DURABLE STATE (single      │
                          │ writer): dashboard-data.json│
                          │ + the PWA as actuator/UI    │
                          └───────────────────────────┘
```

### 13.1 Tier 1 — the master orchestrator (self-hosted)

**What it is:** a long-running, headless process you host on your own hardware, built on the **Claude Agent SDK** — "the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript" [32]. It is the **LeadResearcher** analog [7]: it owns the goal queue, decomposes goals into tasks, decides how many workers to spawn, enforces budgets, and synthesises results.

**Why the SDK and not the API directly:** the SDK *runs the loop for you* ("Claude handles tools autonomously"), versus the raw Client SDK where "you implement a tool loop" [32]. You want the batteries-included loop plus built-in context management (compaction §4.1, subagents §4.5).

**Effort scaling (don't over-spawn).** Bake Anthropic's effort-scaling rules into the orchestrator's prompt so it matches worker count to task complexity [7]:
- simple fact-finding → **1 worker, 3–10 tool calls**;
- direct comparison → **2–4 workers, ~10–15 tool calls each**;
- complex task → **10+ workers** with divided responsibilities.

This directly controls the §1.7 token bill — over-spawning on a trivial query is the most common multi-agent cost leak [7].

**Plan persistence (§4.3).** The orchestrator's *first* action on any goal is to write its plan + success predicate + budget to **durable memory** [21], because compaction *will* eventually drop the transcript [7][20]. This is the "save plan to Memory" pattern, and it is non-negotiable for multi-hour runs.

**Scheduling.** Run it continuously and trigger work via Claude Code **routines/`/schedule`** (cron-like) [33] or your own cron invoking the SDK headless. This turns your *pull-on-open* loop into a *continuous* loop.

### 13.2 Tier 2 — desktop Claude sub-orchestrators

**What they are:** **Claude Desktop** instances (macOS/Windows) acting as **MCP hosts** — human-facing routers and approval gates. Claude Desktop "consumes MCP tools/servers"; it is *not* the coding CLI [34]. Its role in your topology: be the **human-in-the-loop checkpoint** (§7) and the **routing** layer (§1.5 #2) — you talk to it, it classifies your intent (groceries vs. plan vs. deals vs. "fix the app"), and it dispatches to the master orchestrator or directly to a Claude Code worker.

**How they connect:**
- **Desktop Extensions (`.mcpb`)** — "one-click MCP server installation" for *local* MCP servers, operating "within corporate network boundaries using existing authenticated context" with no token management [34]. Use these to give the desktop tier local tools (read the Drive folder, call your self-hosted services).
- **Connectors** — *remote* MCP servers, supported on both Desktop and claude.ai web [34]. Use these to reach your self-hosted master orchestrator over the network (expose the orchestrator as an MCP server; the desktop tier calls it).

**Why a desktop tier at all:** it gives you a human at the wheel for irreversible actions (§7) and a natural place for the *single human approval* that gates destructive edits — while keeping the heavy, autonomous work off your personal machine and on the self-hosted Tier 1.

### 13.3 Tier 3 — Claude Code workers

**What they are:** **headless `claude -p` invocations** — "using the Agent SDK via the CLI" [13] — spawned by Tier 1 (or Tier 2) to do the actual work. Each is its own process, its own session, its own context window.

**The read/write split (this is where §2's synthesis becomes concrete):**
- **Read-heavy workers** (deal-hunting, flyer scanning, recipe research, pantry reconciliation analysis) → spawn *many in parallel*, each with an isolated context window, each returning a **distilled 1–2K-token summary** [15]. These are the "read-only subagents" that even the multi-agent skeptics endorse [10]. They never write durable state; they produce *proposals* (typed events).
- **Write-heavy workers** (editing `dashboard-data.json`, modifying `index.html`, committing code) → **single-threaded, single writer** [10]. Exactly one worker at a time holds the write lease on a given resource. This honours Cognition's single-writer principle [10] and avoids the 36.9% "inter-agent misalignment" failure class [11].

**Invocation shape (headless):**
```bash
claude -p "Reconcile the pantry against last week's diary; output proposed corrections as coach-*.json" \
  --output-format json \
  --allowedTools "Read,Grep,Glob,Bash" \
  --permission-mode plan
# parse .session_id (to resume) and .total_cost_usd (for the budget stop, §9.3)
```
`--output-format json` returns `result`, `session_id`, and `total_cost_usd` [13]; `stream-json` gives you live events for the §8 trace [13]. Use `--bare` for reproducible CI-style runs (it skips auto-loading hooks/skills/MCP/CLAUDE.md; "will become the default for `-p` in a future release") [13].

## 14. The message bus: generalise your drop-box into a typed event/command bus

Your `coach-*.json` drop-box is already a message bus — keep its proven semantics and generalise it. Two design choices:

1. **Keep the file-based bus** (lowest-risk, builds on working code) — generalise `coach-*.json` into a typed envelope with an **idempotency key** and **provenance**, and keep the drain-and-delete + don't-delete-on-error loop verbatim (it is already correct, §6).
2. **Or upgrade to MCP** — expose the orchestrator and the data layer as **MCP servers** so tiers call each other as tools (`mcp__<server>__<tool>`) [35]. Claude Code's `.mcp.json` is "the only scope that carries into cloud sessions" [35], and MCP **channels** can even push inbound events (webhooks/Telegram/Discord) into a session [35] — a substrate for event-driven loops.

**Recommended:** do both, in this order — start with the file bus (it works today), add an MCP layer for the *control plane* (orchestrator ↔ desktop) while keeping files for the *data plane* (proposals → the PWA). Generalised envelope:

```json
{
  "type": "grocery",                       // your existing typed contract
  "id": "evt_2026-06-16T22:14_a1b2",       // NEW: idempotency key (dedupe across retries)
  "source": "master-orchestrator",         // NEW: provenance (you already tag source:"coach")
  "requires": ["recipes:evt_..."],         // NEW: dependency (formalises additions→recipes→mealplan order)
  "ttl": "2026-06-20",                      // NEW: expiry (don't apply stale proposals)
  "items": [ /* ... existing shape ... */ ]
}
```
The `requires` field formalises what your ingest order already encodes implicitly (mealplan depends on recipes) [`index.html:592`]; the `id` makes at-least-once delivery *safe* even if a retry double-delivers; `ttl` prevents a stale overnight plan from applying days later.

## 15. The single-writer rule for your data file (§11.3 made concrete)

`dashboard-data.json` has exactly **one writer**. Today that's the PWA's ingest path. Keep it that way:

- Tier 1/3 workers **never write `dashboard-data.json` directly.** They emit *proposals* (typed events) to the bus.
- The **PWA's `ingestCoachFiles` loop remains the sole commit path** — it already merges idempotently and tags provenance [`index.html:584`].
- For changes that *must* be applied outside the app (e.g., a backfill), designate **one** Claude Code worker holding a write lease, never two in parallel.

This single rule prevents the largest empirically-documented multi-agent failure class (inter-agent misalignment / conflicting writes, 36.9% of failures [11]) and aligns with both Anthropic's "coding is less parallelizable / needs shared context" caution [7] and Cognition's single-writer finding [10].

## 16. Concrete Claude Code configuration for the worker tier

### 16.1 Specialised sub-agents (`.claude/agents/*.md`)

Define read-only specialists with restricted tools and a cheap model (Haiku for scanning, Sonnet for synthesis) — each "runs in its own context window with a custom system prompt, specific tool access, and independent permissions" [23]:

```markdown
---
name: deal-hunter
description: Read-only researcher. Finds and verifies current grocery deals for target ingredients. Use for the nightly deal sweep.
tools: Read, Grep, Glob, WebSearch, WebFetch
model: haiku
---
You are a deal-hunting researcher. Search for current, unexpired deals on the
target ingredients. Verify each price and expiry. Return ONLY a distilled
coach-deals.json proposal (store, item, price, note, expires) — never write app state.
```

Tier appropriately: scanning/search → **Haiku 4.5** ($1/$5); synthesis/planning → **Sonnet 4.6** ($3/$15); only the hardest reasoning → **Opus 4.8** ($5/$25) [19]. The orchestrator itself should be **Opus** (lead) with **Sonnet/Haiku** workers — the exact split Anthropic measured at **+90.2%** over single-agent Opus [7].

### 16.2 Hooks for deterministic control (`settings.json`)

Hooks are "deterministic shell/HTTP/MCP/prompt/agent callbacks at lifecycle events" [26] — they are how you put *non-stochastic* guardrails around a *stochastic* loop (§11.4). Lifecycle events include `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, `SubagentStop`, `PreCompact`, `UserPromptSubmit` and more [26]. Examples for your system:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [{ "type": "command",
          "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard-single-writer.sh" }] }
    ],
    "PostToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [{ "type": "command",
          "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/validate-schema.sh" }] }
    ],
    "SessionStart": [
      { "hooks": [{ "type": "command",
          "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/load-plan-from-memory.sh" }] }
    ],
    "PreCompact": [
      { "hooks": [{ "type": "command",
          "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/checkpoint-progress.sh" }] }
    ]
  }
}
```
- `PreToolUse` on `Write|Edit` → enforce the single-writer lease (deny if another worker holds it). A `PreToolUse` hook can return `permissionDecision: "allow|deny|ask"` and even rewrite the call via `updatedInput` [26].
- `PostToolUse` on `Write|Edit` → validate the JSON against your schema before it propagates (catch the 21.3% "verification failure" class [11]).
- `SessionStart` → inject the current plan from durable memory as `additionalContext` (its stdout becomes Claude's context) [26], realising §4.3.
- `PreCompact` → write a checkpoint *before* the transcript is summarised away (§4.1 + §11).

### 16.3 Permissions and budget stops

Run workers in `plan` mode for read-only analysis, `acceptEdits` for trusted write workers, `dontAsk` for locked-down CI sweeps [24]. Permission rules **merge across scopes with `deny` winning** [25]:
```json
{ "permissions": {
    "allow": ["Bash(git diff *)", "Read(./coach-templates/*)", "WebSearch"],
    "deny":  ["Bash(curl *)", "Read(./.env)", "Bash(rm *)"] } }
```
Track `total_cost_usd` from each worker's JSON output [13] and trip the orchestrator's budget stop (§3, §9.3) when the nightly cap is hit.

## 17. End-to-end walk-through: the nightly "plan + provision" loop

Putting all parts together, here is one full cycle of the target system:

1. **Schedule fires** (Tier 1, via routine/cron [33]). Orchestrator (Opus) loads its standing goal ("keep the pantry stocked and a 7-day plan that hits my macros from what's on sale").
2. **Plan to memory** (§4.3). Orchestrator writes the plan + success predicate ("7 days planned, each ±10 g protein, total grocery spend ≤ $X") + tonight's token budget to durable memory [21].
3. **Decompose + effort-scale** (§13.1). It spawns, *in parallel* (§2): a **deal-hunter** (Haiku) per store, a **diary-analyst** (Sonnet) to compute the week's macro gaps, a **pantry-reconciler** (Sonnet) to compute shortfalls. Each is a **read-only** Claude Code worker with its own context window, returning a **1–2K-token summary** [15].
4. **Synthesise** (§1.5 #4). Orchestrator merges summaries → a draft meal plan + grocery list, expressed as typed proposals (`coach-mealplan.json`, `coach-grocery.json`, `coach-deals.json`) with idempotency keys (§14).
5. **Verify** (evaluator–optimizer, §1.5 #5 + §10). A **critic** worker scores the plan against the success predicate (rule-based grader: macros, budget, expiry). If it fails, loop back to step 4 (bounded by max iterations, §3). Outcome-based, not path-based [7].
6. **Checkpoint to the bus.** Verified proposals are written to the Drive folder (or pushed via MCP). At-least-once + idempotent + provenance-tagged (§14).
7. **Human checkpoint** (§7). For anything destructive or high-value, the **desktop sub-orchestrator** surfaces the proposal for your one-tap approval; additive proposals can flow through automatically.
8. **Commit** (single writer, §15). On next app open, the PWA's `ingestCoachFiles` drains the folder, idempotently merges, and deletes — *leaving any file that errors for retry* [`index.html:584`]. The app is the actuator; the data file is the single source of truth.
9. **Observe + account** (§8–9). Every step emitted OTel spans to self-hosted Langfuse [27][28] with token/cost/tool telemetry; the orchestrator summed `total_cost_usd` and stopped if the cap was hit.
10. **Stop** (§3). Loop terminates on the success predicate being met (verified, step 5), or the iteration/budget/wall-clock ceiling.

Every numbered step traces to a principle in Parts I–III. That traceability *is* loop engineering.

---

# PART V — A PHASED BUILD PLAN

Build in increasing complexity, per the simplicity principle (§1.4). Do not skip to Phase 3.

| Phase | Goal | What you build | Patterns used | Exit criterion |
|------:|------|----------------|---------------|----------------|
| **0** | Instrument what exists | OTel/Langfuse tracing around the current Claude.ai → Drive → PWA flow; add idempotency keys + provenance to `coach-*.json` (§14) | — | You can see token cost + every ingest in a trace |
| **1** | One self-hosted worker loop | A single headless `claude -p` worker (Agent SDK) that does the nightly **deal sweep**, writes `coach-deals.json`; budget + stop conditions (§3); `total_cost_usd` accounting (§9.3) | Autonomous agent (§1.6) | Nightly deals appear, under a fixed $ cap, fully traced |
| **2** | Orchestrator + read-only fan-out | Tier-1 orchestrator (Opus) spawning parallel **read-only** workers (Haiku/Sonnet) for deals + diary + pantry; plan-to-memory (§4.3); synthesis | Orchestrator–workers (§1.5#4) + parallelization (§1.5#3) | A verified weekly plan generated end-to-end overnight |
| **3** | Verify loop + evals | Evaluator–optimizer critic (§1.5#5); rule-based + LLM-judge eval set from 20–50 real failures (§10); human-checkpoint via desktop tier (§7) | Evaluator–optimizer (§1.5#5) | Plans pass the success predicate ≥ 95% before they reach you |
| **4** | Desktop sub-orchestrators + MCP control plane | Claude Desktop as MCP host routing your requests; orchestrator exposed as MCP server/connector (§13.2, §14); single-writer leases enforced by hooks (§16.2) | Routing (§1.5#2) + single-writer (§15) | You drive the whole system by talking to Claude Desktop |
| **5** | Harden | Rainbow deploys (§11.3), resumable sessions (§11.2), full guardrail/permission matrix (§7, §16.3), cost dashboards | — | Survives a crash mid-run and a version upgrade without data loss |

---

## Appendix A — Quick-reference design rules

1. **Simplicity first** — don't build a loop if a single call + retrieval suffices [1].
2. **Quality is bought with tokens** — every loop is a structured way to spend tokens; budget accordingly (~4× single-agent, ~15× multi-agent vs. chat) [7].
3. **Four independent stop conditions** — goal, iterations, budget, wall-clock/no-progress [1][14].
4. **Context is a curated working set, not a bucket** — fight context rot with compaction, editing, memory, JIT retrieval, sub-agent isolation [15][16][20][21].
5. **Plan to durable memory before you start** — the transcript will be compacted away [7][20][21].
6. **Single writer to durable state** — read-only fan-out, single-threaded writes [10][15].
7. **Idempotent, at-least-once, retry-on-error** — exactly what your `ingestCoachFiles` already does; keep it [§12].
8. **Evaluate outcomes, not paths; start with 20–50 real failures** [7][31].
9. **Trace everything (privacy-preserving), tier your models, cache your prefixes** [7][19][27][30].
10. **Deterministic guardrails around stochastic loops** — hooks, permissions, validators [11][24][26].

## Appendix B — Cost cheat-sheet (per MTok, 2026-06-16) [19]

- **Opus 4.8** $5 / $25 (cache read $0.50) · **Sonnet 4.6** $3 / $15 (cache read $0.30) · **Haiku 4.5** $1 / $5 (cache read $0.10).
- Cache: write 1.25× (5m) / 2× (1h); **read 0.1×**. Batch: **−50%**. 1M context: standard-priced. Tokenizer (4.7+): up to **+35% tokens**.
- Multi-agent ≈ **15×** chat tokens; single agent ≈ **4×** [7]. Lead-Opus + worker-Sonnet ≈ **+90.2%** vs single Opus [7].

## Appendix C — References (Bibliography)

1. Anthropic, *Building Effective Agents* (Dec 2024). https://www.anthropic.com/research/building-effective-agents (also /engineering/building-effective-agents). Mirror/commentary: https://simonwillison.net/2024/Dec/20/building-effective-agents/
2. Anthropic, *Building agents with the Claude Agent SDK*. https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk (mirror https://claude.com/blog/building-agents-with-the-claude-agent-sdk)
3. Anthropic Cookbook — agent pattern implementations. https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents
4. Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR 2023). https://arxiv.org/abs/2210.03629 · https://react-lm.github.io/
5. Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning* (2023). https://arxiv.org/abs/2303.11366
6. Wang et al., *Self-Consistency Improves Chain of Thought Reasoning* (2022). https://arxiv.org/abs/2203.11171
7. Anthropic, *How we built our multi-agent research system* (Jun 2025). https://www.anthropic.com/engineering/built-multi-agent-research-system (also /engineering/multi-agent-research-system)
8. Secondary analyses of [7]: https://simonwillison.net/2025/Jun/14/multi-agent-research-system/ · https://www.zenml.io/llmops-database/building-a-multi-agent-research-system-for-complex-information-tasks · https://blog.bytebytego.com/p/how-anthropic-built-a-multi-agent
9. Cognition (Walden Yan), *Don't Build Multi-Agents* (Jun 2025). https://cognition.ai/blog/dont-build-multi-agents
10. Cognition, *Multi-Agents: What's Actually Working* (2026). https://cognition.ai/blog/multi-agents-working
11. Cemri et al. (UC Berkeley), *Why Do Multi-Agent LLM Systems Fail?* (MAST). https://arxiv.org/abs/2503.13657
12. Benchmark synthesis: https://arxiv.org/abs/2506.17208 (SWE-bench leaderboards) · MAS benchmark series https://christophermeiklejohn.com/ai/agents/mas-series/2026/04/30/mas-series-07-benchmarks.html
13. Claude Code — Headless mode / CLI. https://code.claude.com/docs/en/headless · Agent SDK overview https://code.claude.com/docs/en/agent-sdk/overview
14. Claude API — Task Budgets, rate limits, retries (Anthropic SDK behaviour). https://platform.claude.com/docs/en/about-claude/pricing and SDK docs.
15. Anthropic, *Effective context engineering for AI agents* (2025). https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents · commentary https://the-decoder.com/anthropic-claims-context-engineering-beats-prompt-engineering-when-managing-ai-agents/
16. Anthropic docs, *Context windows* (context rot, context awareness, window sizes). https://platform.claude.com/docs/en/build-with-claude/context-windows
17. Chroma Research, *Context Rot* (Jul 2025). https://www.trychroma.com/research/context-rot · https://github.com/chroma-core/context-rot
18. Anthropic docs — 1M context standard pricing note. https://platform.claude.com/docs/en/build-with-claude/context-windows
19. Anthropic, *Pricing*. https://platform.claude.com/docs/en/about-claude/pricing
20. Anthropic docs, *Compaction*. https://platform.claude.com/docs/en/build-with-claude/compaction
21. Anthropic docs, *Memory tool*. https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
22. Anthropic, *Effective harnesses for long-running agents*. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents · ref impl https://github.com/anthropics/cwc-long-running-agents
23. Claude Code — Subagents. https://code.claude.com/docs/en/sub-agents
24. Claude Code — Permission modes. https://code.claude.com/docs/en/permission-modes
25. Claude Code — Settings. https://code.claude.com/docs/en/settings
26. Claude Code — Hooks. https://code.claude.com/docs/en/hooks
27. OpenTelemetry GenAI semantic conventions. https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/ · https://github.com/open-telemetry/semantic-conventions
28. Langfuse (self-hosted, OTel-based observability). https://langfuse.com/faq/all/langsmith-alternative
29. LangSmith observability. https://www.langchain.com/langsmith/observability
30. Anthropic — prompt caching cost/latency (1-hour TTL announcement). https://x.com/AnthropicAI/status/1925633128174899453 · docs https://platform.claude.com/docs/en/build-with-claude/prompt-caching
31. Anthropic, *Demystifying evals for AI agents* (Jan 2026). https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents · summary https://verifywise.ai/ai-governance-library/agentic-evaluation/agent-anthropic-demystifying-evals-2026
32. Claude Agent SDK overview. https://code.claude.com/docs/en/agent-sdk/overview
33. Claude Code — Routines/`/schedule`, background agents, agent teams, channels. https://code.claude.com/docs/en/routines · https://code.claude.com/docs/en/agent-view · https://code.claude.com/docs/en/agent-teams · https://code.claude.com/docs/en/channels
34. Anthropic — Desktop Extensions (`.mcpb`) & Connectors. https://www.anthropic.com/engineering/desktop-extensions · https://support.claude.com/en/articles/11503834-build-custom-connectors-via-remote-mcp-servers
35. Claude Code — MCP. https://code.claude.com/docs/en/mcp · Claude Code on the web https://code.claude.com/docs/en/claude-code-on-the-web · Managed Agents https://platform.claude.com/docs/en/managed-agents/overview
36. OpenAI, *A Practical Guide to Building Agents* (manager vs. decentralized patterns; "maximize a single agent first"). https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
37. METR, *Measuring AI Ability to Complete Long Tasks* (50%-time-horizon, doubling ~7 months). https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/ · https://arxiv.org/abs/2503.14499

## Appendix D — Claims Confidence Ledger (read before quoting numbers)

The research pass hit a transient HTTP 403 on automated fetches of several `anthropic.com` engineering posts. Where that happened, *figures* were corroborated across ≥3 independent sources, but *verbatim wording* and a few exact numerals are secondary-sourced. Confidence levels:

| Claim | Confidence | Note |
|-------|-----------|------|
| Loop = gather context → take action → verify → repeat [2] | **High** | Verbatim, multiply corroborated |
| Workflow vs. agent definitions; pattern catalogue [1] | **High** | Verbatim from primary |
| ReAct +34% (ALFWorld) / +10% (WebShop) [4] | **High** | Matches paper abstract |
| Multi-agent **+90.2%** vs single-agent Opus [7] | **High** | Identical across sources |
| **4× / 15×** token multipliers; **80%** variance from tokens [7] | **High** (figures) / Med (verbatim) | Numbers solid; exact punctuation unconfirmed (403) |
| "up to 90%" research-time reduction; 3–5 subagents / 3+ tools [7] | **Med-High** | From the post; corroborated in summaries |
| MAST 41.8% / 36.9% / 21.3% failure split; 7 frameworks [11] | **Med-High** | Trace count varies 200+ vs 1,600+ across summaries |
| Current pricing table (Opus 4.8 $5/$25 etc.) [19] | **High** | Fetched from primary pricing page 2026-06-16 |
| 1M context standard-priced (no surcharge) [18][19] | **High** (current) | The *historical* Sonnet-4 premium figure is secondary |
| Caching 1.25×/2×/0.1×; −90% cost / −85% latency [19][30] | **High** | Multipliers primary; latency from Anthropic announcement |
| Compaction trigger 150K (min 50K) [20] | **High** | Primary docs |
| Context rot 20–50% drop 10k→100k tokens [17] | **Med** (magnitude) / High (direction) | Band from secondary summaries of Chroma |
| Reflexion ~+20 pts HotPotQA [5] | **Med** | Secondary summaries; confirm against arXiv tables |
| Eval: $0.06 / ~15s per LLM-judge; 20–50 failures [31] | **Med-High** | From secondary summary of the Anthropic post (403) |
| Auto-compact internal formula (13K buffer etc.) | **Low** | Community-reverse-engineered, not official |
| Hard per-step latency benchmarks | **Gap** | Not published in primary sources; measure your own (§9.4) |
| Model lineup names (Opus 4.8, Sonnet 4.6, Fable/Mythos 5) | **Env-dated** | Reflects 2026-06 docs; re-confirm if targeting another date |

*If you need a number for an external/high-stakes artefact, pull the cited primary page in a browser to lock exact wording before publishing.*

---

*End of report.*
