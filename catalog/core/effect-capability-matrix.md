# Matriks efek dan capability DCT-003

Ditampilkan dari registry dan profil Debian 13; semua capability BLOCKED, compatibility NOT VERIFIED, execute_eligible=false, host-equivalence NOT RUN. Efek adalah proyeksi operasi, bukan izin atau aktivitas yang dijalankan. P = permanen proposal-only; C = kandidat F5 masih BLOCKED; I = INFO tanpa executor.

| # | Intent | Kelas / efek | Status masa depan | Surface | Capability | Sumber kandidat |
|---:|---|---|---|---|---|---|
| 1 | `help.command.explain` | INFO / — | I | indexed-docs | `linux.help.command.explain` | catalog build index |
| 2 | `help.intent.list` | INFO / — | I | indexed-docs | `linux.help.intent.list` | catalog build index |
| 3 | `system.os.info` | INFO / filesystem-read | I | native-candidate | `linux.system.os.info` | os-release(5), uname(2) |
| 4 | `system.uptime.summary` | INFO / filesystem-read | I | native-candidate | `linux.system.uptime.summary` | proc_uptime(5), proc_loadavg(5) |
| 5 | `network.listener.lookup` † | READ / filesystem-read, ipc, secret-exposure, spawn | C | command-candidate | `linux.network.listener.lookup` | ss(8), proc_pid_fd(5) |
| 6 | `network.connection.active` | READ / ipc, resource-usage, secret-exposure, spawn | C | command-candidate | `linux.network.connection.active` | ss(8) |
| 7 | `network.interface.list` | READ / ipc, secret-exposure, spawn | C | command-candidate | `linux.network.interface.list` | ip-link(8), ip-address(8) |
| 8 | `network.route.table` | READ / ipc, secret-exposure, spawn | C | command-candidate | `linux.network.route.table` | ip-route(8) |
| 9 | `network.dns.config` | READ / filesystem-read, ipc, secret-exposure | C | native-ipc-candidate | `linux.network.dns.config` | resolv.conf(5), resolved.conf(5), org.freedesktop.resolve1(5) |
| 10 | `network.dns.lookup` | READ / filesystem-read, ipc, network, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.network.dns.lookup` | dig(1), resolv.conf(5) |
| 11 | `network.connectivity.ping` | READ / filesystem-read, ipc, network, requires-privilege, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.network.connectivity.ping` | ping(8), resolv.conf(5) |
| 12 | `diagnosis.connectivity` | READ / — | P | narrative-only | `linux.diagnosis.connectivity` | baseline v3 diagnostic guide |
| 13 | `service.status.get` | READ / filesystem-read, ipc, secret-exposure, spawn | P | command-candidate | `linux.service.status.get` | systemctl(1) |
| 14 | `service.list.active` | READ / filesystem-read, ipc, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.service.list.active` | systemctl(1) |
| 15 | `service.failed.list` † | READ / filesystem-read, ipc, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.service.failed.list` | systemctl(1) |
| 16 | `service.enabled.list` | READ / filesystem-read, ipc, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.service.enabled.list` | systemctl(1) |
| 17 | `log.service.query` † | READ / filesystem-read, ipc, requires-privilege, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.log.service.query` | journalctl(1) |
| 18 | `log.system.errors` | READ / filesystem-read, ipc, requires-privilege, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.log.system.errors` | journalctl(1) |
| 19 | `log.boot.messages` | READ / filesystem-read, ipc, requires-privilege, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.log.boot.messages` | dmesg(1), journalctl(1) |
| 20 | `storage.filesystem.usage` † | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.storage.filesystem.usage` | df(1) |
| 21 | `storage.inode.usage` | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.storage.inode.usage` | df(1) |
| 22 | `storage.directory.usage` † | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.storage.directory.usage` | openat2(2), getdents64(2), statx(2) |
| 23 | `storage.block.list` | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.storage.block.list` | lsblk(8) |
| 24 | `storage.mount.list` | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.storage.mount.list` | findmnt(8), proc_pid_mountinfo(5) |
| 25 | `file.search` † | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.file.search` | openat2(2), getdents64(2), statx(2) |
| 26 | `file.text.search` | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.file.text.search` | openat2(2), getdents64(2), read(2), statx(2) |
| 27 | `file.metadata.stat` | READ / filesystem-read, secret-exposure | C | native-candidate | `linux.file.metadata.stat` | openat2(2), statx(2), fstat(2) |
| 28 | `file.permission.check` | READ / filesystem-read, secret-exposure | C | native-candidate | `linux.file.permission.check` | access(2), faccessat2(2) |
| 29 | `file.head_tail.view` | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.file.head_tail.view` | openat2(2), read(2), lseek(2) |
| 30 | `archive.contents.list` | READ / filesystem-read, resource-usage, secret-exposure, spawn | C | command-candidate | `linux.archive.contents.list` | tar(1), unzip(1) |
| 31 | `process.list.top_cpu` | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.process.list.top_cpu` | proc_pid_stat(5), proc_stat(5) |
| 32 | `process.list.top_mem` | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.process.list.top_mem` | proc_pid_status(5) |
| 33 | `process.lookup.name` | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.process.lookup.name` | proc_pid_comm(5), proc_pid_status(5) |
| 34 | `process.tree.view` | READ / filesystem-read, resource-usage, secret-exposure | C | native-candidate | `linux.process.tree.view` | proc_pid_stat(5), proc_pid_comm(5) |
| 35 | `memory.summary` † | READ / filesystem-read, spawn | C | command-candidate | `linux.memory.summary` | free(1), proc_meminfo(5) |
| 36 | `cpu.hardware.info` | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.cpu.hardware.info` | lscpu(1) |
| 37 | `package.installed.check` | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.package.installed.check` | dpkg-query(1) |
| 38 | `package.search.local` | READ / filesystem-read, resource-usage, secret-exposure, spawn | C | command-candidate | `linux.package.search.local` | apt-cache(8) |
| 39 | `user.session.who` | READ / filesystem-read, secret-exposure, spawn | C | command-candidate | `linux.user.session.who` | who(1), utmp(5) |
| 40 | `user.identity.info` | READ / — | C | native-candidate | `linux.user.identity.info` | getuid(2), getgid(2), getgroups(2) |
| 41 | `diagnosis.disk_full` | READ / — | P | narrative-only | `linux.diagnosis.disk_full` | baseline v3 diagnostic guide |
| 42 | `diagnosis.high_load` | READ / — | P | narrative-only | `linux.diagnosis.high_load` | baseline v3 diagnostic guide |
| 43 | `diagnosis.service_crash` | READ / — | P | narrative-only | `linux.diagnosis.service_crash` | baseline v3 diagnostic guide |
| 44 | `diagnosis.dns_failure` | READ / — | P | narrative-only | `linux.diagnosis.dns_failure` | baseline v3 diagnostic guide |
| 45 | `service.restart` † | CHANGE / filesystem-read, ipc, persistent-mutation, requires-privilege, resource-usage, spawn | P | command-candidate | `linux.service.restart` | systemctl(1) |
| 46 | `service.reload` | CHANGE / filesystem-read, ipc, persistent-mutation, requires-privilege, resource-usage, spawn | P | command-candidate | `linux.service.reload` | systemctl(1) |
| 47 | `archive.extract.safe` | CHANGE / filesystem-read, filesystem-write, persistent-mutation, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.archive.extract.safe` | tar(1), unzip(1) |
| 48 | `file.compress.archive` | CHANGE / filesystem-read, filesystem-write, persistent-mutation, resource-usage, secret-exposure, spawn | P | command-candidate | `linux.file.compress.archive` | tar(1) |

† Walking skeleton F0-C. Rincian rights, namespace, socket/IPC, scope, output, fixture dan oracle terdapat pada pasangan record JSON. Tidak ada resep executable yang siap dipakai.
