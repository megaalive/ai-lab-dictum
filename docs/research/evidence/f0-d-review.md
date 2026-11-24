# F0-D — integrated technical review matrix (candidate)

24 November 2026 · reviewer **SELF** (GPT-6.2 implementer/technical lead) · owner decision **PENDING**. Review of F01–F12 and A-01–A-19 as required by [F0 v3 §5](../../../plans/drafts/f0-v3.md) and [DEC-009](../../../plans/baseline-v3.md). No separate model reviewer required; no EXT or independent gold claim. This is a technical candidate for owner acceptance, not a GO decision or an authorization to merge/start F1.

## Evidence references (immutable tested sources, not evidence-addendum SHAs)

| Key | Artifact / exact source | Actual method and result |
|---|---|---|
| C | [F0-C integration evidence](f0-c.md), code `74f7998d8077328f6fd333686db2a1957985b454`, tree `f4a145a3e6196430fcf17e7e64baf733244fd7a2` | 4 strict native configs 20/20 each, 420 differential, 104 span, 61 digest, 25k fuzz; functional B0 140/140, C05 113/113 and 16 inert round-trips, C06/C07 150 traces; B1 and S2 misses retained. [Raw](f0-c-results-v1.json). |
| A2 | [IR oracle](dct-002.md) `69c7b73c9d03d316d5063f2d1ac8c1fa393b4e2c` | 196/196 Python fixtures; native/digest added in C. |
| A3 | [Catalog revision](dct-003.md) `da84ace9f7e7e828042926c2219aedc075e42473` | 106/106 checks and axis/deferred-domain subprobes; all 48 bindings BLOCKED, compatibility NOT VERIFIED. |
| A4 | [Renderer contract](dct-004.md) `430e2ee95e9805f7ee806fc3d1597559191fefa3` | 113/113 data-only; integration in C. |
| A5 | [Authority/lab contract](dct-005.md) `e6bb6196f4eac88456a929289278335bbb0bb9a7` | 24/24 data-only preflight cases; actual broker and VM containment NOT RUN. |
| A6 | [Model pack/trust](dct-006.md) `29d4df72a99303039759c45a8aa14fa816b06e3f` | 45/45 binary + 41/41 manifest, unsigned synthetic dev fixture; release trust NOT RUN. |
| A7 | [Corpus/metric contract](dct-007.md) `1745823b52328d97368872119c982e92fb10b2e3` | 52/52 metric/data-only tests; human gold/blind/FES NOT RUN. |
| S1 | [Inert shell oracle](s1.md) `c63a04045fcef8c9ef99ceaa8e15c4e0aedaf228` | 10k generated/profile, 7k accepted + 3k rejected + 8 fixed, no mismatch; C native gold integration separate. |
| S2 | [Development prototypes](s2.md) `3b54a95ed094aad9ec7b8740761d24b2f9f7220b` | B0 78/80, B1 73/80 supported; all errors retained; C replay substantially lower coverage. |
| S4 | [Tiny numeric parity](s4.md) `b08c870860f452a7cdb42263110e179939cd39ec` | 50/50 per compiler, exact synthetic intermediates, shape count 1,342,917. No full model. |
| S5 | [Rights/source audit](s5.md) `05902bafc79be48a9d784a43ab40d50fbbb5b942` | 7 pinned Debian docs HOLD-PER-FILE-RIGHTS, external exclusions maintained; distribution not authorized. |
| G | [Governance #17](https://github.com/megaalive/ai-lab-dictum/issues/17), tested docs `d2c886d849572d20d898ac425bbbd25c403df358`; [checkpoint #16](https://github.com/megaalive/ai-lab-dictum/issues/16) | DEC-009 supersedes different-model requirement; original normative v3 blobs unchanged; checkpoint closed, S3 BLOCKED. |

Status semantics: VERIFIED is restricted to the named phase/method; DESIGN-ADDRESSED means contract only, not passed implementation; DEFERRED-BLOCKED means later implementation/attestation unavailable or unauthorized. All rows reviewed SELF. Owner field PENDING for the F0-D decision; later gates require their own authorization. Existing valid evidence referenced, not rerun or counted as independent cases.

## F01–F12

| ID / phase | Status | Artifact / actual | Limit and next action | Owner |
|---|---|---|---|---|
| F01 F0/F4 | DESIGN-ADDRESSED | A6 DCTM explicit 32-byte prefix, binary bounds and manifest oracle 86/86 | Native loader and release pack verification F4 NOT RUN. | PENDING |
| F02 F5 | DEFERRED-BLOCKED | A3/A5 descriptor/openat2 contract; C exact synthetic root allowlist and no target access | Actual race/symlink/mount identity and descriptor enforcement F5; S3 unavailable. | PENDING |
| F03 F0/F1+ | VERIFIED | A7 metric oracle full denominator; C raw/resolved JIA, JS, coverage, selective risk/accuracy and miss list | No blind quality gate; future grouped/human gold. | PENDING |
| F04 F0/F5 | VERIFIED (proposal) | A3 effect axes; C 150 traced launches, no network attempts | Egress/IPC proxy/host visibility during execution F5 DEFERRED-BLOCKED. | PENDING |
| F05 F5 | DEFERRED-BLOCKED | A5 lab/authority contract, C no filesystem target reads; S3 BLOCKED | Actual per-operation confinement, helper privilege and kernel compatibility NOT RUN. | PENDING |
| F06 F0-C | VERIFIED | A2 four contracts, C generated subset validator differential 420, actual digest/context checks | Restricted v1 profile, no externally serialized plan authority. | PENDING |
| F07 F0-B/F2/F4 | VERIFIED (tiny parity) | S4 50/50, exact intermediates and separate INT8/FP32 | Real model parity and quality-loss comparison NOT RUN. | PENDING |
| F08 F5 | DEFERRED-BLOCKED | A5 bounded pipe/deadline/cgroup requirements; isolated inert lab bounded IO | Actual executor flood/orphan/cgroup tests F5, S3 BLOCKED. | PENDING |
| F09 F0/F4/F5 | DESIGN-ADDRESSED | A6 exact-byte detached manifest/trust anchor design; C SHA identity/digest | Signature, rollback, verified snapshot and trusted release enforcement NOT RUN; hash is not approval. | PENDING |
| F10 F0/F1+ | DESIGN-ADDRESSED | A7 independent oracle/gold/split protocol; C independent code oracle but SELF-authored gold | Actual human review, entailment/holdout and CHANGE/NET gold required for future corpus/release; no human gold claim. | PENDING |
| F11 F0-B/F2 | VERIFIED (shape count) | S4 config card, 1,342,917 parameters by shape arithmetic | No instantiated weights, actual model/training budget decision F2. | PENDING |
| F12 F0 | VERIFIED (contract lint) | G pinned normative blobs, A3 48 canonical IDs and exact fixture/contract drift checks | Historical drafts retained; no claim general document lint or phase acceptance. | PENDING |

## A-01–A-19

| ID / phase | Status | Artifact / actual | Limit and next action | Owner |
|---|---|---|---|---|
| A-01 F0-C | VERIFIED | A4, S1, C native 113/113 + 16 golden real Bash/dash inert argv | Product all NON_COPYABLE; no utility binding or other shell trust. Actual executable previews later require verified recipes. | PENDING |
| A-02 F0/F5 | DESIGN-ADDRESSED | A5 [broker approval ADR](../../adr/0002-broker-approval.md), threat/IPC trust; C no broker/executor path | Approval UI/IPC adversarial/replay FD checks F5 DEFERRED-BLOCKED. | PENDING |
| A-03 F0 | VERIFIED (governance) | G DEC-009, SELF source/evidence review; labels separate | LLM-ADV optional; human gold and EXT release executor review not waived. | PENDING |
| A-04 F5 | DEFERRED-BLOCKED | A3 service/log/network semantics, A5 confinement; #16 S3 BLOCKED | Host-equivalence and per-intent isolation not observed. | PENDING |
| A-05 F0/F4 | DESIGN-ADDRESSED | A6 snapshot/exact-byte signature/rollback contract | Native artifact verification/use race and release trust F4/F5 NOT RUN. | PENDING |
| A-06 F0 | VERIFIED (metric contract) | A7 52/52; C full counts and limitations | Actual preregistered blind intervals/quality gates NOT RUN. | PENDING |
| A-07 F0-C/F1/F5 | VERIFIED (proposal scope) | A3 scope/projection contract, C 60 security cases per model, canary/escape traces | No real data read/projection/descriptor safety claim; F1 catalog and F5 host enforcement pending. | PENDING |
| A-08 F0-C | VERIFIED (skeleton) | A3 effect/privilege/eligibility lint; C READ/CHANGE metadata, CHANGE warning, execute forbidden | Wider catalog/policy compiler and actual privilege checks later. | PENDING |
| A-09 F0-C | VERIFIED | C actual CLI includes memory/info, search/inspect/explain/run with no subsequent exec/network | No actual utility/docs probe, no observed OS data. | PENDING |
| A-10 F0-B/F5 | DEFERRED-BLOCKED | A5 preflight contract; #16 S3 BLOCKED | Requires independent disposable Debian reference VM lab evidence; no substitution by GitHub container. | PENDING |
| A-11 F0-C | VERIFIED | A2 + C native codegen and strict byte/schema differential, actual SHA/JCS | Closed subset, not generic schema/JCS implementation. | PENDING |
| A-12 F0/F1 | DESIGN-ADDRESSED | A7 grouped split/provenance/prereg; S2/C synthetic diagnostics | Actual corpus grouping/holdout/human review in F1+, no contamination-free claim for dev. | PENDING |
| A-13 F0-B/F1+ | VERIFIED (exclusion decision) | S5 audit; C no external source data imported | Rights unknown stays HOLD, owner license/distribution decision still PENDING; no assumed rights. | PENDING |
| A-14 F0/F5 | DESIGN-ADDRESSED | A5 isolation contract, S1/C actual inert fixture and no-network trace | Actual executable fixture harness/host equivalence FES NOT RUN; S3 BLOCKED. | PENDING |
| A-15 F0-B/F2 | VERIFIED (config) | S4 shape count and memory lower bound, no instantiated model | F2 actual model architecture/compute/size decision later. | PENDING |
| A-16 F0 | VERIFIED (scoped lint) | G normative identity; A3 exact IDs/enums/contract drift | No claim unrelated docs lint; retain original histories. | PENDING |
| A-17 F0 | DESIGN-ADDRESSED | G and rencana-v3 updated OWASP reference disposition | Documented version choice only; no new external standards audit. | PENDING |
| A-18 F0/F5 | DESIGN-ADDRESSED | A2/A5 lifetime/session TTL/boottime/approval contracts; C synthetic UTC snapshot | C not persistent approval; actual boot-time/replay/session invalidation F5 NOT RUN. | PENDING |
| A-19 F0-C | VERIFIED (walking skeleton) | #16, S1/S2/S4/S5 and C; eight intents, scoped end-to-end functional evidence | Substantial S2 coverage loss, F1 generalization and human curated labels required; S3 deferred. | PENDING |

## Decision packet and remaining issues

- Technical C-01–C-10 evidence is present in [#27](https://github.com/megaalive/ai-lab-dictum/pull/27) at the bounded synthetic scope, subject to owner decision. C-02 independence limited to separate SELF labels; C-09 is a measured **negative** coverage finding on broader S2 (B0 12/80; B1 11/80), not a quality gate pass. Recommendation: keep B0 primary and B1 experimental; do not claim practical general-language quality. F1 should prioritize wider compositional grammar/retrieval and independently curated gold over neural training. No further fitting on the same S2 diagnostic labels.
- Proposal material findings from reviewed scope: crypto dependency and CI/harness failures remediated with exact source evidence; no observed unauthorized proposal-side effects in bounded tests. Unknown/excluded source rights unchanged; owner must accept protocol and scope and decide licensing/distribution before release. Human gold and preregistered holdout must precede any applicable quality gate.
- S3/containment/host-equivalence remains **DEFERRED-BLOCKED**, no local VM access or authorization established by CI. If owner chooses to pursue it, Codex desktop must use a genuinely disposable Debian 13 reference VM and independently authorized scope with [lab preflight](../../../spec/security/lab-harness-v1.md). Stop on failed preflight; no host or production probes. S3 is not a blocker to proposal research.
- **Owner decision pending: HOLD F0-D/F1**, no merge/phase acceptance inferred. Owner may accept the bounded contract and F0 evidence or require coverage remediation; scope approval and data/protocol decisions must be explicit. No F1 implementation, training, FES or executor authorization in this PR. All 48 real profile bindings remain blocked; executor NO-GO; F5 EXT mandatory.
