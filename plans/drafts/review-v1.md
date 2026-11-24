> **ARSIP REVIEW v1 — BUKAN KONTRAK YANG DISETUJUI.**
> Dokumen berikut merupakan masukan reviewer yang diterima pada 24 November 2026, disalin dari lampiran percakapan sebagai teks arsip. Status APPROVED-V1 di dalam sumber adalah klaim reviewer, bukan persetujuan pemilik. Gunakan rencana-v2.md untuk kandidat revisi terbaru. Arsip bukan salinan byte-for-byte yang telah diverifikasi.

---

# AI Lab — Dictum: Rencana Proyek & Kontrak Implementasi (v1)

**Tanggal:** 24 November 2026  
**Status:** APPROVED-V1 — Kontrak Implementasi Fase F0–F1 (Menggantikan `DRAFT-0`)  
**Repositori:** [megaalive/ai-lab-dictum](https://github.com/megaalive/ai-lab-dictum)  
**Nama Proyek:** Dictum (Penerjemah Bahasa Manusia ke Operasi Sistem Operasi)  
**Keputusan Tata Kelola:** **GO** untuk pengembangan kontrak, katalog, baseline, dan riset model di lingkungan terisolasi; **NO-GO** untuk eksekusi otomatis maupun deployment di mesin produksi.

---

## Ringkasan Audit & Perubahan dari v0 ke v1

Dokumen `DRAFT-0` dinilai sangat matang secara arsitektural, memiliki *security-first mindset* yang kuat, serta pendekatan ilmiah yang ketat (menolak *hype* LLM besar demi pembuktian empiris dari nol). Namun, agar v1 sah sebagai **kontrak implementasi**, audit menemukan beberapa area yang masih berupa "keputusan terbuka" atau kurang presisi secara teknis. Perubahan utama pada **v1** meliputi:

1. **Resolusi Keputusan Terbuka (Section 14 v0 → Section 14 v1):** Menetapkan keputusan konkret untuk *stack* runtime awal (`C17` murni tanpa dependensi eksternal berat), skema lisensi terpisah (`MIT` untuk kode, `Apache-2.0` untuk katalog/spesifikasi, `CC-BY-SA-4.0` untuk dataset), batas komposisi bahasa pelatihan (`70% ID / 30% EN`), serta mode rilis MVP (`Proposal-Only` wajib sebelum *gate* keamanan F5 lulus).
2. **Spesifikasi Formal IR & Katalog (Section 5):** Menambahkan kontrak JSON Schema formal untuk *Intermediate Representation* (IR) serta struktur definisi Katalog Operasi agar tidak ambigu antara tim model, *compiler*, dan *validator*.
3. **Konkretisasi Daftar 48 Intent MVP (Section 3 & Lampiran A):** Mengunci tepat **48 intent baca (READ/INFO)** dan **4 intent proposal-only terbatas** untuk Debian 13 (Bookworm/Trixie), menghilangkan ambiguitas rentang "40–60 intent".
4. **Protokol Kuantisasi & Reproduksibilitas Eksperimen (Section 6 & 10):** Menambahkan definisi *Model Pack Binary Format* (`.dctm`), batas toleransi numerik FP32 vs INT8, dan rumus metrik *Selective Risk / Coverage* agar evaluasi *abstain* terukur secara matematis.
5. **Penguatan Kontrak Keamanan & Mitigasi TOCTOU (Section 9):** Memperjelas mekanisme *file descriptor pinning* (`openat`, `O_NOFOLLOW`), *digest binding* berbasis SHA-256, serta daftar *Release Blocker* yang dapat diaudit secara otomatis di CI.

---

## 1. Latar Belakang, Visi, dan Prinsip Dasar

Pengguna sistem operasi tidak semestinya dipaksa menghafal ratusan nama utilitas, variasi *flag*, perbedaan antar-distribusi, dan sintaks shell yang rapuh hanya untuk mengeksekusi maksud yang sudah dipahami secara konseptual. Dokumentasi manual (`man`) dan *command history* hanya efektif jika pengguna sudah mengetahui kata kunci yang tepat. Di sisi lain, penggunaan *Large Language Model* (LLM) umum menimbulkan biaya memori tinggi, latensi lambat, ketergantungan jaringan, risiko kebocoran telemetri/konteks sistem, serta halusinasi sintaks yang berbahaya.

**Dictum** adalah proyek riset dan rekayasa untuk membangun *Small Language Model* (SLM) mandiri yang mampu memahami instruksi operasional sehari-hari dalam **Bahasa Indonesia** dan **Bahasa Inggris**, memetakannya ke representasi operasi formal yang tervalidasi (*Intermediate Representation*), dan menyajikannya sebagai usulan perintah yang aman, transparan, serta dapat diaudit.

### Visi Jangka Panjang & Peran Edukasi AI Lab
* **Kedaulatan Lokal:** Setiap pengguna memiliki penerjemah OS pribadi yang berjalan 100% *offline*, ringan (< 50 MB), dapat diaudit hingga tingkat bobot dan katalog, serta dapat dilatih ulang tanpa bergantung pada API pihak ketiga.
* **Instrumen Riset AI Lab:** Proyek ini berfungsi sebagai wahana eksperimen terstruktur melalui tiga pilar: **Explore** (inspeksi mekanisme tokenisasi, atensi, dan kuantisasi), **Experiment** (pelatihan dari nol dan komparasi arsitektur), dan **Research** (pengujian hipotesis ilmiah yang dapat direproduksi).
* **Pragmatisme Rekayasa:** Model hasil *training from scratch* adalah keluaran riset utama. Namun, pada produk praktis, pendekatan non-neural (retrieval/classifier) atau hibrida akan digunakan jika bukti empiris menunjukkan rasio akurasi-biaya yang lebih unggul.

### Empat Hukum Desain Dictum
1. **Manusia menyatakan maksud**, model hanya mengusulkan struktur semantik.
2. **Katalog dan aturan deterministik menentukan operasi yang sah**, bukan probabilitas token model.
3. **Manusia memegang kendali penuh atas eksekusi**, dengan *preview* eksplisit sebelum tindakan apa pun.
4. **Dictum adalah alat bantu presisi**, bukan pengganti shell, administrator sistem, maupun dokumentasi resmi OS.

---

## 2. Pertanyaan Riset (RQ) dan Hipotesis Terukur

Seluruh eksperimen pada Fase F1–F3 dirancang untuk menjawab delapan pertanyaan riset berikut:

* **RQ1 (Batas Skala Parameter):** Berapa jumlah parameter minimum (rentang 0,3M–50M) yang dibutuhkan untuk menerjemahkan maksud operasional OS dengan akurasi praktis ($\ge 90\%$)?
* **RQ2 (Struktur vs Generasi Bebas):** Apakah model kecil dengan klasifikasi *intent* dan ekstraksi *slot* bertipe mengungguli generator teks shell bebas pada anggaran komputasi dan memori yang setara?
* **RQ3 (Dampak Eksternalisasi Katalog):** Sejauh mana pemisahan katalog operasi mengurangi kebutuhan jumlah parameter, ukuran dataset latih, dan frekuensi *retraining* saat versi utilitas OS berubah?
* **RQ4 (Efektivitas Data Sintetis Tervalidasi):** Apakah korpus sintetis yang divalidasi secara skematis mampu meningkatkan generalisasi pada kombinasi argumen, variasi bahasa (ID/EN), dan lingkungan yang tidak terlihat (*unseen*) saat pelatihan?
* **RQ5 (Kontribusi Komponen Arsitektur):** Seberapa besar kontribusi relatif dari desain tokenizer, *copy/pointer mechanism*, retrieval top-$k$, *constrained decoding*, kuantisasi INT8, dan injeksi konteks OS terhadap akurasi akhir?
* **RQ6 (Batas Kegunaan Neural Model):** Pada titik mana *classifier* klasik (fastText/linear) atau *retrieval* (BM25) sudah memadai sehingga model neural tidak memberikan manfaat bersih (*net benefit*)?
* **RQ7 (Kalibrasi Ketidakpastian & Keamanan):** Bagaimana mengukur dan meningkatkan kemampuan model untuk menolak (*abstain*) atau meminta klarifikasi saat menghadapi input ambigu/OOD, terutama pada kasus *high-confidence error*?
* **RQ8 (Portabilitas Lintas-OS):** Dapatkah satu model semantik inti memetakan *intent* yang sama ke operasi berbeda pada Linux (Debian/Ubuntu) dan Windows (PowerShell) melalui lapisan *adapter* tanpa melatih ulang pengetahuan sintaks?

### Hipotesis Kerja
* **H1:** Kombinasi katalog operasi deterministik + model *intent/slot* kecil ($\le 10	ext{M}$ parameter) mencapai kualitas setara atau lebih baik dibanding generator shell umum ($0,5	ext{B}–1	ext{B}$) dengan jejak memori $>20	imes$ lebih kecil.
* **H2:** *Constrained decoding* (grammar/schema) hanya mengeliminasi kesalahan sintaks struktural, tetapi tidak mencegah kesalahan pemilihan *intent* maupun pelanggaran kebijakan keamanan.
* **H3:** Metrik *exact match* string perintah tidak memadai untuk evaluasi OS; kesetaraan hasil eksekusi (*execution equivalence*) pada *fixture* terkontrol merupakan indikator kebenaran yang sahih.
* **H4:** Model yang dilatih dari bobot acak (*from scratch*) mampu bekerja efektif pada domain sempit, namun tidak boleh diasumsikan otomatis mengungguli *baseline retrieval* tanpa pembuktian statistik.

> **Catatan Metodologis:** Seluruh hipotesis di atas bersifat *falsifiable*. Kegagalan hipotesis (hasil negatif) wajib didokumentasikan sebagai temuan ilmiah yang sah dan menjadi dasar pengambilan keputusan arsitektur berikutnya.

---

## 3. Target Pengguna dan Cakupan Use Case MVP

### Profil Pengguna & Lingkungan Target
* **Pengguna Utama:** Administrator sistem lokal, pengembang perangkat lunak, operator lab infrastruktur, dan pelajar yang mempelajari administrasi Linux.
* **Lingkungan Referensi MVP (Target Utama):** Debian 13 (Trixie) x86-64 berjalan di atas VM Proxmox VE tanpa akselerator GPU (spesifikasi referensi: 2 vCPU, 2 GiB RAM).
* **Target Uji Portabilitas Tahap Lanjut:** Ubuntu 24.04 LTS (Fase F7), diikuti Windows 11 / Server dengan PowerShell 7.5+ dan FreeBSD.

### Sampel Kasus Penggunaan & Pemetaan Perilaku

| Instruksi Pengguna | Intent Canonical | Kategori Risiko | Perilaku Sistem MVP |
| :--- | :--- | :--- | :--- |
| *"siapa yang menggunakan port 5432?"* | `network.listener.lookup` | `READ` | Menampilkan `ss -ltnp 'sport = :5432'`; catatan bahwa PID proses milik user lain butuh hak akses lebih tinggi. |
| *"tampilkan lima direktori terbesar di sini"* | `storage.directory.usage` | `READ` | Menampilkan perintah `du` dengan batas kedalaman, *sorting*, `head -n 5`, dan konteks `cwd` saat ini. |
| *"service apa yang gagal sejak boot?"* | `service.failed.list` | `READ` | Menampilkan `systemctl --failed --no-pager`; membedakan unit yang saat ini *failed* vs riwayat log. |
| *"tunjukkan log nginx 10 menit terakhir"* | `log.service.query` | `READ` | Ekstraksi slot `unit="nginx"`, `since="10m"`; merender perintah `journalctl` terikat batas baris. |
| *"berapa RAM yang masih tersedia?"* | `memory.summary` | `READ` | Menekankan kolom `available` (bukan sekadar `free`) menggunakan `free -h` atau `/proc/meminfo`. |
| *"cari file PDF yang diubah kemarin"* | `file.search` | `READ` | Ekstraksi ekstensi `.pdf`, rentang waktu relatif terhadap zona waktu host, dan batas direktori pencarian. |
| *"apa arti opsi -ltnp di ss?"* | `help.command.explain` | `INFO` | Penjelasan deterministik bersumber langsung dari katalog terverifikasi dan `man` lokal yang dipin. |
| *"kenapa PostgreSQL tidak bisa diakses?"* | `diagnosis.connectivity` | `READ` | Menyajikan *checklist* diagnostik baca bertahap (status service → port → socket lokal) tanpa mengubah konfigurasi. |
| *"restart service nginx"* | `service.restart` | `CHANGE` | **Proposal-Only:** Menampilkan usulan perintah dan dampak perubahan state; tombol eksekusi dinonaktifkan di MVP. |
| *"bersihkan disk"* | `ambiguous` | `UNKNOWN` | **Clarify:** Menolak menebak penghapusan; meminta pengguna menentukan direktori target atau jenis pembersihan. |

---

## 4. Scope Kontrak dan Anti-Scope (Non-Goals)

### Ruang Lingkup MVP (Fase F0–F6)
1. **Satu Host Lokal:** Operasi ditujukan eksklusif untuk mesin lokal tempat Dictum dijalankan (Debian 13).
2. **Dukungan Bilingual:** Bahasa Indonesia (formal & kasual teknis) dan Bahasa Inggris, termasuk *code-switching* umum (contoh: *"cek status service postgresql"*).
3. **48 Intent Terdefinisi:** Terdiri dari 44 *intent* kategori `INFO` dan `READ`, serta 4 *intent* kategori `CHANGE` terbatas yang hanya beroperasi dalam mode *proposal-only* (lihat Lampiran A).
4. **Ekstraksi Argumen Bertipe & Validasi:** Konversi slot menjadi tipe data ketat sebelum kompilasi perintah.
5. **Mode Eksekusi Bertahap:** Default sistem adalah **Proposal-Only** (menampilkan perintah, penjelasan, sumber versi, dan opsi salin). Eksekusi otomatis untuk operasi `READ` hanya dapat diaktifkan secara eksplisit (*opt-in*) setelah lulus audit keamanan Fase F5.

### Anti-Scope (Dilarang Keras pada v1)
* **Bukan Chatbot Umum:** Tidak menjawab pertanyaan pengetahuan umum, penulisan kode aplikasi, atau percakapan terbuka.
* **Tanpa Ketergantungan Cloud/Jaringan:** Tidak ada panggilan API eksternal, telemetri, pembaruan otomatis, atau *web search* saat *inference*.
* **Bukan Agent Otonom:** Tidak ada *loop* eksekusi mandiri berdasarkan `stdout`/`stderr`, tidak ada eskalasi `sudo`/`root` otomatis, dan tidak ada modifikasi konfigurasi sistem secara diam-diam.
* **Tanpa Generasi Script Bebas:** Model dilarang menghasilkan *one-liner* Bash kompleks, *pipe* sembarangan, atau *subshell* (`$(...)`, backticks).
* **Runtime Bebas Interpreter Berat:** Produk rilis tidak boleh bergantung pada Python, Node.js, JVM, atau Electron. (Python/PyTorch hanya digunakan pada tahap *offline training* dan *test harness*).

---

## 5. Arsitektur Sistem: Pemisahan Pengetahuan, Model, dan Otoritas

Arsitektur Dictum memisahkan secara fisik antara **pemahaman bahasa** (probabilistik), **pengetahuan perintah** (deklaratif/katalog), dan **otoritas eksekusi** (deterministik).

```text
+-----------------------------------------------------------------------+
| 1. INPUT & CONTEXT LAYER                                              |
|    CLI / TUI  --->  Input Normalizer (NFC, Length Cap)                |
|                     Bounded OS Context Probe (Enum/ID Only)           |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 2. NLU & RETRIEVAL LAYER (Untrusted Proposal Generator)               |
|    Tokenizer  --->  [Baseline B0-B2 / Mini-Model M0-M2]               |
|                     + Catalog Retriever (Top-K Candidates)            |
|                     Output: Ranked Intent, Typed Slots, Uncertainty   |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 3. RESOLUTION & POLICY LAYER (Deterministic Authority)                |
|    Slot Resolver & Type Checker  --->  Operation IR (JSON)            |
|    Policy Validator (Risk Class, Scope, Allowlist, Binary Check)      |
|    Decision: PROPOSE | CLARIFY | UNSUPPORTED | DENY                   |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 4. COMPILATION & EXECUTION LAYER (Isolated / Least Privilege)         |
|    Deterministic Compiler  --->  Immutable Plan (argv[] + SHA-256)    |
|    Explicit User Approval (if Execute Mode enabled & Policy allows)   |
|    Sandboxed Executor (execve without shell, bounded output/timeout)  |
|    Deterministic Renderer  --->  Formatted Output + Audit Log         |
+-----------------------------------------------------------------------+
```

### 5.1 Kontrak Intermediate Representation (IR v1)

IR adalah bahasa perantara terstruktur yang menjadi satu-satunya antarmuka antara komponen NLU dan *Policy Validator*. Model **tidak pernah** menghasilkan string perintah shell secara langsung.

```json
{
  "$schema": "https://dictum.local/spec/ir-v1.schema.json",
  "schema_version": "1.0.0",
  "request_id": "req-20261124-001",
  "decision": "propose",
  "intent": "network.listener.lookup",
  "confidence": {
    "intent_score": 0.94,
    "margin_top2": 0.61,
    "calibrated_uncertainty": "low"
  },
  "slots": {
    "port": { "type": "port", "value": 5432, "source": "user_literal" },
    "protocol": { "type": "enum_proto", "value": "tcp", "source": "catalog_default" }
  },
  "context_ref": {
    "os_profile": "debian-13-x86_64",
    "catalog_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015..."
  },
  "abstain_reason": null
}
```

#### Aturan Ketat IR:
1. **Isolasi Otoritas:** Field `risk_class`, `executable_path`, `privilege_level`, dan `approval_token` **dilarang** ada di dalam output model; seluruhnya diinjeksi oleh *Policy Validator* setelah pencocokan katalog.
2. **Tipe Data Slot Ketat:** Setiap slot wajib divalidasi terhadap tipe primitif berikut:
   * `port`: Integer `1..65535`
   * `enum_proto`: `"tcp" | "udp" | "all"`
   * `duration`: String ISO-8601 duration atau integer detik terikat batas maksimum katalog (misal maks `7d`)
   * `safe_path`: Path kanonik tanpa karakter kontrol, diverifikasi terhadap batas direktori yang diizinkan
   * `unit_name`: Regex `^[a-zA-Z0-9:._@-]{1,128}$`
   * `positive_int`: Integer `1..1000` (untuk limit/top-$N$)
3. **Pemetaan Keputusan:**
   * Slot wajib kosong atau skor ambigu (`margin_top2 < threshold`) $
ightarrow$ `decision: "clarify"`.
   * *Intent* di luar domain atau tidak ada di katalog $
ightarrow$ `decision: "unsupported"`.
   * Melanggar batasan kebijakan atau tipe data $
ightarrow$ `decision: "deny"`.

### 5.2 Katalog Operasi & OS Context Probe

* **Katalog Terversi (`catalog/debian/v1.json`):** Merupakan *source of truth* yang ditandatangani (*pinned hash*) pada setiap rilis. Berisi definisi *intent*, skema slot, utilitas target (misal `/usr/bin/ss`), versi utilitas minimal, pemetaan argumen `argv[]`, batas output, *test fixture*, dan teks penjelasan.
* **Bounded Context Probe:** Saat startup atau per sesi, *probe* hanya membaca metadata minimal yang aman: distribusi & versi OS (`/etc/os-release`), arsitektur CPU, `cwd` aktif, `UID/GID`, zona waktu, keberadaan serta versi biner utilitas yang terdaftar di katalog, dan *service manager* aktif (`systemd`).
* **Larangan Probe:** Dilarang membaca variabel *environment* secara menyeluruh (`env`), riwayat shell (`~/.bash_history`), isi direktori `/etc` sensitif, kunci SSH, maupun melakukan pemindaian jaringan.

### 5.3 Strategi Adapter Lintas-Platform

* **Linux Adapter (MVP):** Mengeksekusi biner secara langsung melalui `execve` menggunakan array `argv[]` tanpa memanggil `/bin/sh`. Jika diperlukan penyortiran atau pemotongan baris sederhana (seperti `top 5`), hal tersebut ditangani oleh fungsi *native* di dalam runtime Dictum atau melalui argumen resmi utilitas, bukan dengan merangkai `|` (pipe) shell.
* **Windows Adapter (Masa Depan - F7):** Menggunakan *constrained PowerShell runspace* atau pemanggilan API Win32/CIM langsung dengan parameter bertipe. Dilarang keras meneruskan string ke `Invoke-Expression` (`iex`). Lingkungan WSL diperlakukan sebagai profil host Linux terpisah.

---

## 6. Strategi Model: Eksperimen Bertahap dari Nol

Dictum menerapkan disiplin ilmiah dengan tidak langsung menggunakan arsitektur Transformer sebelum mengukur *baseline* non-neural pada antarmuka input/output yang identik.

### Matriks Kandidat Model

| ID | Arsitektur / Pendekatan | Target Parameter | Peran dalam Riset & Produk |
| :--- | :--- | :--- | :--- |
| **B0** | Rule-based Keyword + Regex Slot Parser | 0 (Non-neural) | *Baseline* deterministik paling dasar; pengukur batas bawah akurasi & latensi. |
| **B1** | BM25 / Character $n$-gram Retrieval | 0 (Non-neural) | *Baseline* pencocokan katalog & contoh terdekat tanpa pelatihan bobot. |
| **B2** | fastText / Linear Classifier + CRF/Regex Slot | $< 2	ext{ MB}$ | *Baseline* pembelajaran mesin klasik yang sangat cepat di CPU. |
| **M0** | Character/Byte-level Mini Transformer | $0,3	ext{M} – 0,5	ext{M}$ | Replikasi prinsip footprint ultra-kecil (inspirasi *Tiny-2.1*); uji ketahanan typo. |
| **M1** | Bidirectional Encoder + Intent Head + BIO Slot Head + Pointer | $1	ext{M}, 3	ext{M}, 10	ext{M}$ | **Kandidat Utama Produk:** Seimbang antara akurasi semantik, ekstraksi slot, dan kecepatan CPU. |
| **M2** | Encoder-Decoder / Decoder-only (Constrained IR) | $1	ext{M}, 10	ext{M}, 25	ext{M}, 50	ext{M}$ | Uji kemampuan komposisi struktur IR kompleks dan *multi-slot*. |
| **M3** | Pretrained SLM Fine-tuned (misal Qwen/SmolLM) | $0,5	ext{B} – 1	ext{B}$ | Pembanding batas atas (*upper-bound reference*) pada hardware kelas atas; bukan target footprint utama. |

### Desain Teknis Pelatihan & Kuantisasi
1. **Pelatihan dari Bobot Acak (*From Scratch*):** Jalur utama riset untuk M0–M2 menggunakan PyTorch dengan *fixed random seeds* (minimal 3 seed untuk kandidat final). Fungsi objektif adalah gabungan *Cross-Entropy Loss* untuk klasifikasi *intent* dan *Token/Span Cross-Entropy* dengan *padding mask* untuk ekstraksi slot, ditambah *Pointer/Copy Loss* untuk menyalin nilai literal (nama file, port, nama service) langsung dari input.
2. **Desain Tokenizer:** Menggunakan *Unigram/BPE* berukuran kecil ($4	ext{k}–8	ext{k}$ token) yang dilatih **hanya** pada data `train` (dilarang menyentuh data `dev`/`test`), dilengkapi token atomik khusus untuk penanda struktur dan karakter ASCII/byte *fallback* agar nama path yang *case-sensitive* tidak mengalami normalisasi *lossy* (misal tidak mengubah huruf kapital menjadi huruf kecil secara paksa).
3. **Format Biner Model Pack (`.dctm`):** Untuk menjaga runtime C bebas dari ketergantungan kompleks dan aman dari serangan deserialisasi (seperti *pickle exploit*), model diekspor ke format biner kustom sederhana dengan struktur:
   * `Header (64 bytes)`: Magic bytes (`DCTM`), versi format (`1`), SHA-256 hash bobot, SHA-256 hash katalog yang kompatibel, jumlah layer/dimensi, dan tipe kuantisasi.
   * `Tokenizer Table`: Tabel kosakata terindeks statis.
   * `Tensor Payloads`: Bobot matriks *aligned* 64-byte untuk optimalisasi SIMD (AVX2/NEON).
4. **Protokol Kuantisasi:** Evaluasi konversi pasca-pelatihan (*PTQ*) dari FP32 ke **INT8 per-channel** (target ukuran bobot $1	ext{M} pprox 1	ext{ MB}$, $10	ext{M} pprox 10	ext{ MB}$). Kuantisasi INT4 hanya dieksplorasi jika penurunan akurasi *joint intent-slot* tidak melebihi $1,5\%$ dibanding FP32. Wajib lulus uji *numerical parity* antara referensi Python dan runtime C (toleransi selisih logit $\le 10^{-3}$ pada INT8).

---

## 7. Strategi Dataset: OS-Intent Corpus v1

### Komposisi & Target Skala Corpus
* **Gold Dataset (Kurasi Manusia):** Minimal **300 contoh** untuk set *supported* (rata-rata $\ge 6$ variasi per *intent*), **150 contoh** untuk kasus *ambiguous/OOD*, dan **200 contoh** *adversarial/security*. Seluruhnya ditulis dan diverifikasi manual oleh manusia.
* **Synthetic Dataset (Tervalidasi):** **15.000 – 40.000 contoh** yang dibangkitkan secara terprogram dari templat katalog dan parafrase terkontrol dengan distribusi bahasa **70% Bahasa Indonesia** (mencakup ragam formal, sehari-hari, singkatan umum, dan salah ketik ringan) dan **30% Bahasa Inggris**.

### Pipeline Pembuatan & Tata Kelola Data
1. **Ekstraksi Sumber Katalog:** Menggunakan dokumentasi resmi (`man` dan `--help`) yang dipin pada paket Debian 13 sebagai sumber kebenaran semantik. Dataset publik seperti *tldr-pages*, *NL2Bash*, dan *NLC2CMD* hanya digunakan sebagai inspirasi struktur parafrase atau pembanding evaluasi setelah audit lisensi ketat; tidak ada perintah dari dataset eksternal yang langsung dieksekusi tanpa penulisan ulang ke skema IR Dictum.
2. **Validasi Otomatis (*Gatekeeper* Data):** Setiap record sintetis hasil parafrase wajib melewati:
   * Validasi skema JSON dan tipe slot.
   * Pemeriksaan *round-trip* kompilasi ke `argv[]` yang sah.
   * Deteksi *near-duplicate* menggunakan MinHash/Jaccard similarity agar tidak terjadi dominasi satu pola kalimat.
3. **Protokol Pembagian Data (*Anti-Leakage Split*):** Pembagian `train` (70%), `dev` (15%), dan `test` (15%) dilakukan berdasarkan **kelompok templat semantik (*group-based split*)** sebelum augmentasi parafrase dilakukan. Hal ini menjamin variasi kalimat dari satu pola yang sama tidak bocor ke set pengujian. Selain itu, disiapkan set *Blind Human Holdout* dan *Compositional Holdout* (kombinasi slot yang belum pernah muncul bersamaan saat latih) yang dikunci dan haram digunakan untuk *hyperparameter tuning*.
4. **Sanitasi Privasi:** Dilarang keras memasukkan log produksi nyata, alamat IP internal, nama host spesifik, kredensial, atau path direktori pengguna nyata ke dalam repositori maupun prompt *teacher LLM*.

---

## 8. Runtime Native & Desain Pengalaman Pengguna (UX)

### Spesifikasi Teknis Runtime
* **Bahasa & Build System:** **C17** standar dengan **CMake** (dan *fallback* `Makefile` sederhana). Pemilihan C17 didasarkan pada waktu kompilasi cepat, ukuran biner sangat kecil ($< 1	ext{ MB}$ untuk *engine*), kemudahan audit memori manual, serta portabilitas tinggi antar-arsitektur Linux tanpa runtime tambahan.
* **Strategi Komputasi:** Implementasi referensi menggunakan kode skalar C17 yang bersih dan mudah diverifikasi kebenarannya, diikuti optimasi intrinsik SIMD (AVX2 untuk x86-64, NEON untuk ARM64) hanya pada operasi perkalian matriks (*GEMV/GEMM*) setelah *profiling* membuktikan kebutuhan. Jumlah *thread* dibatasi maksimal 2 *thread* agar tidak mengganggu beban kerja utama host.
* **Artefak Distribusi:** Satu biner statis/semi-statis (`dictum`), satu berkas model (`.dctm`), dan satu berkas katalog bertanda tangan (`catalog.json`).

### Antarmuka Baris Perintah (CLI)

```bash
# 1. Mode default (Proposal-Only): menerjemahkan maksud & menampilkan preview aman
dictum ask "siapa yang menggunakan port 8080?"

# 2. Penjelasan rinci mengenai alasan pemilihan intent, argumen, dan batasannya
dictum explain "siapa yang menggunakan port 8080?"

# 3. Pencarian deterministik langsung ke katalog/manpage tanpa melibatkan model neural
dictum search "port listener"

# 4. Eksekusi opt-in (hanya aktif jika diizinkan kebijakan & setelah konfirmasi interaktif)
dictum run "berapa RAM yang masih tersedia?"

# 5. Inspeksi metadata model, hash katalog, profil OS, dan latensi inference
dictum inspect

# 6. Mode edukasi AI Lab: menampilkan tokenisasi, probabilitas top-k, dan profil kuantisasi
dictum lab "tampilkan log nginx 10 menit terakhir"
```

### Prinsip Desain UX
* **Transparansi Ringkas:** Output default menampilkan: (1) Perintah yang diusulkan, (2) Penjelasan fungsi dalam satu kalimat, (3) Tingkat risiko & ruang lingkup (`READ / Lokal`), dan (4) Sumber referensi utilitas.
* **Klarifikasi Terarah:** Jika masukan pengguna ambigu (misal *"hapus file lama"*), sistem tidak menampilkan pesan error generik, melainkan menjelaskan mengapa permintaan ditolak/ditunda dan memberikan contoh cara memperjelas maksud.
* **Proteksi Shell History:** Dictum tidak pernah menyuntikkan perintah usulan secara otomatis ke dalam *shell history* pengguna sebagai perintah yang telah dieksekusi.

---

## 9. Kontrak Keamanan (Security Architecture & Policy)

Keamanan dalam Dictum bersifat **deterministik dan berlapis (*defense-in-depth*)**. Output model selalu diperlakukan sebagai masukan tidak tepercaya (*untrusted input*), setara dengan input jaringan eksternal.

### Klasifikasi Risiko Operasi
* **`INFO`:** Penjelasan dokumentasi atau inspeksi metadata internal Dictum. Tidak memicu proses eksternal.
* **`READ`:** Operasi pembacaan status sistem lokal yang dibatasi ruang lingkupnya (tidak membaca berkas kredensial/konfigurasi sensitif). Diizinkan untuk mode `dictum run` setelah lulus F5.
* **`CHANGE`:** Operasi yang mengubah status sistem atau layanan (misal `service.restart`). Pada v1 **wajib Proposal-Only** (diblokir di lapisan *Executor*).
* **`HIGH`:** Operasi destruktif (`rm`, `dd`, `mkfs`), eskalasi hak akses (`sudo`, `su`), akses jaringan keluar, atau modifikasi kebijakan keamanan. **Ditolak mutlak (*Hard Deny*)** di seluruh komponen.
* **`UNKNOWN`:** Maksud tidak dikenali atau gagal divalidasi. **Fail-Closed (Deny)**.

### Kontrol Teknis Wajib
1. **Eliminasi Shell & Option Injection:**
   * Eksekusi hanya menggunakan `execve()` dengan array `argv[]` eksplisit.
   * Setiap perintah wajib menyertakan terminator opsi `--` sebelum argumen posisional (jika didukung utilitas) untuk mencegah nama file berawalan tanda hubung (seperti `-rf`) ditafsirkan sebagai *flag*.
   * Jalur biner wajib berupa *absolute path* yang telah diverifikasi identitas dan hash/ kepemilikannya (`root:root`, tidak *world-writable*), mengabaikan variabel `PATH` pengguna.
2. **Pengikatan Persetujuan (*Cryptographic Approval Binding*):**
   * Rencana eksekusi (*Execution Plan*) di-hash menggunakan **SHA-256** mencakup: path biner, seluruh elemen `argv[]`, `cwd` kanonik, versi katalog, UID pengguna, dan *timestamp* kedaluwarsa (TTL maksimal 30 detik).
   * Persetujuan pengguna mengikat digest tersebut secara satu kali pakai (*single-use nonce*). Perubahan sekecil apa pun pada target atau konteks membatalkan token persetujuan.
3. **Mitigasi TOCTOU & Symlink Attack:**
   * Untuk operasi yang menyasar berkas atau direktori, *Executor* membuka target menggunakan `openat()` dengan bendera `O_NOFOLLOW` dan memvalidasi metadata melalui `fstat()` sebelum meneruskan *file descriptor* atau path terverifikasi, mencegah serangan *symlink race condition*.
4. **Isolasi Proses & Pembatasan Sumber Daya:**
   * Proses anak dijalankan dengan pembersihan variabel *environment* (*strict allowlist*: `LC_ALL=C.UTF-8`, `PATH=/usr/bin:/bin`), penutupan seluruh *file descriptor* warisan selain `stdin/stdout/stderr`, penetapan `PR_SET_NO_NEW_PRIVS`, pembatasan sumber daya (`setrlimit` untuk waktu CPU, memori virtual, dan ukuran output maks `64 KiB`), serta *timeout* keras (default 5 detik) dengan terminasi seluruh *process group* (`killpg`).
   * Pengujian eksekusi selama pengembangan (Fase F5) dilakukan secara eksklusif di dalam VM Debian 13 terisolasi (*disposable snapshot*) tanpa akses jaringan keluar dan tanpa *shared folder* ke host Proxmox.
5. **Sanitasi Output & Audit Trail:**
   * Seluruh `stdout`/`stderr` yang ditampilkan ke terminal disanitasi dari karakter kontrol ANSI berbahaya (*terminal escape injection*).
   * Setiap permintaan mencatat log audit terstruktur minimal (`timestamp`, `request_id`, `intent`, `decision`, `plan_digest`, `exit_code`, `latency_ms`) tanpa menyimpan argumen sensitif atau isi output mentah secara default.

### Daftar Release Blocker (Zero-Tolerance)
Rilis v1 dianggap **GAGAL** dan tidak boleh dipublikasikan apabila ditemukan satu saja kondisi berikut:
* Kemampuan melewati validasi kebijakan (*policy bypass*).
* Eksekusi perintah di luar katalog atau terjadinya *command/option injection*.
* Kebocoran data keluar mesin (*data egress*) atau pembacaan berkas di luar *scope* yang diizinkan.
* Penggunaan kembali (*replay*) token persetujuan yang sudah kedaluwarsa atau berbeda digest.
* Kegagalan gagal-aman (*fail-open*) ketika berkas model atau katalog rusak/dimodifikasi.

---

## 10. Protokol Benchmark dan Evaluasi Ilmiah

Seluruh kandidat (`B0–B2`, `M0–M3`) dievaluasi menggunakan perangkat uji (*evaluation harness*) yang identik pada VM referensi Debian 13 (2 vCPU, 2 GiB RAM).

### Definisi Metrik Utama
1. **Kualitas Pemahaman NLU (Model-Level):**
   * *Intent Macro-F1* dan *Slot Span Exact-F1*.
   * *Joint Intent-Slot Accuracy*: Persentase permintaan di mana *intent* dan seluruh *slot* beserta tipenya tepat 100%.
   * *Selective Risk & Coverage Curve*: Mengukur akurasi pada cakupan (*coverage*) permintaan yang diterima sistem pada berbagai ambang batas kepercayaan (*confidence threshold*), serta tingkat *OOD/Unsafe Refusal Recall*.
2. **Kebenaran Operasional (End-to-End):**
   * *Execution Equivalence Rate*: Persentase kasus uji di mana perintah yang dikompilasi menghasilkan keluaran terstruktur dan status sistem yang setara dengan *oracle* pada *fixture* VM bersih, tanpa efek samping terlarang.
   * *Policy Compliance Rate*: Wajib **100%** pada seluruh kasus uji keamanan (200+ skenario adversarial).
3. **Efisiensi Sumber Daya (System-Level):**
   * *Cold Start Latency* (memuat biner + model + katalog hingga siap memproses).
   * *Warm Proposal Latency* ($p50$ dan $p95$ dari masukan teks hingga IR tervalidasi).
   * *Peak RSS Memory* (target $\le 128	ext{ MiB}$) dan total ukuran paket disk (target bobot model $\le 50	ext{ MB}$).

### Kriteria Kelulusan MVP (Quantitative Gates)
* **Joint Accuracy (Blind Supported Set):** $\ge 90,0\%$
* **End-to-End Fixture Equivalence:** $\ge 90,0\%$ (pada permintaan yang tidak di-*abstain*)
* **OOD & Ambiguity Refusal Recall:** $\ge 95,0\%$
* **Security Policy Violations:** $0$ pelanggaran teramati (*zero observed*)
* **Latensi Proposal Warm ($p95$):** $\le 500	ext{ ms}$ pada 2 vCPU
* **Peak RSS Footprint:** $\le 128	ext{ MiB}$

> **Aturan Integritas Benchmark:** Ambang batas kelulusan di atas dikunci sebelum evaluasi *blind test* dijalankan. Dilarang mengubah *threshold* setelah melihat hasil pengujian akhir. Laporan wajib menyertakan interval kepercayaan 95% (*confidence interval*) dan varians antar-seed.

---

## 11. Roadmap Bertahap dan Gerbang Keputusan (Gates)

| Fase | Nama Fase | Deliverable Utama | Kriteria Gerbang (Gate GO/NO-GO) |
| :--- | :--- | :--- | :--- |
| **F0** | **Kontrak & Spesifikasi** | Dokumen v1 disetujui, JSON Schema IR, skema Katalog, 48 daftar intent, *Threat Model*, audit lisensi. | Tinjauan manusia selesai; tidak ada kode produksi/eksekusi sebelum F0 disetujui. |
| **F1** | **Katalog & Baseline** | Implementasi katalog Debian 13 (48 intent), *Context Probe*, CLI *Proposal-Only*, baseline `B0/B1/B2`, dan 300+ *Gold Dataset*. | Seluruh *gold fixture* lulus uji validator; angka *baseline* terukur sebagai patokan. |
| **F2** | **Mini-Model Eksperimen** | Tokenizer domain, skrip pelatihan PyTorch dari nol (`M0` & `M1` 1M/3M), format `.dctm`, *reference inference*. | Pelatihan *reproducible*; mengungguli `B1/B2` pada set `dev` tanpa menyentuh `blind test`. |
| **F3** | **Evaluasi Komparatif** | Studi ablasi (tokenizer, pointer, retrieval), evaluasi `M2`/`M3` (pembanding), kurva Pareto ukuran vs akurasi. | Memilih model terkecil yang memenuhi *gate* kualitas, atau memutuskan kembali ke `B2`/hibrida jika neural tidak efisien. |
| **F4** | **Native Runtime C17** | Mesin inferensi C17 mandiri, kuantisasi INT8, pemuat `.dctm` dengan verifikasi hash, paket rilis *offline*. | Paritas numerik Python vs C terverifikasi; RSS $\le 128	ext{ MiB}$; korup file gagal aman (*fail-closed*). |
| **F5** | **Isolated Executor** | *Compiler* deterministik, *Policy Validator*, *Approval Digest*, *Sandbox Executor* (`execve`, `seccomp`/`rlimit`), *fuzz testing*. | **0 pelanggaran** pada 200+ uji keamanan & *fuzzing*; lulus audit keamanan mandiri. |
| **F6** | **Daily-Use Pilot** | Uji coba penggunaan harian lokal (mode *Proposal-Only* default, *opt-in* `READ` jika F5 lulus), evaluasi kegunaan (*usability*). | Umpan balik pengguna lokal positif; rilis resmi `v1.0.0` bertanda tangan. |
| **F7** | **Ekstensi Lintas-OS** | *Adapter* Ubuntu 24.04, Windows/PowerShell, FreeBSD, dan antarmuka edukasi `dictum lab` lanjutan. | Setiap *adapter* melewati gerbang pengujian terisolasi masing-masing; operasi `CHANGE/HIGH` tetap terkunci. |

---

## 12. Struktur Repositori Standar

Struktur direktori berikut dibakukan mulai Fase F0 untuk memisahkan spesifikasi, data, pelatihan *offline*, dan kode runtime *native*:

```text
ai-lab-dictum/
├── plans/
│   ├── drafts/                 # Arsip draft historis (immutable, termasuk rencana-v0.md)
│   └── approved/               # Kontrak aktif yang disetujui (rencana-v1.md)
├── docs/
│   ├── adr/                    # Architecture Decision Records (format MADR)
│   ├── security/               # Threat model, matriks kebijakan, laporan audit F5
│   └── research/               # Kartu eksperimen, catatan ablasi, laporan benchmark
├── spec/
│   ├── ir/                     # JSON Schema untuk IR v1 & aturan kompatibilitas
│   ├── catalog/                # JSON Schema untuk definisi katalog operasi
│   └── model-pack/             # Spesifikasi format biner .dctm
├── catalog/
│   ├── core/                   # Definisi abstrak 48 intent lintas-platform
│   └── debian-13/              # Implementasi konkret & fixture untuk Debian 13
├── data/
│   ├── gold/                   # Dataset kurasi manusia (versi terkontrol di Git)
│   ├── manifests/              # Provenance, SHA-256 checksum, license ledger
│   └── fixtures/               # Snapshot lingkungan uji & oracle deterministik
├── training/
│   ├── tokenizers/             # Skrip & konfigurasi pelatihan tokenizer
│   ├── configs/                # Hyperparameter & seed konfigurasi eksperimen
│   └── scripts/                # Pipeline PyTorch training, evaluasi, dan eksportir .dctm
├── runtime/
│   ├── reference/              # Implementasi referensi Python (test oracle)
│   └── native/                 # Implementasi produksi C17 (loader, tensor ops, SIMD)
├── adapters/
│   └── linux/                  # Context probe, compiler argv[], dan sandbox executor POSIX
├── cli/                        # Antarmuka baris perintah dictum (ask, explain, search, run, lab)
├── tests/
│   ├── unit/                   # Uji unit parser, validator slot, dan sanitizer
│   ├── golden/                 # Uji paritas output Python vs C17
│   ├── execution/              # Uji integrasi pada VM disposable
│   └── security/               # Suite adversarial, fuzzing, dan uji bypass kebijakan
└── benchmarks/
    ├── harness/                # Otomasi pengukuran latensi, memori, dan akurasi
    └── reports/                # Hasil benchmark terverifikasi (JSON & Markdown)
```

> **Kebijakan Git:** Berkas bobot model (`.dctm`), dataset sintetis berukuran besar ($>5	ext{ MB}$), dan log pelatihan tidak disimpan langsung di riwayat Git utama, melainkan dikelola melalui *GitHub Releases* atau penyimpanan artefak terverifikasi dengan manifes SHA-256 di direktori `data/manifests/`.

---

## 13. Keputusan Arsitektur Terkunci (Resolusi v1)

Menutup daftar keputusan terbuka pada `DRAFT-0`, berikut adalah ketetapan resmi untuk implementasi v1:

1. **Bahasa Runtime Produksi:** **C17** murni dengan pustaka standar POSIX/Linux, dibangun menggunakan **CMake**. Alasan: jejak memori minimal, waktu *cold start* sub-milidetik, serta kemudahan audit keamanan tanpa *garbage collector* atau runtime eksternal.
2. **Skema Lisensi Terpisah:**
   * Kode sumber (*runtime, CLI, training scripts*): **MIT License**.
   * Spesifikasi IR & Katalog Operasi: **Apache License 2.0** (memberikan perlindungan paten dan kejelasan kontribusi).
   * Dataset *Gold* & *OS-Intent Corpus* buatan sendiri: **CC-BY-SA-4.0**.
3. **Mode Produk Awal (MVP):** Rilis `v1.0` beroperasi secara default dalam mode **Proposal-Only**. Fitur `dictum run` (khusus kelas `READ`) hanya dibuka melalui *flag* konfigurasi eksplisit setelah seluruh *gate* keamanan Fase F5 dinyatakan lulus.
4. **Arsitektur Kandidat Pertama:** **M1 (Bidirectional Encoder 4-layer, $d_{	ext{model}}=128$, $pprox 1,2	ext{M}$ parameter)** dengan *Intent Classification Head*, *BIO Slot Tagging Head*, dan *Pointer/Copy Mechanism*, dibandingkan langsung terhadap **B1 (BM25)** dan **B2 (fastText + Regex)**.
5. **Mekanisme Isolasi Executor:** Kombinasi *privilege dropping*, sanitasi *environment*, pembatasan `setrlimit`, `PR_SET_NO_NEW_PRIVS`, `openat(..., O_NOFOLLOW)`, serta filter `seccomp-bpf` mode *allowlist* untuk panggilan sistem dasar.

---

## 14. Manajemen Risiko Proyek

| Kategori Risiko | Dampak | Strategi Mitigasi Terukur |
| :--- | :--- | :--- |
| **Overfitting Data Sintetis** | Model gagal pada kalimat alami manusia di dunia nyata. | *Group-based split* ketat sebelum augmentasi; evaluasi wajib pada *Blind Human Holdout* dan uji *near-miss*. |
| **Halusinasi Argumen / Target** | Model menyisipkan flag atau nama file yang tidak ada. | Slot bertipe ketat, mekanisme *copy/pointer* dari teks asli pengguna, serta validasi terhadap katalog dan *context probe*. |
| **Model Neural Tidak Efisien** | Akurasi model kecil kalah dibanding *retrieval* biasa. | Pendekatan bertahap dari `B0–B2`; jika model neural tidak memberi keunggulan signifikan, rilis produk berbasis `B2`/hibrida tetap dilanjutkan. |
| **Pergeseran Versi Utilitas OS** | Flag perintah tidak valid pada versi distro berbeda. | Pinning versi paket pada katalog, pemeriksaan versi saat *startup probe*, dan *fail-closed* jika terjadi ketidakcocokan. |
| **Kompleksitas Keamanan Executor** | Celah eksekusi perintah berbahaya (*command injection*). | Pemisahan total antara mode *Proposal-Only* (F1–F4) dan *Executor* (F5); penggunaan `execve` tanpa shell; audit independen sebelum F6. |
| **Kontaminasi Lisensi Dataset** | Hambatan distribusi publik repositori atau model. | *Clean-room authoring* untuk dataset inti; penggunaan dataset eksternal (NL2Bash/tldr) dibatasi sesuai audit lisensi masing-masing. |

---

## 15. Referensi & Landasan Ilmiah (Tinjauan per 24 November 2026)

Seluruh referensi berikut digunakan sebagai landasan desain dan pembanding metodologis (bukan klaim performa Dictum):

* **Arsitektur Ultra-Ringan & Data Sintetis:**
  * *WollyMonjac/Tiny-2.1* — Inspirasi desain transformer karakter sub-1M parameter dan jejak memori kilobyte.
  * *Eldan & Li (2023), TinyStories* — Pembuktian efektivitas korpus sintetis terkontrol untuk melatih SLM pada domain sempit.
* **Runtime C/C++ & Kuantisasi:**
  * *karpathy/llama2.c* & *karpathy/llm.c* — Referensi implementasi *forward pass* C murni, ekspor biner sederhana, dan verifikasi paritas numerik.
  * *ggml-org/llama.cpp (GBNF)* — Referensi konsep *grammar-constrained decoding* beserta batasannya terhadap kebenaran semantik.
* **Domain Natural Language to OS/Shell:**
  * *Lin et al. (LREC 2018), NL2Bash* & *Agarwal et al. (NeurIPS 2020), NLC2CMD* — Referensi struktur pemetaan bahasa alami ke perintah shell serta metrik evaluasi.
  * *IBM/nl2bash-eabench* — Landasan metodologi evaluasi berbasis eksekusi (*execution-based equivalence*) dibanding sekadar kemiripan teks.
  * *NL2Shell & Vox* — Pembanding model *pretrained* skala $0,8	ext{B}$ pada domain terminal.
  * *tldr-pages* & *ShellCheck* — Inspirasi penyusunan katalog perintah ringkas lintas platform dan analisis statis argumen shell.
* **Keamanan Sistem & AI:**
  * *OWASP Top 10 for LLM Applications 2025/2026 (LLM01 Prompt Injection, LLM06 Excessive Agency, LLM10 Improper Output Handling)* — Dasar prinsip *zero-trust* terhadap output model dan pembatasan otoritas eksekusi.
  * *Linux Manual Pages: `execve(2)`, `seccomp(2)`, `setpriv(1)`, `PR_SET_NO_NEW_PRIVS`* — Primitif isolasi proses tingkat kernel pada Debian 13.

---

## Lampiran A: Daftar Resmi 48 Intent MVP (Debian 13)

Daftar berikut mengunci ruang lingkup semantik untuk **Katalog v1**:

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
10. `network.dns.lookup` — Melakukan kueri resolusi nama domain ke alamat IP secara lokal.
11. `network.connectivity.ping` — Menguji keterjangkauan dasar ke host/IP lokal dengan jumlah paket terbatas (maks 4 paket).
12. `diagnosis.connectivity` — Menjalankan alur diagnostik baca bertahap untuk layanan jaringan lokal yang tidak merespons.

### 3. Kategori `READ` — Layanan (Systemd) & Log (7 Intent)
13. `service.status.get` — Memeriksa status berjalan (*active/inactive/failed*), PID utama, dan memori satu layanan.
14. `service.list.active` — Menampilkan daftar layanan yang sedang aktif berjalan.
15. `service.failed.list` — Menampilkan daftar layanan yang mengalami kegagalan (*failed units*).
16. `service.enabled.list` — Menampilkan layanan yang dikonfigurasi berjalan otomatis saat *boot*.
17. `log.service.query` — Mengambil log jurnal untuk satu unit layanan tertentu dengan filter waktu dan batas baris.
18. `log.system.errors` — Menampilkan log sistem dengan tingkat prioritas `err` hingga `emerg` dalam rentang waktu tertentu.
19. `log.boot.messages` — Menampilkan pesan kernel/boot terakhir (`dmesg` / `journalctl -b`).

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
39. `user.session.who` — Menampilkan pengguna yang sedang masuk (*logged in*) dan riwayat login terakhir.
40. `user.identity.info` — Menampilkan UID, GID, dan keanggotaan grup untuk pengguna saat ini.

### 6. Kategori `READ` — Diagnostik Terpadu (4 Intent)
41. `diagnosis.disk_full` — Panduan pemeriksaan bertahap saat ruang disk penuh (kapasitas, direktori besar, *inode*).
42. `diagnosis.high_load` — Panduan pemeriksaan saat beban CPU/sistem tinggi (top proses, *I/O wait*, memori).
43. `diagnosis.service_crash` — Panduan pemeriksaan saat layanan gagal mulai (status unit, log terakhir, konflik port).
44. `diagnosis.dns_failure` — Panduan pemeriksaan saat resolusi domain gagal (konfigurasi resolver, jalur jaringan).

### 7. Kategori `CHANGE` — Proposal-Only Terbatas di MVP (4 Intent)
45. `service.restart` — Menyusun usulan perintah restart layanan (wajib salin manual oleh admin di MVP).
46. `service.reload` — Menyusun usulan perintah *reload* konfigurasi layanan tanpa memutus koneksi.
47. `archive.extract.safe` — Menyusun usulan ekstraksi arsip ke subdirektori baru yang terisolasi.
48. `file.compress.archive` — Menyusun usulan pengarsipan direktori/berkas ke format `.tar.gz`.

---

## Lampiran B: Daftar Periksa Tindakan Awal (Sprint F0 → F1)

1. **[F0-01]** Simpan dokumen ini ke `plans/approved/rencana-v1.md` dan arsipkan `rencana-v0.md` ke `plans/drafts/` sebagai artefak *immutable*.
2. **[F0-02]** Buat file `spec/ir/ir-v1.schema.json` dan `spec/catalog/catalog-v1.schema.json` beserta skrip validator otomatis.
3. **[F0-03]** Buat dokumen `docs/security/threat-model-v1.md` dan `docs/adr/0001-runtime-c17-and-proposal-only-mvp.md`.
4. **[F1-01]** Susun file katalog konkret `catalog/debian-13/v1.json` untuk 48 *intent* beserta *fixture* pengujiannya.
5. **[F1-02]** Kumpulkan dan tinjau minimal 300 *gold utterances* (70% ID / 30% EN) + 150 kasus *ambiguous/OOD*.
6. **[F1-03]** Bangun prototipe CLI `dictum` (mode *Proposal-Only*) dan jalankan *benchmark* baseline `B0`, `B1`, dan `B2`.
