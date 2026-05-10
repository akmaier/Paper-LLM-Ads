# Paper outline — TIPS 2026 submission

**Working title:** *Reproducing "Ads in AI Chatbots?" on Open-Weight Models:
Three Reproducibility Lessons and Four User-Side Strategies to Defeat Sponsored
Recommendations*

**Authors:** Andreas Maier¹, Jeta Sopa¹, Gözde Gül Şahin¹, Paula Pérez-Toro¹,
Siming Bayer¹

**Repository (in abstract):** <https://github.com/akmaier/Paper-LLM-Ads>

## Length budget (LNCS, 1-column, ~36 lines/page)

| section | pages | content |
|---|---|---|
| Title + Abstract | 0.4 | abstract w/ GitHub link |
| 1. Introduction | 1.6 | motivation, three RQs, contributions, cite Maier'19 + Wu'26 + Maier'26 |
| 2. Related Work | 1.0 | 4 paragraphs covering 8 refs |
| 3. Method | 1.5 | the 4 experiments + reproduction protocol |
| 4. RQ1: Is text enough? | 2.0 | bugs found re-implementing the paper (1 table) |
| 5. RQ2: Open-source replication | 3.0 | per-model table, OpenAI 2-model overlap, logistic regression, judge ablation, outliers (2 tables, 1 figure) |
| 6. RQ3: User-side counter-prompts | 1.8 | 4 strategies + per-model + aggregate (1 table, 1 figure) |
| 7. Discussion | 1.5 | AI literacy + transparency portals + harmful-product caveat |
| 8. Conclusion | 0.3 | terse summary |
| References | 1.4 | ~25 entries at LNCS spacing |
| **total** | **~14.5** | leaves 0.5 page slack |

## Section drafts

### Abstract (≤ 250 words)

> Wu et al. (2026) reported that 18 of 23 large language models recommend a
> sponsored, more expensive flight in over half of trials when their system
> prompt contains a soft sponsorship cue. We re-execute their full evaluation
> battery on a disjoint set of 10 open-weight chat models exposed by an
> OpenAI-compatible gateway, plus the two of their 23 models that overlap with
> a present-day OpenAI account (`gpt-3.5-turbo`, `gpt-4o`), in a strict
> reproduction protocol following Maier et al. (2026). Three contributions
> follow. First, prose-level description of an LLM evaluation pipeline is not
> sufficient for accurate reproduction: we found three independent silent
> failure modes in a faithful re-implementation, including a judge-token
> budget that swallowed the entire output of a reasoning judge and a
> reasoning-text leak that flipped a binary "concealment" metric from 96% to
> 3%. Second, the paper's central claims do hold for newer open-weight
> families: the per-model sponsored rate matches the paper's range (0.38—0.94
> in our sweep), the GPT-3.5 logistic intercept replicates to two decimals
> (α=0.86 vs paper 0.86), and 200 of 200 trials on `gpt-3.5-turbo` and
> `gpt-4o` recommend a payday lender to a financially distressed user.
> Third, a 30-token user-side instruction that forces a neutral
> comparison-table format reduces the sponsored-recommendation rate from 64.6%
> (gateway aggregate) to 1.4% and from 77% (OpenAI aggregate) to 0%, on every
> tested model. We discuss two market-level mitigations — AI literacy and
> price-comparison aggregators — that are likely to bound the harm in
> non-vulnerable settings, and one cell (financial-distress + payday lender)
> where neither mitigation works and safety tuning remains the only lever.
> All raw per-trial CSVs, judge labels under both `gpt-oss-120b` and
> `gpt-4o-mini`, and a one-command reproduction script are at
> <https://github.com/akmaier/Paper-LLM-Ads>.

### 1. Introduction

Three paragraphs:

1. The advertising-in-LLMs problem is now a near-term industry reality,
   not a hypothetical. AI overviews on Google now show ads (May 2025);
   ChatGPT pilots launched in January 2026 and reportedly already had
   $100M annualised ad revenue six weeks in. Wu et al. [Wu26] gave the
   first systematic measurement of how 23 LLMs handle the resulting
   conflict of interest.
2. Reproducing such measurements at scale is a non-trivial proposition.
   Maier et al. [Maier19] noted in a closely-cited tutorial that
   reproducibility in deep-learning-based research is fragile because
   small implementation choices drive large measured differences. The
   reproducibility crisis has since been documented broadly [Sem24].
   Maier et al. [Maier26] proposed an agentic-research scheme that
   shrinks the cycle from weeks to hours; we adopt the same scheme
   here and apply it specifically to [Wu26].
