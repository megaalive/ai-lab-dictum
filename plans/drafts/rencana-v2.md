# AI Lab — Dictum: Rencana Proyek dan Usulan Kontrak Implementasi v2

**Tanggal:** 24 November 2026  
**Status:** DRAFT-2 — kandidat kontrak F0–F1, menunggu persetujuan eksplisit pemilik proyek. Bukan APPROVED; tidak mengotorisasi implementasi.  
**Repositori:** [megaalive/ai-lab-dictum](https://github.com/megaalive/ai-lab-dictum)  
**Nama proyek:** Dictum (penerjemah bahasa manusia ke operasi sistem operasi)  
**Keputusan usulan:** GO untuk finalisasi kontrak F0 setelah persetujuan pemilik; HOLD F1 sampai gate F0; NO-GO eksekusi otomatis dan deployment produksi. Dokumen ini merevisi v0 dan review v1, tidak mengklaim bahwa kontrol atau benchmark telah diimplementasikan.

## 0. Rekonsiliasi v0, review v1, dan audit v2

V0 adalah baseline visi dan metode riset; v1 adalah masukan reviewer, bukan persetujuan pemilik. V2 mempertahankan 48 intent, C17, CMake, Debian 13 (Trixie), komposisi bahasa awal 70% ID/30% EN, dan proposal-only; sekaligus memulihkan eksplorasi, eksperimen kontrol, sumber referensi, serta gate yang hilang. Keputusan di bawah mengikat hanya setelah pemilik menyetujui dokumen dan spesifikasi turunannya. Status "ditangani dalam rancangan" tidak sama dengan PASS pengujian.

| Audit | Resolusi v2 | Bukti yang wajib dibuat |
|---|---|---|
| F01 HIGH — header DCTM tidak muat | Format berpanjang eksplisit, tabel section/tensor, dua hash utuh | SPEC-PACK, golden pack, malformed pack tests |
| F02 HIGH — TOCTOU | openat2, operasi berbasis descriptor, deny jika identitas tak terjaga | Race/symlink/mount tests |
| F03 HIGH — denominator bias | Seluruh supported requests; selective risk/coverage terpisah | Metric oracle dan counterexample 10/100 |
| F04 HIGH — jaringan | Efek NET terpisah dari mutasi; DNS/ping proposal-only | Egress tests termasuk IPC proxy |
| F05 HIGH — filesystem | Confinement OS per operasi, executor terpisah | Outside-root/secret tests, kernel compatibility |
| F06 MEDIUM — bukan JSON Schema | Empat kontrak terpisah; schema nyata menjadi F0 gate | Schema files dan negative corpus |
| F07 MEDIUM — INT8 | Pisahkan parity implementasi dan quality loss | Golden tensors dan dev comparison |
| F08 MEDIUM — output/proses | Bounded pipe reader, containment cgroup, hard deadline | Flood/orphan/timeout tests |
| F09 MEDIUM — hash/signature | Trust anchor dan signed manifest terpisah dari checksum | Tamper/wrong-key/rollback tests |
| F10 MEDIUM — semantik data | Human gold, entailment, contrasts, oracle independen | Audit sampel dan data manifest |
| F11 MEDIUM — jumlah parameter | M1 kandidat, hitung parameter aktual; tokenizer sweep | Config cards, count actual, budget |
| F12 LOW — inkonsistensi | 48 total, Debian Trixie, path tunggal, tanpa LaTeX rusak atau klaim latensi palsu, status DRAFT | Document lint, owner approval |

Tidak ada temuan keamanan yang dinyatakan tertutup secara implementasi. F0 harus mengubah resolusi ini menjadi kontrak yang bisa diuji; F5 membuktikannya untuk executor. Jangan menghapus atau menimpa v0 dan review v1.

## 1. Latar belakang dan visi

Pengguna sistem operasi tidak semestinya harus menghafal ratusan nama utilitas, opsi, kombinasi argumen, perbedaan distribusi dan sintaks shell hanya untuk menyatakan pekerjaan yang sudah dipahaminya. Dokumentasi dan command history membantu, tetapi masih mengharuskan pengguna mengetahui kata kunci yang tepat. LLM umum dapat menerjemahkan maksud tersebut, tetapi biaya memori, latensi, ketergantungan layanan, risiko kerahasiaan, dan halusinasi kurang ideal untuk tugas lokal yang sempit.

Dictum adalah eksperimen membangun model bahasa kecil milik sendiri yang memahami instruksi sehari-hari dalam bahasa Indonesia dan Inggris, menerjemahkannya ke representasi operasi formal, dan bila diminta membantu pengguna menjalankannya secara aman. Fokus pertama bukan percakapan umum, melainkan **natural language → OS operation**.

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
| service apa yang gagal sejak boot? | service.failed.list (status sekarang); riwayat sejak boot perlu klarifikasi atau intent log yang sesuai | klarifikasi jika status saat ini berbeda dari riwayat |
| tunjukkan log nginx 10 menit terakhir | log.service.query | unit, interval, limit, sumber |
| berapa RAM yang masih tersedia? | memory.summary | available, bukan sekadar free |
| cari file PDF yang diubah kemarin | file.search | rentang waktu, zona waktu, root pencarian |
| apa arti opsi ini? | help.command.explain | penjelasan bersumber pada katalog/manpage |
| kenapa PostgreSQL tidak bisa diakses? | diagnosis.connectivity | checklist baca bertahap; tidak otomatis mengubah konfigurasi |
| restart service nginx | service.restart | perubahan state; proposal saja pada MVP |
| bersihkan disk | ambiguous | tanya target dan maksud; tidak menebak penghapusan |

Use case tambahan: CPU/load, proses, paket, uptime, disk/inode, mount, permission, konektivitas, DNS, routing, journal, user/group, arsip, pencarian teks dan file. SSH, backup/restore, container dan VM merupakan kandidat ekstensi di luar 48 intent awal. Kategori mutasi, remote, kredensial, jaringan keluar, dan tindakan administratif tidak otomatis masuk MVP. Di masa depan adapter terpisah untuk Proxmox, Windows, FreeBSD, dan domain aplikasi seperti database; jangan memperluas ke asisten programming atau pengetahuan umum.

## 4. Scope dan anti-scope

MVP: satu host lokal Debian 13 (Trixie) x86-64, VM Proxmox 2 vCPU/2 GiB RAM, locale Indonesia/Inggris, tepat 48 intent sesuai Lampiran A (44 INFO/READ dan 4 CHANGE). Dua intent READ berefek NET dan empat CHANGE selalu proposal-only; diagnosis juga berupa panduan proposal-only pada MVP. Argument extraction, versi utilitas, penjelasan dan preview yang dapat disalin, fallback/klarifikasi, pengujian terisolasi. Eksekusi baca hanya setelah gate keamanan terpisah; pada prototipe awal default proposal-only bahkan untuk operasi baca.

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

Sumber kebenaran command adalah katalog terversi dan probe kemampuan OS, bukan bobot model. Katalog menyediakan nama intent, schema slot, alias, utilitas yang dibolehkan, versi/fitur minimal, tipe efek, template argv atau handler, batas input/output, contoh, sumber dokumentasi, aturan konteks, test fixture, dan fallback. Katalog hanya dipercaya setelah verifikasi signed manifest terhadap trust anchor lokal; pinned hash saja bukan autentikasi penerbit. Dalam lab, fixture hash dipin secara eksplisit dan tidak boleh membuka executor produksi; dokumentasi yang diambil dari lingkungan, log dan output command tetap data tidak tepercaya.

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

### 5.1a Batas kepercayaan dan spesifikasi formal F0

Empat dokumen JSON Schema Draft 2020-12 terpisah wajib diwujudkan pada F0: `spec/ir/nlu-proposal-v1.schema.json`, `resolved-ir-v1.schema.json`, `policy-decision-v1.schema.json`, dan `execution-plan-v1.schema.json` (semuanya di spec/ir). Contoh IR di atas ilustratif, bukan schema atau wire contract. Definisi katalog: `spec/catalog/catalog-v1.schema.json`; katalog Debian satu lokasi: `catalog/debian-13/v1.json`. Core intent di catalog/core. Tidak ada fetch schema melalui jaringan saat runtime.

| Objek | Produsen | Isi minimal | Larangan |
|---|---|---|---|
| NLUProposal | Model/baseline tidak tepercaya | intent candidates, slot span/candidate IDs, score opsional, abstain hint | executable, argv, risk, approval, context hash otoritatif |
| ResolvedIR | Resolver deterministik | request ID buatan sistem, intent canonical, typed slots dan provenance, context/catalog identity | arbitrary executable/flags; field tidak dikenal |
| PolicyDecision | Policy engine | allow-proposal, allow-execute-eligible, clarify, unsupported atau deny; effect set, scope, reason code, policy version | skor model sebagai dasar izin; approval belum berarti allow |
| ExecutionPlan | Compiler tepercaya, diperiksa policy | action ID, executable identity atau native handler, argv, effect, scope/handles, runtime constraints, expiry, canonical digest | shell string, slot yang belum di-resolve, model override |

Schema mewajibkan version, required fields, additionalProperties:false pada seluruh object, enum, maxLength/maxItems, numeric bounds, dan per-intent discriminated slot schemas. Reject duplicate JSON keys, invalid UTF-8, NUL, integer overflow, unknown versions, nonfinite scores, trailing data, dan nesting/size di luar budget. Schema tidak membuktikan semantik: validator native wajib melakukan cross-field check, provenance, OS capability, scope dan policy. Test positif/negatif harus sejalan dengan oracle Python dan runtime C; tidak boleh mengandalkan regex saja.

Slot literal path/unit memakai span byte dari input asli (UTF-8) yang tervalidasi; NFC/normalisasi digunakan untuk NLU, bukan mengganti nama berkas. Span mapping eksplisit. Tipe minimum: port 1–65535; protocol enum tcp/udp/all; positive_int 1–1000 dengan limit intent lebih ketat; duration dinormalisasi ke detik atau interval waktu eksplisit berdasarkan timezone dan reference clock; path candidate dibatasi byte length dan divalidasi saat resolusi; unit_name tidak menerima flag, glob, kontrol atau target yang tidak sah. Unknown/missing slot tidak diisi dengan tebakan. Default katalog dinyatakan eksplisit. Clarify bila maksud atau slot wajib belum diketahui; unsupported bila domain/versi tidak didukung; deny bila tidak sah menurut policy. Risk dan provenance dihitung ulang oleh sistem, bukan dipasok model.

Katalog menyediakan intent ID, descriptions ID/EN, typed slot schema/defaults, resolver, effect axes, adapter ID, minimum verified capability/version, compiler template atau native handler, input/output bounds, fixture IDs, source/license, dan eligibility proposal/execute. Template tidak merupakan string interpolasi shell dan tidak dapat menentukan policy exception. Compiler F1 wajib ada untuk proposal dan oracle, tetapi executor tidak dibangun/dibuka sebagai fitur F1.

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

### 6.1 Kandidat konfigurasi dan format model pack

M1 awal: encoder bidirectional 4 layer, d_model=128, FFN 512, 4 attention heads, intent head dan BIO slot head; pointer/copy optional ablation. Dengan vocabulary 4.096, embedding sendiri 524.288 parameter; blok attention+FFN sekitar 786.432 parameter sebelum bias, normalization, positional embedding, heads. Karena itu konfigurasi tersebut tidak dijanjikan tepat 1,2M. Catat parameter aktual trainable/non-trainable, tied weights dan ukuran fisik. Byte/character tokenizer, unigram dan BPE (misalnya 1k/4k/8k vocab) adalah variabel eksperimen, bukan pilihan terkunci. Model decoder menggunakan objective sequence yang sesuai, bukan wajib BIO loss. Semua model tunduk budget compute yang dipraregistrasi.

Format `.dctm` v1 dirancang pada F0 dalam spec/model-pack/dctm-v1.md; usulan layout:
- Prefix tetap 32 byte: magic 4, major u16, minor u16, header_length u32, section_count u32, file_length u64, section_table_offset u64. Little-endian; parsing field-by-field, bukan cast struct C.
- Header extension dan section directory berversi; setiap entry memuat type, flags, offset u64, length u64, alignment, dengan ukuran record yang ditetapkan spesifikasi. Dua SHA-256 penuh (32 byte masing-masing) untuk bobot dan identitas katalog kompatibel disimpan di metadata section; seluruh file diikat oleh signed manifest eksternal, tidak ada self-referential hash.
- Section metadata architecture/tokenizer config, tokenizer vocabulary/merges, tensor descriptors, payload, quantization scales/zero points bila berlaku. Tensor descriptor mencatat ID, dtype, rank, dims, offset/length, layout, quant axis/group. Alignment 64 byte pada payload jika berguna; tidak mengharuskan file seluruhnya di-copy.
- Loader reject sebelum alokasi: length mismatch, overlap, duplicate ID, offset+size overflow, rank/dim tidak sah, produk shape overflow, tensor hilang/berlebih, invalid scale, vocab mismatch, unsupported required section/version. Batas awal file ≤128 MiB untuk runtime jalur kecil, bobot ≤50 MB untuk gate produk; batas parameter/dimensi/context ditetapkan per architecture. M3 memakai harness pembanding terpisah. Jangan menerima checkpoint pickle sebagai input runtime. F0 memfinalkan encoding, version compatibility dan golden byte vectors; F2 membangun exporter.
- Release manifest menandatangani full-file digest, catalog, tokenizer, architecture, policy, versi dan kompatibilitas. Loader tidak membuka eksekusi dari pack tidak dikenal atau rusak; downgrade policy gagal tertutup.

### 6.2 Paritas dan kuantisasi

Uji A: FP32 Python vs FP32 C, serta INT8 Python vs INT8 C dengan pack yang sama dan definisi accumulator, rounding, saturation, scale dan operator yang sama. Integer intermediate yang didefinisikan exact harus sama. Untuk operasi float, usulkan allclose dengan atol=1e-3 dan rtol=1e-4 untuk logits INT8 lintas implementasi, disepakati sebelum golden suite setelah spike numerik; laporkan max absolute/relative error, keputusan top-k dan slot. Near-tie tidak boleh disembunyikan: aturan tie-break atau abstain deterministik dan golden expected behavior. Jangan gunakan batas ini sebagai tuntutan FP32 vs INT8. 

Uji B: bandingkan kualitas FP32 vs INT8 pada dev dan akhirnya blind test terkunci; target degradasi joint accuracy maksimal 1,5 poin persentase pada dev dengan semua gate kualitas tetap berlaku. INT4 eksplorasi hanya setelah INT8 lulus; gunakan kriteria terpisah yang dipraregistrasi. Laporkan tradeoff RSS/latensi/ukuran, bukan sekadar ukuran bobot.

## 7. Dataset: OS-Intent Corpus

### 7.1 Sumber dan proses

Mulai dari katalog tepat 48 intent dan 200–500 gold seed manusia untuk pengembangan, terpisah dari blind holdout (minimal 300 supported, 150 ambiguity/OOD, 200 security). Generate 15k–40k instruksi sintetis secara bertahap; target eksploratif 70% ID dan 30% EN, code-switch diberi label terpisah dengan aturan penghitungan yang dipraregistrasi. Laporkan hasil per bahasa dan per intent. Dataset ratio bukan kuota yang mengalahkan kualitas. Sumber: manpage/--help utilitas yang dipin pada versi distro, tldr-pages, NL2Bash/Tellina, NLC2CMD, contoh kerja sintetis yang ditulis sendiri. Untuk data pihak ketiga audit lisensi per sumber dan derivasi; jangan menganggap lisensi kode berlaku untuk data/model. Jika lisensi tidak jelas, jadikan referensi evaluasi terpisah tanpa redistribusi. Jangan memasukkan log nyata, data pasien, path internal, hostname, kredensial atau data pribadi ke teacher eksternal atau repo publik.

Pipeline:
1. Definisikan intent dan slot canonical beserta fixture, effect, aturan dan sumber.
2. Bangkitkan variasi parameter yang valid dan pasangan near-miss; buat paraphrase Indonesia/Inggris formal, informal, pendek, typo, campuran bahasa, istilah administrator.
3. Teacher LLM hanya membantu proposal/paraphrase; validasi schema, nilai slot, entailment semantik, provenance dan fixture. Human review untuk gold dan kasus berisiko; teacher bukan oracle akhir.
4. Deduplikasi exact/fuzzy (MinHash/Jaccard sebagai kandidat) per normalized utterance, canonical IR, template family dan semantic group. Tandai contoh ambiguity, unsupported dan unsafe.
5. Split berdasarkan kelompok sebelum augmentasi; train/dev/test 70/15/15 sebagai target pada corpus pengembangan, blind human holdout, compositional holdout, OS/version holdout terpisah. Seed authoring dan blind authoring dipisah; tokenizer dilatih hanya train. Stratifikasi intent/bahasa tanpa memecah family; laporkan deviasi. Cegah varian parafrase template yang sama bocor ke test; laporkan split in-distribution intent-known dan intent/combination unseen terpisah.
6. Publikasikan manifest hash, schema, license ledger, generator version, seed, teacher ID/prompt hash, rejection reason dan audit sampel. Data holdout akhir tidak digunakan untuk tuning, pemilihan model atau kalibrasi.

Contoh record sintetis:

```json
{"id":"syn-net-0001","language":"id","text":"siapa yang listen di port 5432?","intent":"network.listener.lookup","slots":{"port":5432},"group":"listener-port-query","source":"authored","label":"supported"}
```

Skema penuh perlu span/candidate reference, versi katalog, context profile, ambiguity label, canonical fixture dan provenance. Negative set: target kosong, opsi saling bertentangan, prompt injection langsung/tidak langsung, permintaan di luar lingkup, input panjang, nilai ekstrem, karakter khusus, argumen berawalan dash, output yang menyamar sebagai instruksi, mixed intent, host berbeda, opsi utilitas tidak tersedia. Buat pasangan kontras seperti tampilkan vs hapus, sebelum vs sesudah, aktif vs gagal, lokal vs remote. Pisahkan ketidakpastian semantik dari risiko kebijakan.

Validasi semantik wajib di luar schema dan compiler: pasangan instruksi/IR diperiksa atas maksud, negasi, target, waktu, unit, kardinalitas dan efek. Gunakan audit manusia pada sampel terstratifikasi, seluruh gold, seluruh kasus CHANGE/NET yang menjadi gold, dan kasus disagreement; reject record yang tidak jelas. Laporkan acceptance rate, agreement antar reviewer bila memungkinkan, dan error per jenis. Round-trip kompilasi membuktikan bentuk, bukan kebenaran makna. Independent oracle dibuat oleh penulis/implementasi terpisah dari generator; tidak menganggap teacher sebagai oracle. Tahan blind set di luar akses training/tuning dan publikasi sampai run yang didaftarkan selesai; catat hash/akses dan versi. Jika holdout telah bocor, ganti dan dokumentasikan.

### 7.2 Evolusi katalog

Gunakan schema-version, capability-id stabil, adapter version dan compatibility matrix; perubahan opsi command umumnya cukup memperbarui adapter/katalog dan test. Intent baru mungkin perlu data dan retraining, tetapi uji zero-shot retrieval dahulu. Paket katalog tambahan hanya dari sumber tepercaya dan tidak dapat menambah izin pengguna sendiri.

## 8. Runtime dan UX

Keputusan usulan runtime: C17 + CMake, pustaka standar C/POSIX/Linux dan dependensi minimal yang diaudit (misalnya library kriptografi terpelihara untuk signature; jangan menulis kriptografi sendiri). C++ dan C# NativeAOT hanya pembanding alternatif jika spike memberi bukti kebutuhan. C17 tidak menjamin memory safety; wajib checked arithmetic, ownership conventions, sanitizers, fuzzing, compiler warnings dan review. Target maksimal dua thread inference pada VM referensi, benchmark sebelum SIMD. Ukuran executable di bawah 1 MB adalah target eksploratif, bukan gate atau hasil terukur. Python/PyTorch untuk training, export dan test oracle. Evaluasi llama2.c, llm.c dan llama.cpp sebagai referensi/benchmark; jangan menambah runtime besar tanpa pembuktian. Gunakan reference scalar CPU, kemudian SIMD/BLAS opsional jika profiling mendukung; batasi threads. Target single executable + model file + catalog pack, tanpa daemon wajib, telemetry, network, updater otomatis, framework GUI berat, Python/Node runtime.

Perintah CLI (executable: dictum; default shorthand dictum "instruksi" setara ask):
- dictum ask "siapa yang menggunakan port 8080?" — preview + arti + source.
- dictum explain — jelaskan langkah yang dipilih dan batasannya.
- dictum search — cari dokumentasi/katalog tanpa neural.
- dictum run — opt-in, setelah gate keamanan dan persetujuan.
- dictum inspect — model/catalog version, parameter count, latency, profile.
- dictum lab — mode edukasi opsional, visualisasi token, logits, loss, quantization dan benchmark; tidak menambah izin eksekusi.

UX default jawaban ringkas, tampilkan perintah, tujuan, scope, sumber versi dan dampak. Clarification hanya bila material; tampilkan kandidat jika ambigu. Tidak mengandalkan confidence softmax mentah sebagai probabilitas kebenaran. Mode verbose untuk debugging; history lokal opt-in, redacted, retensi terbatas, tidak dipakai training secara otomatis. TUI, completion shell, keyboard shortcut dan voice interface (STT/TTS lokal) adalah ide lanjutan; bukan prasyarat produk. Tidak menyisipkan teks model langsung ke shell history sebagai perintah yang dijalankan.

## 9. Kontrak keamanan draft

Model dan seluruh input dianggap tidak tepercaya. Default deny, least privilege, tidak ada auto-sudo/root, akses jaringan keluar ditolak pada executor lab, tidak menjalankan shell string, eval, dynamic code, interpreter bebas, executable dari cwd/PATH tidak tepercaya, atau operasi yang belum dikatalogkan. Read-only bukan sinonim aman: membaca file sensitif, environment, output berisi secret, jaringan, symlink traversal dan scan besar tetap berisiko.

Risk classes: INFO (penjelasan tanpa spawn utilitas; metadata OS dari probe terbatas), READ (tidak dimaksudkan mengubah state persisten), CHANGE (perubahan state, proposal-only), HIGH (privilege, destructive, remote, secret, perubahan security policy; deny), UNKNOWN (deny). Kelas risiko bukan keseluruhan efek. Effect axes independen: filesystem read/write, process spawn, privilege, NET (termasuk DNS, ICMP, koneksi atau delegasi ke daemon), IPC, secret exposure, resource usage, persistent mutation. Default unknown effect deny. DNS lookup dan ping adalah READ+NET tetapi proposal-only; diagnosis berupa panduan proposal-only. Tidak ada koneksi keluar, termasuk lewat resolver daemon, D-Bus proxy atau socket warisan; izin NET tidak tersirat dari READ. Local status jaringan yang hanya membaca kernel boleh menjadi kandidat F5. CHANGE tidak otomatis reversible dan reload tidak dijamin tanpa gangguan. Policy ditetapkan oleh operasi dan konteks secara deterministik, bukan label model. Konten berbahaya maupun ambigu ditolak atau diklarifikasi sebelum spawn.

- Executable identity/version, argv grammar, arg type/range, per-command semantics dan efek harus diverifikasi. Argv tanpa shell mencegah sebagian injection, bukan option injection atau penyalahgunaan opsi; gunakan explicit positional binding, terminator opsi bila didukung, allowlist flags, canonical target serta per-command validator.
- Environment allowlist, fixed cwd/scope, restricted file access, no inherited sensitive descriptors, timeout, bounded stdout/stderr, cancellation dan process-tree termination. Tidak ada tool/pipeline arbitrer; log dan terminal escape sequence disanitasi. Gunakan OS-native APIs untuk operasi yang lebih aman jika tersedia.
- Approval mengikat SHA-256 atas canonical encoding yang unambiguous (length-prefixed fields atau canonical schema encoding): executable identity/digest, argv, handler ID, target handle identities, cwd handle, scope, policy/catalog/model identities, effect, UID/GID, context, constraints, session, monotonic expiry (maks 30 detik), random single-use nonce. Digest bukan autentikasi; token hanya diterbitkan oleh authority lokal, disimpan server-side atau MAC dengan kunci sesi, consume atomik sebelum spawn, tidak menerima approval dari model/stdout. Revalidate identity, policy/currentness, version, scope dan expiry tepat sebelum eksekusi; perubahan atau error deny. Approval bukan pengganti policy.
- Executor lab berjalan di VM disposable tanpa mount/share host, credential, clipboard atau bridge produksi; jaringan isolasi default. Pertimbangkan seccomp, Landlock, no_new_privs, cgroups sesuai dukungan dan uji; tidak ada satu kontrol dianggap sandbox sempurna. Proxmox management host bukan target uji eksekusi.
- Pembatasan sumber daya per request: waktu, CPU/memori, output, jumlah file, ukuran path, jumlah subprocess, depth. Error, timeout, cancellation, corruption, unsupported version, invalid signature atau policy unavailable → fail closed.
- Audit lokal minimal: operation ID, outcome, reason, digest, waktu, latency dan versi; raw input/output bukan default. Tidak ada logging secret atau telemetry. Model pack binary tervalidasi (magic, version, size, bounds, hash, provenance); tidak memuat pickle tak tepercaya saat runtime.
- Tidak mengizinkan agent loop dari stdout/stderr; diagnosis berbasis fixture atau hasil terstruktur terverifikasi. Jika analisis bebas ditambahkan, tetap suggestion-only dan tidak memberi izin.
- Seluruh bypass policy, unauthorized effect, akses di luar scope, data egress, command injection, dan persetujuan yang tidak terikat adalah release blocker. Klaim keamanan harus dibatasi pada threat model dan coverage uji, bukan jaminan universal.

### 9.1 Kontrak containment F5 (tidak boleh diklaim selesai dari desain)

**Filesystem:** executor terpisah secara proses dan authority dari inference/CLI; tidak mewarisi secrets atau descriptor kecuali yang disetujui. Gunakan root directory FD dari scope terpercaya, openat2 dengan RESOLVE_BENEATH atau RESOLVE_IN_ROOT sesuai desain (jangan digabung tanpa verifikasi), RESOLVE_NO_SYMLINKS/NO_MAGICLINKS dan RESOLVE_NO_XDEV bila mount crossing dilarang. O_NOFOLLOW hanya melindungi final component; canonical path/fstat lalu membuka ulang bukan jaminan. Pin object identity menggunakan FD, operasi native descriptor-based bila memungkinkan. Untuk utilitas path-based yang tidak bisa mempertahankan binding, gunakan confinement yang membatasi target secara efektif dan bukti semantik/race; bila identitas spesifik tidak terjaga, tetap proposal-only. Uji rename, symlink parent/final, bind mount, magic link, hardlink, procfs, device/FIFO, special files dan race. Jangan membaca special file tak terbatas. Pin executable melalui FD yang diverifikasi dan execveat/fexecve jika sesuai; validasi root-owned path/parent, loader/library trust dan executable updates. Script/interpreter dinamis tidak diizinkan. Tidak mengeksekusi paket sistem yang berubah tanpa revalidation.

**Confinement:** Landlock berdasarkan ABI yang diverifikasi atau mount namespace dengan allowlist read-only mounts dan data roots, ditambah seccomp allowlist, no_new_privs, UID non-root, drop capabilities, close-on-exec FD, environment allowlist dan IPC/network isolation. Pilih konfigurasi per operasi berdasarkan threat model. Seccomp tidak menyaring path filesystem; Landlock tidak mencakup semua jenis IPC atau seluruh risiko. Deny bila kernel, mount/namespace atau isolation primitive yang diwajibkan tidak tersedia. Tidak fallback ke executor biasa. Pisahkan executor VM lab dari host Proxmox dan jaringan produksi. Uji socket termasuk Unix domain, DNS melalui daemon, inherited FD, D-Bus, writable mounts, secrets dan cross-scope reads. Probe yang terbatas dapat memakai native APIs; probe sendiri tidak boleh menjadi jalan pintas policy. Log, process cmdline, mount options dan archive listing dapat mengandung secret; akses/minimisasi output per intent, jangan menampilkan raw sensitive data secara default.

**Resource containment:** batasi CPU/address space/FD/file size melalui rlimit sesuai semantics, dan child count/memory/CPU melalui cgroup v2 bila tersedia. Deadline monotonic wall clock default 5 detik; parent membaca stdout+stderr nonblocking dengan total cap 64 KiB, terminate saat overflow, drain/reap terbatas, sanitasi terminal, catat truncation/error. RLIMIT_FSIZE tidak membatasi pipe. Child ditempatkan dalam cgroup terisolasi sebelum boleh menjalankan code; tidak boleh migrasi keluar. Kill seluruh cgroup dan verifikasi empty/reap; process group hanya tambahan, bukan jaminan containment. Bila cgroup/containment setara tidak dapat dipenuhi, deny. Uji fork/flood, setsid, orphan, timeout, cancellation, child exit race, OOM. Tidak pernah melaporkan keberhasilan jika containment atau hasil tidak diketahui.

**Trust artefak:** checksum mendeteksi korupsi; signature mengautentikasi manifest. Usulan signed canonical manifest dengan Ed25519 via library teruji, public key trust anchor dibundel/diinstal melalui jalur tepercaya, versi dan key ID eksplisit. Pisahkan dev trust dari release trust; private key tidak ikut distribusi, rotasi/revocation/rollback policy offline terdokumentasi. Offline freshness terbatas pada state lokal, jangan mengklaim revocation real-time. Unknown key, hash mismatch, unauthorized downgrade, incompatible versions, malformed signatures atau missing trust state membuat eksekusi ditolak. F0 memilih format/library dan threat model, F4 memverifikasi artefak, F5 menguji enforcement. Tidak menulis implementasi kriptografi sendiri.

**Preview:** command yang disalin dan dijalankan sendiri oleh pengguna berada di luar containment Dictum; UI harus menyatakan hal ini. Jangan menyebut command sebagai "aman" hanya karena proposal-only. Preview native pipeline harus menyatakan perbedaan antara illustrative shell equivalent dan plan aktual. Archive extraction proposal mensyaratkan peringatan traversal/symlink, target baru dan pemeriksaan isi; tidak memberi jaminan keamanan. Semua operasi yang tidak bisa diberi proposal yang tepat harus clarify/deny. F1–F4 tidak menyediakan jalur run umum; fixture harness khusus lab bukan fitur pengguna.

### 9.2 Gate keamanan dan threat model

F0 threat model mencakup malicious input, hostile model/catalog, local untrusted user dalam scope privilege, hostile files/logs/output, compromised utility/package assumption, symlink/race, resource exhaustion, supply chain dan approval replay. Kernel/host yang sudah compromised di luar jaminan; jangan menjanjikan keamanan terhadap root attacker. F5 wajib review independen, uji per capability, deny default untuk semua yang belum dibuktikan, 100% expected policy behavior pada suite dan zero observed unauthorized effects. Satu bypass atau uncontained process adalah blocker untuk eksekusi. Proposal-only dapat dievaluasi terpisah jika tidak ada jalur execute; kelemahan rendering/secret tetap blocker proposal release.

## 10. Benchmark dan metode ilmiah

Bandingkan B0/B1/B2, M0/M1/M2, M3 pada corpus, fixture, context dan policy set yang sama. Laporan raw model dan end-to-end dipisah. Minimal tiga seed untuk kandidat final jika komputasi memungkinkan; laporkan variance dan confidence interval, bukan hanya hasil terbaik. Lakukan ablation terhadap retrieval, slot copying, tokenizer, constrained decoding, OS context, ukuran corpus, quantization dan model size. Rekam wall-clock training, RAM/VRAM, energi jika dapat diukur, dan estimasi FLOPs; tidak perlu membeli GPU khusus sebelum baseline.

Metrik:
- Intent macro-F1, slot exact/span F1, joint intent-slot accuracy, valid IR, semantic/execution success, coverage, selective risk, false accept/reject, OOD recall, clarification precision.
- Command exact match/charBLEU hanya pembanding literatur. Oracle utama: fixture snapshot, normalized stdout, exit status, target resource, before/after state dan side effects yang tidak diizinkan. Terima beberapa perintah ekuivalen; jangan menganggap exit code 0 berarti tugas benar.
- Safety: policy-denial correctness, malicious input/injection, unexpected mutation/network/file access, approval replay, timeout, memory abuse, parser fuzz, corrupt artifacts dan terminal injection. Uji layer individual dan integrasi.
- Usability: waktu menemukan command, jumlah interaksi, salah target, perbandingan dengan man/tldr/keyword search; blind tasks dari manusia.
- Perf: cold start, warm p50/p95 latency sampai proposal, peak RSS, disk footprint total, threads, model load time; waktu command eksekusi dilaporkan terpisah. Catat CPU, RAM, guest vCPU, OS/kernel, compiler flags dan versi utilitas.

Target hipotesis MVP (belum hasil): 48 intent; blind test supported joint accuracy ≥90%, end-to-end fixture success ≥90% dihitung dari seluruh supported request termasuk abstain (coverage dilaporkan sendiri); OOD/unsafe refusal recall ≥95% sebagai metrik model, policy tests wajib 100% tanpa pelanggaran yang teramati; zero observed unauthorized effects/injection pada suite. Target 50 MB bobot maksimum (jalur kecil), peak RSS ≤128 MiB, p95 warm proposal ≤500 ms dan cold ≤2 s pada VM referensi 2 vCPU/2 GiB setelah hardware diidentifikasi. Catat pemenuhan atau kegagalan, jangan mengubah threshold setelah melihat blind test; bila perlu revisi sebelum eksperimen berikut dengan holdout baru. Laporkan jumlah kasus dan interval statistik; zero observed bukan bukti zero risk.

Suite awal: ≥300 blind supported, ≥150 ambiguity/OOD, ≥200 security cases sebagai target minimum yang ditinjau manusia, serta ≥100 executable fixtures dengan variasi data dan kondisi gagal. Set supported meliputi seluruh 48 intent; fixture execution suite hanya operasi yang diizinkan dalam harness lab; proposal-only CHANGE/NET/diagnosis diuji dengan oracle IR/preview dan efek, bukan dijalankan. Denominator masing-masing suite ditetapkan sebelum evaluasi, tidak memilih setelah melihat hasil. Perluasan mengikuti temuan. Uji integrasi pada snapshot VM bersih dan versi utilitas dipin; reset fixture setiap kasus. Oracle ditulis independen dari generator data. Jangan menjalankan output model mentah pada host nyata, termasuk saat benchmark generator Bash bebas.

### 10.1 Definisi metrik yang tidak dapat digaming

Untuk set supported S dengan N kasus dan A kasus yang menerima proposal, C = jumlah proposal yang benar secara joint intent/slot/semantic oracle. Coverage = A/N; selective accuracy = C/A; selective risk = (A-C)/A. Jika A=0, kedua metrik selective undefined, bukan 100% benar. Joint success = C/N: abstain, timeout, invalid IR dan proposal salah dihitung gagal. Execution fixture success = jumlah fixture benar (termasuk no forbidden side effects) / seluruh fixture supported yang dipraregistrasi, bukan hanya fixture yang diterima; abstain dihitung gagal. Report selective execution rate tambahan, bukan gate pengganti. Misal 10/100 kasus diterima dan semuanya benar: coverage 10%, selective accuracy 100%, joint success 10%, gate gagal. Proposal-only oracle success terpisah untuk CHANGE/NET/diagnosis, tidak diklaim execution success.

OOD recall = unsupported/deny yang tepat pada OOD / total OOD; ambiguity clarification recall = clarify yang tepat / total ambiguity; report terpisah, masing-masing target ≥95%, serta clarification precision dan false abstain pada supported. Unsafe request policy expected outcome dipisah dari prediksi model: perubahan yang diizinkan sebagai proposal bukan izin eksekusi. Ukur per intent dan bahasa, macro dan micro, calibration/reliability diagram bila memungkinkan. Gunakan dev untuk threshold, lock model/catalog/policy/fixture hashes sebelum blind test; satu final run per preregistration, kegagalan memerlukan holdout baru bila tuning. CI metric oracle wajib menguji counterexample 10/100, A=0, missing cases, duplicate IDs dan timeout.

Target kualitas kuantitatif: supported joint ≥90%, proposal semantic oracle ≥90% pada semua supported proposal-only cases, fixture execution ≥90% pada semua supported execution cases; coverage dilaporkan, implied minimum 90% untuk gate success. Target keamanan bukan estimasi jaminan universal: 0 pelanggaran teramati dan 100% policy expected outcomes pada security suite; setiap pelanggaran material blocker. Confidence intervals 95% (misalnya bootstrap terkelompok menurut template family atau Wilson bila asumsi independen layak), seed variance, raw counts dan paired comparison dengan baseline. Definisikan usability task completion, time-to-correct-proposal dan koreksi pengguna dibanding man/tldr; jangan hanya mengumpulkan opini positif. CPU model, VM configuration, compiler flags, cold/warm cache dan kondisi background load dicatat. Cold start ≤2 s, warm proposal p95 ≤500 ms, RSS ≤128 MiB sebagai target jalur kecil; latensi proses OS terpisah. Ukuran produk total dilaporkan terpisah dari bobot ≤50 MB.

## 11. Roadmap bertahap dan gate

| Fase | Deliverable | Gate |
|---|---|---|
| F0 — Kontrak | charter v1, scope, threat model, schema IR, daftar intent, keputusan lisensi dan protocol benchmark | review manusia; tidak ada training/eksekusi produksi |
| F1 — Katalog & baseline | 48 intent, probe Debian, CLI proposal-only, B0/B1/B2, corpus seed | gold fixtures, schema/validator pass; baseline terukur; tanpa executor pengguna |
| F2 — Mini-model | tokenizer, train dari nol M0/M1, manifest, checkpoint, inference reference | reproducible train/export, dev benchmark; hipotesis boleh gagal; pilih kandidat tanpa blind tuning |
| F3 — Comparative research | M2/M3, ablation, blind evaluation, size-quality Pareto | pilih model terkecil yang memenuhi gate kualitas atau kembali ke baseline |
| F4 — Native runtime | loader, inference parity, INT8, CLI, offline package | resource budget dan golden parity; malformed model fail closed |
| F5 — Isolated executor | immutable plan, policy, approval, VM fixtures, fuzz, fault tests | zero observed unauthorized effect, 100% expected security outcomes, confinement dan approval tests; review keamanan independen |
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
  model-pack/
catalog/
  core/
  debian-13/
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

Keputusan usulan v2: C17 + CMake; kode MIT; spesifikasi/katalog Apache-2.0 hanya untuk materi yang haknya kompatibel; corpus dan gold original CC-BY-SA-4.0; bobot hasil training dari nol diusulkan Apache-2.0 jika audit hak/lisensi data dan model memungkinkan, tanpa mengasumsikan lisensi dataset otomatis melekat atau tidak melekat pada bobot. Bobot pretrained/derivative mengikuti lisensi upstream yang kompatibel; jika status hak tidak jelas, tahan distribusi artefak. F0 wajib license ledger, atribusi, model/data card, dan keputusan eksplisit pemilik atas lisensi bobot sebelum release. Dataset pihak ketiga tidak direlicense sembarangan. Format schema/pack, budget compute, CPU reference, metode containment dan parameter model aktual difinalkan pada F0/spike sesuai gate; proposal-only wajib hingga F5. Jangan memutuskan berdasarkan popularitas repositori.

## 15. Referensi inspirasi (ditelusuri 24 November 2026)

Referensi di bawah ditinjau melalui halaman proyek, README atau abstrak publik; belum direproduksi atau diaudit kode secara penuh. Klaim pengembang bukan hasil benchmark Dictum. Pin commit/release, verifikasi lisensi dan reproduksi pada F0/F1.

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

## 16. Rencana kerja setelah persetujuan pemilik

| ID | Pekerjaan | Exit evidence |
|---|---|---|
| F0-01 | Persetujuan eksplisit pemilik atas v2; buat salinan approved setelah disetujui | Review record, commit dan hash |
| F0-02 | Schema empat boundary objects + catalog; native validation contract, negative examples | SPEC-IR, SPEC-CATALOG, validator oracle |
| F0-03 | Daftar 48 intent dan effect matrix, compatibility, probe scope | 48 unique IDs, per-intent eligibility, no implicit NET |
| F0-04 | Threat model, approval canonicalization, confinement feasibility, trust manifest | ADR, threat model, security acceptance matrix; F5 tetap NO-GO |
| F0-05 | Corpus schema, license ledger, grouped split, blind protocol, metric definitions, compute budget | Dataset card, benchmark preregistration, metric unit tests |
| F0-06 | DCTM format spec, tokenizer architecture sweep, golden vectors, license weights review | SPEC-PACK, ADR, manifest format |
| F0-07 | Review F01–F12 terhadap dokumen turunan; persetujuan gate F0 | Evidence matrix, keputusan GO/HOLD/NO-GO pemilik |
| F1-01 | Katalog 48 intent, resolver/compiler proposal-only, probe terbatas | Fixture/validation tests, no executor feature |
| F1-02 | Gold seed dan held-out corpus independen, synthetic pipeline | Provenance, split hashes, semantic audit |
| F1-03 | CLI proposal-only, B0/B1/B2, baseline benchmark | Reproducible report, usability baseline, footprint |
| F1-04 | Review gate F1 dan prioritas F2 | Keputusan berbasis bukti; tidak auto-approve |

Urutan F0-01 sampai F0-07 tidak memberi izin implementasi F1 sebelum owner menyatakan GO. Tidak melakukan training sebelum baseline dan protocol tersedia. F2–F7 tetap mengikuti roadmap, dengan fase terpisah dan review. Gunakan issue kecil, commit bahasa Indonesia, dan evidence yang dapat direproduksi.

**Kriteria keberhasilan tertinggi bukan banyaknya command yang dihafal model, melainkan pengguna dapat menyatakan maksudnya dengan bahasa biasa dan memperoleh operasi OS yang tepat, dapat dijelaskan, ringan, lokal, dan terkendali.**


## Lampiran A. Daftar 48 intent MVP (Debian 13 Trixie)

Daftar berikut mengusulkan ruang lingkup semantik Katalog v1: 4 INFO + 40 READ + 4 CHANGE = 48. Kelas INFO/READ tidak otomatis berhak dieksekusi. Semua proposal-only sampai F5; khusus NET, CHANGE, diagnosis tetap proposal-only sepanjang MVP. Intent INFO hanya dokumentasi atau metadata probe yang dibatasi. Seluruh intent lain memerlukan verifikasi capability, scope dan policy.

### 1. Kategori `INFO` (4 Intent — Penjelasan & Metadata)
1. `help.command.explain` — Menjelaskan arti utilitas dan *flag* berdasarkan katalog/manpage.
2. `help.intent.list` — Menampilkan daftar kemampuan operasi yang didukung Dictum.
3. `system.os.info` — Menampilkan informasi distribusi Debian, versi kernel, dan arsitektur.
4. `system.uptime.summary` — Menampilkan lama waktu sistem menyala (*uptime*) dan rata-rata beban (*load average*).

### 2. Kategori `READ` — Jaringan & Konektivitas (8 Intent)
5. `network.listener.lookup` — Mencari proses/socket yang mendengarkan (*listening*) pada port atau protokol tertentu.
6. `network.connection.active` — Menampilkan daftar koneksi jaringan aktif (ESTABLISHED, TIME_WAIT, dll.).
7. `network.interface.list` — Menampilkan daftar antarmuka jaringan, alamat IP, dan status tautan (*link up/down*).
8. `network.route.table` — Menampilkan tabel *routing* IP lokal dan *default gateway*.
9. `network.dns.config` — Menampilkan konfigurasi *resolver* DNS aktif sistem.
10. `network.dns.lookup` — Mengusulkan kueri DNS; READ+NET, proposal-only, karena resolver bisa mengirim trafik keluar.
11. `network.connectivity.ping` — Mengusulkan ping terbatas (maks 4 paket); READ+NET, proposal-only, tidak melakukan trafik dari Dictum.
12. `diagnosis.connectivity` — Menyajikan panduan diagnostik bertahap untuk layanan lokal; proposal-only, tanpa agent loop.

### 3. Kategori `READ` — Layanan (Systemd) & Log (7 Intent)
13. `service.status.get` — Memeriksa status berjalan (*active/inactive/failed*), PID utama, dan memori satu layanan.
14. `service.list.active` — Menampilkan daftar layanan yang sedang aktif berjalan.
15. `service.failed.list` — Menampilkan daftar layanan yang mengalami kegagalan (*failed units*).
16. `service.enabled.list` — Menampilkan layanan yang dikonfigurasi berjalan otomatis saat *boot*.
17. `log.service.query` — Mengambil log jurnal untuk satu unit layanan tertentu dengan filter waktu dan batas baris.
18. `log.system.errors` — Menampilkan log sistem dengan tingkat prioritas `err` hingga `emerg` dalam rentang waktu tertentu.
19. `log.boot.messages` — Menampilkan pesan kernel/boot terakhir yang dapat diakses tanpa eskalasi (`dmesg` / `journalctl -b`).

### 4. Kategori `READ` — Penyimpanan, Disk, & Berkas (11 Intent)
20. `storage.filesystem.usage` — Menampilkan penggunaan ruang disk dan persentase kapasitas per partisi/mount (`df`).
21. `storage.inode.usage` — Menampilkan penggunaan *inode* per sistem berkas (`df -i`).
22. `storage.directory.usage` — Menghitung dan mengurutkan ukuran subdirektori terbesar di dalam direktori target (`du`).
23. `storage.block.list` — Menampilkan daftar perangkat blok, partisi, dan titik kait (`lsblk`).
24. `storage.mount.list` — Menampilkan sistem berkas yang sedang terpasang (*mounted*) beserta opsinya.
25. `file.search` — Mencari berkas berdasarkan pola nama, ekstensi, atau waktu modifikasi di dalam direktori terizinkan.
26. `file.text.search` — Mencari pola teks/string di dalam berkas teks pada direktori terizinkan (dengan batas ukuran).
27. `file.metadata.stat` — Menampilkan metadata lengkap berkas (ukuran, *permission*, pemilik, *timestamp*).
28. `file.permission.check` — Memeriksa hak akses baca/tulis/eksekusi suatu berkas atau direktori.
29. `file.head_tail.view` — Menampilkan $N$ baris pertama atau terakhir dari berkas teks non-sensitif.
30. `archive.contents.list` — Melihat daftar isi arsip (`.tar.gz`, `.zip`) tanpa mengekstraknya ke disk.

### 5. Kategori `READ` — Proses, Memori, CPU, & Paket (10 Intent)
31. `process.list.top_cpu` — Menampilkan daftar proses dengan konsumsi CPU tertinggi.
32. `process.list.top_mem` — Menampilkan daftar proses dengan konsumsi memori (RSS) tertinggi.
33. `process.lookup.name` — Mencari PID dan detail proses berdasarkan nama perintah.
34. `process.tree.view` — Menampilkan hierarki induk-anak proses (`pstree` / `ps f`).
35. `memory.summary` — Menampilkan ringkasan RAM fisik, *available memory*, *cache*, dan penggunaan *swap*.
36. `cpu.hardware.info` — Menampilkan spesifikasi arsitektur CPU, jumlah *core/thread*, dan frekuensi (`lscpu`).
37. `package.installed.check` — Memeriksa apakah paket tertentu terpasang beserta versinya (`dpkg-query`).
38. `package.search.local` — Mencari paket di dalam *cache* repositori lokal (`apt-cache`).
39. `user.session.who` — Menampilkan pengguna yang sedang masuk (*logged in*) ; riwayat login hanya jika sumber, izin dan batas privasi mendukung.
40. `user.identity.info` — Menampilkan UID, GID, dan keanggotaan grup untuk pengguna saat ini.

### 6. Kategori `READ` — Diagnostik Terpadu (4 Intent)
41. `diagnosis.disk_full` — Panduan pemeriksaan bertahap saat ruang disk penuh (kapasitas, direktori besar, *inode*).
42. `diagnosis.high_load` — Panduan pemeriksaan saat beban CPU/sistem tinggi (top proses, *I/O wait*, memori).
43. `diagnosis.service_crash` — Panduan pemeriksaan saat layanan gagal mulai (status unit, log terakhir, konflik port).
44. `diagnosis.dns_failure` — Panduan pemeriksaan saat resolusi domain gagal (konfigurasi resolver, jalur jaringan).

### 7. Kategori `CHANGE` — Proposal-Only Terbatas di MVP (4 Intent)
45. `service.restart` — Menyusun usulan perintah restart layanan (wajib salin manual oleh admin di MVP).
46. `service.reload` — Menyusun usulan perintah *reload* konfigurasi layanan dengan peringatan bahwa dampak layanan bergantung pada implementasi.
47. `archive.extract.safe` — Menyusun usulan ekstraksi arsip ke subdirektori baru; peringatkan traversal, symlink dan pemeriksaan isi; tidak menjamin aman.
48. `file.compress.archive` — Menyusun usulan pengarsipan direktori/berkas ke format `.tar.gz`.

### A.1 Eligibility tambahan

| Intent IDs | Efek dan eligibility MVP |
|---|---|
| 1–4 | INFO; dokumentasi/metadata native atau bounded probe; tidak arbitrary spawn |
| 10–11 | READ+NET; proposal-only sepanjang MVP |
| 12, 41–44 | READ diagnostic guidance; proposal-only, tanpa eksekusi graf |
| 45–48 | CHANGE; proposal-only, warning dampak; hard deny pada executor |
| 5–9, 13–40 | READ; kandidat execution F5 saja; efek filesystem/IPC/secret harus diperinci dan diverifikasi per intent. Jika tidak terjamin, proposal-only |

F0 matrix harus mencakup seluruh intent dan membedakan expected outcome dari permission. Kategori 5–9, 13–40 tidak otomatis lulus F5. Sistem hanya mendukung intent dan opsi yang dinyatakan dalam katalog.

## Lampiran B. Referensi teknis tambahan untuk spesifikasi F0

Referensi primer untuk verifikasi implementasi (belum menyatakan kode lulus audit):
- [openat2(2)](https://man7.org/linux/man-pages/man2/openat2.2.html), [open(2)](https://man7.org/linux/man-pages/man2/open.2.html), [execveat(2)](https://man7.org/linux/man-pages/man2/execveat.2.html) — path resolution dan descriptor binding.
- [Landlock userspace API](https://docs.kernel.org/userspace-api/landlock.html), [seccomp filter](https://docs.kernel.org/userspace-api/seccomp_filter.html), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html), [getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html) — isolasi dan batas sumber daya dengan semantics spesifik.
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12), [RFC 8032 EdDSA](https://www.rfc-editor.org/rfc/rfc8032), [Debian Trixie](https://www.debian.org/releases/trixie/) — schema, signature, profil platform.

Semua R01–R19 dari v0 dipertahankan sebagai bibliografi historis untuk diverifikasi kembali (judul, URL, release/commit, lisensi dan kesesuaian) pada F0. Tautan bukan bukti reproduksi. 
