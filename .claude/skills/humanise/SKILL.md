---
name: humanise
description: Write or revise prose so it reads like a careful human wrote it. Removes known AI-writing tells (corrective "not X but Y" framing, importance-flagging, stock vocabulary, uniform sentences, mannered metaphors, list-and-bold formatting) while keeping every fact, number, citation and caveat. Use for any paper section, report, README or message in this project, and always for Phase IV of the CNET paper.
---

# Humanise

The goal is prose a careful student researcher would write: specific, direct, varied, honest. The full catalogue of tells, with sources and measured rates, is in `references/signs.md`. Read it the first time this skill is used in a session.

## Rules that never bend

1. **Substance is fixed.** Never change a number, a citation, a claim's strength, or a caveat to make text "sound" better. "Descriptive, not causal", "within the pre-declared margin", "22 of 70 runs preserved": these stay word for word in meaning.
2. **No invented specifics.** Human-sounding detail must be true. Don't add anecdotes, sources, or "we noticed" moments that didn't happen.
3. **Fit the register.**
   - *Paper:* first person plural ("we") is normal. No contractions, exclamation marks, emoji, or chatty qualifiers ("pretty", "sort of").
   - *Chat and messages:* contractions, "you", the odd aside and plain enthusiasm are fine.
4. **This is about clarity, not about beating detectors.** If the user's course has an AI-use disclosure rule, they follow it. Don't advise hiding AI assistance.

## Procedure

### 1. Draft from the evidence, not from a template

- Start each paragraph with its point, then the number that backs it.
- Keep odd, specific details ("all 1,468 duplicated DoS rows were detected by every seed"). Specificity is the strongest human signal; generic summary is the strongest AI signal.
- One idea per paragraph. Vary paragraph length.

### 2. Sentence craft (Gopen & Swan, Orwell)

- **Placement:** subject and verb early. Context and old information go at the start (topic position); the new point goes at the end (stress position).
- **Verbs:** put the action in a verb. Write "we compared", not "a comparison was performed". Prefer the active voice. Use is/are/has freely; don't write "serves as" or "represents".
- **Word choice:** pick the short, plain word: use, show, help, start, about, enough.
- **Terms:** repeat the exact technical term. Don't cycle synonyms for the same thing.
- **Sentence length:** vary it on purpose. In every paragraph of four or more sentences, have at least one short sentence (under 10 words) and one long one (over 25).

### 3. Kill-list pass

Search the draft for each item and rewrite every hit. Run `scripts/humanise_check.py` (below) to find them mechanically.

**Corrective framing.** Say what it is, not what it isn't.
- not only… but also; it's not X, it's Y; not just; not simply; not merely
- rather than (simply/merely/relying); instead, it; less like… more like; is more than a… it is

**Importance flags.** Show the consequence instead.
- this matters; why X matters; matters because; matters most; the distinction matters
- it is important/worth noting; note that; crucially; just as important

**Significance puffing.**
- marks/represents a pivotal/significant shift; underscores/highlights the importance
- reflects broader; sets the stage; indelible; testament; enduring legacy
- has shaped discussions; prompted broader debate

**Tacked-on -ing analysis.** End the sentence where the fact ends.
- …, highlighting / underscoring / reflecting / ensuring / contributing to / fostering / showcasing / emphasizing…

**Stock vocabulary.** Use the plain word or nothing.
- delve, underscore(s), showcase, pivotal, crucial, intricate, interplay, tapestry, landscape (abstract), vibrant, robust (unless technical), comprehensive, notably, additionally, furthermore, moreover, enhance, foster, leverage, align with, garner, bolster
- dependable, practical, meaningful, thoughtful, steady, deliberate, measured, multifaceted, seamless, invaluable, groundbreaking, unprecedented, paramount, profound, remarkable(ly), incredibly, absolutely

**Claude-specific (Opus 5.5).**
- single most / perhaps the most / arguably the most / the most powerful; every single
- is genuinely; enormously; can help you; makes it easier; helps you avoid
- what comes next; looking ahead; adds another layer; in practice (as an opener)

**Stock transitions at the start of a sentence.**
- Additionally / Furthermore / Moreover / Notably / Consequently / Ultimately / Together, these / Overall / In summary / In conclusion
- Use none, or and / but / so / also.

**Hedge formulas.**
- "should be treated as … rather than …", "does not by itself establish", "based on available information", "while details are limited"
- Replace these with one precise statement of the limit, in the limitations section.

**Trade-off denial.** without sacrificing/losing/compromising/requiring. State the real cost.

**Vague association.** "associated with", "in connection with" where a direct relation is known. Name the relation.

**Rule of three.** If a list has exactly three items for rhythm rather than truth, change it.

### 4. Punctuation and format

- Use a normal mix of commas, parentheses (humans use more asides), colons and semicolons. The odd unspaced em dash is fine. Zero dashes across a whole document is itself a tell now, so neither overuse nor ban them.
- **Paper:** prose paragraphs; lists only for true enumerations. No bold inside prose. Sentence-case headings unless the template dictates otherwise. Tables only for real tabular data.
- **Chat:** short paragraphs; bullets only when they help.

### 5. Read-back check

Run the checker:
```
python .claude/skills/humanise/scripts/humanise_check.py <file> [--paper]
```
It reports kill-list hits with line numbers, sentence-length mean and SD, em dashes per 1,000 words, sentence-initial transitions, and characters per word.

**Targets for paper prose:**
- 0 kill-list hits (a hit that is a technical term is allowed, with a reason);
- sentence-length SD of at least 8 words;
- average word length of 5.3 characters or less (excluding LaTeX);
- no paragraph whose sentences are all within ±4 words of each other.

Then read the text aloud in your head. Any sentence you wouldn't say to a supervisor across a desk gets rewritten.

### 6. Don't over-correct

These are not tells; leave them alone (Wikipedia "ineffective indicators"):
- correct grammar;
- formal register;
- a single "however";
- correct citations;
- a stray "in order to".

A text scrubbed of every transition and every long word reads machined too.

## Quick before/after (CNET project)

- AI: "This finding underscores the pivotal role of duplicate handling, highlighting that evaluation choices matter."
  Human: "Removing the 3,330 training twins cut MCC from 0.784 to 0.719. The models and their false negatives stayed the same; only the test population changed."
- AI: "R4a-i is not simply a robustness check; rather, it reveals how models depend on extractor definitions."
  Human: "Scored on corrected flows, the original models found 9% of DDoS attacks. Models trained without the TCP flag counts found 96%. We report this as a description, since the corrected extractor changed more than the flag counts."
- AI: "Furthermore, our comprehensive analysis offers valuable insights into the evolving landscape of NIDS evaluation."
  Human: (delete the sentence, or say which result supports which claim)
