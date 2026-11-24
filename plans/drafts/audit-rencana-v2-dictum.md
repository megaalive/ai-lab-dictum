> **Arsip audit v2 — masukan reviewer, bukan keputusan pemilik.**
> Disalin dari lampiran percakapan sebagai teks arsip; tidak diklaim salinan byte-for-byte. Disposisi temuan tersedia di [rencana-v3.md](rencana-v3.md).

---

# Review dan Audit: `rencana-v2.md` (AI Lab — Dictum)

| | |
|---|---|
| **Objek** | `plans/drafts/rencana-v2.md`, branch `main` (504 baris, ±64,6 KB; status dokumen: DRAFT-2) |
| **Tanggal audit** | 24 November 2026 |
| **Jenis** | Desk review: konsistensi internal, kelayakan teknis, desain keamanan, metodologi evaluasi, kebersihan dokumen |
| **Tidak dilakukan** | Tidak ada kode, benchmark, atau kontrol yang dijalankan (dokumen juga tidak mengklaim ada). Bagian lisensi bukan nasihat hukum. Hanya sebagian referensi yang diverifikasi (lihat §7). |

---

## 1. Ringkasan eksekutif

**Penilaian: GO bersyarat untuk finalisasi kontrak F0; HOLD F1 sampai 3 temuan HIGH ditutup.** Ini sejalan dengan keputusan usulan dokumen sendiri (GO F0, HOLD F1, NO-GO eksekusi otomatis), dengan tambahan syarat di bawah.

Dokumen ini matang untuk sebuah draf kontrak. Angka internalnya konsisten (48 intent, pembagian kategori, prefix header DCTM 32 byte), batas klaimnya jujur (tidak ada klaim "sudah aman"), dan ada jalan keluar bila hipotesis neural gagal (kembali ke baseline). Kelemahannya bukan pada visi, melainkan pada **tiga hal yang menentukan apakah gate-gate dokumen ini bisa benar-benar dipenuhi**, ditambah beberapa kontradiksi teknis antara kontrak isolasi (§9) dan semantik intent (Lampiran A).

| Severity | Jumlah | Arti |
|---|---|---|
| HIGH | 3 | Harus diputuskan di kontrak F0; bila dibiarkan, jaminan inti atau kelayakan gate terancam |
| MEDIUM | 11 | Harus diperjelas sebelum fase terkait (F0–F5) dimulai |
| LOW | 5 | Kebersihan dokumen, konsistensi, saran praktis |

**Tiga HIGH:**

1. **A-01** — Pada MVP proposal-only, *renderer preview* adalah satu-satunya tempat data berpengaruh-model bertemu konteks eksekusi (shell milik pengguna), tetapi kontrak pengujiannya belum ada.
2. **A-02** — Proses yang menerbitkan approval tidak dipisahkan dari proses yang mem-parsing input tak tepercaya (C17, tanpa jaminan memory safety); protokol CLI↔executor belum didefinisikan.
3. **A-03** — Gate "independen" (oracle, blind holdout, review keamanan) tidak punya definisi operasional. Dokumen hanya menyebut satu "pemilik proyek" dan tidak menyebut reviewer lain, sehingga gate bisa tidak terjangkau atau diam-diam dilemahkan.

---

## 2. Cakupan dan metode

- Seluruh dokumen dibaca (§0–§16, Lampiran A–B).
- Pemeriksaan aritmetika dan hitungan ulang (jumlah intent, ukuran header, jumlah parameter, interval statistik): §6 dan Lampiran.
- Pemeriksaan silang antarbagian (mis. definisi risiko §9 vs Lampiran A; split data §7 vs scope §4).
- Pemeriksaan kelayakan teknis klaim keamanan Linux (openat2, Landlock, seccomp, cgroup v2, namespace). Beberapa butir saya tandai "sepengetahuan saya; verifikasi di VM Trixie" karena tidak diuji langsung.
- Verifikasi sebagian referensi (R01, R10, R18) lewat pencarian web: §7.
- Skala severity ditentukan relatif terhadap tujuan dokumen: kontrak F0 yang bisa diuji.

---

## 3. Kekuatan (dipertahankan)

- **Pemisahan otoritas yang tegas:** model hanya mengusulkan; risk, privilege, executable, dan approval tidak pernah berasal dari model (§5.1, §5.1a). Empat objek batas (NLUProposal → ResolvedIR → PolicyDecision → ExecutionPlan) adalah desain yang tepat.
- **Metrik yang tahan manipulasi** (§10.1): denominator seluruh supported request, abstain dihitung gagal, contoh tandingan 10/100, kasus A=0 tidak terdefinisi. Matematikanya benar: `joint = coverage × selective accuracy`, jadi gate ≥90% memang menyiratkan coverage ≥90%.
- **Efek NET dipisah dari READ**, dan "read-only bukan sinonim aman" dinyatakan eksplisit (§9).
- **Hasil negatif diterima** (H4, RQ6, off-ramp ke baseline di §11) sehingga proyek tidak terkunci pada Transformer.
- **Kejujuran klaim:** "ditangani dalam rancangan ≠ PASS", "zero observed ≠ zero risk", ukuran executable <1 MB ditandai eksploratif.
- **Format `.dctm`:** prefix 32 byte benar secara aritmetika (4+2+2+4+4+8+8), loader menolak sebelum alokasi, tidak ada hash self-referential, tidak menerima pickle.
- **Kebijakan holdout:** satu final run per preregistration, holdout diganti bila bocor.

