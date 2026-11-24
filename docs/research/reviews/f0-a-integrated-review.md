# F0-A — paket audit terintegrasi

Status: kandidat kontrak untuk satu kali audit menyeluruh. Tidak mengubah baseline v3/DEC-003, tidak mengotorisasi F0-B, F1, training, atau executor.

Base main (DCT-003 sudah diterima issue-level): `0ed0b5a378afa4d32ea51c8222d2908ca42f57c5`.

| Paket | Draft PR | Head immutable (evidence included) | CI kontrak |
|---|---|---|---|
| DCT-004 | [#12](https://github.com/megaalive/ai-lab-dictum/pull/12) | `72787e7e1f14fece278ecd4e11a0a151326a553d` | 85/85 PASS |
| DCT-005 | [#13](https://github.com/megaalive/ai-lab-dictum/pull/13) | `7a15f23c6216ae78948893fb726a5de778cc4d02` | 14/14 PASS |
| DCT-006 | [#14](https://github.com/megaalive/ai-lab-dictum/pull/14) | `e71bce40055268dede034853d1c784db87ece2ef` | 45/45 PASS |
| DCT-007 | [#15](https://github.com/megaalive/ai-lab-dictum/pull/15) | `9336cb59bfa62c55a12cb6490844c6bc030e3078` | 30/30 PASS |

Snapshot menyatukan blob tambahan asli dari keempat PR tanpa mengubah blob baseline dan tanpa collision. Review SELF implementer: fixture development-only PASS; jangan menganggap hasil ini sebagai pengesahan sistem atau LLM-ADV. Lihat `docs/research/evidence/dct-003.md` sampai `dct-007.md`.

## Satu audit F0-A

Auditor model berbeda (LLM-ADV), baca sumber sebenarnya di snapshot ini, bukan hanya evidence. Catat model, prompt, commit SHA, scope yang berhasil dibaca, expected vs actual, severity serta reproduksi. Periksa:
- A1/A2: intent boundary, IR schema dan strict unknown fields, slot typing/provenance, canonical scope, fail-closed.
- A3: 48 ID, 8 skeleton, surface/rights/effects, exact join/allowlist, 48 blocked/no execute, narasi tanpa child action; F-01–F-08 remediasi sebelumnya; bedakan audit eksternal parsial dari audit menyeluruh.
- A4: byte-preserving quoting Bash/dash, non-copyable gates, operand semantics/leading dash, invalid UTF-8, C0/C1, format/bidi, terminal/canary; S1 >=10.000 generated cases per shell masih NOT RUN.
- A5: boundaries TCB, separate consent vs peer identity, IPC/FD/replay, strict no executor, synthetic checklist tidak membuktikan attestation, S3 BLOCKED.
- A6: exact prefix/sections/tensor/quant byte layout, arithmetic/overlap/hash, trusted manifest/snapshot/rollback, dev vs release; synthetic only, F4 verification deferred.
- A7: rights/derivation, grouped splits/holdout access, metric denominators and counterexamples, prereg thresholds/CI methods, resource budget; no benchmark/training claim.
- Cross-contract: consistency baseline, scope/effects/unknown rights, no implied capability, no weakened gates. Compare with issue acceptance criteria. Report REQUEST CHANGES only for actual unresolved material issues; list deferred proof obligations separately. Do not execute target utilities or conduct spikes; no secret/production data.

## Handoff setelah owner menerima F0-A

GitHub-capable: S1 inert argv-dumper dan shell byte oracle sesuai kontrak, S2 rule/retrieval dev baseline, S5 source rights audit (pin sources, exclude unknown). Codex desktop only when actual local disposable Proxmox Trixie VM/isolation or numerical profiling needed (S3, S4 where local reference required); preflight evidence mandatory, no production host execution. Gate DEC-003 requires integrated SELF + LLM-ADV and owner bounded scope before spikes. Current S3 BLOCKED/NOT RUN, S1/S2/S4/S5 NOT RUN. No training, no product executor.
