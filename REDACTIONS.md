# Redactions

Tool: no secret scanner was installed (gitleaks and trufflehog not found on the machine). A regex sweep was written for this job and run twice: on the candidate source set (to choose omit versus rewrite) and on the assembled tree (final). Patterns: GitHub token prefixes, `hf_`, `sk-`, AWS key ids, PEM private-key headers, bearer tokens, key/token/password assignments, a high-entropy string pass, email addresses (noreply allowed), phone numbers, LAN IPs, EIN / SAM / CAGE identifiers, home paths, the private config directory name, conference/journal/review-system names, family and personal names, personal-status / SBIR / pricing / grant terms, gated-dataset names, agent-transcript markers. The first assembly claimed no personal emails; that was wrong (an email split across lines inside a LaTeX file evaded the regex, and one binary was not scanned). A leak check on 2026-10-16 found it, the files were deleted, and a second sweep (including split-line emails and binaries) was run on the final tree: no secrets, no personal emails, no phone numbers, no gated-dataset rows; the remaining hits are listed under "Not changed".

Redacted text is replaced by a bracketed placeholder; the removed content is not reproduced here.

## Counts by category (replacements in text files)

| category | rule | replacements | files |
|---|---|---|---|
| venue | conference/journal/review-system name | 20 | 12 |
| venue | anonymised-artifact phrase | 1 | 1 |
| business | funding-program reference | 2 | 1 |
| paths | home directory path | 6351 | 213 |
| paths | home directory path (claudius-maximus root) | 43 | 38 |
| transcripts | agent session link / trailer | 1 | 1 |
| network | LAN IP | 6 | 3 |
| secret-paths | reference to private config directory | 1 | 1 |
| secrets | API keys, tokens, passwords, private keys | 0 found | 0 |
| personal | personal data categories | 0 found | 0 |
| personal | personal email address (split across lines in LaTeX, and in a PDF) | found in 3 files, all deleted (see below) | 3 |
| gated data | raw rows from gated or licensed evaluation sets | 0 found (counts and hashes only appear in the records) | 0 |

Per-file lists for every rule: `REDACTIONS-FILES.tsv`.

## Whole files left out

