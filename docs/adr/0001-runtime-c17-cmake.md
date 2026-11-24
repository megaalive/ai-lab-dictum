# ADR 0001 — Runtime native C17 dan CMake

Keputusan ini berlaku untuk fondasi DCT-008. [Baseline v3](../../plans/baseline-v3.md)
menetapkan Debian 13 Trixie x86-64 sebagai target referensi.

## Keputusan dan alternatif

Gunakan C17 untuk menghasilkan executable lokal dengan toolchain GCC dan Clang
serta pustaka standar C. C17 memberi akses langsung ke representasi data dan
pengelolaan memori yang dapat diaudit pada target. Runtime membatasi diri pada
fitur standar bahasa. Penambahan ekstensi atau API khusus OS perlu alasan
teknis dan pengujian pada target.

CMake menetapkan standar bahasa, build Debug dan Release, serta flag per
target. CTest memakai hasil build yang sama untuk smoke test dan kasus negatif.
Makefile langsung cukup untuk dua unit kompilasi saat ini, tetapi akan
menduplikasi sebagian konfigurasi dan integrasi uji antar-toolchain. C++
membawa RAII dan tipe yang dapat mempermudah pengelolaan resource. C# NativeAOT
menawarkan pengecekan memori dengan model runtime dan toolchain berbeda.
Keduanya dapat dipertimbangkan kembali bila hasil spike menunjukkan kebutuhan.

## Dependensi dan batas produk

Executable memakai pustaka standar C serta komponen sistem yang dipilih
toolchain. Audit dependensi pada artefak hasil link dan catat versi serta alasan
sebelum menambah pustaka. Setiap penambahan membutuhkan fungsi yang jelas,
versi yang dapat diidentifikasi, tinjauan lisensi dan pemeliharaan, serta uji
dampak terhadap distribusi offline.

Toolchain, CTest, tracer, sanitizer, dan tooling riset seperti Python/PyTorch
untuk training atau oracle adalah alat pengembangan. Target produk tidak
menautkan komponen riset dan tidak memerlukan interpreter riset saat berjalan.
Masukan untuk pengujian fondasi ini bersifat sintetis.

Dictum mengikuti batas arsitektur **proposal-only**. CLI saat ini hanya
menampilkan bantuan dan versi atau menolak permintaan. `ask` dengan satu
instruksi tidak kosong melaporkan `unsupported`. Token pertama `run` selalu
ditolak. Tidak ada penerjemahan, preview operasi OS, API spawn, atau akses
jaringan. Executor berstatus **NO-GO** sampai ada gate keamanan dan otorisasi
terpisah sesuai baseline.

## Ownership, lifetime, dan batas input

CLI meminjam `argv` dan stream standar selama proses. Runtime meminjam pointer
instruksi sebagai baca-saja selama panggilan, memeriksa byte pertama untuk
membedakan string kosong, dan mengembalikan status tanpa menyimpan pointer.
CLI memeriksa jumlah argumen sebelum mengindeks `argv` dan mencocokkan token
perintah dari himpunan tetap. Isi instruksi tidak disalin atau dikutip kembali.
Teks keluaran berasal dari literal program. Tahap ini tidak memiliki alokasi
heap atau resource milik aplikasi yang perlu dilepas.

Saat format masukan bertambah, gunakan pasangan pointer dan panjang byte pada
batas parser. Tetapkan batas ukuran, jumlah elemen, dan kedalaman per format.
Validasi rentang sebelum membaca, membentuk pointer, atau mengalokasi. Untuk
rentang dengan `offset` dan `length`, periksa `offset <= size` sebelum
`length <= size - offset`. Periksa operasi terhadap batas tipe sebelum
penjumlahan, perkalian, atau konversi ke tipe yang lebih sempit. Tolak data
terpotong, versi tak dikenal, dan data ekstra sesuai kontrak format.

## Kesalahan dan cleanup

Runtime mengembalikan status eksplisit. CLI memetakan status ke exit code dan
diagnostik tetap di stderr. Kegagalan penulisan atau flush yang terdeteksi
menghasilkan status I/O. Stream standar tetap dikelola oleh runtime C.
Untuk resource yang kelak dibutuhkan, tetapkan pemilik dan titik perpindahan
ownership di kontrak fungsi. Lepas setiap resource tepat sekali, termasuk saat
inisialisasi parsial. Jalur gagal menyisakan output dalam keadaan terdokumentasi
dan tidak meneruskan permintaan ke jalur eksekusi.

## Peringatan, sanitizer, dan fuzzing

Aktifkan peringatan ketat GCC dan Clang pada target produk. CI membuatnya fatal
dan menguji Release serta Debug berinstrumentasi ASan dan UBSan. Opsi sanitizer
terpisah memungkinkan isolasi diagnostik. Laporan UBSan menghentikan proses uji.

Ketika parser byte tersedia, uji antarmuka parser secara langsung dengan
fuzzer berinstrumentasi ASan dan UBSan. Mulai dari corpus sintetis kecil berisi
kasus valid, ukuran batas, input terpotong, encoding cacat, dan panjang yang
memicu overflow. Simpan seed, batas waktu, versi toolchain, serta contoh gagal
yang telah diminimalkan untuk uji regresi. Invarian dasarnya adalah kegagalan
terkendali, penggunaan resource yang dibatasi, dan hasil deterministik untuk
input yang sama. DCT-008 hanya memiliki validasi bentuk argumen CLI dan
menguji keluaran serta exit code melalui CTest.

## Addendum F0-C — digest melalui libcrypto

Untuk C-04 dan snapshot konteks, gunakan OpenSSL libcrypto >= 3.0
(`EVP_Digest`, SHA-256), bukan implementasi kriptografi sendiri. Debian
13 menyediakan paket `libssl-dev` dan `libssl3t64`; versi aktual dan
tautan binary dicatat pada CI. OpenSSL 3.x upstream berlisensi Apache-2.0;
metadata copyright paket Debian mencakup komponen tambahan dan harus
dipertahankan bila redistribusi. Ini keputusan dependensi riset, bukan
audit distribusi atau approval signature. JCS subset plan memakai key ASCII
tertutup, integer exact dan UTF-8 scalar; hash mengikat byte, bukan
otoritas. Tidak ada API TLS, HTTP, signing, key loading atau jaringan pada
kode produk. Audit syscall produk setelah integrasi tetap C-06.
