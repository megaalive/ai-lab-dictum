# Profil kontrak IR Dictum v1

DCT-002 menetapkan empat kontrak JSON Schema Draft 2020-12 untuk lintasan
proposal. Pemanggil tepercaya memilih kontrak tahap dari API internal, lalu
memeriksa `schema_version: 1`. Hak berasal dari komponen tepercaya yang
membuat atau memeriksa ulang artefak pada tahapnya. Lolos schema hanya
menetapkan bentuk data. Mode produk F0–F4 tetap **proposal-only**.
[Baseline v3](../../plans/baseline-v3.md) · [A2 dan walking skeleton](../../plans/drafts/f0-v3.md)

## Produsen dan batas otoritas

| Objek | Produsen dan konsumen | Data dan kewenangan |
| --- | --- | --- |
| `NLUProposal` | Model atau baseline → resolver | Hipotesis intent, slot, dan abstain hint. Seluruh isi dianggap masukan tak tepercaya. |
| `ResolvedIR` | Resolver deterministik → policy | Intent kanonik dan slot bertipe dengan provenance, terikat ke request, konteks, dan katalog. `resolution.state` menyatakan hasil resolusi. |
| `PolicyDecision` | Policy engine deterministik → compiler | Satu keputusan kanonik, kelas dan sumbu efek, scope, reason code, serta identitas policy. Policy menentukan kelayakan proposal dan, pada fase yang diizinkan, eligibility eksekusi. |
| `ExecutionPlan` | Compiler deterministik → konsumen proposal atau otoritas masa depan | Aksi bertipe yang terikat ke resolusi, policy, scope, dan target. Konsumen wajib memeriksa ulang artefak terhadap keputusan dan snapshot yang sah. |

Envelope lokal yang tepercaya memasangkan `NLUProposal` dengan instruksi
UTF-8 asli dan konteks request. NLU dapat merujuk kandidat dari tabel
request itu dengan ID dan `expected_kind`. Semua objek NLU tertutup,
termasuk objek bersarang. Field executable, argv, privilege, risk
otoritatif, approval, context ID otoritatif, policy exception, dan izin
eksekusi ditolak sebagai properti asing. Skor opsional `score_bp` adalah
integer 0–10.000. Ini sinyal ranking per sepuluh ribu, tanpa asumsi
kalibrasi atau peran dalam keputusan izin. `abstain_hint` adalah petunjuk
untuk resolver. Urutan kandidat dipertahankan selama pengiriman.

ID request, resolusi, keputusan, aksi, scope, kandidat konteks, dan binding
adalah token buram 128-bit, ditulis sebagai 32 digit hex lowercase. Tiap
produsen tepercaya membuat ID tahap untuk rekaman baru dan mengikatnya ke
rekaman immutable dalam request yang sama. ID kandidat slot NLU merupakan
indeks simbolis lokal 0–31 dalam proposal, unik dan tidak perlu berurutan.
`context_id` adalah SHA-256 atas byte persis snapshot konteks yang
diregistrasikan oleh produsen tepercaya. `catalog` dan `policy` membawa
versi integer positif hingga 2.147.483.647 serta SHA-256 byte snapshot
masing-masing. Hash ditulis sebagai 64 digit hex lowercase. Konsumen
mencocokkan identitas dengan rekaman tepercaya yang aktif, termasuk batas
lintas request, sesi, dan boot. Hash atau ID yang sama dalam payload
memerlukan verifikasi ke sumber tersebut. Identitas publisher dan trust
anchor tetap tunduk pada baseline.

## Byte, sintaks JSON, dan batas

