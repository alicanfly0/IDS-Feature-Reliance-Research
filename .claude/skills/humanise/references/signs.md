# Signs of AI writing and signs of human writing: full list

This list was compiled on 2026-11-15 from the sources below. Each item says what the tell is, gives the words or patterns to watch, and says what a person would write instead. The sources disagree on a few points, and where they do, both views are given.

## Sources

| Key | Source |
|---|---|
| **W** | Wikipedia, *Wikipedia:Signs of AI writing* (WikiProject AI Cleanup field guide), read 2026-11-15, plus its subpage *…/Style* |
| **G** | Graphite, *AI Tells* (Druck, Paredes and Smith, 16 Sep 2026): 10,000 pre-ChatGPT human articles vs 90,000 AI articles from nine models |
| **G5** | Graphite, *AI Tells: Opus 5.5 Update* (1 Oct 2026). **This covers the model writing these documents (Claude Opus 5.5).** |
| **K** | Kobak et al., "Delving into LLM-assisted writing in biomedical publications through excess vocabulary", *Science Advances* 11(27), 2025: 15M PubMed abstracts |
| **GS** | Gopen and Swan, "The Science of Scientific Writing", *American Scientist*, 1990 |
| **O** | Orwell, "Politics and the English Language" (1946), six rules |

Read it with three caveats (W). Signs are observations, not rules. A single sign proves nothing. Fixing the surface of a sign without fixing the problem underneath (vague content, an unsupported claim) is pointless.

---

## Part A: AI tells to remove

### A1. Content and framing

1. **Puffing up significance and legacy** (W). The writer asserts that a detail "marks a pivotal moment", "reflects broader trends", "underscores its importance", "sets the stage for", or "leaves an indelible mark".
   - *Instead:* state the fact. If it really matters, show why with a number or a consequence.
2. **Saying a thing "shaped discussions" or "prompted broader debate"** (W). *Instead:* name the actual debate and cite it, or cut the sentence.
3. **Over-attributing to sources and coverage** (W). For example: "has been extensively documented across major outlets", "independent coverage", "trade publications".
   - *Instead:* say what the source found, not that it exists.
4. **Over-stressing that a database or record "identifies X as…"** (W). *Instead:* state the fact and cite it.
5. **Superficial "-ing" analysis tacked onto the end of a sentence** (W): "…, highlighting/underscoring/reflecting/ensuring/contributing to/fostering…". *Instead:* end the sentence where the fact ends, or give the analysis its own sentence with evidence.
6. **Vague connection words** (W): "associated with", "in connection with", "connected to", used where a direct relation exists. *Instead:* say the relation: "was CEO of", "taught at", "caused", "correlated with r = 0.4".
7. **Weasel attributions and invented plurality** (W): "experts argue", "observers note", "several studies", "such as" before a list that is actually complete. *Instead:* name the source. Count the sources honestly.
8. **A "Despite its…, X faces challenges" formula, often followed by "Future outlook"** (W). *Instead:* put limitations where they belong and be specific about each one.
9. **Header pairs like "X and Y", such as "Awards and recognition" or "Challenges and Legacy"** (W). *Instead:* use plain, specific headings.
10. **Hedging disclaimers about sources** (W, 2026 pattern): "while specific details are limited", "based on available information", "[claim] should be treated as … rather than …", "does not by itself establish…".
    - *Instead:* make one precise statement of what the evidence does and doesn't show, once, in the right place.
    - Note: in a research paper real limitations must stay. The point is precision, not removal.
11. **Didactic notes**: "It is important to note that…", "It's worth noting", "Note that" (W, G). *Instead:* just say it.
12. **Summaries that restate the paragraph**: "In summary", "In conclusion", "Overall", "Ultimately, this…" (W, G). *Instead:* end on the last new fact. A Conclusion section is fine in a paper, but don't restate what was just said.
13. **Flagging importance** (G, G5): "this matters", "why X matters", "matters because", "matters most", "the distinction matters", "just as important", "absolutely essential". *Instead:* show the consequence and let the reader judge.
14. **Avoiding trade-offs** (G): "without sacrificing/losing/compromising/requiring". *Instead:* state the trade-off honestly; real methods have costs.
15. **Generic regression to the mean** (W): the specific fact becomes a generic, positive description ("inventor of the first train coupling" turns into "a revolutionary titan of industry"). *Instead:* keep the odd, specific detail. Specificity is the strongest human signal.

