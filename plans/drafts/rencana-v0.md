# AI Lab — Trans OS: Draft Rencana v0

**Tanggal:** 24 November 2026  
**Status:** DRAFT-0 — eksplorasi, belum disetujui sebagai kontrak implementasi  
**Repositori:** [megaalive/ai-lab-trans-os](https://github.com/megaalive/ai-lab-trans-os)  
**Nama kerja:** Trans OS (penerjemah bahasa manusia ke operasi sistem operasi)  
**Keputusan saat ini:** GO untuk riset dan prototipe terisolasi; NO-GO untuk eksekusi otomatis di mesin produksi.

## 1. Latar belakang dan visi

Pengguna sistem operasi tidak semestinya harus menghafal ratusan nama utilitas, opsi, kombinasi argumen, perbedaan distribusi dan sintaks shell hanya untuk menyatakan pekerjaan yang sudah dipahaminya. Dokumentasi dan command history membantu, tetapi masih mengharuskan pengguna mengetahui kata kunci yang tepat. LLM umum dapat menerjemahkan maksud tersebut, tetapi biaya memori, latensi, ketergantungan layanan, risiko kerahasiaan, dan halusinasi kurang ideal untuk tugas lokal yang sempit.

Trans OS adalah eksperimen membangun model bahasa kecil milik sendiri yang memahami instruksi sehari-hari dalam bahasa Indonesia dan Inggris, menerjemahkannya ke representasi operasi formal, dan bila diminta membantu pengguna menjalankannya secara aman. Fokus pertama bukan percakapan umum, melainkan **natural language → OS operation**.

Visi jangka panjang: setiap orang dapat memiliki penerjemah OS pribadi, offline, ringan, bisa diaudit, dilatih ulang dan diperluas tanpa bergantung kepada penyedia AI. Ini juga menjadi instrumen pendidikan AI Lab: Explore (inspeksi mekanisme), Experiment (latih dan bandingkan), Research (uji hipotesis dan reproduksi). Model hasil training dari nol adalah keluaran riset utama; aplikasi praktis boleh memakai pendekatan non-neural atau hibrida bila bukti lebih mendukungnya.

Prinsip: manusia menyatakan maksud, model mengusulkan, katalog dan aturan menentukan operasi yang sah, manusia mengendalikan eksekusi. Sistem tidak menggantikan shell, OS, administrator, maupun dokumentasi resmi.

## 2. Pertanyaan riset dan hipotesis

- RQ1: berapa jumlah parameter minimum untuk menerjemahkan maksud ke operasi OS dengan kualitas yang berguna?
- RQ2: apakah model kecil dengan intent dan slot bertipe mengungguli generator shell bebas pada ukuran dan biaya komputasi yang sama?
- RQ3: apakah katalog eksternal mengurangi kebutuhan parameter, data, dan retraining ketika utilitas OS berubah?
- RQ4: apakah data sintetis yang tervalidasi meningkatkan generalisasi pada maksud, kombinasi argumen, bahasa dan lingkungan yang tidak terlihat saat training?
- RQ5: seberapa besar kontribusi tokenizer, copy/pointer mechanism, retrieval, constrained decoding, kuantisasi, dan konteks mesin?
- RQ6: kapan classifier klasik atau retrieval saja sudah cukup, sehingga neural model tidak memberi manfaat bersih?
- RQ7: bagaimana mengukur kemampuan menolak, bertanya klarifikasi, serta mempertahankan keamanan saat model salah dengan keyakinan tinggi?
- RQ8: dapatkah model yang sama menerjemahkan satu intent semantik menjadi operasi berbeda di Linux dan Windows tanpa mempelajari ulang semua sintaks?

H1: katalog operasi + model intent/slot kecil dapat mencapai kualitas praktis dengan jauh lebih sedikit bobot dibanding generator umum. H2: grammar mengurangi kesalahan struktur, bukan kesalahan maksud atau risiko. H3: exact match perintah tidak cukup; kesetaraan hasil di lingkungan terkontrol lebih relevan. H4: model dari nol dapat berguna pada domain sempit, tetapi tidak diasumsikan mengungguli baseline retrieval. Semua hipotesis dapat gagal; hasil negatif tetap bernilai.

## 3. Pengguna dan contoh use case

Pengguna pertama: administrator lokal, pengembang, operator lab, pelajar yang sedang mempelajari OS. Profil awal Debian 13 di VM Proxmox x86-64; Ubuntu 24.04 sebagai uji portabilitas berikutnya, Windows/PowerShell setelah fondasi terbukti. Target penggunaan lokal pada komputer biasa, bukan GPU server.

| Instruksi | Maksud | Keluaran awal |
|---|---|---|
| siapa yang menggunakan port 5432? | network.listener.lookup | daftar socket/proses; catatan akses PID mungkin terbatas |
| tampilkan lima direktori terbesar di sini | storage.directory.usage | operasi baca, batas jumlah, lokasi cwd, satuan |
| service apa yang gagal sejak boot? | service.failed.list atau log.service.query | klarifikasi jika status saat ini berbeda dari riwayat |
| tunjukkan log nginx 10 menit terakhir | log.service.query | unit, interval, limit, sumber |
| berapa RAM yang masih tersedia? | memory.summary | available, bukan sekadar free |
| cari file PDF yang diubah kemarin | file.search | rentang waktu, zona waktu, root pencarian |
| apa arti opsi ini? | help.command.explain | penjelasan bersumber pada katalog/manpage |
| kenapa PostgreSQL tidak bisa diakses? | diagnosis.connectivity | checklist baca bertahap; tidak otomatis mengubah konfigurasi |
| restart service nginx | service.restart | perubahan state; proposal saja pada MVP |
| bersihkan disk | ambiguous | tanya target dan maksud; tidak menebak penghapusan |

Use case tambahan: CPU/load, proses, paket, uptime, disk/inode, mount, permission, konektivitas, DNS, routing, journal, user/group, arsip, pencarian teks dan file, SSH, backup/restore, container, VM. Kategori mutasi, remote, kredensial, jaringan keluar, dan tindakan administratif tidak otomatis masuk MVP. Di masa depan adapter terpisah untuk Proxmox, Windows, FreeBSD, dan domain aplikasi seperti database; jangan memperluas ke asisten programming atau pengetahuan umum.

## 4. Scope dan anti-scope

MVP: satu host lokal Debian 13, locale Indonesia/Inggris, 40–60 intent baca yang didefinisikan, argument extraction, versi utilitas, penjelasan dan preview yang dapat disalin, fallback/klarifikasi, pengujian terisolasi. Eksekusi baca hanya setelah gate keamanan terpisah; pada prototipe awal default proposal-only bahkan untuk operasi baca.

Non-goal: chatbot umum, akses cloud wajib, web search saat inference, agent otonom, root otomatis, bebas menulis script Bash, self-modification, self-training diam-diam, instalasi paket otomatis, multi-host orchestration, mengganti shell, mendukung seluruh kombinasi command pada versi pertama. Tidak ada ketergantungan Python/Node/Electron saat runtime produk; Python/PyTorch diperbolehkan untuk riset/training offline. Native tidak berarti harus menulis ulang semua library atau menghindari dependensi yang kecil, stabil dan perlu.

## 5. Arsitektur: pisahkan pengetahuan, model, dan otoritas

```text
CLI / TUI (opsional)
    ↓ instruksi + konteks yang dibatasi
Normalizer / tokenizer / slot candidate extractor
    ↓
Retriever + intent router / model kecil
    ↓ intent, slot bertipe, uncertainty
Resolver + OS profile + capability catalog
    ↓ operation IR
Policy validator + deterministic compiler
    ↓ immutable execution plan / explanation / abstain
Preview + explicit approval (jika mode execute diaktifkan)
    ↓
Executor terpisah, least privilege, bounded output
    ↓
Renderer deterministik + evidence + optional diagnosis
```

Sumber kebenaran command adalah katalog terversi dan probe kemampuan OS, bukan bobot model. Katalog menyediakan nama intent, schema slot, alias, utilitas yang dibolehkan, versi/fitur minimal, tipe efek, template argv atau handler, batas input/output, contoh, sumber dokumentasi, aturan konteks, test fixture, dan fallback. Katalog merupakan data tepercaya yang ditandatangani/dipin pada release; dokumentasi yang diambil dari lingkungan, log dan output command tetap data tidak tepercaya.

### 5.1 Intermediate representation (IR)

IR adalah bahasa operasi domain, bukan shell string. Contoh konseptual:

```json
{
  "schema_version": 1,
  "intent": "network.listener.lookup",
  "slots": {"port": 5432, "protocol": "tcp"},
  "scope": "local",
  "decision": "propose"
}
```

Model tidak boleh menentukan risk level, privilege, executable, path program, izin, approval, atau policy exception. Nilai slot disalin dari input/hasil resolver yang sah bila memungkinkan, bukan ditebak atau dibangkitkan bebas. Slot dibatasi tipe (port 1–65535, enum protocol, duration, path, unit name, limit, timestamp). Input ambiguity dan slot missing menghasilkan clarify; out-of-domain menghasilkan unsupported; kandidat tak lolos validator menghasilkan deny. Tidak ada fallback ke shell bebas.

Compiler menghasilkan executable yang diizinkan dan array argumen, misalnya untuk profil Debian yang sudah diverifikasi, `/usr/bin/ss` dengan argv `["-ltnp","sport = :5432"]`. Tampilan shell di-escape hanya untuk preview; eksekusi tidak menggunakan hasil string tersebut. Lokasi executable nyata harus ditemukan dan divalidasi dari instalasi tepercaya, bukan mengasumsikan semua host identik.

### 5.2 Context dan adapter

Probe minimal: platform/versi, arsitektur, cwd yang diizinkan, shell untuk rendering, locale/timezone, UID/capability, versi utilitas, service manager, daftar fitur yang diperlukan. Context dinormalisasi ke enum/ID dan dibatasi. Jangan membaca environment lengkap, history, kredensial, file sensitif, inventory jaringan, atau secret secara implisit. Jangan mengirim context keluar mesin.

Linux adapter: argv langsung, proses dan structured output bila tersedia. Windows adapter mendatang: binding cmdlet bertipe melalui API/runspace yang dibatasi atau wrapper tetap; bukan meneruskan hasil model ke Invoke-Expression. Perbedaan object pipeline PowerShell dan text pipeline Unix harus ditangani di adapter, bukan disamarkan. WSL dianggap lingkungan berbeda dari host Windows.

Komposisi pipeline, sorting, filtering, limit, dan agregasi sederhana dilakukan oleh handler native atau operasi IR terbatas; jangan menghasilkan pipe/redirection shell sewenang-wenang. Diagnostic workflow ke depan berupa graf langkah yang ditinjau, dengan batas langkah dan persetujuan terpisah; output tidak memberi otoritas baru.

## 6. Strategi model: mulai dari nol dan ukur alternatif

Tidak mengunci Transformer sebelum baseline terbukti. Gunakan interface yang sama: input → ranked intent/slot/abstain. Dua jalur riset paralel secara konseptual, dengan urutan kerja tetap hemat:

| ID | Kandidat | Ukuran / peran |
|---|---|---|
| B0 | keyword/rules + slot parser | tanpa bobot neural; baseline fungsional |
| B1 | BM25/TF-IDF atau character n-gram retrieval | tanpa neural; ranking contoh/katalog |
| B2 | fastText/logistic/linear classifier + extractor | baseline sangat ringan |
| M0 | character/byte transformer | 0,3–0,5M; replikasi prinsip Tiny 2.1 |
| M1 | encoder kecil dengan intent head + slot head | 1M, 3M, 10M; kandidat produk |
| M2 | encoder-decoder atau decoder-only | 1M, 10M, 25M, 50M; IR constrained |
| M3 | pretrained kecil, quantized/fine-tuned | pembanding 0,5–1B; NL2Shell sebagai salah satu baseline Bash |

Ukuran target bukan jaminan konfigurasi persis. Hitung parameter nyata termasuk embedding dan head, simpan konfigurasi dan FLOPs/steps, bandingkan akurasi dan biaya end-to-end. Model 100M boleh diuji hanya bila kurva menunjukkan kebutuhan. Baseline pretrained diberi konteks/katalog yang sebanding; laporkan benchmark output bebas terpisah dari IR. Jangan mengukur keunggulan keamanan model dengan membandingkan executor yang berbeda.

Eksperimen desain: encoder 2–6 layer, lebar 64–256, attention heads yang membagi dimensi, context 128–512 token; variasikan vocab dan parameter sharing secara terkendali. Encoder bidirectional untuk klasifikasi/slot; decoder untuk komposisi IR; copy mechanism untuk path/nama service/angka, retrieval top-k untuk domain baru. Tokenizer: byte/char, unigram/BPE kecil, vocab domain dengan atomic intent/slot markers. Periksa Unicode/NFC, code-switch, typo, istilah teknis, kasus path case-sensitive. Jangan menormalisasi path secara lossy. Jangan menggunakan tokenizer yang dilatih dengan holdout.

Training from random weights adalah jalur utama. Untuk awal, PyTorch CPU sebagai reference, fixed seeds, checkpoint/resume, cross entropy intent dan slot, loss mask padding, early stopping pada dev; decoder masked loss dan grammar optional. GPU hanya akselerasi opsional, bukan persyaratan deployment. Distillation teacher untuk data atau soft labels adalah eksperimen tersendiri; catat perbedaan terhadap training murni supervised.

Ukuran teoritis bobot INT8: 1M=1 MB, 10M=10 MB, 50M=50 MB (desimal). INT4 sekitar setengahnya, belum termasuk scale, padding, metadata, tokenizer, runtime, activation dan cache. FP32 4 byte/parameter. Uji FP32→INT8 per-channel/row, INT4 hanya jika loss kualitas dapat diterima; uji kesetaraan Python/native pada golden tensor/output, numerical tolerance, input invalid, NaN, overflow dan model corrupt. Quantization-aware training adalah opsi berikutnya, bukan keharusan.

## 7. Dataset: OS-Intent Corpus

### 7.1 Sumber dan proses

Mulai dari katalog 40–60 intent dan 200–500 contoh manusia/gold yang ditinjau. Generate 10k–50k instruksi sintetis secara bertahap, bukan mengejar volume tanpa kualitas. Sumber: manpage/--help utilitas yang dipin pada versi distro, tldr-pages, NL2Bash/Tellina, NLC2CMD, contoh kerja sintetis yang ditulis sendiri. Untuk data pihak ketiga audit lisensi per sumber dan derivasi; jangan menganggap lisensi kode berlaku untuk data/model. Jika lisensi tidak jelas, jadikan referensi evaluasi terpisah tanpa redistribusi. Jangan memasukkan log nyata, data pasien, path internal, hostname, kredensial atau data pribadi ke teacher eksternal atau repo publik.

Pipeline:
1. Definisikan intent dan slot canonical beserta fixture, effect, aturan dan sumber.
2. Bangkitkan variasi parameter yang valid dan pasangan near-miss; buat paraphrase Indonesia/Inggris formal, informal, pendek, typo, campuran bahasa, istilah administrator.
3. Teacher LLM hanya membantu proposal/paraphrase; validasi schema, nilai slot, entailment semantik, provenance dan fixture. Human review untuk gold dan kasus berisiko; teacher bukan oracle akhir.
4. Deduplikasi exact/fuzzy per normalized utterance, canonical IR, template family dan semantic group. Tandai contoh ambiguity, unsupported dan unsafe.
5. Split berdasarkan kelompok sebelum augmentasi; pisahkan train/dev/test, blind human holdout, compositional holdout, OS/version holdout. Cegah varian parafrase template yang sama bocor ke test; laporkan split in-distribution intent-known dan intent/combination unseen terpisah.
6. Publikasikan manifest hash, schema, license ledger, generator version, seed, teacher ID/prompt hash, rejection reason dan audit sampel. Data holdout akhir tidak digunakan untuk tuning, pemilihan model atau kalibrasi.

Contoh record sintetis:

```json
{"id":"syn-net-0001","language":"id","text":"siapa yang listen di port 5432?","intent":"network.listener.lookup","slots":{"port":5432},"group":"listener-port-query","source":"authored","label":"supported"}
```

Skema penuh perlu span/candidate reference, versi katalog, context profile, ambiguity label, canonical fixture dan provenance. Negative set: target kosong, opsi saling bertentangan, prompt injection langsung/tidak langsung, permintaan di luar lingkup, input panjang, nilai ekstrem, karakter khusus, argumen berawalan dash, output yang menyamar sebagai instruksi, mixed intent, host berbeda, opsi utilitas tidak tersedia. Buat pasangan kontras seperti tampilkan vs hapus, sebelum vs sesudah, aktif vs gagal, lokal vs remote. Pisahkan ketidakpastian semantik dari risiko kebijakan.

### 7.2 Evolusi katalog

Gunakan schema-version, capability-id stabil, adapter version dan compatibility matrix; perubahan opsi command umumnya cukup memperbarui adapter/katalog dan test. Intent baru mungkin perlu data dan retraining, tetapi uji zero-shot retrieval dahulu. Paket katalog tambahan hanya dari sumber tepercaya dan tidak dapat menambah izin pengguna sendiri.

## 8. Runtime dan UX

Pilihan awal: C17 atau C++17/20, CMake atau Make sederhana; pilih setelah spike berdasarkan waktu build, footprint, portability, memory safety dan maintainability. C# NativeAOT adalah alternatif produk/binding, bukan keputusan awal. Python/PyTorch untuk training, export dan test oracle. Evaluasi llama2.c, llm.c dan llama.cpp sebagai referensi/benchmark; jangan menambah runtime besar tanpa pembuktian. Gunakan reference scalar CPU, kemudian SIMD/BLAS opsional jika profiling mendukung; batasi threads. Target single executable + model file + catalog pack, tanpa daemon wajib, telemetry, network, updater otomatis, framework GUI berat, Python/Node runtime.

Perintah CLI ilustratif (nama final belum dipilih):
- transos ask "siapa yang menggunakan port 8080?" — preview + arti + source.
- transos explain — jelaskan langkah yang dipilih dan batasannya.
- transos search — cari dokumentasi/katalog tanpa neural.
- transos run — opt-in, setelah gate keamanan dan persetujuan.
- transos inspect — model/catalog version, parameter count, latency, profile.
- transos lab — mode edukasi opsional, visualisasi token, logits, loss, quantization dan benchmark; tidak menambah izin eksekusi.

UX default jawaban ringkas, tampilkan perintah, tujuan, scope, sumber versi dan dampak. Clarification hanya bila material; tampilkan kandidat jika ambigu. Tidak mengandalkan confidence softmax mentah sebagai probabilitas kebenaran. Mode verbose untuk debugging; history lokal opt-in, redacted, retensi terbatas, tidak dipakai training secara otomatis. TUI, completion shell, keyboard shortcut dan voice interface (STT/TTS lokal) adalah ide lanjutan; bukan prasyarat produk. Tidak menyisipkan teks model langsung ke shell history sebagai perintah yang dijalankan.

## 9. Kontrak keamanan draft

Model dan seluruh input dianggap tidak tepercaya. Default deny, least privilege, tidak ada auto-sudo/root, akses jaringan keluar ditolak pada executor lab, tidak menjalankan shell string, eval, dynamic code, interpreter bebas, executable dari cwd/PATH tidak tepercaya, atau operasi yang belum dikatalogkan. Read-only bukan sinonim aman: membaca file sensitif, environment, output berisi secret, jaringan, symlink traversal dan scan besar tetap berisiko.

Risk classes: INFO (penjelasan tanpa eksekusi), READ (operasi lokal terbatas), CHANGE (perubahan reversible; proposal-only MVP), HIGH (privilege, destructive, remote, secret, perubahan security policy; deny execution MVP), UNKNOWN (deny). Policy ditetapkan oleh operasi dan konteks secara deterministik, bukan label model. Konten berbahaya maupun ambigu ditolak atau diklarifikasi sebelum spawn.

- Executable identity/version, argv grammar, arg type/range, per-command semantics dan efek harus diverifikasi. Argv tanpa shell mencegah sebagian injection, bukan option injection atau penyalahgunaan opsi; gunakan explicit positional binding, terminator opsi bila didukung, allowlist flags, canonical target serta per-command validator.
- Environment allowlist, fixed cwd/scope, restricted file access, no inherited sensitive descriptors, timeout, bounded stdout/stderr, cancellation dan process-tree termination. Tidak ada tool/pipeline arbitrer; log dan terminal escape sequence disanitasi. Gunakan OS-native APIs untuk operasi yang lebih aman jika tersedia.
- Approval terikat digest immutable plan (executable, argumen, scope, policy/catalog version, context, effect, expiry, session); sekali pakai, revalidate tepat sebelum eksekusi, perubahan target/privilege membatalkan persetujuan. Mitigasi TOCTOU/symlink race dengan handle atau operasi berbasis descriptor bila perlu; jika tidak dapat dijamin, deny. Approval bukan pengganti policy.
- Executor lab berjalan di VM disposable tanpa mount/share host, credential, clipboard atau bridge produksi; jaringan isolasi default. Pertimbangkan seccomp, Landlock, no_new_privs, cgroups sesuai dukungan dan uji; tidak ada satu kontrol dianggap sandbox sempurna. Proxmox management host bukan target uji eksekusi.
- Pembatasan sumber daya per request: waktu, CPU/memori, output, jumlah file, ukuran path, jumlah subprocess, depth. Error, timeout, cancellation, corruption, unsupported version, invalid signature atau policy unavailable → fail closed.
- Audit lokal minimal: operation ID, outcome, reason, digest, waktu, latency dan versi; raw input/output bukan default. Tidak ada logging secret atau telemetry. Model pack binary tervalidasi (magic, version, size, bounds, hash, provenance); tidak memuat pickle tak tepercaya saat runtime.
- Tidak mengizinkan agent loop dari stdout/stderr; diagnosis berbasis fixture atau hasil terstruktur terverifikasi. Jika analisis bebas ditambahkan, tetap suggestion-only dan tidak memberi izin.
- Seluruh bypass policy, unauthorized effect, akses di luar scope, data egress, command injection, dan persetujuan yang tidak terikat adalah release blocker. Klaim keamanan harus dibatasi pada threat model dan coverage uji, bukan jaminan universal.

## 10. Benchmark dan metode ilmiah

Bandingkan B0/B1/B2, M0/M1/M2, M3 pada corpus, fixture, context dan policy set yang sama. Laporan raw model dan end-to-end dipisah. Minimal tiga seed untuk kandidat final jika komputasi memungkinkan; laporkan variance dan confidence interval, bukan hanya hasil terbaik. Lakukan ablation terhadap retrieval, slot copying, tokenizer, constrained decoding, OS context, ukuran corpus, quantization dan model size. Rekam wall-clock training, RAM/VRAM, energi jika dapat diukur, dan estimasi FLOPs; tidak perlu membeli GPU khusus sebelum baseline.

Metrik:
- Intent macro-F1, slot exact/span F1, joint intent-slot accuracy, valid IR, semantic/execution success, coverage, selective risk, false accept/reject, OOD recall, clarification precision.
- Command exact match/charBLEU hanya pembanding literatur. Oracle utama: fixture snapshot, normalized stdout, exit status, target resource, before/after state dan side effects yang tidak diizinkan. Terima beberapa perintah ekuivalen; jangan menganggap exit code 0 berarti tugas benar.
- Safety: policy-denial correctness, malicious input/injection, unexpected mutation/network/file access, approval replay, timeout, memory abuse, parser fuzz, corrupt artifacts dan terminal injection. Uji layer individual dan integrasi.
- Usability: waktu menemukan command, jumlah interaksi, salah target, perbandingan dengan man/tldr/keyword search; blind tasks dari manusia.
- Perf: cold start, warm p50/p95 latency sampai proposal, peak RSS, disk footprint total, threads, model load time; waktu command eksekusi dilaporkan terpisah. Catat CPU, RAM, guest vCPU, OS/kernel, compiler flags dan versi utilitas.

Target hipotesis MVP (belum hasil): 40–60 intent; blind test supported joint accuracy ≥90%, end-to-end fixture success ≥90% dihitung dari seluruh supported request termasuk abstain (coverage dilaporkan sendiri); OOD/unsafe refusal recall ≥95% sebagai metrik model, policy tests wajib 100% tanpa pelanggaran yang teramati; zero observed unauthorized effects/injection pada suite. Target 50 MB bobot maksimum (jalur kecil), peak RSS ≤128 MiB, p95 warm proposal ≤500 ms dan cold ≤2 s pada VM referensi 2 vCPU/2 GiB setelah hardware diidentifikasi. Catat pemenuhan atau kegagalan, jangan mengubah threshold setelah melihat blind test; bila perlu revisi sebelum eksperimen berikut dengan holdout baru. Laporkan jumlah kasus dan interval statistik; zero observed bukan bukti zero risk.

Suite awal: ≥300 blind supported, ≥150 ambiguity/OOD, ≥200 security cases sebagai target minimum yang ditinjau manusia, serta ≥100 executable fixtures dengan variasi data dan kondisi gagal. Perluasan mengikuti temuan. Uji integrasi pada snapshot VM bersih dan versi utilitas dipin; reset fixture setiap kasus. Oracle ditulis independen dari generator data. Jangan menjalankan output model mentah pada host nyata, termasuk saat benchmark generator Bash bebas.

## 11. Roadmap bertahap dan gate

| Fase | Deliverable | Gate |
|---|---|---|
| F0 — Kontrak | charter v1, scope, threat model, schema IR, daftar intent, keputusan lisensi dan protocol benchmark | review manusia; tidak ada training/eksekusi produksi |
| F1 — Katalog & baseline | 40–60 intent baca, probe Debian, CLI proposal-only, B0/B1/B2, corpus seed | gold fixtures dan validator pass; baseline terukur |
| F2 — Mini-model | tokenizer, train dari nol M0/M1, manifest, checkpoint, inference reference | reproducible train/export, dev benchmark; pilih kandidat tanpa blind tuning |
| F3 — Comparative research | M2/M3, ablation, blind evaluation, size-quality Pareto | pilih model terkecil yang memenuhi gate kualitas atau kembali ke baseline |
| F4 — Native runtime | loader, inference parity, INT8, CLI, offline package | resource budget dan golden parity; malformed model fail closed |
| F5 — Isolated executor | immutable plan, policy, approval, VM fixtures, fuzz, fault tests | zero observed unauthorized effect; review keamanan independen |
| F6 — Daily-use pilot | local proposal-only pilot, usability, troubleshooting help, signed model/catalog release | review manusia; read-only execution opt-in hanya jika F5 lulus |
| F7 — Extension | Ubuntu, Windows/PowerShell, FreeBSD/Proxmox adapters, lab UI | gate per adapter; mutasi/remote tetap NO-GO sampai kontrak baru |

Tidak menetapkan kalender palsu sebelum spike. F0/F1 bisa dilakukan tanpa GPU. Jika model tidak memberi manfaat dibanding retrieval/rules, tetap rilis baseline yang berguna dan dokumentasikan kegagalan hipotesis; jangan menambah parameter tanpa bukti. Jika gate keamanan gagal, hentikan jalur execute tanpa menghalangi mode proposal-only. Setiap fase: issue kecil, branch terpisah, commit bahasa Indonesia, test evidence, ADR, review dan keputusan GO/NO-GO.

## 12. Struktur repositori usulan

```text
plans/
  drafts/                 # draft awal, revisi immutable
  approved/               # rencana yang disetujui
docs/
  adr/                    # keputusan dan trade-off
  security/               # threat model, policy contract
  research/               # experiment cards, benchmark report
spec/
  ir/                     # schema dan compatibility
  catalog/
catalog/
  core/
  debian/
  windows/                # tahap berikut
data/
  seeds/
  manifests/              # provenance, hashes, license ledger
  fixtures/
training/
  tokenizers/
  configs/
  scripts/
runtime/
  reference/
  native/
adapters/
  linux/
  windows/
cli/
tests/
  unit/
  golden/
  execution/
  security/
benchmarks/
  harness/
  reports/
```

Struktur belum dibuat pada v0. Data besar, weights, training logs dan fixture sensitif tidak dimasukkan ke Git biasa. Gunakan artifact release atau penyimpanan yang ditinjau, dengan hash dan manifest. CI unit/parser/golden tests CPU, benchmark VM khusus terpisah; jangan memberi CI akses host produksi. Format model sederhana terdokumentasi, versioning schema dan release model card/data card, reproducible build jika layak.

## 13. Ide eksplorasi setelah MVP

- Semantic command aliases personal tanpa retrain: user-defined vocabulary yang tidak mengubah policy.
- Model cascade: retrieval murah → classifier → decoder lebih besar hanya bila perlu; jangan menaikkan privilege saat fallback.
- Catalog-aware decoding dan pointer network untuk menghindari model menghafal opsi/path, intent composition sebagai tree.
- On-device personalization dari koreksi yang dipilih pengguna secara eksplisit; data review, export/delete, rollback, eval ulang sebelum aktivasi.
- Paket profil administrator, developer, pelajar; izin tidak bergantung pada paket vocabulary.
- Native structured result rendering dan context-aware troubleshooting, hanya evidence-backed; model tidak boleh mengarang hasil.
- Multi-OS semantic equivalence: intent sama, implementasi berbeda; semantic diff antardistribusi.
- Mode Explore untuk melihat attention/activation secara opsional (bukan penjelasan kausal), tokenizer, loss landscape sederhana, tradeoff size/accuracy, perbandingan bobot FP32/INT8.
- Lab reproducibility: train model 0,3M–1M di CPU, export dan jalankan pada VM kecil; eksperimen kelas dengan dataset sintetik tanpa akses executor.
- Kompilasi sebagian katalog menjadi decision tables/trie, memory mapping weights, lazy load, SIMD, INT4; ukur sebelum optimasi.
- Katalog command aktual yang dihasilkan dari manpage/help dengan review manusia, bukan menjadikan parser dokumentasi sebagai otoritas otomatis.
- Contextual command history yang aman, bahasa daerah lain hanya setelah corpus Indonesia/Inggris matang, voice-to-command dengan konfirmasi visual wajib.

## 14. Risiko proyek dan keputusan terbuka

| Risiko | Respons |
|---|---|
| Overfit data sintetis | grouped split, blind human holdout, near-miss, ablation |
| Model mengarang argumen | typed slots, copy, resolver, abstain |
| Model kecil tidak berguna | baseline non-neural, ukur Pareto, batasi scope |
| Versi OS/utilitas bergeser | pin catalog/version, probe, compatibility tests |
| Katalog menjadi terlalu mahal dipelihara | mulai dari intent frekuensi tinggi, schema, fixture reusable |
| Keamanan executor terlalu sulit | produk proposal-only tetap berguna; gate mandiri |
| Lisensi dataset/model tidak kompatibel | audit per artefak, clean-room corpus bila perlu |
| Benchmark tidak realistis | snapshot, variasi kondisi, oracle independen, pilot manusia |
| Scope creep menjadi agent umum | non-goal eksplisit, adapter dan fase terpisah |
| Mesin training terbatas | model kecil, fixed compute budget, profiling CPU, GPU opsional |

Keputusan yang masih perlu review pada v1: nama executable; bahasa runtime; lisensi proyek/data/model terpisah; daftar intent prioritas; definisi oracle; hardware referensi dan budget compute; ukuran/model architecture pertama; format IR/model pack; apakah catalog license memungkinkan distribusi; metode sandbox; apakah produk awal hanya preview. Jangan memutuskan berdasarkan popularitas repositori.

## 15. Referensi inspirasi (ditelusuri 24 November 2026)

Referensi di bawah ditinjau melalui halaman proyek, README atau abstrak publik; belum direproduksi atau diaudit kode secara penuh. Klaim pengembang bukan hasil benchmark Trans OS. Pin commit/release, verifikasi lisensi dan reproduksi pada F0/F1.

| ID | Referensi | Ide yang diambil dan batasnya |
|---|---|---|
| R01 | [WollyMonjac/Tiny-2.1](https://github.com/WollyMonjac/Tiny-2.1) | README melaporkan transformer 367k parameter, empat layer/lebar 96, character-level, bobot INT8 380 KB, RAM DOS sekitar 540 KB dan training kit. Bukti inspirasi footprint; README mengakui halusinasi di luar data. Periksa DATA_LICENSES terpisah dari MIT kode. |
| R02 | [TinyStories — Eldan & Li, 2023](https://arxiv.org/abs/2305.07759) | Corpus sintetis terkontrol untuk meneliti model bahasa sangat kecil. Terapkan gagasan domain sempit, bukan menganggap hasil cerita berlaku pada shell. |
| R03 | [karpathy/llama2.c](https://github.com/karpathy/llama2.c) | Reference inference C dan training Python; kandidat pembelajaran export, tokenizer dan forward pass. |
| R04 | [karpathy/llm.c](https://github.com/karpathy/llm.c) | Training C/CUDA sebagai referensi eksperimen native; bukan kewajiban menulis trainer sendiri. |
| R05 | [NL2Bash, LREC 2018](https://lrec.elra.info/lrec2018-main-491) dan [TellinaTool/nl2bash](https://github.com/TellinaTool/nl2bash) | Corpus sekitar 10k pasangan bahasa alami/Bash serta semantic parsing. Audit lisensi, split dan batas distro; bukan dataset siap eksekusi tanpa review. |
| R06 | [NLC2CMD Competition, NeurIPS 2020/PMLR 2021](https://proceedings.mlr.press/v133/agarwal21b.html) | Benchmark natural language-to-Bash; contoh metrik dan baseline. Jangan menyamakan similarity dengan correctness. |
| R07 | [NL2CMD updated workflow](https://arxiv.org/abs/2302.07845) | Referensi perkembangan pipeline semantic translation. |
| R08 | [LLM-Supported Natural Language to Bash Translation, NAACL 2025](https://aclanthology.org/2025.naacl-long.555/) | Pentingnya kualitas dataset dan evaluasi eksekusi. |
| R09 | [IBM/nl2bash-eabench](https://github.com/IBM/nl2bash-eabench) | Inspirasi execution-based benchmark; fixture dan oracle lokal tetap harus dibuat sendiri. |
| R10 | [NL2Shell](https://github.com/nl2shell/nl2shell) dan [Vox](https://github.com/nl2shell/vox/) | Proyek menerapkan model Qwen3.5-0.8B yang di-fine-tune untuk shell dan antarmuka terminal. Pembanding pretrained, bukan target footprint dari nol. |
| R11 | [Bag of Tricks for Efficient Text Classification, EACL 2017](https://aclanthology.org/E17-2068/) | fastText sebagai pembanding classifier ringan. |
| R12 | [PICARD, EMNLP 2021](https://aclanthology.org/2021.emnlp-main.779/) | Incremental parsing untuk constrained decoding dalam text-to-SQL; adaptasi ide ke IR, bukan bukti keamanan shell. |
| R13 | [llama.cpp GBNF](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md) | Grammar decoding; struktur sah tidak menjamin maksud atau efek benar. |
| R14 | [tldr-pages](https://github.com/tldr-pages/tldr) dan [client specification](https://github.com/tldr-pages/tldr/blob/main/CLIENT-SPECIFICATION.md) | Contoh ringkas lintas OS, pembagian platform; sumber ide katalog dan baseline retrieval, perlu atribusi sesuai lisensi. |
| R15 | [ShellCheck manual](https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md) dan [bash-language-server](https://github.com/bash-lsp/bash-language-server) | Analisis shell, parser dan dokumentasi sebagai inspirasi validator/explain. Linter tidak menjamin safety. |
| R16 | [PowerShell Get-Command](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/get-command?view=powershell-7.5) dan [about_Parsing](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing?view=powershell-7.5) | Discovery metadata dan perbedaan parsing untuk adapter Windows; pin versi aktual. |
| R17 | [Linux setpriv(1)](https://www.man7.org/linux/man-pages/man1/setpriv.1.html) dan [PR_SET_NO_NEW_PRIVS](https://man7.org/linux/man-pages/man2/PR_SET_NO_NEW_PRIVS.2const.html) | Primitif pembatasan privilege yang perlu dipadukan dengan isolasi; bukan sandbox lengkap. |
| R18 | [OWASP Prompt Injection](https://genai.owasp.org/llm2026/llm012026-prompt-injection/), [Improper Output Handling](https://genai.owasp.org/llm2026/llm102026-improper-output-handling/), [Excessive Agency (2025)](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) | Perlakukan output model sebagai untrusted, batasi agency dan privilege, uji adversarial. |
| R19 | [Local LLMs for NL2Bash — NDSS](https://www.ndss-symposium.org/ndss-paper/auto-draft-683/) | Evaluasi model lokal 1B–32B sebagai referensi pembanding skala lebih besar, bukan target deployment. |

Sumber kebenaran lokal pada implementasi: dokumentasi man/--help versi terpasang, metadata paket dan hasil capability probe yang dibatasi. Jangan mengunduh dokumentasi pada runtime default.

## 16. Tindakan pertama setelah review draft

1. Setujui kontrak scope Debian read-only/proposal-only dan definisi intent/slot/abstain.
2. Buat daftar 40–60 intent prioritas dan minimal 200 gold utterance sebelum memilih model.
3. Definisikan IR dan katalog v1, fixture oracle dan split protocol; audit lisensi.
4. Implementasikan baseline retrieval/rules, ukur kualitas dan footprint.
5. Baru jalankan training model 0,3M dan 1M dari bobot acak; bandingkan dengan baseline dan tentukan apakah perlu skala 10M.
6. Native runtime setelah model terbukti; executor setelah kontrak keamanan dan review tersendiri.

**Kriteria keberhasilan tertinggi bukan banyaknya command yang dihafal model, melainkan pengguna dapat menyatakan maksudnya dengan bahasa biasa dan memperoleh operasi OS yang tepat, dapat dijelaskan, ringan, lokal, dan terkendali.**
