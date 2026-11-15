"""Find AI-writing tells in a draft (Markdown, plain text or LaTeX). Read-only; prints a report.

    python .claude/skills/humanise/scripts/humanise_check.py FILE [--paper]

Pattern lists come from references/signs.md (Wikipedia: Signs of AI writing; Graphite AI Tells 2026
and its Opus 5.5 update; Kobak et al. 2025). A hit is a prompt to rewrite, not proof of anything.
--paper also flags contractions, exclamation marks and chatty qualifiers, which do not belong in a paper.
"""
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

PATTERNS = {
    "corrective framing": [r"\bnot only\b", r"\bit'?s not\b[^.]{0,40}\bit'?s\b", r"\bnot just\b", r"\bnot simply\b", r"\bnot merely\b",
                           r"\brather than (simply|merely|relying|focusing)\b", r"\binstead, it\b", r"\bless like\b[^.]{0,60}\bmore like\b",
                           r"\bis more than (a|an|just)\b"],
    "importance flag": [r"\bthis matters\b", r"\bwhy [^.]{1,40} matters\b", r"\bmatters (because|most|more than|enormously)\b",
                        r"\bdistinction matters\b", r"\bit is (important|worth|crucial) to note\b", r"\bit'?s worth noting\b",
                        r"(^|\. )note that\b", r"\bjust as important\b", r"\babsolutely essential\b"],
    "significance puffing": [r"\b(marks?|represents?|marking|representing) a (pivotal|significant|key|major|crucial) (shift|moment|step|turning point)\b",
                             r"\b(underscores?|highlights?) (the|its) (importance|significance)\b", r"\breflects? (a )?broader\b",
                             r"\bsets? the stage\b", r"\bindelible\b", r"\btestament\b", r"\benduring legacy\b",
                             r"\bshaped (the )?(conversation|discussion|debate)s?\b", r"\bbroader (debate|reflection|discussion)s?\b"],
    "tacked-on -ing analysis": [r",\s+(highlighting|underscoring|reflecting|ensuring|contributing to|fostering|showcasing|emphasizing|emphasising|demonstrating|illustrating)\b"],
    "stock vocabulary": [r"\bdelv(e|es|ed|ing)\b", r"\bunderscor(e|es|ed|ing)\b", r"\bshowcas(e|es|ed|ing)\b", r"\bpivotal\b", r"\bcrucial(ly)?\b",
                         r"\bintricat(e|ies|ely)\b", r"\binterplay\b", r"\btapestry\b", r"\blandscape\b", r"\bvibrant\b", r"\bcomprehensive\b",
                         r"\bnotably\b", r"\badditionally\b", r"\bfurthermore\b", r"\bmoreover\b", r"\benhanc(e|es|ed|ing)\b", r"\bfoster(s|ed|ing)?\b",
                         r"\bleverag(e|es|ed|ing)\b", r"\balign(s|ed)? with\b", r"\bgarner(s|ed)?\b", r"\bbolster(s|ed)?\b", r"\bseamless(ly)?\b",
                         r"\binvaluable\b", r"\bgroundbreaking\b", r"\bunprecedented\b", r"\bparamount\b", r"\bprofound(ly)?\b",
                         r"\bremarkabl(e|y)\b", r"\bincredibly\b", r"\babsolutely\b", r"\bmultifaceted\b", r"\bmeticulous(ly)?\b",
                         r"\bvaluable insights?\b", r"\binsights?\b", r"\bevolving\b", r"\brealm\b", r"\bnavigat(e|es|ing) the\b"],
    "evaluative adjective": [r"\bdependable\b", r"\bmeaningful(ly)?\b", r"\bthoughtful(ly)?\b", r"\bsteady\b", r"\bdeliberate(ly)?\b",
                             r"\bpractical\b(?![\s-](equivalence|relevance|relevant))"],
    # "measured" is left out: in research prose it is almost always literal (G lists it at only 4.2x).
    "Claude emphasis/helpfulness": [r"\bsingle most\b", r"\b(perhaps|arguably) the most\b", r"\bthe most powerful\b", r"\bevery single\b",
                                    r"\benormous(ly)?\b", r"\bis genuinely\b", r"\bgenuinely\b", r"\bcan help you\b", r"\bmakes? it easier\b",
                                    r"\bhelps? you avoid\b", r"\bwhat comes next\b", r"\blooking ahead\b", r"\badds another layer\b"],
    "hedge formula": [r"\bshould be (treated|read|presented|understood) as\b[^.]{0,80}\brather than\b", r"\bdoes not by itself establish\b",
                      r"\bbased on (the )?available information\b", r"\bwhile (specific )?details are (limited|scarce)\b"],
    "trade-off denial": [r"\bwithout (sacrificing|losing|compromising|requiring)\b"],
    "vague association": [r"\b(is|are|was|were) associated with\b", r"\bin connection with\b", r"\bconnected (to|with)\b"],
    "copula avoidance": [r"\bserves? as (a|an|the)\b", r"\bstands? as (a|an|the)\b", r"\bfunctions? as (a|an|the)\b", r"\bboasts?\b", r"\brefers to\b"],
    "summary closer": [r"(^|\. )(in summary|in conclusion|overall|ultimately|to sum up|in short),", r"(^|\. )together, these\b"],
    "chat residue": [r"\bi hope this helps\b", r"\bwould you like\b", r"\blet me know\b", r"\bhere is (a|an|the)\b", r"\bcertainly!\b", r"\bgreat question\b"],
}
PAPER_ONLY = {"chatty in a paper": [r"\b\w+n't\b", r"\b(it|that|there|what|we|they|you)'(s|re|ll|ve|d)\b", r"!", r"\bpretty\b", r"\bsort of\b", r"\bkind of\b"]}
OPENERS = re.compile(r"^(Additionally|Furthermore|Moreover|Notably|Consequently|Ultimately|Overall|Importantly|Crucially|Interestingly|Indeed|Thus|Hence|Therefore)\b")


