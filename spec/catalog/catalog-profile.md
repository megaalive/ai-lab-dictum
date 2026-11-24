# Kontrak katalog operasi v1 (F0-A / A3)

Status: spesifikasi internal, proposal-only. [Baseline v3](../../plans/baseline-v3.md), [A3](../../plans/drafts/f0-v3.md), [IR v1](../ir/schema-profile.md).

## Artefak dan authority

- `catalog/core/intents-v1.json`: registry semantik tepat 48 ID, urutan dan kelas Lampiran A; marker skeleton dari F0-C.
- `catalog/debian-13/v1.json`: profil binding Debian 13 x86-64, satu capability ID stabil per intent. Status semua binding **BLOCKED** / **NOT VERIFIED**; tidak ada executable identity, versi minimum terverifikasi, argv template, handler yang bisa dijalankan, atau grant.
- `spec/catalog/catalog-v1.schema.json`: Draft 2020-12, tiga bentuk dokumen tertutup (registry, profil, fixture) dengan discriminator implisit pada field wajib yang berbeda. Ref lokal terhadap definisi IR untuk intent, slot, typed default, dan effect. Ini schema data build/development, bukan subset codegen IR atau validator native.
- `catalog/core/effect-capability-matrix.md`: tampilan hasil join, bukan authority terpisah.
- `tests/catalog/fixtures/intent-contracts-v1.json`: satu pasangan positive/negative contract vector untuk tiap intent, bukan corpus gold atau pengujian OS.

Katalog adalah input bagi resolver/policy/compiler tepercaya yang memverifikasi snapshot dan manifest sesuai §5.1a/§9.1 baseline. Katalog, profil, policy dan context identity berasal dari authority, tidak dari model. Hash tanpa trust anchor tidak mengotentikasi penerbit. F0 menggunakan fixture kontrak; trust release belum diverifikasi. Konsumen wajib menolak schema/version/field/effect/slot/binding yang tidak dikenal, mismatch join, dan referensi di luar snapshot. Lolos lint tidak memberi izin. DCT-003 tidak mengubah schema IR, native CLI atau batas F0.

## Policy dan capability

`proposal_eligible` adalah eligibility semantik, bukan klaim proposal runtime tersedia. `execute_eligible` selalu false. Semua intent dapat tercatat sebagai cakupan proposal, tetapi capability yang BLOCKED tidak boleh menghasilkan klaim host yang pasti atau command copyable yang belum terbukti. Resolver mengembalikan clarify/unsupported/deny menurut kontrak IR saat prasyarat gagal; structured non-copyable guidance harus menyebut batasnya.

Kelas INFO/READ/CHANGE dan effect axes berasal dari kosakata IR. Efek konservatif adalah risiko operasi yang diusulkan (termasuk spawn/IPC/privilege yang mungkin dibutuhkan), bukan efek dari inference. `requires_privilege=POSSIBLE` menandai potensi hak tambahan, `NOT VERIFIED` tidak membuktikan privilege tidak diperlukan. Hak minimal dan grup belum diverifikasi; `required_groups=[]` artinya belum ada grup yang disetujui/ditetapkan, bukan bukti operasi cukup dengan hak saat ini. Jangan meminta tambahan grup, sudo, su, capability atau akses daemon. INFO tidak spawn. Koneksi socket/IPC yang dicantumkan adalah kandidat untuk penilaian, bukan allowlist akses OS; egress melalui IPC juga dilarang.

`future_execution`: PERMANENT-PROPOSAL-ONLY untuk #10–19, #41–48; #1–4 NO-EXECUTOR-NEEDED (bounded metadata/index); #5–9 dan #20–40 F5-CANDIDATE-BLOCKED. Tidak ada pembukaan F5 dari field ini. Diagnosis hanya panduan terstruktur bounded, tanpa menjalankan langkah; bila langkah menyebut DNS/ping, subproposal harus menandai NET. CHANGE memerlukan warning dampak; tidak menjanjikan reversible atau aman. NET, CHANGE, diagnosis, service/log tidak boleh diubah eligibility sepanjang MVP.

Minimum version null, status NOT VERIFIED dan capability BLOCKED wajib di fase ini. F1 harus memverifikasi paket/version/executable identity/digest, perintah/option grammar, probe native bounded, namespace/rights, data source dan compatibility per binding sebelum compiler proposal dapat menyatakan dukungan. Tidak ada fallback PATH, command spawn, jaringan, NSS lookup bebas, atau baca environment. Backend kandidat menyatakan keluarga representasi: executable-candidate, structured-candidate, native-metadata, indexed-documentation, diagnostic-guide; bukan resep. Host-equivalence `method` adalah kewajiban pengujian, result NOT RUN. Kandidat F5 wajib perbandingan visibility, projected fields, semantics dan efek terhadap oracle host lab yang setara; mismatch atau isolation gap tetap BLOCKED. Untuk permanently proposal-only, oracle hanya memeriksa semantic/policy proposal, tidak mengeksekusi target.

## Slot dan batas