---

## 4. Temuan

Format: **Lokasi** → **Temuan** → **Dampak** → **Rekomendasi** → **Bukti penutupan**.

### HIGH

#### A-01 — HIGH — Renderer preview belum punya kontrak keamanan yang bisa diuji
- **Lokasi:** §5.1 ("tampilan shell di-escape hanya untuk preview"), §9.1 (Preview), §10 (suite keamanan), §11 (F1–F6 proposal-only).
- **Temuan:** Sampai F5 (dan untuk CHANGE/NET/diagnosis selamanya di MVP), pengguna menyalin preview dan menjalankannya sendiri di shell mereka. Artinya fungsi *render argv → string shell* adalah satu-satunya tempat slot (yang berasal dari input pengguna dan resolver) menjadi kode di konteks eksekusi. Dokumen mengakui bahwa itu "di luar containment" dan bahwa kelemahan rendering adalah blocker rilis proposal (§9.2), tetapi tidak menetapkan: profil shell target (bash/dash/zsh/fish), aturan quoting, penolakan karakter berbahaya, maupun uji yang membuktikan preview ≡ argv.
- **Dampak:** Satu bug quoting (path berisi `'`, `$(…)`, newline, awalan `-`, karakter bidi/ANSI) mengubah "proposal-only" menjadi injeksi yang dijalankan pengguna sendiri, di luar semua kontrol F5.
- **Rekomendasi:**
  1. Spesifikasikan `render_preview(argv, shell_profile)` sebagai komponen sendiri di F0, dengan profil shell eksplisit; untuk selain POSIX sh sebutkan perbedaan (fish).
  2. Validator slot menolak: NUL, CR/LF, karakter kontrol C0/C1, ESC, override/isolate bidi (U+202A–202E, U+2066–2069), zero-width, dan byte non-UTF-8 pada jalur preview. Preview selalu satu baris (hindari eksekusi saat *paste*).
  3. Posisional aman: selalu `--` atau awalan `./` untuk operand yang bisa berawalan `-`.
  4. **Uji round-trip:** render → parse oleh shell nyata di harness → argv hasil parse harus identik byte-per-byte dengan argv terkompilasi. Jalankan sebagai property/fuzz test per shell (differential).
  5. Tambahkan kelas kasus "terminal injection / copy-paste attack" ke suite keamanan (≥200) secara eksplisit, bukan hanya di daftar metrik.
- **Bukti penutupan:** Dokumen spesifikasi renderer, korpus negatif, laporan fuzz round-trip, 0 mismatch.

#### A-02 — HIGH — Batas kepercayaan proses: authority approval vs parser input tak tepercaya
- **Lokasi:** §8 (C17, tanpa jaminan memory safety), §9 (approval: "token hanya diterbitkan oleh authority lokal"), §9.1 (executor terpisah).
- **Temuan:** Dokumen memisahkan *executor* dari inferensi/CLI, tetapi tidak menyebut proses mana yang menjadi *authority* (penerbit/pengonsumsi token approval, penyimpan nonce). Bila authority berada di proses yang sama dengan CLI/NLU (yang mem-parsing teks pengguna, JSON, katalog, dan model pack dalam C17), satu korupsi memori di parser dapat memalsukan approval. Protokol IPC CLI↔authority↔executor juga belum ada, padahal seluruh jaminan approval bergantung padanya.
- **Dampak:** TCB (trusted computing base) lebih besar dari yang dinyatakan; jaminan "approval terikat digest, single-use" bisa dilangkahi tanpa menyentuh executor.
- **Rekomendasi:** Tetapkan tiga peran proses di F0:
  1. **Front** (CLI/NLU/inferensi): memproses semua input tak tepercaya; di-sandbox sendiri (tanpa jaringan, tanpa exec, seccomp, Landlock read-only ke model/katalog).
  2. **Broker/authority**: sangat kecil; hanya menerima frame biner berukuran tetap; memegang policy, digest, nonce, kunci MAC sesi; tidak mem-parsing bahasa alami atau JSON bebas.
  3. **Executor**: terkurung per §9.1.
  Definisikan IPC: Unix domain `SOCK_SEQPACKET`, autentikasi peer via `SO_PEERCRED`, panjang frame dibatasi, aturan FD-passing. Pertimbangkan di ADR apakah broker perlu bahasa memory-safe (opsional; dokumen saat ini hanya membandingkan C++/NativeAOT).
- **Bukti penutupan:** ADR + diagram TCB, spesifikasi frame IPC, uji fuzz parser frame, uji "front dikompromikan tidak bisa memalsukan approval".