| file | reason |
|---|---|
| paper/CIS2-paper-arxiv-draft-2026-08-28.pdf | PDF contains a personal email address and a venue name in its text; the Markdown/LaTeX draft is included instead |
| paper/lab-paper/ARTIFACT-MANIFEST.md | submission-artifact manifest (venue, anonymised hosting, session links); not CIS-2 content |
| paper/lab-paper/ARTIFACT-README.md | submission-artifact readme (venue, submission number); not CIS-2 content |
| code/cis2-llm/server/licensing.py | commercial licence-enforcement code (internal business) |
| code/cis2-llm/docs/USE-CASES.md | internal business analysis (buyers, willingness to pay) |
| 69 files under labs/*/results/ | duplicate of a file kept elsewhere in the same lab folder |
| PUBLISH-SCORE.md in each w1x / w3 / rust lab report folder | internal publication-scoring record (out of scope) |
| cis2-llm/licensing/ (EULA.md, license_tool.py, PRICING-INTERNAL.md, README.md) | pricing and licence terms (internal business) |

## Large or non-text files left out

Non-text files (binaries, archives) and text files over 1.5 MB are omitted per lab with size and sha256 in each folder `OMITTED.tsv`. No model weights are included.

## Not changed, and why

- Ledger `bar` text and `PREREG-from-ledger.md` are verbatim, because each bar is pinned by its sha256 (two bars, rust-2b and rust-4b, contain a home-directory path inside the bar text). Other ledger fields had paths rewritten.
- PREREG and plan files that the ledger pins by sha256 (`plan.sha256`) were passed through the same rewrites as other text; where a home path or venue name was in them, the file hash no longer equals the ledger hash. The affected files are listed in `REDACTIONS-FILES.tsv`.
- The given name "Justin" and the alias "Fable" appear in rulings ("ruled by Justin", "Justin decision") in many records and in commit messages. Left in place so the bars stay verifiable; the publisher may decide to strip them later.
- `code/cis2-llm/tests/GATEWAY-LOG.md` and the cis3-2b patch contain 64-hex `cap_token` values from a local gateway test. They are test outputs, not credentials. Flagged by the regex only.
- `"role": "user"` / `"assistant"` strings in cis2-llm and conformance vectors are chat-API test messages, not session transcripts.
- `POSTGRES_PASSWORD_FILE` in a docker-compose file names a secrets mount path, no value.
- Hostnames w1 to w4, hq and box names are kept. LAN IPs were replaced by host labels (the five known fleet addresses became w1 to w4 and hq; unknown ones became `<lan-ip>`).
- Third-party defect reports: none found in CIS-2 scope.
- Venue names inside cited literature (for example a related-work table) were also replaced by `[venue]`; arXiv ids and titles are unchanged.

## Deleted in the 2026-10-16 clean-up (after the leak check; the counts above include these files' original rewrites, `REDACTIONS-FILES.tsv` lists only files that remain)

| path | reason |
|---|---|
| paper/cis2-fp-paper-draft/docs/paper/arxiv/ (whole directory: main.tex, main.pdf, cis2-arxiv.tar.gz, bibliography, README) | contained a personal email address (split across lines in main.tex, in the PDF text, and inside a corrupt tarball) and a venue name in cited literature |
| paper/lab-paper/ | double-blind submission text and ALICE ternary content |
| labs/pre-ledger-moat/ | ALICE ternary checkpoint experiments (moat series) |
| labs/pre-ledger-e23-receipt-tamper/ | agent-receipt (CIS-1/ALICE) experiments on the ALICE ternary checkpoint |
| labs/pre-ledger-fm5-gpu-training-determinism/ | ALICE training experiments |
| labs/pre-ledger-models-and-scale/reports/2026-09-17-cost1-overhead.md | ALICE ternary checkpoint artifacts |
| labs/pre-ledger-replay-selfcheck-vectors/reports/2026-10-01-MAXR-CIS2-MODEL-CONSTRAINTS.md | CIS-1 / ALICE internals |
| code/cis2-llm/PROGRAMME.md, code/cis2-llm/docs/CLAIMS.md, code/cis2-llm/deploy/ | programme, claims and deployment material (internal business) |

## Text rewritten in the 2026-10-16 clean-up

- `code/cis2-fp/gpu/README.md` and `code/cis2-fp/gpu/kaggle/push.sh`: the ALICE ternary kernel scheduling text removed.
- Stale "private / do not publish / proprietary / held" marker lines in non-pinned files (code snapshots, READMEs, result notes) replaced by "Published 2026-10-16 as part of the CIS-2 archive."
- Absolute home-directory fragments (user name, Claude session scratch paths) in non-pinned files replaced by `<user>`, `<tmp>/<session>`. `PROGRAMME.md`, the only file naming /mnt/aegis1tb and /mnt/toshiba1tb, is deleted.
- Co-author trailer line removed from `code/patches/cis2-spec__seeded-sampling.patch` (not hash-pinned).
- Git history replaced by one commit.

## Left unchanged because ledger-pinned (sha256 equals a ledger hash), including private markers and absolute paths

Absolute paths that remain: `labs/rust-4b/PREREG-from-ledger.md:103` and `labs/rust-4b/ledger.jsonl` (/home/<user>/feed-payload/rust4b), `labs/rust-2b/PREREG-from-ledger.md:87` and `labs/rust-2b/ledger.jsonl` (/home/cm/rust2b), `labs/rust-2b/reports/rust-2b/VERIFY-RESULT-2026-10-16.md` (session scratch path). `code/patches/cis2-llm__cis3-2b.patch` keeps one scratch path as a diff line; the e18c / gpu2 / gpu3 patches keep the ALICE kernel scheduling text as diff lines (patches are not edited so they still apply).

Private markers that remain: the `PREREG` / bar files of w3, w4, w6 (for example "Private until ..."), `labs/rust-1/reports/rust-1/RESULT.md` ("PROPRIETARY, private"), and all ledger rows. Prose that says a repository "(private)" at the time a report was written is historical and was not changed.

Some records carry 'private' markers written before the 2026-10-16 decision to publish the CIS-2 archive; they are left unchanged so their ledger hashes still match.

## Licence scope

Code under code/ is published for reference; no licence is granted for it at this time. Documentation and results are under the root LICENSE (Apache-2.0). See `NOTICE`.
