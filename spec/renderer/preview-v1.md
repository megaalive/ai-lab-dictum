# Kontrak preview deterministik v1 — A4

Status: kontrak F0-A; proposal-only. Normatif terhadap baseline v3 §9.3, §9.4, F0 S1/C-05/C-07, [IR](../ir/schema-profile.md) dan [katalog](../catalog/catalog-profile.md). Tidak mengotorisasi eksekusi, tidak membuktikan S1.

## Interface dan authority

Renderer murni, tanpa shell/spawn, network, filesystem probe atau LLM. Masukan berasal dari compiler tepercaya dan policy yang memverifikasi ulang snapshot: ExecutionPlan v1 yang valid, decision allow-proposal, action proposal-only, identitas executable absolut, versi/digest/capability/recipe/target/context/catalog/policy yang masih aktif, dan shell profile eksplisit. Renderer tidak mempercayai flag otoritas dari model, teks bebas, nama executable dari PATH, maupun digest payload tanpa verifikasi. Jika binding belum terverifikasi (termasuk seluruh profil A3 saat ini), slot unresolved, target/scope tidak sah, stale identity atau policy terminal, tidak ada preview copyable. Jangan memproduksi command dari field string tak tepercaya atau merender action execution-candidate. Structured/native/narrative-only (termasuk top-N, file search native dan diagnosis) hanya representasi non-copyable; tanpa command/pipeline pengganti atau child operation plan tersembunyi.

Output tagged: COPYABLE (preview, profile ID, scope, source dan warning terpisah) atau NON_COPYABLE (reason code dan diagnostic terstruktur teredaksi, tidak ada field command). Policy deny/unsupported/clarify tidak direduksi menjadi copyable. Error tidak echo input/argv, path, source text, secret atau control sequence. Jangan otomatis mengisi clipboard/history atau mengeksekusi hasil. Rendering tidak memberi approval; preview yang disalin di luar containment, mungkin gagal/berdampak, identitas file bisa berubah. Copyable hanya berarti sintaks dan semantics recipe yang telah diverifikasi, bukan aman/sukses di shell modifikasi pengguna.

## Profil shell

Dua profil yang akan diuji: bash-posix-clean-v1 (Bash dengan --noprofile --norc, noninteractive POSIX mode) dan dash-clean-v1 (dash noninteractive). Versi aktual dipin di S1; belum didukung sebagai klaim runtime. CWD yang sama dengan scope terverifikasi (bukan grant), LC_ALL=C.UTF-8, TZ=UTC, TERM=dumb, PATH minimal; environment kosong selain allowlist, HOME fixture kosong, tanpa BASH_ENV/ENV, startup, alias/function, history expansion, plugin, pager atau konfigurasi user; shell binaries absolute/pinned, loader dan fixture trust terpisah. Jangan bergantung pada shell default atau terminal escaping. Profil asing termasuk fish/zsh/PowerShell/unknown -> NON_COPYABLE. Profil pengguna yang tidak memenuhi asumsi tidak mendapat jaminan round-trip; jangan mencoba mengubah shell pengguna.

## Byte dan token