Produsen membingkai tepat satu nilai JSON per payload. Parser menerima UTF-8
ketat tanpa BOM. Whitespace di luar string terbatas pada SP, TAB, LF, dan CR.
Nama anggota dibandingkan setelah unescape, peka huruf besar-kecil, tanpa
normalisasi. Tolak duplikat dalam objek yang sama, termasuk ejaan escaped
yang menghasilkan key identik. Tolak NUL pada byte mentah, nama, dan nilai
terdekode. Tolak UTF-8 overlong, terpotong, encoding surrogate, serta
surrogate tunggal atau pasangan escape yang tidak sah. Pasangan high–low
yang sah menghasilkan satu scalar. Tolak noncharacter Unicode di nama dan
nilai, termasuk U+FDD0–U+FDEF serta dua titik kode terakhir di tiap plane,
agar semua objek v1 memenuhi batas karakter I-JSON untuk kanonisasi.
Tolak sintaks rusak, nilai JSON kedua,
dan data lain setelah nilai pertama selain whitespace yang diizinkan.
[RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html) · [RFC 7493](https://www.rfc-editor.org/rfc/rfc7493.html#section-2.1)

| Batas | Nilai dan alasan |
| --- | --- |
| Instruksi asli | 1–4.096 byte UTF-8 tanpa NUL atau noncharacter. Cukup untuk pertanyaan CLI dan menjaga span kecil. |
| Payload JSON per objek | 32.768 byte termasuk whitespace. Memberi ruang untuk slot, argv, dan provenance sambil membatasi kerja decode. Instruksi asli berada di envelope lokal terpisah. |
| Kedalaman | Maksimum 12 kontainer, akar objek/array dihitung satu. Bentuk IR saat ini dangkal dan parser memeriksa depth sebelum decode rekursif. |
| Lebar kontainer | Maksimum 32 anggota per objek dan 64 elemen per array di layer byte. Schema memperketat per field. |
| String | Maksimum 4.096 byte setelah decode, termasuk nama anggota. `maxLength` JSON Schema dihitung dalam scalar Unicode. |
| Bilangan | Token desimal integer JSON dalam rentang `[-9007199254740991, 9007199254740991]`. Pecahan, eksponen, `-0`, `NaN`, dan infinity ditolak. Rentang ini mempertahankan integer eksak pada JCS dan mudah diperiksa sebelum akumulasi C. |
| Kandidat dan slot | Maksimum 8 intent dan 32 slot kandidat NLU, 16 referensi slot per intent, 16 slot serta 16 slot unresolved pada IR. |
| Path dan argv | Path maksimum 1.024 byte UTF-8, literal satu argv maksimum 1.024 byte, dan paling banyak 32 argumen setelah executable. |

Layer byte menegakkan grammar token, encoding, dan budget generik. Contohnya
`1.0` ditolak meski Draft 2020-12 menganggap nilai matematis itu integer.
Layer schema menegakkan objek tertutup, field wajib, `const` versi,
discriminator, dan batas khusus field seperti port. Versi asing dan field
asing jatuh pada layer schema karena caller sudah memilih kontrak v1.
Layer semantik memeriksa batas byte khusus tipe serta hubungan yang
memerlukan instruksi asli atau state tepercaya. Data yang ditolak berhenti di
layer pertama yang gagal. Untuk fixture dengan lebih dari satu pelanggaran,
urutan diagnostik bukan bagian dari wire contract.
[Draft 2020-12 Validation](https://json-schema.org/draft/2020-12/json-schema-validation)

## Resolusi, tipe, dan provenance

Intent ID berupa 3–64 byte ASCII lowercase, terdiri dari minimal dua komponen
bertitik dengan huruf awal dan karakter berikutnya dari huruf, digit, atau
underscore. Slot name merupakan satu komponen dengan batas 32 byte.
Schema memeriksa bentuk ID. Resolver dan policy menggunakan snapshot
katalog terverifikasi untuk membership, tipe dan kewajiban slot,
default, konflik lintas slot, efek, dan capability. Fixture DCT-002 memakai
aturan sintetis per contoh. Registry produksi menjadi bagian DCT-003.

| Tipe slot | Domain v1 |
| --- | --- |
| `port`, `protocol` | Port 1–65.535, protokol `tcp`, `udp`, atau `all`. |
| `positive-int`, `depth`, `duration-seconds` | Berturut-turut 1–1.000, 1–32, dan 1–604.800 detik. Katalog boleh memperketat. |
| `time-window` | Interval setengah terbuka dalam detik Unix UTC, dengan awal lebih kecil dari akhir. Batas atas 253.402.300.799. Jam referensi dan zona input berasal dari konteks request yang terverifikasi. |
| `path`, `unit-name`, `extension`, `filename` | Literal path 1–1.024 byte, unit subset ASCII 1–255 byte tanpa flag/glob, ekstensi 1–32 byte, nama berkas 1–255 byte. Resolver memeriksa sintaks dan makna per intent dan profil. |

Span `{start, end}` menggunakan offset byte berbasis nol pada snapshot asli,
dengan awal inklusif dan akhir eksklusif. Periksa
`0 <= start < end <= jumlah_byte_input` dan batas scalar UTF-8 pada kedua
ujung. Tabel pemetaan teks normalisasi ke byte asli wajib menghasilkan satu
slice kontinu yang tepat. Ambiguitas pemetaan menghasilkan klarifikasi.
Nilai literal path dan nama target memakai byte slice asli tanpa NFC, case
folding, atau substitusi. Untuk angka, resolver dapat memetakan token ke
nilai bertipe setelah cek rentang. Interval waktu memakai hasil resolusi
tepercaya yang terikat ke request dan jam referensinya.

Setiap slot yang di-resolve memiliki satu provenance tertutup.
`input-span` menunjuk slice yang mendukung slot dalam kandidat intent
tersebut. `context-ref` menunjuk kandidat request yang sudah diverifikasi
dan memiliki nama slot serta tipe yang sama. `catalog-default` tersedia
saat slot belum diberi nilai dan katalog memiliki default eksplisit.
Provenance menyertai nilai sampai validasi policy. Katalog dan konteks
yang dirujuk memakai snapshot beridentitas di atas.

## State dan policy

`resolved` membawa intent kanonik, slot wajib yang lengkap, dan daftar
`unresolved` serta `alternatives` kosong. `incomplete` menyebut intent
dan slot wajib yang hilang dengan problem `missing`. Untuk `ambiguous`,
ambiguity slot pada intent yang diketahui memakai problem `ambiguous`
atau `conflict` dan mencatat setiap slot wajib yang belum terisi.
Ambiguity antara intent memakai minimal dua alternatif katalog dan
mengosongkan intent terpilih serta daftar slot. `unsupported` dan
`invalid` membawa daftar slot, problem, dan alternatif kosong. Intent
boleh absen ketika belum ada hasil kanonik.

| State | Keputusan dan reason yang konsisten |
| --- | --- |
| `resolved` | `allow-proposal`/`proposal-eligible`, `allow-execute-eligible`/`execute-eligible` pada fase yang mengizinkan, atau `deny`/`policy-restriction`. |
| `incomplete` | `clarify`/`missing-slot` atau `deny`/`policy-restriction`. |
| `ambiguous` | `clarify`/`ambiguous` atau `deny`/`policy-restriction`. |
| `unsupported` | `unsupported`/`unsupported-intent` atau `unsupported-profile`, atau `deny`/`policy-restriction`. |
| `invalid` | `deny`/`invalid-candidate` atau `policy-restriction`. |

`PolicyDecision` menyimpan satu definisi enum keputusan. Efek berasal dari
binding katalog dan capability aktual. `effect.class` memakai INFO, READ,
CHANGE, HIGH, atau UNKNOWN. `axes` berisi sumbu unik dalam urutan ASCII
sesuai kosakata schema. Untuk state selain `resolved`, gunakan UNKNOWN dan
sumbu kosong. Keputusan yang mengizinkan proposal atau eligibility memakai
scope lokal yang diverifikasi. Keputusan terminal memakai scope `none`
dan berhenti sebelum penerbitan plan. Permintaan profil yang tak didukung
dapat menghasilkan `unsupported`. Upaya mengikat target di luar scope
atau melanggar kebijakan menghasilkan penolakan. Policy menghitung efek
serta eligibility sendiri dari trust context. Skor model tetap data ranking.

`allow-execute-eligible` tersedia sebagai nilai wire untuk fase mendatang.
Policy F0–F4 menolaknya secara semantik. Pada fase yang memenuhi gate,
eligibility hanya berlaku untuk binding INFO/READ yang memenuhi katalog,
capability, dan scope. Efek jaringan, CHANGE, serta kelompok service/log
yang ditetapkan baseline tetap proposal-only. Approval manusia melalui
kanal tepercaya, otorisasi broker, dan pemeriksaan ulang sebelum
eksekusi adalah langkah terpisah.

## Rencana dan identitas target

| `action.kind` | Kontrak |
| --- | --- |
| `proposal-only` | Representasi executable dan argv bertipe untuk konsumen proposal. Copyability kelak ditentukan renderer dan semantik operand. |
| `structured-proposal` | Handler native dan referensi slot bertipe untuk penyajian terstruktur non-executable. Cocok untuk operasi seperti top-N direktori. |
| `execution-candidate` | Kontrak fase mendatang untuk backend executable atau native. Wajib membawa constraints dan expiry. Membutuhkan policy `allow-execute-eligible` serta gate terpisah sebelum otorisasi. |

Executable diidentifikasi dengan path absolut, versi, dan SHA-256 executable
yang diverifikasi. Argv mengecualikan `argv[0]`, yang berasal dari identitas
executable tepercaya. Setiap argumen merupakan satu atom `flag`,
`option-end` (`--`), `literal` UTF-8, atau `integer`. Integer diproyeksikan
ke token desimal kanonik. Literal dapat memuat spasi atau tanda baca dalam
satu atom. Compiler dan konsumen memeriksa binding per opsi dan operand
dengan template serta capability katalog. Free-form shell, ekspansi,
pipeline, dan approval tidak memiliki field pada kontrak ini.

Handler native memakai ID terversi melalui snapshot katalog dan daftar slot
IR yang tepat. `target_bindings` mengikat nama slot unik ke ID target yang
tercatat dalam scope dan konteks yang sama, dengan urutan dari recipe
kompilasi. Konsumen memeriksa kebijakan target dan identitas handle yang
aktif melalui otoritas konteks. Path literal dan token ID sendiri belum
memberi akses. Efek plan harus sama dengan keputusan policy. Backend
executable mencantumkan efek `spawn` sebagai proyeksi operasi yang
diusulkan.

Untuk execution candidate, `constraints` membatasi wall clock menjadi
1–5.000 ms dan total output menjadi 1–65.536 byte, dengan batas yang dapat
diperketat binding. `expires_boottime_ms` ialah waktu absolut milidetik
dari CLOCK_BOOTTIME pada boot dan sesi otoritas yang sama. Expiry harus
lebih besar dari waktu sekarang dan tidak melampaui expiry konteks.
Gunakan 30.000 ms sebagai TTL awal saat tersedia, dengan maksimum 120.000
ms. Perlakukan pergantian sesi, boot, snapshot, atau kegagalan clock
sebagai kondisi usang. Mode proposal tunduk pada freshness konteks.

### Digest kanonik

Keluarkan hanya field `digest` pada root dari objek plan yang telah
tervalidasi. Serialisasikan objek yang tersisa sebagai UTF-8 menggunakan
JCS RFC 8785, termasuk urutan array, field opsional yang hadir, dan scalar
Unicode asli. Hitung SHA-256 atas prefiks ASCII persis
`dictum:execution-plan:v1\n` (byte terakhir LF `0a`, tanpa NUL) diikuti byte
JCS, lalu tulis hasil sebagai 64 digit hex lowercase. Tidak ada byte
pemisah tambahan. Konsumen memeriksa ulang digest atas snapshot immutable
yang dipakai pemeriksaan policy. Digest mengikat isi plan. Autentikasi
authority, persetujuan, TTL challenge, dan anti-replay bergantung pada
kontrak otorisasi F5. DCT-002 menetapkan algoritme. Fixture membawa hash
sintetis agar dapat menguji bentuk dan binding tanpa implementasi JCS.
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html)

## Matriks pemeriksaan semantik

| Kondisi | Pemeriksaan di luar JSON Schema |
| --- | --- |
| Request atau rekaman resolusi, keputusan, aksi berbeda | Cocokkan ID dengan rekaman immutable yang diterbitkan pada request yang sama. Tolak mismatch termasuk ketika setiap objek sah secara struktur. |
| Context/catalog/policy berbeda atau usang | Cocokkan versi dan hash dengan snapshot terverifikasi yang aktif. Periksa freshness, sesi, dan domain waktu yang sama. |
| Span atau provenance invalid | Periksa batas byte, scalar, nilai literal, hubungan kandidat, tipe, dan sumber default. Tolak default palsu atau ref yang berasal dari konteks lain. |
| Slot wajib hilang atau bertentangan | Periksa himpunan slot katalog, keunikan nama, tipe dan nilai, serta batas per intent. Tolak slot yang sekaligus terisi dan unresolved, slot ganda, interval terbalik, serta kombinasi yang dilarang katalog. |
| Intent asing | Izinkan ID dengan sintaks sah sebagai hipotesis. Canonical intent dan alternatif resolver wajib ada di katalog aktif. |
| Transisi atau reason tidak konsisten | Gunakan matriks state/keputusan dan larang penerbitan plan setelah keputusan terminal. |
| Efek atau eligibility berubah | Bandingkan efek dan scope dengan rule serta keputusan tepercaya. Tolak perluasan scope, eligibility pada F0–F4, dan binding yang permanen proposal-only. |
| Plan berbeda dari IR atau recipe | Cocokkan binding slot, identitas backend, typed argv atau referensi input, scope, efek, dan batas runtime. Hitung ulang digest apabila implementasi digest tersedia. |
| Percobaan eskalasi otoritas | Struktur tertutup menolak field authority asing. Authority yang memakai field sah tetapi tidak cocok dengan rekaman tepercaya tetap ditolak. Keputusan eligibility yang sah meneruskan ke gate masa depan yang terpisah. |

## Subset Draft 2020-12 untuk codegen

Meta-schema standar memeriksa format schema terlebih dahulu. Linter Dictum
membatasi konstruksi yang dapat dikompilasi. Keyword asing atau keyword di
luar bentuk berikut menggagalkan konfigurasi, termasuk pada definisi yang
belum dipakai.

| Bentuk | Keyword dan batas profil |
| --- | --- |
| Root | `$schema` persis Draft 2020-12, `$id` unik dari prefix nominal `https://dictum.invalid/spec/ir/` dan nama berkas, `title` opsional, serta `$defs` satu tingkat di root. |
| Object | `type: object`, `properties`, `required`, dan `additionalProperties: false` pada node yang sama. Nama properti/definisi berbentuk ASCII lowercase dengan angka atau underscore setelah huruf awal. |
| Array | `type: array`, satu schema `items`, serta `minItems` dan `maxItems` integer eksplisit. |
| Integer dan string | `type: integer` dengan `minimum`/`maximum` eksplisit atau `const`. String menggunakan `minLength`/`maxLength` dengan `pattern` opsional, `enum` string unik, atau `const`. Konstanta string profil memakai ASCII. |
| Pattern | Daftar pola tetap mencakup intent ID, nama field, hex 32/64 digit, subset unit, prefix path absolut, serta flag. Gunakan kelas ASCII dan assertion akhir absolut tetap `(?![\s\S])` untuk pola full match, sehingga LF terakhir tidak lolos lewat semantik `$` Python. Codegen menggantinya dengan pemindai sederhana dan pemeriksaan akhir. |
| Reference | Node `$ref` tunggal berbentuk `#/$defs/nama` atau `nama-berkas.schema.json#/$defs/nama` dalam empat berkas yang dipin. Lint seluruh graf containment dan referensi sebelum validasi. Siklus, target hilang, ref remote, anchor, dan ref dengan sibling ditolak. |
| Union | Node `oneOf` tunggal dengan cabang objek tertutup, langsung atau lewat ref. Tiap cabang mewajibkan `kind` ber-`const` string yang unik. |

Linter menolak konstruksi seperti Boolean subschema, union tipe, keyword
komposisi lain, dynamic refs, `format`, dan regex arbitrer. Kosakata keputusan,
efek, scope, dan identitas dipakai via ref. Lint oracle memeriksa kesetaraan
tag typed slot `ResolvedIR` dengan enum `expected_kind`. Registry oracle
memuat empat resource lokal dan menolak retrieval URI lain. `$id` hanya
identitas logis. [Draft 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core)

## Oracle pengembangan dan differential

Di Debian 13 Trixie, gunakan Python 3.13 dan paket Debian
`python3-jsonschema` (teruji 4.19.2-6) serta dependensi transitive dari
repositori Debian, termasuk `python3-referencing` (teruji 0.36.2-1).
Langkah instalasi memerlukan hak administrasi di lingkungan pengembangan.

```sh
apt-get update
apt-get install --no-install-recommends python3-jsonschema
python3 -B tests/ir/run.py
```

Suite membandingkan expected dan actual. Fixture raw mewakili byte melalui
teks, hex, atau pengulangan untuk uji batas. Fixture schema mengambil objek
golden dan perubahan terisolasi. Fixture semantik menguji rantai dan
konteks sintetis, termasuk contoh lengkap untuk tiap intent walking
skeleton. Harness memilih artefak dan konteks secara terpisah. Digest,
executable, ID, serta recipe fixture hanya data uji. Oracle tidak membaca
lingkungan operasi yang dimaksud dan tidak menjalankan aksi.

Untuk codegen berikutnya, lint dan urutkan graf lokal sebelum membentuk
tabel validasi C17. Bentuk node dapat diturunkan ke dispatch `kind`,
lookup field dan bitset required, serta pemeriksaan batas integer,
panjang, dan terminasi string. Parser byte C menerima pointer dan
panjang lalu memeriksa offset, akumulasi integer, dan ukuran sebelum baca
atau alokasi. Validator semantik mempertahankan rekaman tepercaya dan
pemeriksaan lintas objek secara terpisah. Dependensi CMake untuk generator
kelak harus mencakup seluruh graph input. Produk menggunakan artefak C,
tanpa dependensi Python.

Untuk C-04, jalankan parser dan validator C terhadap byte fixture yang sama
dan bandingkan dengan oracle Python independen serta ekspektasi gold.
Bandingkan layer penolakan, nilai bertipe pada penerimaan, dan span byte.
Gunakan sedikitnya 100 kasus unik, mencakup batas tepat dan di luar batas,
UTF-8, duplikat, overflow, field asing, dan perubahan urutan key atau
escape ekuivalen. Ulangi dengan GCC/Clang dan sanitizer. Simpan seed,
toolchain, dan payload minimal untuk mismatch. Native validator, codegen
produksi, penghitungan digest, dan kelulusan C-04 memerlukan evidence
tersendiri. [Gate C-04](../../plans/drafts/f0-v3.md#4-f0-c--walking-skeleton)
