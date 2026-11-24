# AI Lab — Dictum

**From words to operations.**

Dictum adalah riset AI Lab tentang penerjemahan instruksi bahasa manusia ke
usulan operasi sistem operasi secara lokal. F0-C mengembangkan pipeline native C17 untuk delapan intent dan
usulan terstruktur non-copyable. Semua binding Debian masih NOT VERIFIED;
mode ini hanya memakai katalog dan scope sintetis, bukan data host.

Dictum mengikuti batas **proposal-only**. Produk tidak menjalankan operasi
OS atas permintaan pengguna, tidak membuka koneksi jaringan, dan tidak
mensimulasikan hasil OS. Executor berstatus **NO-GO**.

## Build dan uji

Target referensi adalah Debian 13 Trixie x86-64. Siapkan CMake 3.24 atau lebih baru
beserta CTest, Make, GCC atau Clang dengan driver bergaya GCC, dan header serta
linker sistem. Contoh paket build Debian untuk kedua compiler tersedia di
bawah. `libclang-rt-dev` menyediakan runtime sanitizer untuk build uji Clang.

```sh
apt-get update
apt-get install --no-install-recommends cmake make gcc clang libc6-dev libclang-rt-dev libssl-dev python3-jsonschema
```

Dari root repositori, gunakan direktori terpisah untuk setiap konfigurasi.

```sh
CC=gcc cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_COMPILE_WARNING_AS_ERROR=ON
cmake --build build/release
ctest --test-dir build/release --output-on-failure --no-tests=error

CC=clang cmake -S . -B build/sanitizer -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_COMPILE_WARNING_AS_ERROR=ON \
  -DDICTUM_ENABLE_ASAN=ON -DDICTUM_ENABLE_UBSAN=ON
cmake --build build/sanitizer
ctest --test-dir build/sanitizer --output-on-failure --no-tests=error
```

Opsi sanitizer dinonaktifkan secara bawaan dan dapat diaktifkan satu per satu.
Build dari source memakai Python dan jsonschema untuk codegen IR; executable produk tidak membutuhkan Python saat berjalan. Library OpenSSL libcrypto (>=3.0) digunakan untuk SHA-256 identitas/digest, bukan approval atau signature; versi dan link dicatat CI.

## CLI F1 — metadata / pipeline F0-C

```sh
./build/release/dictum ask "siapa yang menggunakan port 5432?"
./build/release/dictum explain "show available memory"
./build/release/dictum search memory.summary
./build/release/dictum search network.route.table
./build/release/dictum inspect
./build/release/dictum run "restart demo.service"
```

`ask` dan `explain` stateless menampilkan JSON non-copyable: arti intent,
sumber, typed slots yang diizinkan pada fixture, dan batasan. Exit 0 proposal,
1 I/O, 2 argumen invalid, 3 unsupported, 4 deny, 5 clarify, 6 internal.
`run` selalu ditolak, termasuk tanpa atau dengan argumen tambahan.
Tidak ada hasil OS palsu, command copyable, akses filesystem target, spawn
atau jaringan. Scope hanya literal synthetic allowlist; bukan klaim target ada.
`search` adalah lookup ID persis untuk seluruh 48 intent, metadata saja.
`pipeline_status` membedakan 8 SYNTHETIC_PROPOSAL dari 40 NOT_IMPLEMENTED;
semua binding aktual tetap BLOCKED/NOT VERIFIED, tidak ada output OS.
`inspect` memisahkan jumlah katalog, pipeline sintetis, dan binding terverifikasi, serta melaporkan identitas versi/hash
dan tidak mengklaim pengukuran latency. B0 primary; B1 guarded retrieval
hanya tersedia melalui probe development dengan interface pipeline yang sama.

[ADR runtime C17 dan CMake](docs/adr/0001-runtime-c17-cmake.md) ·
[Baseline proyek v3 dan amandemen governance DEC-009](plans/baseline-v3.md)

Review teknis SELF berbasis evidence dapat memenuhi persyaratan review model;
LLM-ADV (model berbeda) opsional. Keputusan fase oleh pemilik, seluruh gate
teknis dan review manusia EXT untuk release executor tetap wajib.