1. Validasi wire/IR, decision/scope/recipe dan target oleh authority sebelum render. Executable absolute UTF-8 path, 1–1024 byte per token, argv maksimum 32 setelah argv[0]; argv[0] adalah executable persis (bukan basename). Literal kosong dapat sah hanya jika recipe mengizinkan. Integer signed exact <=2^53-1, proyeksi desimal ASCII tanpa plus/leading zeros; per-recipe bound lebih sempit. Atom option-end tepat '--'; flag hanya allowlist exact recipe. Tidak menerima string shell atau flag gabungan hasil interpolasi.
2. Reject seluruh preview jika token mengandung NUL, C0 (U+0000..001F), DEL/C1 (U+007F..009F), invalid UTF-8/surrogate/noncharacter, Unicode Cf (format, termasuk bidi override/isolate/zero-width), Zl/Zp (line/paragraph separator), atau invisibles konservatif U+034F, U+115F..1160, U+17B4..17B5, U+180B..180F, U+3164, U+FE00..FE0F, U+FFA0, U+E0100..E01EF. Unicode category version dicatat dan dipin untuk artefak release; daftar v1 konservatif, bukan deteksi lengkap spoofing. Reject bukan menghapus/mengganti/menormalisasi byte. NFC/NFD berbeda dipertahankan. Diagnostic hanya reason code dari daftar tertutup, tanpa raw token.
3. Render setiap token (termasuk executable, flag, integer dan '--') sebagai literal single-quoted: buka ASCII apostrof, salin scalar bytes tanpa perubahan kecuali apostrof ASCII U+0027 diganti empat byte apostrof, backslash, apostrof, apostrof (hex 27 5c 27 27), tutup apostrof. Gabungkan token dengan satu SP; tidak ada trailing newline, tab, expansion, substitution, pipe, redirect, heredoc, eval, multi-command atau interpolation. Karakter $, backtick, glob, ;, |, & dan backslash di dalam literal tetap data; bukan operator. Seluruh preview maksimal 32768 byte; reject jika melewati batas, bukan truncation.
4. Policy/recipe harus memeriksa grammar tiap utilitas **sebelum** quote. Option-end hanya jika utilitas mendukung pada posisi tersebut; tidak menambahkan '--' universal. Leading dash pada operand harus terbukti literal setelah terminator yang sah atau ditolak. '-' yang berarti stdin/stdout, @file/response file, pattern/regex, remote syntax, filter expression, unit name, path identity, relative target dan opsi yang membawa efek khusus harus diputuskan oleh validator per command. Jangan mengubah operand menjadi './' atau absolute path kecuali identitas descriptor sama dibuktikan terpisah; kontrak A4 memilih reject daripada rewrite. Quoting tidak mencegah option injection atau makna berbahaya dalam utilitas. Unknown recipe/capability -> NON_COPYABLE.

## Skeleton dan batas semantik

| Intent | Bentuk kandidat | Syarat sebelum copyable |
|---|---|---|
| memory.summary | command candidate | versi/grammar serta available vs free; tidak ada data OS palsu |
| network.listener.lookup | command candidate | port+protocol, local socket filter, PID visibility; expression grammar diperiksa, tidak ada active probe |
| service.failed.list | structured command candidate | status current bukan since boot, no pager/daemon side effects yang tidak diketahui |
| log.service.query | structured command candidate | literal unit, pinned interval/timezone/limit, hak yang ada, no raw sensitive output |
| storage.filesystem.usage | command candidate | scope local mount, remote/sensitive exclusion; tidak mengklaim mount dibaca |
| storage.directory.usage | native structured | non-copyable top-N; tidak membuat pipeline du/sort/head |
| file.search | native structured | non-copyable literal filters, root/descriptor, bounded traversal |
| service.restart | structured command candidate | exact unit, CHANGE dan privilege warning, tidak menambah sudo/su; belum ada binding terverifikasi |

Semua delapan saat ini NON_COPYABLE jika profil aktual A3 dipakai. Test recipe fixture bukan katalog produksi, tidak pernah digunakan CLI. Warning CHANGE/NET/privilege adalah metadata terpisah, tidak dimasukkan ke command. Kontrak renderer hanya bagian akhir, tidak memutuskan izin atau makna intent.

## Oracle A4 dan S1

Data-only golden suite dalam tests/renderer memeriksa literal quoting byte, bentuk terminal/non-copyable, trust gate sintetis dan dua grammar inert (terminator-supported dan no-terminator), satu bounded integer grammar. Expected preview ditulis eksplisit dan dibandingkan dengan hasil renderer reference development-only; bukan proof shell parse atau oracle policy/semantic host. Python oracle tidak menjalankan shell atau utility. S1 design di [s1-oracle.md](s1-oracle.md). S1 wajib >=10.000 generated cases per shell nyata + edge corpus, zero accepted mismatch, zero unintended command, reject no copyable. Semantic oracle (intent/slot/recipe/scope/efek) terpisah; argv equivalence tidak membuktikan operasi benar atau aman. S1 belum dijalankan, tidak ada product renderer atau scope gate yang dilonggarkan.