#### A-03 — HIGH — "Independen" tidak punya definisi operasional
- **Lokasi:** §7.1 (oracle "dibuat oleh penulis/implementasi terpisah", blind authoring dipisah, agreement antar-reviewer), §9.2 dan §11 F5 ("review independen"), §16 (F0-01, F0-07 "keputusan pemilik").
- **Temuan:** Banyak gate bergantung pada independensi (oracle, blind holdout, review keamanan, audit semantik manusia). Dokumen hanya menyebut satu "pemilik proyek" dan tidak menjelaskan siapa reviewer, berapa orang, atau apa yang terjadi bila tidak tersedia.
- **Dampak:** Dua kemungkinan buruk: gate tidak pernah terpenuhi (proyek macet), atau dipenuhi secara formal oleh self-review sehingga klaim "independen" tidak bermakna. Yang kedua merusak nilai seluruh evidence matrix.
- **Rekomendasi:** Definisikan tingkat independensi dan label bukti:
  - `SELF` (pemilik sendiri), `SELF+DELAY` (pemilik, pemisahan waktu ≥ N hari, checklist tertulis), `LLM-ADV` (peninjau LLM dari keluarga model berbeda dengan checklist adversarial dan log), `EXT` (manusia lain).
  - Tetapkan gate minimum per jenis bukti: blind holdout dan review F5 wajib `EXT` (mis. 2–3 relawan administrator untuk penulisan blind set dengan panduan pelabelan; satu peninjau keamanan eksternal untuk F5).
  - Bila `EXT` tidak tersedia: gate F5 tidak boleh dinyatakan lulus; rilis tetap proposal-only. Tulis aturan ini di dokumen supaya tidak diputuskan ad hoc.
  - Evidence matrix F0-07 wajib mencantumkan label tingkat independensi tiap bukti.
- **Bukti penutupan:** Bagian "Governance dan independensi" di dokumen, label pada evidence matrix.

### MEDIUM

#### A-04 — MEDIUM — Kontrak isolasi F5 bertabrakan dengan semantik intent READ
- **Lokasi:** §9.1 (network/IPC isolation, UID non-root, drop capabilities), Lampiran A (intent 5–9, 13–19, 31–34), A.1.
- **Temuan:** Beberapa intent READ hanya bermakna jika executor *melihat keadaan host*:
  - **Intent 5–9 (jaringan):** Bila isolasi jaringan diwujudkan dengan network namespace baru, `ss`, `ip addr`, `ip route` akan melaporkan keadaan namespace kosong, bukan host. Hasilnya salah tanpa error (silent wrong result). Pembatasan egress harus diwujudkan lain (mis. seccomp allowlist domain `socket()`: izinkan `AF_NETLINK`/`AF_UNIX` bila perlu, tolak `AF_INET/INET6/PACKET`), bukan namespace.
  - **Intent 13–19 (service/log):** `systemctl` berbicara ke systemd lewat D-Bus/socket. `journalctl` membutuhkan root atau keanggotaan grup `systemd-journal`/`adm`. Itu bertentangan dengan "UID non-root + IPC isolation" dan "tidak ada koneksi D-Bus". Mengizinkan socket D-Bus ke executor "READ" membuka seluruh kemampuan D-Bus yang hanya dibatasi polkit.
  - **`ss -p`, `ps`, proses lain:** visibilitas PID/cmdline pemilik lain bergantung pada hak akses dan `hidepid`.
- **Dampak:** Banyak dari 33 intent "kandidat F5" akan jatuh ke proposal-only, atau lolos dengan hasil salah/privilege lebih besar dari yang dinyatakan. Metrik "execution success" menjadi tidak realistis.
- **Rekomendasi:** Matriks F0-03 perlu kolom per intent: *sumber data* (native /proc, netlink, D-Bus, file), *hak akses minimum*, *socket domain yang dibutuhkan*, *grup yang dibutuhkan*. Putuskan eksplisit: intent 13–19 proposal-only di MVP sampai ada proxy D-Bus terfilter yang divalidasi, atau handler native membaca langsung (journal API) dengan privilege terbatas. Ganti kata "network isolation" dengan mekanisme per intent.
- **Bukti penutupan:** Matriks intent×mekanisme, uji "hasil di sandbox = hasil di host" per intent READ.

#### A-05 — MEDIUM — Integritas artefak: celah *verify-then-use* dan detail signature/rollback
- **Lokasi:** §6.1 (loader, signed manifest), §9.1 (Trust artefak), §13 (memory mapping, lazy load).
- **Temuan:**
  - TOCTOU dibahas panjang untuk *target* operasi, tetapi tidak untuk artefak milik Dictum sendiri: bila hash model/katalog diverifikasi lalu file di-`mmap`, file yang bisa ditulis pihak lain (atau diganti lewat rename) dapat berubah di antara verifikasi dan pemakaian. §13 bahkan mengusulkan *memory mapping* dan *lazy load* tanpa menyebut syaratnya.
  - "Signed canonical manifest": cara kanonikalisasi tidak ditentukan. Menandatangani JSON hasil kanonikalisasi adalah sumber bug klasik.
  - Anti-rollback bergantung pada state lokal; tidak disebut siapa yang boleh menulis state itu dan apa yang terjadi saat snapshot/restore VM (yang justru dipakai di §10).