### A2. Sentence-level patterns

16. **Negative parallelism / corrective framing** (W, G, G5). This is one of the strongest current tells.
    - Patterns: "not only … but also", "it's not X, it's Y", "not just X", "not simply", "rather than (simply/merely/relying)", "instead, it…", "less like X and more like Y", "is more than a _, it's…".
    - Measured rates: Claude writes "less like a _ and more like" 82–105× the human rate (G); Opus 5.5 writes "is more than a _ it" 98×, "rather than simply" 32× (G5); "the _ is not simply" 576× (G).
    - *Instead:* say what the thing is. Use a contrast only when the reader really holds the wrong view, and then name that view.
17. **Rule of three** (W). Triplets of adjectives or phrases ("clear, robust, and scalable") used to look comprehensive. *Instead:* give the one or two that are true and specific, or vary the count.
18. **Avoiding is/are/has** (W, K): "serves as", "stands as", "functions as", "represents", "boasts", "features", "offers". *Instead:* write "is", "are", "has". The basic copula is a human sign.
19. **"Refers to" in definitions** (W): "X refers to…" when the subject itself is meant. *Instead:* "X is…".
20. **Uniform sentence length** (G). AI sentence lengths vary much less than human ones; GPT-6-era output also clusters at 8–20 words (W). *Instead:* mix short sentences with long ones. A three-word sentence is allowed.
21. **Mannered prose** (G, G5): metaphor and flourish in place of a direct statement ("a dial worth turning" for "a parameter worth varying"). Opus 5.5 still scores about 1.6× the human rate. *Instead:* use the literal statement. Use a figure of speech only if it carries meaning a literal phrase can't (O rule 1).
22. **Elegant variation** (W): cycling synonyms to avoid repeating a word ("the model… the classifier… the system… the framework" for one thing). *Instead:* repeat the precise term. In technical writing a consistent term is correct.
23. **Formulaic transitions at sentence start** (W, G, K): "Additionally,", "Furthermore,", "Moreover,", "Notably,", "Consequently,", "Ultimately, this", "Together, these", "Looking ahead,", "What comes next", "Adds another layer", "In practice,", "Another dimension". *Instead:* use no transition, or "and", "but", "so", "also" mid-sentence, or let the logic carry the link.

### A3. Vocabulary (overused words, with era)

24. **2023–mid 2024** (W): additionally, boasts, bolstered, crucial, delve, emphasizing, enduring, garner, intricate/intricacies, interplay, key (adj.), landscape (abstract), meticulous(ly), pivotal, underscore, tapestry, testament, valuable, vibrant.
25. **Mid 2024–mid 2025** (W): align with, bolstered, crucial, emphasizing, enhance, enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant.
26. **Mid 2025–mid 2026** (W): emphasizing, enhance, highlighting, showcasing.
27. **Mid 2026 on** (W): challenge, clearer, dependable, echoed, foster, leverage, matters, multifaceted, practical, prioritize, quietly, steady, universally.
28. **Academic abstracts** (K):
    - Rare words with the biggest excess: **delves** (28×), **underscores** (13.8×), **showcasing** (10.7×).
    - Common words with the biggest excess: **potential**, **findings**, **crucial**.
    - The common "style" set: **across, additionally, comprehensive, crucial, enhancing, exhibited, insights, notably, particularly, within**.
    - 66% of the excess style words are verbs.
29. **Evaluative adjectives that rate instead of describing** (G, G5):
    - dependable (23–59×), practical, meaningful, thoughtful, steady, deliberate, measured;
    - Gemini-style: incredibly, profound, immense, remarkably.
30. **Claude-family emphasis** (G, G5): "single most", "arguably the most", "perhaps the most", "the most powerful", "one of the best … about", "every single", "enormously", "is genuinely", "matters enormously".
31. **Helpfulness language** (G5, Opus 5.5 specifically): "can help you", "is especially helpful", "makes it easier", "helps you avoid".
32. **Hedging stock phrases** (G): "may provide", "can provide", "not necessarily", "need not". Real hedges stay; stock hedges go.
33. **Marketing verbs** (G): unlock, elevate, amplify, streamline, boost, leverage, payoff, wins, tangible.
34. **Hype words** (G): groundbreaking, paramount, unprecedented, revolutionary, invaluable, profound, exceptional.
35. **Puffery** (W, historical): nestled, in the heart of, renowned, rich (figurative), commitment to, diverse array, natural beauty.
36. **Intensifiers** (G): absolutely, entirely, highly, incredibly, exactly, precisely, specifically (Gemini 13× human).
37. **Longer words overall** (G): AI averages 5.2–5.7 characters per word vs 4.9 for humans. *Instead:* prefer the short word (O rule 2): use not utilize, help not facilitate, show not demonstrate, start not commence, enough not sufficient.