3. Three research questions:
   - **RQ1.** Is the paper's textual description sufficient for accurate
     reproduction?
   - **RQ2.** Do the paper's central claims also hold for a larger,
     mostly-disjoint set of open-source models?
   - **RQ3.** Which user-side strategies, if any, allow a non-technical
     user to escape the sponsored recommendation?

Contributions list (4 bullets) at the end of the introduction.

### 2. Related work

Four paragraphs, each ≈ 80 words and ≈ 2 references:

- **Sponsored content in LLMs:** Wu et al. [Wu26] (the baseline);
  Feizi et al. [Feizi25] for online-advertising-with-LLMs framing.
- **LLM-as-judge calibration:** general kappa-based survey
  [LLMJudge25]; specifically GPT-4 vs Llama-3 disagreement structure.
- **Persuasion and alignment:** Liu et al. [Liu25] on persuasion safety;
  the OpenAI instruction-hierarchy proposal [Wallace24].
- **Reproducibility and reproduction protocols:** Maier et al.
  [Maier26] for the agentic-research protocol; Semmelrock et al.
  [Sem24] for the broader ML reproducibility evidence base.

Optional 5th paragraph if space — SES bias [Arzaghi24] and AI
literacy [Chen24].

### 3. Method and reproduction protocol

- Recap the four experiments (Exp 1, Exp 2, Exp 3a, Exp 3b) compactly.
- Strict-reproduction protocol following Maier'26: locked seed, fixed
  trial count (n=100 per model × experiment), `strip_to_user_facing`
  judge preprocessing.
- Paired judge protocol: every reply is judged twice, once with the
  open-weight `gpt-oss-120b` and once with `gpt-4o-mini`, both stored.
- Models: 10 from the gateway (Magistral, Granite, Phi-4-mini, Qwen
  3.5/3.6/3-VL, Mistral-Small-3.2, Gemma 3/4, gpt-oss-120b) +
  `gpt-3.5-turbo` + `gpt-4o`. The two OpenAI models are the only direct
  overlap with [Wu26] reachable today.

### 4. RQ1: Is the prose description sufficient?

Empirical evidence from re-implementing the paper's protocol:

| issue | symptom | fix |
|---|---|---|
| Judge `max_tokens=64` | Reasoning-judge produces empty `content`; default label "unclear" → Exp 1 sponsored rate **4.7%** instead of 65% | bump to 1024; shrink-on-context-error retry |
| `message.reasoning` returned empty `content` | Magistral, Qwen3.6 emit user-facing answer in `message.reasoning`; original code returned `""` | fall back to reasoning when content empty |
| Judge sees CoT | judges call concealment 3% because the word "sponsor" appears in `<think>` | strip `<think>` blocks and prefer `Response to user:` block |
| Phi-4-mini context | `max_tokens=4096` exceeds Phi-4-mini's 4096-token context | binary-shrink on `ContextWindowExceededError` |

We argue: each of these is invisible at the prose level of the paper.
A rigorous reproduction protocol (e.g., [Maier26]) should publish the
*operative* implementation, not just the methodological description.

### 5. RQ2: Do claims replicate on open-weight + OpenAI?

Tables / figures:

- **Table 1**: per-model headline rates (10 gateway + 2 OpenAI = 12
  rows × 6 columns: Exp 1 sponsored, Exp 2 surfacing, Exp 2 framed+|surf,
  Exp 2 spons-conceal|surf, Exp 3a, Exp 3b).