- **Rekomendasi:**
  1. Baca model (≤128 MiB) ke memori terisolasi atau buka FD sekali, hash isi dari FD yang sama, lalu pakai FD itu (`memfd` dengan `F_SEAL_WRITE`, atau file root-owned immutable dengan pemeriksaan `fstat`: uid, mode, `nlink`, bukan symlink). Tandai mmap/lazy-load §13 sebagai "hanya setelah pola ini".
  2. Tandatangani **byte persis** manifest (tanda tangan terpisah), atau pilih skema kanonikalisasi baku (mis. RFC 8785) dan ujinya.
  3. State anti-rollback: root-owned, ditulis hanya oleh jalur instalasi; dokumentasikan perilaku setelah restore snapshot.
- **Bukti penutupan:** Uji tamper di antara verifikasi dan pemakaian (file diganti selama loading), uji wrong-key/rollback.

#### A-06 — MEDIUM — Aturan gate statistik belum tegas; nama metrik "joint" ganda
- **Lokasi:** §10 (target hipotesis), §10.1, §6.2 (Uji B), §7.1 (ukuran suite).
- **Temuan:**
  1. Target "≥90%" tidak menyatakan apakah yang diuji **estimasi titik** atau **batas bawah interval**. Dengan 300 kasus supported, bila 270 benar (tepat 90%), interval Wilson 95% adalah ≈ 86,1–92,9%. Gate yang lulus pada estimasi titik tidak membuktikan "≥90%".
  2. Jumlah kasus tidak mendukung klaim turunan: ≈6 kasus per intent (satu salah = 16,7 poin), ≈90 kasus bahasa Inggris (30%; 81/90 → interval ≈ 82,1–94,6%). Gabungan 150 kasus ambiguity+OOD berarti tiap kategori mungkin ≈75 kasus, sehingga target recall ≥95% sulit dibuktikan.
  3. Zero pelanggaran pada 200 kasus keamanan hanya menyiratkan batas atas ≈1,5% (aturan tiga). Dokumen sudah menyebut "zero observed ≠ zero risk"; angka konkret ini perlu ditulis agar tidak menjadi klaim berlebih.
  4. "joint accuracy" dipakai untuk dua hal berbeda: *joint intent-slot accuracy* (level model, §10 daftar metrik, §6.2) dan *joint success* = C/N (level end-to-end dengan oracle semantik, §10.1). Target "supported joint accuracy ≥90%" ambigu.
- **Rekomendasi:** Tetapkan aturan lulus di preregistration, contoh: "estimasi titik ≥ T dan batas bawah Wilson/cluster-bootstrap 95% ≥ T_low" (nilai T_low diputuskan pemilik). Beri nama baku: `JIA` (joint intent-slot, model) dan `JS` (joint success, end-to-end) dan pakai di setiap gate. Perlakukan metrik per intent/bahasa sebagai diagnostik, bukan gate, kecuali N dinaikkan. Tulis batas atas pelanggaran keamanan di laporan.
- **Bukti penutupan:** Preregistration dengan aturan lulus, uji unit CI metrik (sudah direncanakan) ditambah uji interval.

#### A-07 — MEDIUM — Klasifikasi path sensitif dan proyeksi/redaksi output belum ada di skema katalog
- **Lokasi:** §5.1a (field katalog), §9 ("akses/minimisasi output per intent"), intent 17–19, 25–34, 39.
- **Temuan:** Katalog menyebut "input/output bounds", tetapi tidak ada field untuk *proyeksi output* atau *redaksi*, dan tidak ada definisi "berkas teks non-sensitif" (intent 29) maupun "direktori terizinkan" (intent 25–26). Output `ps`/`process.*` (cmdline berisi password), `log.*`, `file.text.search` (baris hasil), dan arsip dapat memuat secret. Prinsipnya ada (§9.1), kontraknya tidak.
- **Rekomendasi:** Tambahkan ke skema katalog: `scope_policy` (jenis root yang diizinkan), `path_class_denylist`, `output_projection` (field yang boleh tampil, default menyembunyikan cmdline penuh), `redaction_profile`. Daftar kelas path minimum: `/etc/shadow*`, kunci SSH, kredensial cloud/kube, `.env*`, history shell, `/proc/*/environ|mem`, `/dev`, direktori data DB, profil browser. Uji dengan **canary secret** di fixture: nilai canary tidak boleh muncul di output, log, audit, atau preview.
- **Bukti penutupan:** Skema katalog dengan field baru, uji canary 0 kebocoran.

#### A-08 — MEDIUM — Taksonomi risiko saling tumpang tindih (HIGH vs CHANGE vs privilege)
- **Lokasi:** §9 (kelas risiko), Lampiran A kategori 7, A.1.
- **Temuan:** HIGH didefinisikan memuat "privilege … deny", sedangkan `service.restart`/`service.reload` (CHANGE, proposal) pada praktiknya butuh privilege. Tidak jelas apakah "deny" pada HIGH berarti menolak *eksekusi* atau menolak bahkan *proposal*. Dokumen juga tidak menyatakan apakah preview menambahkan `sudo`.
- **Rekomendasi:** Pisahkan dua properti per intent: `proposal_eligible` dan `execute_eligible`; jadikan `requires_privilege` sebagai atribut efek, bukan penentu kelas. Tentukan: Dictum **tidak** menambahkan `sudo` ke preview, tetapi menampilkan catatan "mungkin memerlukan hak akses lebih tinggi". Tulis tabel pemetaan efek → kelas.
- **Bukti penutupan:** Tabel pemetaan di spesifikasi policy, uji policy per intent.

