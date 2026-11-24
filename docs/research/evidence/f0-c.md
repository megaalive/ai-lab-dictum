# F0-C walking skeleton — integrated SELF evidence

24 November 2026. Issue [#23](https://github.com/megaalive/ai-lab-dictum/issues/23), consolidated PR [#27](https://github.com/megaalive/ai-lab-dictum/pull/27), component reviews #24–#26. Reviewer **SELF**, GPT-6.2 author/technical lead, DEC-009. Base `5d4d880539500ba4a403fc7c7cd01874ec8f260b`; tested code `74f7998d8077328f6fd333686db2a1957985b454`; tree `f4a145a3e6196430fcf17e7e64baf733244fd7a2`. [Native push run 45368217222](https://github.com/megaalive/ai-lab-dictum/actions/runs/45368217222) and [isolated renderer/security push run 45368217316](https://github.com/megaalive/ai-lab-dictum/actions/runs/45368217316) completed success: 5/5 and 2/2 jobs. Every job log contains exact tested checkout; this evidence addendum is not the tested code SHA. [Raw structured results and job IDs](f0-c-results-v1.json). No claim of human gold, blind accuracy, release readiness, VM attestation or EXT.

## Reproduction

Debian 13.5 slim x86-64 pinned userspace image from workflows; Ubuntu 24.04 host runners, kernel 7.0.0-1014-aws / 7.0.0-1017-azure; GCC 14.2, Clang 19.1.7, Python 3.13.5, OpenSSL 3.5.9 (Apache-2.0 package copyright excerpt), Unicode 15.1.0. Compiler/package versions and checkout recorded per job. No fixed CPU performance claim; shared CI host, no reference VM.
```sh
CC=gcc cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release -DCMAKE_COMPILE_WARNING_AS_ERROR=ON
cmake --build build/release --parallel 2
ctest --test-dir build/release --verbose --output-on-failure --no-tests=error
CC=clang cmake -S . -B build/sanitizer -DCMAKE_BUILD_TYPE=Debug -DCMAKE_COMPILE_WARNING_AS_ERROR=ON -DDICTUM_ENABLE_ASAN=ON -DDICTUM_ENABLE_UBSAN=ON
cmake --build build/sanitizer --parallel 2
ctest --test-dir build/sanitizer --verbose --output-on-failure --no-tests=error
```
Repeat both configurations for each compiler as in [CI](../../../.github/workflows/ci.yml). Direct parser libFuzzer command in CI (25k fixed-seed budget). Actual shell and CLI trace use [isolated workflow](../../../.github/workflows/f0-c-renderer.yml), no target utility execution. Do not invoke generated previews outside inert harness; no desktop privileged action required for these tests.

## C-01–C-10 technical checklist

| Gate | Expected | Actual and disposition (bounded scope) |
|---|---|---|
| C-01 | 8 unique canonical IDs, valid ID/EN chains | **PASS** functional: all eight, 6 each, 24 ID + 24 EN; native NLU, IR, policy, plan, structured view; no external stage-ingestion API. B0 primary, B1 same interface, experimental guarded retrieval. |
| C-02 | >=40 supported (>=5 each), >=20 ambiguity/OOD, >=40 negative/security | **PASS** count/functional scope: 140 distinct cases, 48 supported + 18 ambiguity + 14 OOD + 60 security. SELF authored after grammar design, not independent human gold. Separate unchanged 100-case S2 replay. |
| C-03 | Correct functional IR/slots/policy/representation | **PASS** B0: 48/48 raw joint explicit slots, resolved JIA/JS and policy/representation; 18/18 ambiguity, 14/14 OOD, 60/60 security. B1 39/48 supported, 17/18 ambiguity; misses retained, not default. Actual SHA-256 of context bytes and plan JCS independently recomputed; schema and semantics separate. |
| C-04 | >=100 oracle/native positive+negative | **PASS** 420 unique differential, 164 gold, 0 mismatches/retrievals, all four stage positive/negative; 104 span checks; 61 SHA-256/JCS checks. A2 196 fixtures. Subset only, not generic JCS/JSON Schema implementation or approval authority. |
| C-05 | S1 + all copyable gold equivalent argv, native/unknown shell noncopyable | **PASS** bounded: prior S1 10k/profile; C05 native 113/113 (16 copyable, 97 reject/byte) and actual 8 Bash + 8 dash inert round-trips; each profile 54 rejects including shared cases, do not sum duplicates as unique. All actual product views NON_COPYABLE. |
| C-06 | Actual CLI trace, no post-launch exec/process/network; run denied | **PASS** 150 actual isolated CLI launches; 0 post-launch execs, process creation, network attempts and target file access under traced classes. Twelve synthetic guard checks. Root read-only, no bind mounts, caps dropped, no-new-privs, network none, nonroot, child network syscall deny. No VM-equivalence or general security proof. |
| C-07 | Sensitive inputs/fixtures not emitted; root boundary | **PASS** bounded synthetic: 60/60 security for both models; actual trace includes root/escape/unknown path/canary tests and run denial. No canary output/error/trace, fixture hashes unchanged, no persisted product audit/log exists. No host projection/descriptor enforcement because no target access. Raw arguments are not a privacy-safe carrier for real secrets. |
| C-08 | C17 strict build, ASan/UBSan, fuzz, reproducible | **PASS** 20/20 CTest in all 4 configurations. Clang direct ASan+UBSan libFuzzer 25,000 runs, max_len=32769, seed 23004, 126 synthetic seeds, no reported sanitizer finding. Finite test budget, no memory-safety guarantee. |
| C-09 | Actual baseline report with complete denominators and limitations | **PASS** measurement only (below); quality thresholds NOT RUN; S2 coverage is substantially worse than prototype. Do not claim F2/F3/blind or reference-VM performance. |
| C-10 | Spec links, provenance, checklist and issue list, no real production data | **PASS** repository evidence/provenance checklist in this addendum. Reviewed source diff (41 files before docs; code, synthetic fixtures, CI, no model pack, external corpus, host data or credentials introduced). S5 excluded sources not imported; original authored fixtures internal development only; distribution/license owner decision pending. Not a comprehensive secret scanner or independent rights audit. |

## Baseline results

48 supported functional (6 per intent; 24 per language), 18 ambiguity, 14 OOD, 60 security. Same fixed corpus for B0/B1, no optional or dropped cases. 140 completed probe calls/model and 140 actual CLI checks per CTest configuration; byte-only cases tested through probe, not impossible embedded-NUL argv. Raw JIA uses explicit candidate span/context-ref gold, no catalog defaults attributed to NLU. Resolved JS includes exact slots, policy/representation invariants. Selective accuracy = correct/accepted, not whole-denominator accuracy.

| Model | Raw JIA | Resolved JIA / JS | Supported coverage | Selective accuracy | Clarify | OOD | Security |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | 48/48 | 48/48 | 48/48 | 48/48 | 18/18 | 14/14 | 60/60 |
| B1 | 39/48 | 39/48 | 39/48 | 39/39 | 17/18 | 14/14 | 60/60 |

B1 misses nine supported + one ambiguity, language ID 20/24 and EN 19/24; B0 ID/EN 24/24 each. All exact miss IDs, confusion and counts are in JSON results. B1 is guarded word-overlap retrieval over 32 pinned S2 refs, not the S2 prototype TF-IDF or independent unguarded model. No training; no quality threshold implied.

Warm timing: same fixed 140 frames, shuffled seed 23009, one full pass warmup, 10 measured passes/model (1400 calls, 480 supported); CLOCK_MONOTONIC around full in-process input→view; excludes subprocess start and harness transport. Each model in separate process; getrusage peak RSS entire process (not isolated model weights, can include launcher high-water). Cold numbers are 140 separate probe subprocesses including startup, transport/output and host scheduling; not pristine cold-cache measurements. GCC Release push example:

| Model | Warm all p50 / p95 us | Warm supported p50 / p95 us | Peak RSS KiB | Cold process p50 / p95 ms |
|---|---:|---:|---:|---:|
| B0 | 22.429 / 120.595 | 109.761 / 126.234 | 18248 | 2.036 / 2.329 |
| B1 | 25.3865 / 125.801 | 111.4915 / 131.676 | 18504 | 2.002 / 2.334 |

Clang Release warm supported p50/p95 B0 92.6455/105.776 us, B1 92.074/107.757 us; RSS 18256/18384 KiB. Debug sanitizer RSS and timings are much higher, retained separately in JSON, not averaged into Release. Timing on small authored data and shared CI only. Reference VM CPU/resource config, PSS/FES, calibrated scores, cluster confidence bounds, human blind gold and inference model weights NOT RUN.

### Negative result on unchanged S2 development

[Prior S2 prototype evidence](s2.md) 78/80 B0 and 73/80 B1 joint accuracy. Native skeleton is **not** a drop-in port of either prototype: complete grammar and exact synthetic scope restrict coverage, and B1 differs in ranking. This is a major coverage limitation, not evidence of quality improvement. Retain original labels and record stricter deny vs original clarify/unsupported as exact-outcome misses.

| Model | Native JIA/JS | Supported coverage | Selective accuracy | Exact clarify | Exact unsupported | No proposal on negative suites |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 12/80 | 12/80 | 12/12 | 2/10 | 8/10 | 20/20 |
| B1 | 11/80 | 11/80 | 11/11 | 2/10 | 8/10 | 20/20 |

Both correctly resolve `dev-6-7` and `dev-7-7` (path/log collision) after explicit regression remediation; no proposal on original 20 ambiguity/OOD. B0 78 overall misses; B1 79. ID/EN supported B0 8/56 and 4/24; B1 7/56 and 4/24. These are diagnostic comparisons, not semantic gold for the exact outcome of changed policy, and not blind. Do not continue tuning to the same S2 labels. F1 should generalize compositional B0/B1 and independently curate broader development gold before new held-out evaluation, conditional on owner GO.

## Provenance and review findings

- Normative [baseline v3](../../../plans/baseline-v3.md), [F0 checklist](../../../plans/drafts/f0-v3.md), [IR profile](../../../spec/ir/schema-profile.md), [catalog](../../../spec/catalog/catalog-profile.md), [renderer](../../../spec/renderer/preview-v1.md), [ADR pipeline](../../adr/0004-f0-c-structured-pipeline.md), [benchmark prereg](../benchmark-preregistration-v1.md), [corpus protocol](../../../data/manifests/corpus-protocol-v1.md).
- Actual functional corpus SHA256 `ba782dc63737d7c6c7d8b243d083f8aeae1b28bb1baffd9d2e9c860d7cedaca8`, raw explicit gold `8b64b1b54bc2ca84b4b765bfd8f15d33b16d8c925f3bfadca44d6cd409291e46`, S2 `bd573c6dbc2b6017ce861e1a2e3b3f89011f82981e7b9731005ce825717dc39a`, A4 `52e62f530648dd8107b847a07077c43abadeb5442389794b3a0fe9a837a5983a`. Grammar/fixture blob `c5b291a6a5b6a1ce7f93ddc2f9acf142d0c23a3b`, catalog `110368054b8d9f1ffa89a18dc23f4927769a32e4`, profile `2cc5431daaf3da0dcaaa7fdcacefdb7b04a8cae9`, S2 blob `3081d95d327c2aa7851efaa673168591c1f7002c`. [S5 ledger/evidence](s5.md) unchanged, no excluded external data imported. Original SELF authored examples, labels derived from expected literals not native results; internal test use only, not human-curated/licensed training corpus. Test seeds 23004 (differential/fuzz), 23009 (digest/benchmark); S1 predecessor 20261124.
- **Material design**: custom SHA-256 was replaced by maintained libcrypto, disabled loading external crypto config; actual plan and context SHA256 checks passed. No hash is authority. Actual CLI only calls non-executable narrative plan renderer; inert quoting is test-only call path. Scope fixture permits exact literal roots/units/filters, never opens targets. No broker, dispatch, command executor, model loader or network client is added.
- **Evidence defect**: initial CTest suppressed counts and had no direct fuzz; fixed verbose output, gold floor, span checks, direct fuzz. Link audit initially failed `1ee6aae8` because incorrect probe location; corrected `83ef8a48`, both CI runs success.
- **Harness defects**: renderer profile filtering crashed on malformed shell list (`4c515a75`); fix type guard `83d62a78`. CLI trace preflight then rejected loader transitive dependencies; exact libz/libzstd path additions based on actual ldd, no broader file access; `9a521db3` and final `74f7998d` isolated runs success. No denied target or failed trace counted as PASS.
- **Quality limitation**: strict syntax/allowlist drastically reduce S2 coverage; not remediated by dev label fitting; track broader language coverage and human-curated gold for F1. Both raw and resolved metrics disclose false abstention. No material proposal safety finding observed in bounded tests, but finite tests do not establish safety on all inputs.
- **Review disposition**: C-01–C-10 technical evidence for the bounded synthetic walking skeleton; no blind or release quality claim. [F0-D technical review matrix](f0-d-review.md) records design vs actual and deferred items. Main remains unchanged until owner decision; F0-D/F1 HOLD, S3 BLOCKED, all 48 Debian bindings NOT VERIFIED/BLOCKED, FES NOT RUN, executor NO-GO. No training or scope expansion. LLM-ADV optional under DEC-009; not performed here.

Issue list: #23 F0-C; #16 F0-B parent; #19 S1, #20 S2, #21 S4, #22 S5; #24 native IR, #25 typed pipeline, #26 renderer/security, #27 integration. Follow-up: F0-D owner acceptance; F1 language coverage/human gold and 48-intent catalog only after GO; S3 reference disposable VM attestation only with independently authorized lab scope. No extra desktop work required for the verified CI fixtures.