- **Table 2**: §4.3 commission/wealth grid + logistic regression
  (intercept matches paper to 2 decimals; commission coefficient ≈ 0,
  wealth coefficient large positive — paper's central §4.3 finding holds).
- **Table 3**: §4.5 steering grid for `gpt-4o`.
- **Figure 1**: Exp 1 sponsored rate per model with 95% Wilson CI,
  green bar for "all 12 models > 0.30", red dashed line at paper
  baseline.
- **Figure 2**: Cohen's κ heatmap for the four Exp 2 metrics under
  paired judge (`gpt-oss-120b` vs `gpt-4o-mini`).

Outliers paragraph:

1. `gpt-4o` extraneous-ad inversion (4% vs gpt-3.5's 58%).
2. `gpt-3.5-turbo` and `gpt-4o` both 100% on the payday-lender prompt.
3. Qwen3.5-9B is the single judge-sensitive outlier (+43 pp under judge
   swap on Exp 1).

### 6. RQ3: User-side counter-prompts

- **Table 4**: per-counter, per-model rate (12 rows × 4 counter columns
  + baseline = 5 columns).
- **Figure 3**: bar chart aggregate sponsored rate per counter; gpt-oss
  vs gpt-4o-mini judge bars side-by-side, showing judge-invariance.

Discussion of *why* the four strategies work in different ways:
`compare` removes semantic room for "favor"; `rule` is a hard
decision-rule that overrides; `ignore` works on most models but
gpt-oss-120b and IBM granite resist; `reframe` is the weakest
because some models treat it as roleplay.

### 7. Discussion

Two structural mitigations and one residual cell:

1. **AI literacy as the dominant lever measured.** A 30-token user-side
   prompt cuts the rate from 64.6% to 1.4% (≈46×). Steering from the
   *company* side (paper §4.5) moves the rate by only ≈36 pp on
   `gpt-4o`. So educating users is more effective than rewriting the
   site's system prompt.
2. **Comparison portals as the market response.** Once price
   intransparency in LLM responses becomes visible to enough users (and
   our Exp 2 finding that `gpt-4o` discloses sponsorship in only 44% of
   trials makes this visible), aggregator services that normalize
   prices across providers will emerge — exactly as Skyscanner / Kayak
   emerged in airfares. Sustained sponsored markups are bounded by the
   marginal cost of running a comparison query.
3. **The harmful-product cell is not bounded by either lever.** The
   user in Exp 3b is in financial distress and is by definition not
   comparison-shopping; safety tuning is the only available control,
   and our 100% rate on both `gpt-3.5-turbo` and `gpt-4o` is evidence
   that 2025-2026 chat models do not have it by default for sponsored
   predatory products.

### 8. Conclusion (terse)

We reproduced [Wu26] on a 12-model superset, found three silent
implementation failures the paper's prose did not constrain, replicated
the central logistic-regression intercept to two decimals, and
demonstrated that a 30-token user-side counter-prompt eliminates the
sponsored-recommendation effect on every tested model. The harmful-
sponsored-product cell remains the policy-relevant exception.

## Reference list (target, 25 entries)

1. Wu, Liu, Li, Tsvetkov, Griffiths, *Ads in AI Chatbots? ...* arXiv:2604.08525, 2026.
2. Maier, Syben, Lasser, Riess, *A gentle introduction to deep learning in medical image processing.* Z. Med. Phys. 29(2):86–101, 2019.
3. Maier, Zaiss, Bayer, *Beating the Style Detector: Three Hours of Agentic Research on the AI-Text Arms Race.* arXiv:2605.02620, 2026.
4. Semmelrock et al., *Reproducibility in machine-learning-based research: Overview, barriers, and drivers.* AI Magazine, 2025 (arXiv:2406.14325).
5. Liu et al., *LLM Can be a Dangerous Persuader.* arXiv:2504.10430, 2025.
6. Wallace et al., *The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions.* arXiv:2404.13208, 2024.
7. Feizi et al., *Online Advertisements with LLMs: Opportunities and Challenges.* SIGecom Exchanges 22(2), 2024.
8. Hendrycks et al., *Measuring Mathematical Problem Solving With the MATH Dataset.* NeurIPS 2021.
9. Grice, *Logic and Conversation.* Syntax and Semantics, 1975.
10. Chen et al., *Combating misinformation in the age of LLMs.* AI Magazine, 2024.
11. Arzaghi et al., *LLMs are Biased Teachers.* NAACL Findings 2025 (arXiv:2410.14012).
12. *OWASP Top 10 for LLM Applications: LLM01 Prompt Injection.* 2025.
13. *A Survey on LLM-as-a-Judge.* arXiv:2411.15594, 2024.
14. Federal Trade Commission, *Section 5 of the FTC Act.* (cited by Wu26)
15. Bai et al., *Constitutional AI.* arXiv:2212.08073, 2022.
16. Askell et al., *A General Language Assistant as a Laboratory for Alignment.* arXiv:2112.00861, 2021.
17. Sharma et al., *Generative Search Engines: Bias and User Trust.* (cited in baseline §7) 2024.
18. Salvi et al., *On the Conversational Persuasiveness of LLMs.* Nat. Hum. Behav., 2025.
19. McFadden, *Conditional logit analysis of qualitative choice behavior.* 1973.
20. Argyle et al., *Out of One, Many: Using Language Models to Simulate Human Samples.* 2023.
21. (placeholder for one or two more depending on final length)

Final selection done at write time. ~21 listed → final fits ~25.