#### A-09 — MEDIUM — INFO "tanpa spawn" vs sumber `--help`/`man` dan probe versi
- **Lokasi:** §5.2 (probe versi utilitas), §9 (definisi INFO), §15 (sumber kebenaran lokal: man/`--help`), intent 1.
- **Temuan:** INFO didefinisikan "tanpa spawn utilitas", namun `help.command.explain` bersumber dari man/`--help` terpasang, dan probe versi biasanya menjalankan `--version`. Menjalankan `--help`/`--version` pada biner target adalah spawn (dengan potensi efek samping, env, pager, `MANPAGER`).
- **Rekomendasi:** Indeks dokumentasi saat *build katalog* (ditandatangani), bukan saat runtime. Probe versi lewat database paket (`/var/lib/dpkg/status`) + digest berkas, bukan eksekusi. Bila spawn tak terhindarkan, perlakukan sebagai READ dengan containment yang sama.
- **Bukti penutupan:** Uji bahwa jalur INFO tidak memanggil `execve`.

#### A-10 — MEDIUM — Kelayakan teknis containment (cgroup, namespace, Landlock) belum dibuktikan
- **Lokasi:** §9.1 (Confinement, Resource containment), §3 (Ubuntu 24.04 sebagai target berikutnya).
- **Temuan:** Kontrak mensyaratkan UID non-root, cgroup v2 terisolasi sebelum code berjalan, namespace/mount allowlist, Landlock, dan seccomp. Tidak dijelaskan siapa yang punya hak menyiapkan semuanya: membuat cgroup butuh subtree yang didelegasikan; namespace/mount butuh capability atau user namespace; menaruh child ke cgroup *sebelum* ia menjalankan kode rawan race kecuali memakai `clone3(CLONE_INTO_CGROUP)`. Sepengetahuan saya, Debian 13 memakai kernel seri 6.12 (cek ABI Landlock aktual dengan `landlock_create_ruleset` versi query; ABI yang lebih baru menambah scoping untuk abstract unix socket/sinyal), dan Ubuntu 24.04 membatasi user namespace tanpa hak lewat AppArmor, jadi pendekatan yang jalan di Trixie bisa gagal di Ubuntu.
- **Rekomendasi:** Tambahkan "spike kelayakan containment" ke F0 pada VM Trixie nyata untuk 4–5 intent representatif (`ss`, `du`, `find`, `systemctl status`, `journalctl`), mencatat: privilege yang dibutuhkan helper, mekanisme delegasi cgroup, ABI Landlock, hasil di Ubuntu 24.04. Bila helper berprivilege diperlukan, masukkan ke TCB di A-02.
- **Bukti penutupan:** Laporan spike + matriks dukungan kernel.

#### A-11 — MEDIUM — Detail JSON Schema 2020-12 dan validator native
- **Lokasi:** §5.1a.
- **Temuan:**
  1. `additionalProperties:false` "pada seluruh object" bersama komposisi (`allOf`/`oneOf`/`if-then` untuk slot per-intent) tidak melihat properti yang dievaluasi di sub-schema; hasilnya sering menolak input sah atau (bila dikendurkan) meloloskan field tak dikenal. Draft 2020-12 menyediakan `unevaluatedProperties:false` untuk kasus ini.
  2. Validator "native wajib" (C) untuk JSON Schema 2020-12 penuh itu besar; kesetaraan dengan oracle Python tidak otomatis.
- **Rekomendasi:** Tetapkan *profil subset* schema yang diizinkan (daftar keyword) dan hasilkan validator C dari schema (codegen) dengan test diferensial terhadap validator Python. Larang `$ref` remote (sudah: tanpa fetch jaringan).
- **Bukti penutupan:** Dokumen profil subset, korpus negatif yang sama lulus/gagal identik di C dan Python.

#### A-12 — MEDIUM — Split data tidak konsisten dengan scope MVP
- **Lokasi:** §7.1 langkah 5, §4, §7.2, RQ4.
- **Temuan:** (a) "OS/version holdout" mensyaratkan lingkungan kedua, padahal MVP hanya Debian 13 satu profil. (b) "Intent/combination unseen" tidak bermakna untuk klasifikasi tertutup 48 intent bila intent itu ada di head; agar bermakna, intent harus dikeluarkan dari training (dan diuji lewat retrieval zero-shot §7.2).
- **Rekomendasi:** Untuk MVP, tandai OS/version holdout sebagai "ditunda sampai Ubuntu 24.04/Debian 12 tersedia" atau definisikan versi utilitas berbeda di Trixie. Untuk intent unseen, tulis protokol: intent X dikeluarkan dari training dan head, diuji via retrieval; laporkan terpisah.
- **Bukti penutupan:** Bagian split dengan definisi yang konsisten dengan scope.

