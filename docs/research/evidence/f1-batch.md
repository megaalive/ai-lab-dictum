# F1 batch — 48 synthetic intents, versioned IR and development baseline

24 November 2026. SELF technical review (DEC-009). Ref #28/#38/#40; sole integration candidate [PR #39](https://github.com/megaalive/ai-lab-dictum/pull/39), includes #36, #30/#33/#34 ancestry. Tested source `6adf5ec5acd792b38e71a8a136f2cd2eaf1a2051`, tree `6c16583b2b03260196a132ee8e63c97a63fc6761`. [Native push](https://github.com/megaalive/ai-lab-dictum/actions/runs/45390656018) 5/5 jobs; [isolated push](https://github.com/megaalive/ai-lab-dictum/actions/runs/45390655918) 2/2 jobs. Exact checkout confirmed in each log. [Structured evidence including all model misses and timing per configuration](f1-batch-results-v1.json). Evidence-only addendum is not the tested code SHA. No independent human gold or EXT review.

## Technical scope and evidence

| Work package | Actual | Limit |
|---|---|---|
| F1-A | 48 metadata entries; 48 synthetic proposal intents, 43 structured and 5 narrative-only. 11 new kinds in closed IR v2. 125 deferred domain vectors, 882 standalone native candidate vectors, 11 v1 rejection checks. | Original registry/profile pinned; all 48 real bindings BLOCKED/NOT VERIFIED. | 
| IR v2 | 1,064 unique version/stage/frame differential vectors, 32 digest tests, 24 semantic mutation rejections (including rehashed wrong recipes), zero mismatch. V1 retained, v2 distinct identity/digest; no execution-candidate. | Shape validity/hash not authority; no external runtime plan ingestion. |
| F1-B | B0 574/574 fixed functional outcomes, B1 237/300 supported; both 274/274 non-supported. 12 new composition cases; old S2 retained. | Narrow authored grammar, major S2 coverage limitation. B2 actual NOT RUN. |
| B2 mechanics | 234 native/Python feature+score+rank checks, six abstract numeric training rows only. | No Dictum fit, weights, common-extractor B2 integration/evaluation or loader. Rights/human-review gate pending. |
| F1-C | 17 utility identity candidates, 48 per-intent obligations, 22 shape vectors. | Actual guest inventory/host equivalence NOT RUN. Codex #37 only authorized disposable guest. |
| F1-D | Pinned inventory 574 functional cases and separate 32 S2 refs/100 dev; 26 toy rows, 22 connected groups, 20 negative vectors. | Human gold 0, rights HOLD, actual corpus/split/holdout/training NOT RUN. |
| F1-E | 29/29 CTest in each GCC/Clang Release/Debug ASan/UBSan configuration; original v1 differential, 25k parser fuzz, 113 renderer fixtures and 16 real-shell inert round trips retained. 633 actual isolated CLI launches, zero observed forbidden post-launch exec/spawn/network/target access/canary leak under traced classes. | Finite tests, no general security proof, no actual OS target execution or FES. |

## Actual baseline (separate locked suites)

| Supported suite | B0 JIA raw/resolved | B1 JIA raw/resolved |
|---|---:|---:|
| F0 (48) | 48/48 | 34/48 |
| F1 v1 (150) | 150/150 | 119/150 |
| F1 v2 (102) | 102/102 | 84/102 |
| Total 300 (150 ID/150 EN) | 300/300 | 237/300 |
| Old S2 supported (80; diagnostic only) | resolved 12/80 | resolved 9/80 |

Both B0/B1 60/60 ambiguity, 47/47 OOD, 167/167 security in the 574 functional cases; no proposal on original S2 20 negative cases. B1 supported misses 63 (14+31+18), accepted supported all correct on these authored cases; full miss IDs/confusion in JSON. Previous #36 B1 146/198 supported; new same denominator 153/198 (+7), F0 unchanged 34/48 and S2 8→9/80. S2 B0 12/80 unchanged; no blind generalization or threshold pass. F0/F1 old gold and S2 original labels not changed. B0 and B1 both use complete grammar and identical resolver/policy; weighted lexical retrieval only abstains, no training. 102 supported v2 cases = 90 six-per-intent for remaining 15 + 12 compositional combinations. Language remains narrow, exact typed domain literals; no tuning to S2 misses.

GCC Release warm v2 suite: 202 input frames, 1 unmeasured pass + 10 measured passes/model (2020 calls; 1020 supported), shared CI host. Full input through view, no process launch. Peak RSS entire process, not weights. Not reference VM gate.

| Model | Supported p50 us | Supported p95 us | RSS KiB |
|---|---:|---:|---:|
| B0 | 118.8625 | 140.513 | 18600 |
| B1 | 120.9515 | 149.6 | 18800 |

Other compilers/configurations, cold subprocess and complete counts in JSON; no averaging Release with sanitizer.

## SELF review and outstanding decisions

- Versioned overlay/digest source identities and fixed synthetic domains, actual native validation and independent Python semantic checks; v1 four schemas and previous fixture source blobs preserved. Five diagnoses produce only fixed narrative guidance, no plan/handler/child operation or raw target projection. DNS/ping are NET proposals with no traffic; archive paths explicit distinct/new synthetic destination, no actual existence/safety claim. All views NON_COPYABLE, no executor, no real filesystem/IPC/network. Native B2 code is linked only to development probe. No third-party source text or real data imported.
- [Native v2 ADR](../../adr/0008-f1-ir-v2-full-proposal.md), [schema profile](../../../spec/ir/schema-profile-v2.md), [B2 contract](../b2-development-contract-v1.md), [human seed packet](../../../data/manifests/f1-human-seed-review-v1.md), [desktop inventory](../f1-debian-inventory-handoff.md). Original license ledger remains HOLD. Native/fixture claims bounded to actual evidence; not a release or general language quality decision.
- F1 remains IN PROGRESS. Actual human-reviewed 200–500 seed and rights permission #35; authorized disposable Debian guest and independent preflight #37; actual B2 fit/common-extractor integration and comparator #40; actual quality and reference VM gates #28. FES/S3 blocked, F2 HOLD, executor NO-GO. No merge authorization inferred; owner decision required. No training or private data upload authorized. Human review cannot be replaced by model authorship or synthetic fixtures. Codex desktop can run #37 on explicitly authorized guest after preflight; absence of preflight means BLOCKED. Repository-side batch technical increment complete, not whole-phase acceptance.
