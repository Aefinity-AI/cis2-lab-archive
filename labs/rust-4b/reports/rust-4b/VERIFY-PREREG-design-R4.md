# rust-4b pre-registration read R4, lens DESIGN AND CLAIMS (verifier, read-only)

VERDICT: REGISTER (0 MUST; 6 SHOULD, wording only).
Read: bars/rust-4b.txt (revision 4, sha256 a40df1d3445ed7f44186308c2660632905fe93a1913a8f0ba1caad097d5b4ac3), bars/rust-4.txt (M2 paragraph, Rule A, sentence), VERIFY-PREREG-design-R3.md, run.py (DESIGN, finish() words, drop command), filelists.json head.
Commands: sha256sum of payload run.py, source run.py, filelists.json, PAYLOAD_SHA256, six wrappers, bin/* and p/* (all equal their PIN lines; sha256sum -c PAYLOAD_SHA256 shows 0 non-OK lines); python3 check of DESIGN (sums, consecutive places, openers); grep of run.py for RESULT words; arithmetic by hand of estimate lines.

## MUST
none. R3's M1 (two words for one outcome) is fixed: "invalid" now needs the FIRST job INVALID and its one redo INVALID; a redo as 10 that ends INVALID goes to inconclusive. Walked every combination (first job OK label / TIE / overlap; INVALID then redo OK, overlap, INVALID, FAIL, OK-PARTIAL; FAIL x3; R or C NOT RUN INVALID = OK-PARTIAL; COST-CAPPED; voids >8): each lands on exactly one of met / inconclusive / invalid.

## SHOULD
S1 Rule A is quoted with words dropped and no ellipsis. rust-4 reads "... checks box1 CPUQuota and thermal state while idle, records the dated result and gets BOXES.md updated"; rust-4b quotes "... while idle and gets BOXES.md updated". Put "..." where "records the dated result" was, or say "abridged".
S2 Positions are counted from 0 (mean 2.0 for 5 arms; the sums 12/13 and 7/8 are 0-based; checked in run.py DESIGN: 6 arms sums 12,12,12,13,13,13; 4 arms 7,7,8,8; 5 arms 10 each; no repeat of a place in consecutive orders incl. row 5 to 1; openers distinct). Say once "positions are counted from 0 (first = 0)"; a non-specialist reads "mean position 2.0" as 1-based.
S3 The 2,000 s rule makes the carried "overlap -> redo as 10 -> TIE (NOT SEPARABLE)" probably unreachable on box1 (the text says so). It is a change to a carried rule (D1 said unchanged) and is disclosed. Keep, but the operator should know it is a decision, not a detail: the likeliest bad outcome (overlap in cold reads) ends as inconclusive with no label. A redo of R and C alone would fit the cap; it needs a new wrapper pin, so only if the operator wants it before registration.
S4 Jargon at first use: OK-PARTIAL (first used in the REVISION 4 header), FAIL, void, discard, clamp, arg-max, "pin", COST-CAPPED are not in the glossary. Add one glossary line: "OK-PARTIAL = the job finished but something was NOT RUN, COST-CAPPED or voided; FAIL = nothing was timed (host busy or sudo failed); void = a run thrown away for other load on the host; discard = a run thrown away for a clock drop or throttle; clamp = the CPU held at a lower speed; arg-max = the token with the highest score."
S5 The pass mark records no hash of itself (correct) but FREEZE.md does not name the revision-4 pass mark hash; the --ref at start must use the final file hash (a40df1d3... today). Registrar: recompute after any edit.
S6 Expectation: operator P 85 percent is probably high (R3 S4; text already calls it so). Left as written; fine.

## CHECKED, NO CHANGE
- Carried sentences: M2 bands, r, sentence form, P definition, expectation text equal word for word to rust-4 line 18/36; changes are only D2-D6, D8, --copies, redo/cap rules, all disclosed.
- Cold check can fail and pass: drop ok -> controls pass, 0 pages, rep kept; sudo -n sh -c true fails -> FAIL nothing timed, requeue up to 3, ledger inconclusive; sudo ok but write fails / tmpfs / mapped elsewhere -> warm control ok, cold control fails 3 times -> job INVALID (runner line 1009) with reason words covering it; one resident venv page -> P alone NOT RUN INVALID, pair unaffected; warm control failing -> INVALID "cannot bite".
- File lists: R, C, Rv, Cv, Q exact templates from traces; P a stated rule (regular files in the venv). Two people would freeze the same list for all but P; P count is recorded per host. Limits of "cold" stated plainly (firmware cache, readahead, unlisted stdlib, mapped libs).
- Unlabelled hosts: banner "no label (Rule A)", band words not used, FRAMEWORK sentences end with it.
- Arithmetic: 50+25+15+10=100; 5.1 tok/s x 39 = 7.6 s; 3 x 15.8 = 47.4 (about 48 s); box1 238.2/rep, 1,624 and 2,815; box2/3 2,788 and 4,970; box4 1,569; box5 1,768; total 10,537; 2,815 x 1.2 = 3,378 < 3,400; 1,624+1,624+2,815 = 6,063 > 5,400; 5,400+1,800 = 7,200. SURPRISE defined for both expectations and the TIE (NOT SEPARABLE) split.
- Pins: every PIN equals the file.
