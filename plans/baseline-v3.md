# Dictum — Persetujuan baseline v3 dan ledger keputusan F0

**Tanggal:** 24 November 2026 (Asia/Jakarta)  
**Otoritas:** pemilik proyek manusia (repositori megaalive/ai-lab-dictum).  
**Sumber persetujuan:** pernyataan eksplisit pemilik dalam percakapan proyek Dictum, direkam oleh technical lead AI; bukan tanda tangan kriptografis atau review EXT.

> Saya sebagai pemilik proyek menyetujui rencana induk v3 dan paket kerja F0 v3 sebagai baseline Dictum, dengan seluruh batasan dan acceptance gate yang ditetapkan. Tetapkan baseline, buat GitHub Issues F0-A, dan berikan prompt executor untuk DCT-008.

## Ketentuan yang berlaku saat ini

Baseline terdiri atas dua dokumen v3 asli yang dipin di bawah **beserta amandemen normatif yang disetujui pemilik dalam decision ledger ini**. DEC-009 mengesampingkan hanya kewajiban memakai model LLM berbeda dalam DEC-003, F0 v3 §2 dan rencana induk v3 §11.1 serta baris F6 pada §11. Ketentuan teknis, acceptance criteria, safety gate dan batas kewenangan lainnya tetap berlaku. Dokumen draft dan evidence historis tetap dipertahankan byte-for-byte; bila menyebut aturan review lama, gunakan DEC-009 untuk keputusan baru.

## Identitas baseline

HEAD sebelum pencatatan: `d0932b42915439225bb37744b8556b99277299f5`.

