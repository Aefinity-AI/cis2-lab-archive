## registered (2026-10-16T08:53:53Z) bar_sha256=7a3426cae92c51ca36668d2e916d7cad405af60599ed6b0c59ff44a4380ceeba

MET if the per-row witness digest for the pinned prompt is identical for batch sizes 1, 2, 4 and 8 on the host build and on the CUDA sm_61 build, and equals the pinned d8274305... at batch 1; a prompt-set of distinct prompts gives each row the same digest it gets alone. Any batch-dependent digest = NOT MET (reported either way).

