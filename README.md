# AI Lab — Dictum

**From words to operations.**

Dictum adalah riset AI Lab tentang penerjemahan instruksi bahasa manusia ke
usulan operasi sistem operasi secara lokal. DCT-008 menyediakan fondasi
executable native C17. Bantuan dan versi tersedia. Penerjemahan, model, dan
preview operasi belum tersedia.

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

## CLI saat ini

```sh
./build/release/dictum --help
./build/release/dictum --version
./build/release/dictum ask "siapa yang menggunakan port 5432?"
./build/release/dictum run "siapa yang menggunakan port 5432?"
```

| Exit code | Perilaku |
| --- | --- |
| `0` | `--help` atau `--version` tanpa tambahan argumen menulis ke stdout. |
| `1` | Penulisan atau flush ke stream gagal dan kesalahan terdeteksi. |
| `2` | Argumen tidak valid, termasuk `ask` tanpa tepat satu argumen instruksi yang tidak kosong. |
| `3` | `ask` menerima satu argumen instruksi yang tidak kosong dan melaporkan `unsupported`. |
| `4` | `run` ditolak dengan atau tanpa argumen tambahan. |

Penolakan menulis diagnostik tetap ke stderr. Isi instruksi tidak muncul pada
keluaran dan tidak diinterpretasikan.

[ADR runtime C17 dan CMake](docs/adr/0001-runtime-c17-cmake.md) ·
[Baseline proyek v3 dan amandemen governance DEC-009](plans/baseline-v3.md)

Review teknis SELF berbasis evidence dapat memenuhi persyaratan review model;
LLM-ADV (model berbeda) opsional. Keputusan fase oleh pemilik, seluruh gate
teknis dan review manusia EXT untuk release executor tetap wajib.