#### A-13 — MEDIUM — Lisensi: ketegangan CC-BY-SA korpus vs bobot Apache-2.0; teks katalog dari manpage
- **Lokasi:** §14 (keputusan lisensi), §7.1 (sumber manpage/tldr/NL2Bash).
- **Temuan (bukan nasihat hukum):** Korpus asli diusulkan CC-BY-SA-4.0 sedangkan bobot hasil training diusulkan Apache-2.0. Apakah bobot yang dilatih dari data SA merupakan "adaptasi" yang tunduk pada share-alike belum jelas secara hukum; dokumen sudah menyatakan tidak berasumsi, tetapi tetap memilih dua lisensi yang membuat pertanyaan itu muncul. Katalog Apache-2.0 yang memuat deskripsi turunan manpage/`--help` perlu audit hak (lisensi manpage beragam). Untuk tldr-pages, lisensi yang dinyatakan proyeknya adalah CC BY 4.0 (sepengetahuan saya; verifikasi saat membuat ledger), sehingga atribusi wajib.
- **Rekomendasi:** Bila tujuan akhir bobot Apache-2.0, pertimbangkan CC-BY-4.0 atau CC0 untuk korpus asli agar pertanyaan share-alike tidak relevan. Konsultasikan pihak yang berwenang sebelum rilis. Pisahkan "teks katalog yang ditulis sendiri" dari "teks turunan sumber pihak ketiga" di license ledger.
- **Bukti penutupan:** License ledger per artefak, keputusan tertulis pemilik.

#### A-14 — MEDIUM — Harness eksekusi fixture sebelum F5 tidak punya kontrak isolasi minimum
- **Lokasi:** §9 (executor lab), §10 (≥100 executable fixtures), §11 (F2–F3 memakai benchmark end-to-end).
- **Temuan:** Benchmark F2–F3 membutuhkan eksekusi rencana hasil kompilasi (keluaran model) pada fixture, jauh sebelum executor F5 tervalidasi. Dokumen menyebut harness lab bukan fitur pengguna dan VM disposable, tetapi tidak menetapkan syarat minimum harness tersebut.
- **Rekomendasi:** Tambahkan "Lab Harness Contract": VM disposable dari snapshot bersih, tanpa jaringan/share/clipboard/kredensial, reset tiap kasus, hanya intent yang `execute_eligible` pada profil lab, log lengkap. Nyatakan bahwa hasil benchmark tidak menjadi bukti keamanan F5.
- **Bukti penutupan:** Dokumen kontrak harness, skrip reset snapshot.

### LOW

#### A-15 — LOW — Konfigurasi M1 melampaui tier "1M"
- **Lokasi:** §6 (tabel, M1: 1M/3M/10M), §6.1.
- **Temuan:** Hitung ulang: embedding 4.096×128 = 524.288; 4 layer × (4·128² + 2·128·512) = 786.432; subtotal **1.310.720** sebelum bias, normalisasi, embedding posisi (16.384 pada konteks 128; 65.536 pada 512), dan kepala intent/slot. Perkiraan total ≈ **1,34–1,39M**. Kalimat "tidak dijanjikan tepat 1,2M" merujuk angka lama yang kini sudah terlampaui oleh subtotal saja.
- **Rekomendasi:** Relabel kandidat sebagai "≈1,3–1,4M" atau turunkan vocab/lebar. Pertimbangkan konteks 64–128 token untuk instruksi pendek (konteks 512 hanya menambah parameter posisi).

#### A-16 — LOW — Sisa teks lama dan inkonsistensi kecil
- "Struktur belum dibuat pada v0" (§12) — frasa usang pada dokumen v2.
- Resolusi F12 menyebut "tanpa LaTeX rusak", tetapi intent 29 masih memuat `$N$`.
- Vocabulary keputusan tidak seragam: contoh IR memakai `"decision":"propose"`, sedangkan PolicyDecision memakai `allow-proposal`/`allow-execute-eligible`/`clarify`/`unsupported`/`deny`, dan teks sering memakai "abstain". Tetapkan satu enum kanonik dan petakan "abstain" ke `clarify`/`unsupported`.
- §0 merujuk "v0" dan "review v1" tanpa tautan relatif ke berkasnya.
- Aturan ID intent (karakter, pemisah titik vs garis bawah, panjang) belum ditulis, padahal mereka campur (`file.head_tail.view`, `diagnosis.disk_full`).

#### A-17 — LOW — Edisi OWASP tercampur
- R18 memakai halaman LLM01 dan LLM10 edisi 2026, tetapi Excessive Agency edisi 2025 (LLM06:2025). Sepengetahuan hasil verifikasi saya (§7), edisi 2026 menempatkan Excessive Agency di peringkat 3. Seragamkan edisi, dan pertimbangkan menambah *OWASP Top 10 for Agentic Applications* karena jalur execute/approval Dictum beririsan dengan topik itu.

#### A-18 — LOW — Detail operasional kecil
- **Environment allowlist:** nilai belum ditetapkan. Pin `LC_ALL` (mis. `C.UTF-8`), `TZ`, `TERM` agar fixture dan parsing output deterministik.
- **Kedaluwarsa approval:** `CLOCK_MONOTONIC` tidak maju saat suspend; untuk token 30 detik lintas suspend/restore VM, pertimbangkan `CLOCK_BOOTTIME` dan invalidasi nonce saat restore.
- **Batas 30 detik** mungkin terlalu pendek bagi pengguna yang membaca preview kompleks (ekstraksi arsip); tentukan lewat uji usability, bukan angka tetap.

