# rust-2b: operator ruling on the Burn arm's feature list (A1)

Ruling by the operator (Fable), written 2026-10-05T18:16Z, before any timing of the registered configuration exists. Asked for by the conformance reader (VERIFY-PRESTART-conformance-R2.md, MUST 1).

## Change record (nothing was timed before any of these versions)

- Version 1, 2026-10-05T18:16Z: the ruling as first written. sha256 be983c2d6e917fb8e353b2b15c7fe9ca476f2c60a455f1d90e1da6f1083e860b, repository commit ce3d37bd.
- Version 2, 18:43Z: sha256 5fac4a00c513db54655a7125d1be69ca936bc9e77cab57ad569dc49379b210f7, repository commit acc7a9c3. The third conformance read (VERIFY-PRESTART-conformance-R3.md) had found one wrong clause in fact 4 of version 1: it said the documentation's line compiles in a second backend (burn-ndarray). It does not. Re-checked on box1 between 18:41Z and 18:44Z: the build tree of that line (tree.txt) has no line with "ndarray", and burn's feature list there has no "ndarray". The mistake most likely came from reading the resolver's full package list (729 entries, which holds every optional package) as if it were the build tree (177 packages). Every change of version 2 against version 1: (a) a correction paragraph at the top; (b) the heading of the facts; (c) fact 1, "the reader repeated" became "the readers repeated"; (d) fact 2, second half (what the documentation example does and does not say); (e) fact 3, the words for the four crates (they are on the path of every step, so "bookkeeping" was too weak) and a new last sentence on the lock and the hash map; (f) fact 4, the wrong clause replaced by the list of the 35 extra packages, and a new description of how the resolve was made; (g) the section "What this ruling does not settle": its first paragraph (direction of the effect not known), "Decided now" became "Decided at 18:16Z", and a NEW last sentence on the lock file, the folders and the binary hash of the unregistered check, which was written at 18:43Z in answer to the third read and was NOT part of the 18:16Z decision; (h) the first bullet under "Use" (cited by sha256; both times in the --reason).
- Version 3, 19:15Z (this text). The fourth conformance read (VERIFY-PRESTART-conformance-R4.md) found two faults in version 2. First, the new last sentence of fact 3 said that without std burn-autodiff uses a spin lock "in place of the standard library's lock". Wrong: with std the lock comes from the parking_lot crate, not from the standard library. The third reader had written it correctly and I restated it wrongly. Read by me in the crate source on box1 shortly before 19:14Z (src/runtime/graph.rs, src/lib.rs and Cargo.toml of burn-autodiff 0.21.0) and corrected below. Second, the correction paragraph of version 2 did not list every change, and the sentence named under (g) stood in a paragraph dated 18:16Z. Changed in version 3: this change record replaces that paragraph; the last sentence of fact 3; the wording of the lock in the first paragraph of "What this ruling does not settle"; the sentence under (g) now stands in its own paragraph with its own time; "came from" became "most likely came from"; the heading of the facts and the first bullet under "Use" name both corrections.

The choice itself (A1 is the registered arm) is the same in all three versions, and no reason for it rested on either wrong clause.

## The question

The registered pass mark says: "Burn 0.21.0 with features flex and autodiff is the arm", and in the same paragraph: "Features, rustc and RUSTFLAGS recorded and frozen before the initial timing (Cargo.lock sha256 recorded)."

The builder's dependency lines (A1 of the staged amendment) are:
- burn 0.21.0, default features off, features flex and autodiff;
- burn-flex 0.21.0 named directly, with its own default features std, simd and rayon.

The reader asks: is the second line a change of the registered arm?

## Facts (each checked before this ruling; facts 2, 3 and 4 changed as the change record says)