| Artefak normatif | Commit asal | Git blob SHA-1 |
|---|---|---|
| [Rencana induk v3](https://github.com/megaalive/ai-lab-dictum/blob/d0932b42915439225bb37744b8556b99277299f5/plans/drafts/rencana-v3.md) | `417a3cc3a531a5233e821774092dd2113ddaaeec` | `b3554946d62549b7417ea451294ff65b4f01a1fe` |
| [Paket kerja F0 v3](https://github.com/megaalive/ai-lab-dictum/blob/d0932b42915439225bb37744b8556b99277299f5/plans/drafts/f0-v3.md) | `025f0e9b84ab90f6ed2f02be5ce5588d942ffcf1` | `20afaa1cf4999d36de78dacf812bae2a7e512c34` |

Blob kedua dokumen pada HEAD tersebut identik dengan blob pada commit asal. Seluruh draft tetap dipertahankan byte-for-byte. Status DRAFT dalam arsip tidak diubah; catatan ini memberi otoritas baseline awal F0, bukan acceptance F0-D. Salinan final plans/approved/ dibuat setelah F0-D hanya dengan otorisasi pemilik sesuai paket kerja.

## Decision ledger

| ID | Keputusan | Status |
|---|---|---|
| DEC-001 | V3 dan F0 v3 menjadi baseline normatif, termasuk seluruh acceptance dan batas | APPROVED oleh pemilik |
| DEC-002 | Mulai F0-A; urutan awal DCT-001 lalu DCT-008; audit sebelum pekerjaan berikut | GO |
| DEC-003 | F0-B menunggu review kontrak SELF + LLM-ADV dan otorisasi scope spike oleh pemilik; F0-C tunduk bukti relevan dan gate paket F0 | Historis; ketentuan wajib LLM-ADV digantikan DEC-009 |
| DEC-004 | F1 menunggu acceptance F0-D serta keputusan pemilik | Historis; dipenuhi oleh DEC-010 |
| DEC-005 | Proposal-only; tidak ada executor produk, sudo otomatis, jaringan keluar saat inference, data produksi/sensitif atau training penuh pada F0 | NO-GO untuk pengecualian |
| DEC-006 | Debian 13 x86-64, C17/CMake, 2 vCPU/2 GiB Proxmox referensi, 48 intent registry dan 8 intent skeleton; baseline B0/B1 sebelum neural | APPROVED sebagai scope dan target riset, bukan hasil |
| DEC-007 | Detail melalui spesifikasi/ADR/evidence; perubahan material scope, tujuan atau gate memerlukan keputusan pemilik; histori tidak ditimpa | APPROVED |
| DEC-008 | F0-A dipecah DCT-001–008, branch terpisah untuk coding, draft PR, evidence terikat SHA; tidak ada auto-merge/auto-accept | APPROVED sebagai tata kerja |
| DEC-009 | Audit teknis SELF berbasis evidence cukup untuk persyaratan review LLM pada riset, F0–F4 dan proposal-only release/pilot; LLM-ADV opsional. Review manusia EXT untuk release executor tetap wajib. | APPROVED oleh pemilik, 24 November 2026 |

| DEC-010 | F0-D diterima untuk scope sintetis proposal-only; GO F1 sesuai kontrak dan protocol/prereg yang ada | APPROVED oleh pemilik, 24 November 2026; S3/F2/executor tetap BLOCKED/HOLD |

## DEC-009 — Amandemen governance review

**Tanggal:** 24 November 2026 (Asia/Jakarta).  
**Otoritas:** pemilik proyek manusia, instruksi eksplisit dalam percakapan proyek.  
**Pernyataan pemilik:** "ubah kewajiban review dari model yang berbeda yang ada di baseline".  
**Base sebelum amandemen:** `149593bf16ea1385f5138d69944d38f00f55b913`. Catatan instruksi ini bukan tanda tangan kriptografis, bukan persetujuan keamanan EXT dan bukan acceptance fase berikutnya.

### Aturan normatif pengganti

1. **Audit teknis tetap wajib.** Technical lead/implementer, termasuk model yang sama dalam sesi yang sama, dapat melakukan review dengan label SELF. Review harus membaca artefak aktual, memeriksa acceptance criteria, menguji atau memeriksa evidence reproducible yang relevan, mencatat finding/severity, disposition, SHA, metode, actual result, coverage dan limitasi. Perbaiki blocker material dan verifikasi perubahan sebelum acceptance; audit dapat dilakukan dalam satu batch terintegrasi, tanpa mengulang pekerjaan yang sudah memiliki evidence valid.
2. **LLM-ADV opsional** untuk riset, F0–F4, dan proposal-only release/pilot F6. Ketidaktersediaan model berbeda, atau tidak dilakukannya LLM-ADV, bukan blocker dan tidak memerlukan waiver per issue/fase. Bila dilakukan, label LLM-ADV hanya sah untuk model berbeda dengan identitas, prompt/checklist, metode dan SHA tercatat. SELF+DELAY tetap opsional dengan syarat asli ≥48 jam, sesi terpisah dan artefak/checklist terkunci. Review adversarial oleh model yang sama tetap SELF; tidak boleh diberi label LLM-ADV atau EXT.
3. **Gate F0-A → F0-B (pengganti bagian review DEC-003 dan F0 v3 §2):** review kontrak terintegrasi SELF atau review dengan independensi tambahan, material design findings affecting intent/preview/policy/parser/secret/provenance diremediasi, evidence terikat SHA tersedia, dan pemilik menerima F0-A serta mengotorisasi scope spike yang bounded. LLM-ADV bukan prasyarat. F0-B/C/D/F1 dan gate teknis berikutnya tetap sesuai baseline. Keputusan ini sendiri tidak menyatakan GO F0-B, tidak menerima hasil yang belum diperiksa, dan tidak memberi otorisasi baru untuk operasi lab atau fase berikut.
4. **Riset dan proposal-only release (pengganti bagian review §11.1 dan F6 §11):** audit SELF dengan evidence yang memadai dan keputusan manusia pemilik dapat memenuhi persyaratan review model. Oracle terpisah dari generator, human gold, provenance, locked holdout, reviewer labels, benchmark minima/thresholds, seluruh release blocker serta acceptance criteria tetap berlaku. Tidak ada auto-approval berdasarkan keluaran model atau CI. Audit tambahan dapat diminta bila temuan material atau risiko membutuhkannya, bukan kewajiban lintas model rutin.
5. **F5/EXT tidak berubah.** Release executor umum tetap memerlukan reviewer keamanan manusia EXT yang kompeten, tidak membuat komponen yang diperiksa, beserta owner approval dan seluruh gate teknis. Independen dalam oracle/holdout/validasi manusia tidak diganti dengan SELF; tidak ada klaim validasi independen tanpa bukti. Executor produk NO-GO; S3 hanya lab disposable dengan scope dan preflight aktual; training, F1, perubahan privilege, data produksi/sensitif dan akses jaringan tidak diotorisasi oleh amandemen ini.

### Histori dan implementasi

Rencana induk v3 dan F0 v3 tidak ditulis ulang, karena identitas blob-nya merupakan bagian baseline serta diperiksa lint katalog A3. Amandemen ini berlaku prospektif untuk gate dan pekerjaan aktif, bukan mengubah label reviewer atau hasil bukti lama. Evidence yang menyebut kewajiban LLM-ADV sebelumnya dibaca sebagai histori saat evidence dibuat. Issue #16 diselaraskan ke aturan baru; dokumentasi aktif renderer, threat model dan benchmark juga diselaraskan. Tidak ada perubahan kode, parameter pengujian, registry, IR atau scope produk.

## Batas klaim

Audit akhir desain oleh technical lead AI tidak menemukan kontradiksi material yang menghambat F0-A; ini review desain, bukan bukti PASS implementasi atau reviewer eksternal. Tidak ada klaim kelulusan 31 temuan audit, performa, keamanan, lisensi atau eksekusi. Review teknis terintegrasi tetap diperlukan di gate F0-A, tetapi review model berbeda tidak lagi menjadi syarat (DEC-009). Gunakan status OPEN/DESIGN-ADDRESSED/VERIFIED/DEFERRED-BLOCKED dan hasil PASS/FAIL/BLOCKED/NOT RUN sesuai bukti.

Tidak ada izin untuk F1, training penuh, atau executor. Pengujian eksekusi S3 hanya setelah gate F0-A di lab disposable sesuai §9.5; jika isolasi tidak terbukti, BLOCKED. Otorisasi ini tidak menggantikan otorisasi spike atau acceptance berikutnya.

## Evidence DCT-001 (A1)

Metode: pemeriksaan HEAD, pembacaan lengkap dua dokumen dari repo, perbandingan Git blob terhadap commit asal, persetujuan eksplisit manusia di atas. Hasil: identitas baseline dan scope tercatat. Label: SELF (catatan proyek oleh technical lead AI atas instruksi pemilik); tidak ada klaim EXT atau audit implementasi. Batas: tidak ada implementasi diuji. Langkah berikut: DCT-008, lalu audit draft PR sebelum melanjutkan.

## DEC-010 — Acceptance F0-D dan GO F1 (24 November 2026)

Sumber: instruksi eksplisit pemilik proyek dalam percakapan setelah laporan akhir PR #27, evidence C-01–C-10, audit F0-D 31 temuan, keterbatasan coverage S2 (B0 12/80, B1 11/80), dan permintaan keputusan merge serta GO F1: **"lakukan !"**. Dicatat oleh technical lead SELF, bukan signature atau EXT. Keputusan ini menerima scope/kontrak proposal-only, protokol corpus dan preregistrasi yang sudah ada untuk melanjutkan riset F1; tidak mengubah ambang kualitas atau mengotorisasi distribusi/training dengan rights HOLD.

- PR #27 telah di-merge pada `9a39162601bc745e1ba21cad01650ce5f61f693c`; tree identik dengan kandidat evidence `897e4feeb677945a7e7e002d3f68281a187e3543`. Semua lima workflow final-head selesai success. Source teruji `74f7998d8077328f6fd333686db2a1957985b454`; native 5/5 dan isolated 2/2 jobs. [F0-C](../docs/research/evidence/f0-c.md), [F0-D matrix](../docs/research/evidence/f0-d-review.md), [raw results](../docs/research/evidence/f0-c-results-v1.json).
- Owner menerima batas evidence C-01–C-10 untuk walking skeleton sintetis; A-01/A-07/A-09/A-11 proposal-side terverifikasi sesuai evidence; A-02 design dan F5 tests deferred; A-03 DEC-009. Tidak mengubah hasil, label, status verified/deferred, atau temuan kualitas negatif pada laporan historis. C-09 adalah measurement bukan blind gate. Seluruh real Debian binding tetap BLOCKED/NOT VERIFIED. S3 dan FES tetap NOT RUN/BLOCKED.
- Salinan approved memuat dokumen asli byte-identical, berlaku bersama ledger ini: [rencana v3](approved/rencana-v3.md), [F0 v3](approved/f0-v3.md), [acceptance record](approved/f0-acceptance.md). Status DRAFT di dalam salinan asli merupakan histori, bukan perubahan kontrak. [Corpus protocol](../data/manifests/corpus-protocol-v1.md) dan [benchmark prereg](../docs/research/benchmark-preregistration-v1.md) tetap normatif. Semua hak sumber UNKNOWN/NOT VERIFIED, termasuk distribusi dan training, tetap HOLD sampai keputusan rights tersendiri. 
- F1 GO: [#28](https://github.com/megaalive/ai-lab-dictum/issues/28). Perlu human gold, verified applicable compatibility, 48 intent dan baseline terukur sebelum F2. Tidak ada izin F2, training penuh/neural, release, executor, akses host atau jaringan produk. S3 bukan prasyarat riset proposal-only; scope lab aktual harus diotorisasi independen. DEC-009 dan EXT F5 tidak berubah. DEC-004 HOLD superseded hanya untuk masuk F1.