def strip_tex(text: str) -> str:
    text = re.sub(r"(?<!\\)%.*", "", text)
    keep_lines = lambda m: "\n" * m.group(0).count("\n")   # removed blocks keep their line count, so line numbers stay right
    text = re.sub(r"\\begin\{(equation|align|tabular|table\*?|figure\*?|algorithmic|tikzpicture)\*?\}.*?\\end\{\1\*?\}", keep_lines, text, flags=re.S)
    text = re.sub(r"\$[^$\n]*\$", " X ", text)
    text = re.sub(r"\\(cite|ref|label|eqref|url|input|includegraphics)\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", text)
    return re.sub(r"[{}~]", " ", text)


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"])", flat)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__); return 2
    path = Path(sys.argv[1])
    paper = "--paper" in sys.argv
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = strip_tex(raw) if path.suffix == ".tex" else re.sub(r"`[^`]*`", " ", raw)
    lines = text.splitlines()
    pats = dict(PATTERNS)
    if paper:
        pats.update(PAPER_ONLY)
    total = 0
    print(f"== {path.name} ({'paper' if paper else 'general'} mode)")
    for cat, plist in pats.items():
        hits = []
        for i, ln in enumerate(lines, 1):
            for p in plist:
                for m in re.finditer(p, ln, flags=re.I):
                    hits.append((i, m.group(0), ln.strip()[:110]))
        if hits:
            total += len(hits)
            print(f"\n[{cat}] {len(hits)}")
            for i, w, ctx in hits[:25]:
                print(f"  L{i}: '{w}'  | {ctx}")
            if len(hits) > 25:
                print(f"  ... {len(hits) - 25} more")
    sents = sentences(text)
    lens = [len(s.split()) for s in sents]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    nwords = max(1, len(words))
    dashes = text.count("\u2014") + len(re.findall(r"(?<=\w)--(?=\w)", raw if path.suffix == ".tex" else ""))
    openers = [s for s in sents if OPENERS.match(s)]
    print("\n== statistics")
    print(f"  sentences {len(sents)}; words {nwords}")
    if len(lens) > 1:
        print(f"  sentence length mean {statistics.mean(lens):.1f}, SD {statistics.stdev(lens):.1f} (target SD >= 8), "
              f"short(<10) {sum(l < 10 for l in lens)}, long(>25) {sum(l > 25 for l in lens)}")
    print(f"  avg characters per word {sum(map(len, words)) / nwords:.2f} (human web ~4.9; AI 5.2-5.7)")
    print(f"  em dashes per 1,000 words {1000 * dashes / nwords:.2f} (neither a flood nor exactly zero)")
    print(f"  sentence-initial stock transitions {len(openers)}")
    print(f"  parentheses per 1,000 words {1000 * text.count('(') / nwords:.1f}")
    print(f"\n== total kill-list hits: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