#### A-19 — LOW — Tidak ada daftar spike/timebox; risiko "dokumen lebih besar dari kode"
- **Lokasi:** §11 ("tidak menetapkan kalender"), §16.
- **Temuan:** Menghindari kalender palsu itu bijak, tetapi F0 saat ini memuat sangat banyak deliverable spesifikasi (5 schema, format DCTM, threat model, matriks 48 intent, preregistration, license ledger) sebelum ada satu pun intent yang berjalan end-to-end.
- **Rekomendasi:** Tambahkan *walking skeleton* proposal-only untuk 6–8 intent (mis. 5, 15, 17, 20, 22, 25, 35, 45) yang melewati seluruh rantai NLUProposal→ExecutionPlan→preview, dan daftar spike berdurasi pendek (lihat §8). Hasil spike mengoreksi spesifikasi sebelum 48 intent diselesaikan.

---

## 5. Penilaian atas resolusi F01–F12 (§0 dokumen)

Penilaian saya atas klaim "Resolusi v2" (bukan atas implementasi, yang memang belum ada):

| ID | Resolusi di dokumen | Penilaian audit | Catatan |
|---|---|---|---|
| F01 | Header DCTM berpanjang eksplisit | **Memadai di desain** | Prefix 32 byte terverifikasi. Lihat A-05 untuk verify-then-use |
| F02 | openat2/descriptor, deny bila identitas tak terjaga | **Sebagian** | Kuat untuk target operasi; artefak sendiri belum tercakup (A-05) |
| F03 | Denominator seluruh supported | **Memadai di definisi** | Aturan lulus statistik belum tegas (A-06) |
| F04 | NET sebagai axis terpisah | **Sebagian** | Mekanisme isolasi jaringan bertabrakan dengan intent baca-jaringan (A-04) |
| F05 | Confinement OS per operasi | **Sebagian** | Kelayakan/privilege helper belum dibuktikan (A-10, A-02) |
| F06 | Empat kontrak + schema nyata | **Memadai** | Perhatikan `unevaluatedProperties`, profil subset (A-11) |
| F07 | Pisah parity vs quality loss | **Memadai** | Pertimbangkan aritmetika tetap penuh untuk bit-exact bila memungkinkan (§6.2) |
| F08 | Pipe terbatas, cgroup, deadline | **Sebagian** | Delegasi cgroup, `CLONE_INTO_CGROUP` (A-10) |
| F09 | Trust anchor + signed manifest | **Sebagian** | Kanonikalisasi, state rollback (A-05) |
| F10 | Human gold, entailment, oracle independen | **Sebagian** | Independensi tidak operasional (A-03) |
| F11 | Hitung parameter aktual | **Sebagian** | Konfigurasi M1 melampaui 1M (A-15) |
| F12 | Inkonsistensi dibersihkan | **Sebagian** | Sisa `$N$`, frasa "v0", enum keputusan (A-16) |

---

## 6. Pemeriksaan angka dan konsistensi

| Klaim di dokumen | Hasil periksa |
|---|---|
| 48 intent = 4 INFO + 40 READ + 4 CHANGE | ✔ 4 + (8+7+11+10+4 = 40) + 4 = 48 |
| A.1: pengelompokan eligibility menutup semua intent | ✔ 4 (1–4) + 2 (10–11) + 5 (12, 41–44) + 4 (45–48) + 33 (5–9, 13–40) = 48 |
| "44 INFO/READ dan 4 CHANGE" (§4) | ✔ konsisten dengan Lampiran A |
| Prefix `.dctm` 32 byte | ✔ 4+2+2+4+4+8+8 = 32 |
| Embedding vocab 4.096 × d 128 | ✔ 524.288 |
| Attention+FFN, 4 layer, d=128, FFN=512 | ✔ 786.432 |
| Bobot INT8: 1M=1 MB, 10M=10 MB, 50M=50 MB | ✔ |
| "Tidak dijanjikan tepat 1,2M" untuk M1 | ⚠ Subtotal sudah 1,31M; total ≈1,34–1,39M (A-15) |
| Gate "≥90%" pada 300 kasus | ⚠ 270/300 → Wilson 95% ≈ 86,1–92,9% (A-06) |
| "zero observed" pada 200 kasus keamanan | ⚠ batas atas 95% ≈ 1,5% (aturan tiga) |
| `joint = coverage × selective accuracy`, gate ≥90% ⇒ coverage ≥90% | ✔ |
| "Tanpa LaTeX rusak" (F12) | ⚠ `$N$` tersisa pada intent 29 |
| Struktur "belum dibuat pada v0" | ⚠ frasa usang (A-16) |
| Debian 13 "Trixie" disebut konsisten | ✔ tidak ditemukan penyebutan versi lain |

---

## 7. Verifikasi referensi (sebagian)

Dokumen sendiri menyatakan referensi "belum direproduksi". Saya memverifikasi yang paling berpengaruh pada klaim:

