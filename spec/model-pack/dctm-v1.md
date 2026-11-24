# DCTM v1.0 — format model pack (A6)

Status: kontrak F0-A dan golden bytes sintetis; bukan loader/inference/training produksi. Baseline v3 §6.1, §6.2, §9.1. Semua integer little-endian, offsets byte berbasis nol. Baca field-by-field dari verified immutable byte snapshot, tidak cast struct C, checked bounds sebelum access/allocation. File <=128 MiB, gate bobot jalur kecil <=50.000.000 byte terpisah. Tidak menerima pickle, executable, interpreter, arbitrary graph/operator code atau policy exception.

## Prefix 32 byte

| Offset | Tipe | Nilai |
|---:|---|---|
| 0 | byte[4] | ASCII DCTM |
| 4 | u16 | major=1 |
| 6 | u16 | minor=0 |
| 8 | u32 | header_length=32 |
| 12 | u32 | section_count 4..5 |
| 16 | u64 | file_length tepat ukuran snapshot |
| 24 | u64 | section_table_offset=32 |

v1.0 tanpa extension; unknown major/minor/header/flags fail closed. Directory 32 byte per entry contiguous setelah prefix, ordered strictly ascending type. Set 1..4 wajib; 5 iff I8 tensor present. Unknown section (termasuk optional), duplicate/order/overlap/flags/reserved/padding reject; future extension butuh version review. Sebelum offset+length periksa offset <= limit dan length <= limit-offset; checked multiplication count*record_size. Setiap section nonzero length, aligned, disjoint dari header/table dan lainnya, increasing offset; gaps nol; akhir section terakhir tepat file_length.

| Entry offset | Tipe | Semantik |
|---:|---|---|
| 0 | u32 | type: 1 metadata, 2 tokenizer, 3 tensor directory, 4 weights, 5 quant |
| 4 | u32 | flags=1 required, lainnya unsupported |
| 8 | u64 | absolute offset |
| 16 | u64 | length |
| 24 | u32 | alignment 8 untuk 1,2,3,5; 64 untuk 4 |
| 28 | u32 | reserved=0 |

## Metadata type 1 (128 byte)

| Offset | Tipe | Field |
|---:|---|---|
| 0 | byte[32] | full SHA-256 weights section termasuk padding |
| 32 | byte[32] | full SHA-256 compatible catalog snapshot |
| 64,68 | u32,u32 | architecture profile ID, tokenizer kind |
| 72,76,80,84,88,92,96 | 7*u32 | vocab, context, layers, d_model, heads, FF dimension, tensor count |
| 100 | u64 | parameter count: jumlah logical elements; shared tensor tidak diduplikasi |
| 108 | u32 | flags=0 |
| 112 | byte[16] | reserved zero |

Bounds vocab 1..65536, context 1..512, layers 1..32, d_model 1..2048, heads 1..32 membagi d_model, FF 1..8192, tensors 1..4096, params 1..50.000.000. Architecture ID menunjuk trusted registry yang menetapkan exact model family, operators, normalization, activation, required tensor IDs/shapes/allowed dtype/layout, tokenizer algorithm/profile version. Unknown/missing/excess reject. 0x7fffffff synthetic-only: vocab3/context4/layers1/d_model2/heads1/FF4, id1 F32 [2,2], id2 I8 [2,2]; never release. Production profile IDs/shapes dipilih F2, loader F4; belum mengklaim M0/M1/M2. Tidak ada code atau authority dari tensor ID.

## Tokenizer type 2

u32 token_count equals vocab, u32 merge_count 0..65536. token_count records implicit IDs 0..N-1: u16 byte length 1..1024, raw token bytes (token bytes boleh NUL/invalid UTF-8, bukan wire request). Unique byte strings, checked length, total token bytes <=8 MiB, exact section coverage. merge_count records 12 byte (u32 left/right/output IDs). Tokenizer kind=1 explicit byte-token/BPE table; output > both operands, all IDs in range, unique pair/output, concatenated input bytes equal output, operands initial token atau output merge sebelumnya (no forward dependency). Order determines merge rank. Tokenizer algorithm, special tokens, normalization, segmentation dan span byte rules dipin dalam verified profile, tidak diasumsikan oleh format. Unknown kind reject; no holdout training. Manifest mengikat SHA tokenizer section exact bytes.

## Tensor directory type 3

Exactly tensor_count*64 byte records. IDs positive increasing, row-major contiguous layout=1, rank 1..4, used dims 1..16384, unused zero. Product checked multiplication <=50M, sum checked equals metadata params. Relative weight offsets aligned 64, ordered disjoint in ID order, byte_length exact product*dtype size, gaps zero, last end exact. F32 IEEE754 binary32 little-endian finite only; I8 signed two's complement; INT4 unsupported.

| Offset | Tipe | Field |
|---:|---|---|
| 0 | u32 | tensor_id |
| 4 | u16 | dtype 1 F32, 2 I8 |
| 6 | u8 | rank |
| 7 | u8 | layout=1 |
| 8 | 4*u32 | dims |
| 24 | u64 | data_offset relative weights |
| 32 | u64 | byte_length |
| 40 | i32 | quant_axis=-1 F32, 0 I8 |
| 44 | u32 | quant_group=0 F32, 1 I8 |
| 48 | u64 | quant_offset relative type5 aligned 8 |
| 56 | u32 | quant_count=0 F32, dims[0] I8 |
| 60 | u32 | reserved=0 |

F32 q_offset=0; sentinel all quant fields above. I8 symmetric per-row, q_count*8 bytes per tensor in quant section, ordered exact coverage no gaps/overlap; entry f32 scale finite >0, i32 zero_point exactly 0. I8 dequant candidate scale*q; accumulator/rounding/saturation/tie/tolerance and parity require S4/F2/F4, not structural proof.

## Detached manifest

See ADR 0003. Detached Ed25519 signature over exact UTF-8 manifest bytes, verified with trusted local key/role before parse, no reserialization, no self-referential pack hash. Manifest binds full file SHA-256+length, role, architecture/profile, tokenizer hash/version, catalog hash/version, policy hash/version, pack version, release sequence, compatibility. Two full metadata SHA-256 checked against same immutable snapshots. Unknown/wrong role, missing/mismatch/rollback/currentness -> reject. Synthetic fixture is explicitly unsigned and pinned; cannot be used in release. Golden format oracle is development-only; signature, trusted install, snapshot races, native loader and parity NOT RUN.

## Golden bytes

tests/model_pack/fixtures/dctm-v1.json contains fixed 600-byte hex pack, four expected full SHA-256 digests and 40 negative byte mutations. tests/model_pack/run.py validates synthetic profile and regenerates bytes using independent builder; no model execution or production loader. Test truncation/trailing bytes; check unsigned fixture manifest digest binding without implying signature verification. CI records SHA and Python/OS; actual architecture profile, full release manifest schema/parser, crypto library, snapshot loading and native parity deferred per baseline to F2/F4/F5.
