# Dictum — Persetujuan baseline v3 dan ledger keputusan F0

**Tanggal:** 24 November 2026 (Asia/Jakarta)  
**Otoritas:** pemilik proyek manusia (repositori megaalive/ai-lab-dictum).  
**Sumber persetujuan:** pernyataan eksplisit pemilik dalam percakapan proyek Dictum, direkam oleh technical lead AI; bukan tanda tangan kriptografis atau review EXT.

> Saya sebagai pemilik proyek menyetujui rencana induk v3 dan paket kerja F0 v3 sebagai baseline Dictum, dengan seluruh batasan dan acceptance gate yang ditetapkan. Tetapkan baseline, buat GitHub Issues F0-A, dan berikan prompt executor untuk DCT-008.

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
| DEC-003 | F0-B menunggu review kontrak SELF + LLM-ADV dan otorisasi scope spike oleh pemilik; F0-C tunduk bukti relevan dan gate paket F0 | HOLD sampai gate |
| DEC-004 | F1 menunggu acceptance F0-D serta keputusan pemilik | HOLD |
| DEC-005 | Proposal-only; tidak ada executor produk, sudo otomatis, jaringan keluar saat inference, data produksi/sensitif atau training penuh pada F0 | NO-GO untuk pengecualian |
| DEC-006 | Debian 13 x86-64, C17/CMake, 2 vCPU/2 GiB Proxmox referensi, 48 intent registry dan 8 intent skeleton; baseline B0/B1 sebelum neural | APPROVED sebagai scope dan target riset, bukan hasil |
| DEC-007 | Detail melalui spesifikasi/ADR/evidence; perubahan material scope, tujuan atau gate memerlukan keputusan pemilik; histori tidak ditimpa | APPROVED |
| DEC-008 | F0-A dipecah DCT-001–008, branch terpisah untuk coding, draft PR, evidence terikat SHA; tidak ada auto-merge/auto-accept | APPROVED sebagai tata kerja |

## Batas klaim

Audit akhir desain oleh technical lead AI tidak menemukan kontradiksi material yang menghambat F0-A; ini review desain, bukan bukti PASS implementasi atau reviewer eksternal. Tidak ada klaim kelulusan 31 temuan audit, performa, keamanan, lisensi atau eksekusi. Review adversarial terpisah tetap diperlukan di gate F0-A. Gunakan status OPEN/DESIGN-ADDRESSED/VERIFIED/DEFERRED-BLOCKED dan hasil PASS/FAIL/BLOCKED/NOT RUN sesuai bukti.

Tidak ada izin untuk F1, training penuh, atau executor. Pengujian eksekusi S3 hanya setelah gate F0-A di lab disposable sesuai §9.5; jika isolasi tidak terbukti, BLOCKED. Otorisasi ini tidak menggantikan otorisasi spike atau acceptance berikutnya.

## Evidence DCT-001 (A1)

Metode: pemeriksaan HEAD, pembacaan lengkap dua dokumen dari repo, perbandingan Git blob terhadap commit asal, persetujuan eksplisit manusia di atas. Hasil: identitas baseline dan scope tercatat. Label: SELF (catatan proyek oleh technical lead AI atas instruksi pemilik); tidak ada klaim EXT atau audit implementasi. Batas: tidak ada implementasi diuji. Langkah berikut: DCT-008, lalu audit draft PR sebelum melanjutkan.