| Ref | Hasil | Catatan |
|---|---|---|
| **R01** Tiny-2.1 | ✔ Dikonfirmasi lewat liputan independen: 367 ribu parameter, 4 layer, lebar 96, tingkat karakter, bobot 8-bit ≈380 KB, ≈540 KB memori DOS, kode MIT, halusinasi di luar data. | Tugasnya QA hafalan ±3.500 fakta, bukan generalisasi slot; jangan ekstrapolasi hasilnya ke RQ1. Dokumen sudah menyebut "inspirasi footprint". |
| **R10** NL2Shell / Vox | ✔ Qwen3.5-0.8B (±859M parameter) di-fine-tune (QLoRA) pada NL2Bash (±8–13 ribu pasangan, tergantung versi); Vox berlisensi MIT. | Vox menyediakan opsi auto-execute (`-x`); kontras dengan desain Dictum, bisa dicatat di bagian pembanding. Bobot ≈0,4–0,8 GB jauh di atas gate 50 MB, sehingga tepat dijadikan pembanding M3 saja. |
| **R18** OWASP | ✔ Edisi 2026 ada (terbit Agustus 2026), Improper Output Handling = LLM10:2026. | Excessive Agency masih dirujuk edisi 2025 (A-17). Ringkasan pihak ketiga menyebut entri output handling 2026 kini mencakup sink ANSI/terminal, relevan langsung dengan sanitasi terminal §9. |
| R02–R09, R11–R17, R19, Lampiran B | **Belum diverifikasi** | Lakukan pada F0 sesuai §15: pin commit/rilis, lisensi, reproduksi. |

**Kandidat pembanding M3 tambahan** (dari hasil pencarian, belum diaudit): `manuelgscom/dale-0.8b` (permintaan Spanyol/Inggris → satu perintah bash, 0,8B) dan `0Time/INCEPT-SH` (Qwen3.5-0.8B GGUF, mendukung Debian/Ubuntu). Keduanya relevan sebagai pembanding bilingual dan Debian-spesifik; periksa lisensi dan data latihnya lebih dulu.

---

## 8. Tindak lanjut yang disarankan (berurutan)

**Tahap 1 — Revisi cepat dokumen (v2.1, ±1 sesi):**
A-16 (kebersihan), A-15 (relabel M1), A-17 (edisi OWASP), A-08 (tabel risiko), A-06 (aturan lulus + nama metrik), A-12 (split), A-18.

**Tahap 2 — Keputusan arsitektur yang mengubah bentuk F0:**
A-02 (peran proses + IPC), A-04 (mekanisme isolasi per intent), A-10 (kelayakan containment), A-05 (artefak).

**Tahap 3 — Tambahan spesifikasi:**
A-01 (renderer), A-07 (path sensitif/redaksi), A-09 (spawn INFO), A-11 (profil schema), A-14 (kontrak harness).

**Tahap 4 — Governance:**
A-03 (tingkat independensi, label bukti), A-13 (lisensi).

**Spike pendek (masing-masing beberapa jam–sehari) sebelum menyetujui F0:**

| Spike | Pertanyaan yang dijawab | Menutup |
|---|---|---|
| S1 | Apakah render preview ≡ argv lewat fuzz round-trip pada bash/dash/zsh/fish? | A-01 |
| S2 | Seberapa jauh B0/B1 (rules + retrieval) pada 48 intent dengan ±100 contoh seed? (RQ6) | A-19, RQ6 |
| S3 | Apakah 5 intent representatif bisa berjalan di Trixie dengan non-root + Landlock/seccomp/cgroup, dan dengan hasil sama seperti di host? | A-04, A-10 |
| S4 | Apakah INT8 C vs Python bit-exact bila seluruh alur memakai aritmetika tetap? | §6.2 |
| S5 | License ledger untuk NL2Bash, tldr-pages, manpage terpilih | A-13 |

---

## Lampiran: perhitungan

**Interval Wilson 95%** (z = 1,96), `p̂ ± ` dengan rumus pusat `(p̂ + z²/2n)/(1 + z²/n)`:

| Kasus | n | benar | Interval |
|---|---|---|---|
| Supported blind (gate 90%) | 300 | 270 | ≈ 86,1% – 92,9% |
| Subset bahasa Inggris (30%) | 90 | 81 | ≈ 82,1% – 94,6% |
| Recall OOD 95% bila n = 150 | 150 | ≈143 | ≈ 90,7% – 97,7% |

**Aturan tiga:** 0 pelanggaran dari n = 200 ⇒ batas atas 95% ≈ 3/200 = 1,5%.

**Parameter M1 (vocab 4.096, d=128, FFN=512, 4 layer, 4 head):**

| Komponen | Parameter |
|---|---|
| Embedding token (4.096 × 128) | 524.288 |
| Attention (4 × 128²) × 4 layer | 262.144 |
| FFN (2 × 128 × 512) × 4 layer | 524.288 |
| **Subtotal** | **1.310.720** |
| Bias + normalisasi (perkiraan) | ≈ 7.000 |
| Embedding posisi (konteks 128–512) | 16.384 – 65.536 |
| Kepala intent (128×48+48) + BIO (≈ 3.000) | ≈ 9.000 |
| **Perkiraan total** | **≈ 1,34M – 1,39M** |

*Catatan: bobot yang berbagi (tied) mengurangi hitungan embedding output bila decoder dipakai; untuk encoder dengan kepala klasifikasi angka di atas berlaku.*