`slots` memakai jenis dan typed value dari IR v1. `required` berarti nilai wajib setelah default yang sah, bukan izin mengambil nilai dari cwd. Default non-null harus bertipe sama, berada dalam rentang dan berasal dari katalog. Tidak ada default path/unit; tidak menebak target. Minimum/maximum null untuk tipe bukan integer; batas tambahan integer tidak boleh memperluas IR. `deferred_slots` adalah kebutuhan semantik yang belum terwakili tipe IR v1 (mis. domain, query literal, enum arah); tidak dikirim ke IR sebagai jenis baru, tidak di-cast ke filename, tidak membuat recipe. Intent dengan slot deferred belum siap untuk compiler; penyelesaian tipe melalui spesifikasi/versioning dan review sebelum F1, bukan perubahan diam-diam pada IR.

`at-least-one` memerlukan minimal satu slot anggota terisi; `at-least-one-explicit` membutuhkan provenance selain catalog-default. Listener menerima port atau protokol eksplisit, protokol default tcp merupakan subset awal yang harus dinyatakan pada preview; bila pengguna bermaksud semua protokol dan tidak jelas, clarify. File search memerlukan root eksplisit serta satu filter nama/ekstensi/waktu, bukan traversal bebas. Nama dan path literal tidak dinormalisasi, root bukan string grant. Resolver/validator per-intent kelak memeriksa batas semantik (unit tepat, nama literal, time window, target, tipe berkas, option semantics), konflik, provenance dan default; schema katalog bukan validator operasi. A2 fixtures adalah snapshot sintetis lebih sempit, bukan registry kedua: port wajib pada listener dan extension pada contoh file search, defaults/slots tambahan di sini belum berarti rantai tersebut sudah dijalankan ulang dengan katalog aktual.

## Scope, output dan redaction

Root types adalah kategori allowlist, bukan path atau handle aktual. Scope harus lokal, root dan field diotorisasi eksplisit oleh policy. Tidak ada recursive permission dari cwd; tidak otomatis mengizinkan /, home, /proc atau mount. Untuk metadata, allowlist field/source saja (bukan arbitrary read); untuk file/arsip, root dan target descriptor/identity harus dijaga, termasuk mount, symlink/hardlink, magic link, race, ukuran dan special file. Tidak ada overwrite; target baru untuk CHANGE. Sensitive classes (shadow, SSH keys, cloud/kube, dotenv, shell history, proc environ/mem, device nodes, DB data, browser profile dan unknown-sensitive) selalu deny, sebagai defense-in-depth. Batas kontrak timeout 5s, total output 64 KiB, maksimum 1000 entries, depth 8 dan input file 1 MiB; per-intent lebih kecil jika dinyatakan. Tidak mengklaim containment.

Output projection adalah allowlist field, bukan format hasil OS yang sudah diimplementasikan. Field yang tidak tercantum ditolak/dihilangkan sebelum output; jangan teruskan raw stdout/stderr, full cmdline, environment, credential mount options, raw journal/message atau isi arsip tak tepercaya. `file_execute_access` hanya metadata izin filesystem pada target, bukan approval execute Dictum. Redaction profile menuntut minimisasi, escaped terminal diagnostics, canary tests pada input/preview/error/audit/log/output, dan fail closed ketika projection atau sensitivitas tidak dapat dijamin; tidak menjamin semua secret dapat dideteksi. Ketidaklengkapan PID/mount/session visibility harus ditampilkan sebagai limited/unknown, bukan daftar lengkap kosong. Preview di luar containment, kontrak renderer DCT-004 terpisah.

## Provenance, hak dan fixture

ID dan batas berasal dari Lampiran A yang dipin Git blob `b3554946d62549b7417ea451294ff65b4f01a1fe`; skeleton dari F0 v3 blob `20afaa1cf4999d36de78dacf812bae2a7e512c34`. Deskripsi ID/EN, fixture dan oracle di sini adalah ringkasan kontrak asli untuk lab, bukan kutipan manpage. Manual/metadata yang disebut adalah kandidat referensi, versi/hash/lisensi belum diverifikasi dan tidak ada konten eksternal yang diimpor; S5/DCT-007 wajib ledger sumber aktual, versi/hash, atribusi, hak dan keputusan distribusi. Unknown rights tidak mengizinkan redistribusi materi pihak ketiga. Tidak menetapkan lisensi artefak atas nama pemilik.

Fixture CAT-01..48 mengikat satu intent, pasangan positive/negative dan expected outcome; bukan runnable gold/hasil host. Seluruh fixture result NOT RUN, execution_allowed=false. Lint memeriksa skema, membership, slot/default, effect, join, dan kontradiksi melalui mutasi. Tidak mengklaim C-01/C-02/C-03/C-04, S1/S3/S5, benchmark, compiler/policy/renderer native atau keamanan runtime PASS.

## Verifikasi development-only

Dari root repo, Python 3 dan python3-jsonschema/referencing (lingkungan Debian CI DCT-002):

```sh
python3 -B tests/catalog/run.py
python3 -B tests/ir/run.py
```

Oracle hanya membaca file repo dan fixture data, tidak menjalankan command target. CI mencatat SHA, versi lingkungan, expected/actual dan count; CTest native tetap regresi. Setelah A3 review terpisah; F0-A acceptance, F0-B, F1 dan executor tetap tunduk gate baseline.