### A4. Formatting and punctuation

38. **Em dashes** (W, G, G5).
    - Older models overused them, usually spaced.
    - Opus 5.5 has dropped them almost entirely (0.015 per 1,000 words vs 2.92 for Opus 5). **Too few** is now its own tell: "commas and periods are more likely now than even human text" (W).
    - *Instead:* use the normal mix of commas, parentheses, colons, semicolons and the odd unspaced dash where a person would.
39. **Bold overuse**, including bolding every instance of a key term (W). *Instead:* little or no bold in prose.
40. **Inline-header vertical lists** ("- **Term:** explanation") (W). *Instead:* write prose when the content is an argument; use lists only for lists.
41. **Title Case In Every Heading** (W). *Instead:* sentence case, unless the venue's style requires otherwise.
42. **Small tables that should be prose** (W).
43. **Emoji, curly-quote inconsistency, and Markdown inside other markup** (W).
44. **Placeholders** ("[Year]", "2025-XX-XX", example.com) **and leftover chat text** ("I hope this helps", "Would you like…", "Here is a…") (W).

### A5. Citations

45. **Fabricated or unverifiable references**: dead links, DOIs that resolve to unrelated papers, book citations with no page numbers, `utm_source=chatgpt.com` (W). *Instead:* cite only sources you have actually checked, with pages where relevant.

---

## Part B: Signs of human writing to use (in the right register)

### B1. Wikipedia's observed human signs (W, "Signs of human writing")

46. Simple is/has phrases: "there is a", "it has a".
47. Plain verbs over stiff synonyms: wrote (not authored), moved (relocated), used (utilized), tried (attempted), died (passed away).
48. Definite and superlative statements **when true and sourced**: "the only", "was the first".
49. Ordinary qualifiers: "very", "perhaps", "tends to".
50. Occasional wordy constructions people really use: "as a result of", "in order to", "the fact that". (Don't remove every one; a perfectly trimmed text reads machined.)

### B2. Graphite's measured human tells (G)

51. First person ("we", "I") and "we're going to".
52. Addressing the reader ("you can't", "did you know").
53. Casual qualifiers ("pretty", "sort of"). *Chat only, not the paper.*
54. Small anecdotes and concrete past events ("years ago", "last year", "he said").
55. Personal experience and enthusiasm ("my favourite", "excited to"). *Chat only.*
56. Parenthetical asides, used far more by humans.
57. Exclamation marks, used 100× more by humans. *Rare in academic text; fine in chat.*
58. Contractions. *Chat yes; formal paper mostly no.*
59. Higher sentence-length variance.
60. Shorter words and less vocabulary variety within a text, meaning the same term is reused.

### B3. Classic principles of clear prose (GS, O)

61. Follow the grammatical subject with its verb as soon as possible (GS).
62. Put the new, important information at the end of the sentence, in the stress position (GS).
63. Put the person or thing whose story it is, and familiar linking information, at the start, in the topic position (GS).
64. Put the action of each clause in its verb, not in a noun: "we compared" not "a comparison was performed" (GS).
65. Give context before asking the reader to take in anything new (GS).
66. Never use a stock metaphor (O1). Never use a long word where a short one will do (O2). Cut any word you can (O3). Prefer the active voice (O4). Prefer the everyday word to jargon when they mean the same thing (O5). Break any rule rather than write something barbarous (O6).

---

## Part C: What is NOT a reliable tell (W, "Ineffective indicators")

Don't "fix" these. Changing them makes text worse without making it more human.

- **Perfect grammar.** Keep it correct.
- **Formal or academic register in itself.** Only specific words are tells.
- **Transition words in isolation.** Only the formulaic sentence-initial pattern is a tell.
- **Mixed casual and technical registers.** These are normal for technical people.
- **Correct citations and formatting.**

Humans are also poor detectors of AI text (W: near chance for non-users; about 90% for frequent LLM users). Detectors have real error rates. The target is good writing, not gaming a detector.