1. With burn's default features off, burn's feature "flex" does not switch on any feature of burn-flex. The backend is then built without its thread pool, without SIMD and without std (builder; the readers repeated the feature tree on box1).
2. Burn's own documentation gives the backend's defaults as std, simd and rayon (burn-flex 0.21.0 README, "Default: std, simd, rayon"; registry copy on box1, read between 18:09Z and 18:16Z). The dependency example in that README names features on the burn crate and does not turn burn's default features off. It does not say in words that burn's defaults are on; that they are on in such a line is how the build tool treats a dependency line without "default-features = false".
3. In the build pinned by A1 (Cargo.lock sha256 1ea4de5a...; feature list read by the operator on box1 between 18:09Z and 18:16Z from the dependency resolver, nothing built or timed): burn-flex has std, simd, rayon; gemm, the matrix-multiply library burn-flex calls, has std and rayon; macerator, its SIMD library, has std. So the code that does the arithmetic is built as Burn ships it. Four other Burn crates are built without their own "std" feature, because burn's default features are off: burn-autodiff (the backward graph), burn-optim (the AdamW step), burn-nn (the layers) and burn-core (the glue between them). All four are on the path of every training step. Read in the crate source of burn-autodiff 0.21.0 (third and fourth conformance readers, and the operator shortly before 19:14Z): without std, its graph lock comes from the spin crate instead of the parking_lot crate, and its other modules use the hashbrown map where they would use the standard library's map (the graph module uses hashbrown in both builds).
4. The other candidate, burn with its default features on (the documentation's line), was resolved by the operator on box1 at 18:11Z (file times in <home>/scratch-rust2b/op-ruling: meta.json 18:11:54Z, tree.txt 18:12:19Z) and NOT built and NOT timed. It gives the same features for burn-flex, gemm and macerator. It differs in: std on in the four crates named in fact 3; a tracing feature in burn-autodiff; 35 more packages in the build tree (177 against 142), namely the cubecl runtime crates, a record and compression stack, the tracing crates, dirs and dirs-sys and some small helper crates (full list in VERIFY-PRESTART-conformance-R3.md, MUST 1), none of them a second backend; and one crate whose name ends in "-sys" (dirs-sys), which by the wording of the registered purity rule ("any -sys crate") would set the label NOT PURE RUST although the reason for that rule is native code. How the resolve was made: in a scratch folder, starting from a copy of the pinned lock file, with network access on box1 (the build tool updated its index, added 356 packages to the lock file and downloaded crates; its messages are in meta.err). That lock file (729 entries, sha256 44d085105bcd7085...) is not the pinned one. All 142 packages of the pinned build tree are in the documentation tree with equal versions (third conformance reader).

## Ruling

A1 as staged IS the registered arm. It is a reading of the registered sentence, not an exception to it.

Reasons:
1. The registered sentence fixes the features of the burn crate: flex and autodiff. A1 has exactly those two on burn and nothing else.
2. The same registered paragraph leaves the full feature list to be "recorded and frozen before the initial timing". A1 is that record.
3. The question registered is about Burn's Flex backend against PyTorch. A Flex backend without threads and SIMD is not the backend Burn ships or documents, the registered two-thread condition could not be honoured with it, and a label from it would mostly measure the missing features. With A1 the backend has exactly its documented defaults, the same as in a build that follows the documentation.
4. Choosing between A1 and the documentation's line (fact 4) was done on these grounds alone. No timing of either exists. What the operator has seen: the direction of an early smoke timing of whole processes on the smoke configuration, and that the stripped build used about 3.6 times the CPU of the A1 build in 3-step check runs (BUILD.md section 5). Neither says anything about A1 against the documentation's line.

## What this ruling does not settle, and what is done about it

Whether building the four crates of fact 3 without "std" changes the speed is not measured, and the direction is not known: the arithmetic code is identical in both builds, but the four crates run in every step; the spin crate's lock may cost time against parking_lot's, the other hash map may save some, and the documentation build also compiles in tracing code that A1 does not have. The operator expects the arithmetic to take most of the step time. That is an expectation, not a measurement.

Decided at 18:16Z, before any timing: after the registered box1 job has been harvested, ONE unregistered job times the same program built with the documentation's dependency line (burn default features on), with the same runner and thread counts. It carries no label, cannot change the registered label, and is reported beside the registered result as "documentation build, unregistered check" with its package count and the dirs-sys remark. If it cannot be built or run, the result says so.

Added at 18:43Z in answer to the third conformance read (not part of the 18:16Z decision): the lock file of that check is fixed and hashed before it is built, and its build and run use their own folders, job names and binary path, so that the registered binary on box1 is not touched (its sha256 is read before and after; BUILD.md step 8b).

## Use

- The amendment's header names A1 as this reading and cites this file by its sha256; `cm-exp amend-bar` gets the ruling time and both correction times in its --reason.
- The result report repeats facts 3 and 4 in plain words next to the Burn numbers.
