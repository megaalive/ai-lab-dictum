# ADR 0003 — Trust artefak dan snapshot terverifikasi

Status: desain F0-A; release verification F4/F5 DEFERRED-BLOCKED. Baseline §9.1 dan DCTM v1. Checksum, path root-owned atau filename bukan authentication.

## Anchor dan manifest

Trusted installer provisions pinned Ed25519 public keys and role mapping (release model/catalog/policy; separate development fixture role). Do not accept key from artifact/model/repository payload. Trusted key ID chosen outside unverified manifest; detached signature 64 bytes, verify exact manifest bytes with reviewed crypto library, no custom crypto, then strict UTF-8 bounded parser: one closed object, duplicate keys/NUL/nonfinite/unknown/trailing bytes rejected, <=32KiB. Manifest v1 exact fields: schema_version=1; role; publisher_key_id; monotonic release_sequence within role+product; model_version; pack {sha256,length,major,minor}; architecture {id,profile_version}; tokenizer {sha256,kind,version}; catalog {sha256,version}; policy {sha256,version}; compatibility {platform,arch,runtime_min,runtime_max}. Digest 64 lowercase hex, lengths positive bounded, versions typed; exact closed schema/parser and version comparison registry before F4 release. Verify full SHA/length of required artifacts and role/key/compatibility/currentness from trusted install, no reserialization before signature. Signature does not prove semantic correctness. Unsigned synthetic lab manifest/hash pinned by separate harness; never fallback from failed release signature to dev.

## Same verified bytes

Read exact bounded expected length into private owned memory or sealed memfd; reject truncation/extra, verify digest/signature binding and only parse/use that snapshot. Same FD without immutable backing insufficient; check F_SEAL_WRITE/GROW/SHRINK and prevent writable mappings before trust. No path reopen, mmap/lazy only from immutable snapshot proved; aggregate snapshot/RSS measured, deny if budget violated. Pack/catalog/tokenizer/policy cross-check, unknown profile/tensor/dtype/version reject. Test replace/rename/truncate/in-place write, wrong key/role, duplicate/malformed manifest, mismatches, sealed FD and mapping races at F4.

## Currentness

Trusted installer/authority holds monotonic per-role accepted release sequence + policy minimum/key state, outside Front write access; durable atomic install after verification, equal sequence only exact same digest, lower reject, missing/corrupt state deny. Explicit reviewed recovery/reset separate authority and audit. Offline revocation only as current as trusted installed state. Privileged host/VM restore may roll back artifact and state together; without external monotonic anchor no protection proof. Detected restore disables authority until trusted reset; separate lab keys. No real-time revocation guarantee or execution opening. F4 signature/loader/seal/race/rollback/parity NOT RUN; F5 remains NO-GO. Golden checks structure/digest only, not authentication.
