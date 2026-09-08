# Writing Clearly and Concisely (Academic)

Write academic prose that is precise and readable without sacrificing the conventions scholarly readers expect: calibrated claims, engagement with sources, and a level of formality appropriate to the discipline. This skill adapts Strunk's *The Elements of Style* for academic contexts and flags AI writing patterns that read as generic or unscholarly.

Academic writing has different constraints than commit messages or UI copy: some passive voice is conventional (especially in methods sections), some hedging is epistemically required rather than a stylistic weakness, and "concrete language" often means precise technical terminology rather than plain words. Apply Strunk's spirit—cut what doesn't earn its place—without flattening the argument.

## When to Use

- Drafting or revising a paper, thesis, or dissertation chapter
- Writing a literature review or synthesizing sources
- Preparing an abstract, grant proposal, or conference submission
- Responding to peer review or revising per reviewer comments
- Editing a colleague's or student's manuscript for clarity

**Trigger phrases:** "Tighten this paragraph for my paper," "Draft an abstract," "Is this hedge appropriate?," "Make my lit review flow better," "Respond to this reviewer comment."

## Core Adaptations from Strunk

| Strunk's rule                             | Academic adaptation                                                                                                                                                                                                                                           |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Use active voice                          | Prefer active voice for argument and analysis ("This study shows...", not "It is shown by this study..."). Passive voice is acceptable and often conventional for methods/procedure ("Samples were collected...") where the actor is irrelevant to the point. |
| Put statements in positive form           | Applies to sentence construction, not to epistemic claims. Don't state a finding more strongly than the data support just to sound "positive."                                                                                                                |
| Use definite, specific, concrete language | Means precise and technically accurate, not simplified. Keep discipline-specific terminology where it is the correct term; don't substitute a vaguer plain-English word for a specific technical one.                                                         |
| Omit needless words                       | Cut filler and throat-clearing ("It is important to note that," "It should be mentioned that"). Do not cut necessary qualifications, scope conditions, or methodological caveats—these are content, not padding.                                             |
| Keep related words together               | Applies directly; especially important in long, clause-heavy academic sentences.                                                                                                                                                                              |
| Place emphatic words at end of sentence   | Applies directly; useful for landing a claim or contribution.                                                                                                                                                                                                 |

## Hedging: Cut the Filler, Keep the Epistemics

The biggest difference from general prose writing: hedging in academic work often isn't a weakness to be edited out. Distinguish two kinds.

**Empty hedging (cut this):**

- "It is important to note that the results might potentially suggest..."
- "It could perhaps be argued that this may indicate..."

**Calibrated hedging (keep this):**

- "These results suggest, but do not confirm, a causal relationship."
- "Given the small sample size, this finding should be interpreted with caution."
- "We did not observe X in this population; whether it generalizes to others is unclear."

The test: does removing the qualifier change what the sentence claims about the evidence? If yes, keep it. If the qualifier is just verbal padding around a claim that's already appropriately scoped, cut it.

## AI Pattern Detection (Academic Context)

Same underlying patterns as general writing, with academic-specific tells:

- **Puffery about the field or topic**: "a rapidly evolving field," "represents a significant contribution," "the enduring importance of." Let the reader judge significance from the evidence, not from adjectives.
- **False balance / manufactured tension**: "While some scholars argue X, others contend Y, ultimately revealing a complex and multifaceted debate" used as a paragraph-ending non-conclusion. Either take a position the evidence supports or specify precisely what remains unresolved.
- **Overused AI vocabulary**: delve, leverage, multifaceted, foster, realm, underscore, tapestry, landscape (as in "the research landscape"), "shed light on," "pave the way for."
- **Generic transitions standing in for argument**: "It is worth noting that," "Furthermore, it is evident that," "This underscores the fact that." These announce that a point is being made instead of making it.
- **Symmetrical list padding in literature reviews**: summarizing three sources in identical sentence structure ("Smith (2020) found... Jones (2021) found... Lee (2022) found...") without synthesis. A literature review should relate sources to each other, not list them.
- **Overclaiming novelty or impact**: "groundbreaking," "unprecedented," "paradigm-shifting" applied to your own work. Let reviewers and readers decide; state the contribution plainly instead.

## How It Works

1. Draft or receive the passage.
2. Check hedging first: is each qualifier doing epistemic work, or is it filler? Cut the filler, keep the epistemics.
3. Apply active voice where the argument is being made; leave passive voice where it's conventional (methods, procedure descriptions).
4. Scan for AI patterns above, especially false-balance conclusions and list-without-synthesis in literature reviews.
5. Check citation integrity: every claim attributed to a source should accurately reflect what that source says (this skill doesn't verify citations, but flags unsupported or overreaching attributions if apparent from context).
6. Cut needless words; do not cut scope conditions, sample limitations, or methodological caveats.

## Usage Examples

### Example 1: Cutting Empty Hedging, Keeping Real Hedging

**Before:**

> It is important to note that the results might potentially suggest that, in certain contexts, the intervention could possibly have some effect on outcomes, although this may not necessarily be the case for all populations.

**After:**

> The intervention appears to affect outcomes in this sample; whether this extends to other populations is untested.

### Example 2: Literature Review Without Synthesis

**Before:**

> Smith (2020) found that social media use correlates with anxiety. Jones (2021) found that social media use correlates with depression. Lee (2022) found that social media use correlates with sleep disruption.

**After:**

> Social media use has been linked to several overlapping outcomes: anxiety (Smith, 2020), depression (Jones, 2021), and sleep disruption (Lee, 2022). These studies rely on similar self-report measures, which may explain the convergence more than a common underlying mechanism does.

### Example 3: False-Balance Non-Conclusion

**Before:**

> While some scholars argue that the policy was effective, others contend it was not, ultimately revealing a complex and multifaceted debate that merits further study.

**After:**

> The disagreement centers on which outcome measure to trust: employment data support effectiveness; wage data do not. Resolving this requires a dataset that tracks both over the same period.

### Example 4: Passive Voice, Kept vs. Cut

**Keep (methods, actor irrelevant):**

> Samples were centrifuged at 3,000 rpm for 10 minutes.

**Cut (argument, actor matters):**

> Before: "It has been argued by this paper that the model is insufficient." After: "This paper argues the model is insufficient."

## Best Practices

1. **Distinguish filler from epistemics** — cut throat-clearing, keep genuine qualifications about evidence and scope.
2. **Synthesize sources, don't just list them** — relate findings to each other, not only to your argument.
3. **Match voice to convention** — active for argument, passive acceptable for procedure.
4. **State your contribution plainly** — let evidence carry the weight, not adjectives like "groundbreaking" or "significant."
5. **Prefer precise technical terms** over vaguer plain-English substitutes, even though this differs from general-audience advice to simplify.
6. **Resolve, don't gesture at, tension between sources** — if the literature disagrees, say specifically where and why; avoid ending on an unresolved "it's complicated."

## Reference

For general (non-academic) prose rules this skill doesn't override—comma usage, sentence-level mechanics, formatting conventions—the underlying Strunk-based reference files from the original writing-clearly-and-concisely skill still apply. Load them the same way; only the guidance on hedging, passive voice, and AI-pattern detection above supersedes the general-purpose version.

## Attribution

- Adapted from the `writing-clearly-and-concisely` skill by softaworks/agent-toolkit (in turn from @joshuadavidthomas and obra/the-elements-of-style, MIT licensed)
- Writing principles from *The Elements of Style* by William Strunk Jr. (1918)
- Academic hedging and citation-synthesis guidance adapted from general scholarly writing conventions
