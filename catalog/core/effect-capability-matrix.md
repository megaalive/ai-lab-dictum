# Matriks efek dan capability DCT-003

Ditampilkan dari registry dan profil Debian 13; semua capability BLOCKED, compatibility NOT VERIFIED, execute_eligible=false, host-equivalence NOT RUN. Efek adalah proyeksi operasi, bukan izin atau aktivitas yang dijalankan. P = permanen proposal-only; C = kandidat F5 masih BLOCKED; I = INFO tanpa executor.

| # | Intent | Kelas / efek | Status masa depan | Capability | Sumber kandidat |
|---:|---|---|---|---|---|
| 1 | `help.command.explain` | INFO / — | I | `linux.help.command.explain` | catalog build index |
| 2 | `help.intent.list` | INFO / — | I | `linux.help.intent.list` | catalog build index |
| 3 | `system.os.info` | INFO / filesystem-read | I | `linux.system.os.info` | os-release(5), uname(2) |
| 4 | `system.uptime.summary` | INFO / filesystem-read | I | `linux.system.uptime.summary` | proc_uptime(5), proc_loadavg(5) |
| 5 | `network.listener.lookup` † | READ / ipc, secret-exposure, spawn | C | `linux.network.listener.lookup` | ss(8) |
| 6 | `network.connection.active` | READ / ipc, resource-usage, secret-exposure, spawn | C | `linux.network.connection.active` | ss(8) |
| 7 | `network.interface.list` | READ / ipc, secret-exposure, spawn | C | `linux.network.interface.list` | ip-link(8), ip-address(8) |
| 8 | `network.route.table` | READ / ipc, secret-exposure, spawn | C | `linux.network.route.table` | ip-route(8) |
| 9 | `network.dns.config` | READ / filesystem-read, ipc, secret-exposure | C | `linux.network.dns.config` | resolv.conf(5), resolved.conf(5) |
| 10 | `network.dns.lookup` | READ / ipc, network, resource-usage, secret-exposure, spawn | P | `linux.network.dns.lookup` | dig(1), resolv.conf(5) |
| 11 | `network.connectivity.ping` | READ / network, requires-privilege, resource-usage, spawn | P | `linux.network.connectivity.ping` | ping(8) |
| 12 | `diagnosis.connectivity` | READ / resource-usage | P | `linux.diagnosis.connectivity` | baseline v3 diagnostic guide |
| 13 | `service.status.get` | READ / ipc, secret-exposure, spawn | P | `linux.service.status.get` | systemctl(1) |
| 14 | `service.list.active` | READ / ipc, resource-usage, secret-exposure, spawn | P | `linux.service.list.active` | systemctl(1) |
| 15 | `service.failed.list` † | READ / ipc, resource-usage, secret-exposure, spawn | P | `linux.service.failed.list` | systemctl(1) |
| 16 | `service.enabled.list` | READ / ipc, resource-usage, secret-exposure, spawn | P | `linux.service.enabled.list` | systemctl(1) |
| 17 | `log.service.query` † | READ / filesystem-read, ipc, resource-usage, secret-exposure, spawn | P | `linux.log.service.query` | journalctl(1) |
| 18 | `log.system.errors` | READ / filesystem-read, ipc, resource-usage, secret-exposure, spawn | P | `linux.log.system.errors` | journalctl(1) |
| 19 | `log.boot.messages` | READ / filesystem-read, ipc, requires-privilege, resource-usage, secret-exposure, spawn | P | `linux.log.boot.messages` | dmesg(1), journalctl(1) |
| 20 | `storage.filesystem.usage` † | READ / filesystem-read, secret-exposure, spawn | C | `linux.storage.filesystem.usage` | df(1) |
| 21 | `storage.inode.usage` | READ / filesystem-read, secret-exposure, spawn | C | `linux.storage.inode.usage` | df(1) |
| 22 | `storage.directory.usage` † | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.storage.directory.usage` | du(1) |
| 23 | `storage.block.list` | READ / filesystem-read, secret-exposure, spawn | C | `linux.storage.block.list` | lsblk(8) |
| 24 | `storage.mount.list` | READ / filesystem-read, secret-exposure, spawn | C | `linux.storage.mount.list` | findmnt(8), proc_pid_mountinfo(5) |
| 25 | `file.search` † | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.file.search` | find(1) |
| 26 | `file.text.search` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.file.text.search` | grep(1) |
| 27 | `file.metadata.stat` | READ / filesystem-read, secret-exposure | C | `linux.file.metadata.stat` | stat(1), stat(2) |
| 28 | `file.permission.check` | READ / filesystem-read, secret-exposure | C | `linux.file.permission.check` | access(2), faccessat2(2) |
| 29 | `file.head_tail.view` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.file.head_tail.view` | head(1), tail(1) |
| 30 | `archive.contents.list` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.archive.contents.list` | tar(1), unzip(1) |
| 31 | `process.list.top_cpu` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.process.list.top_cpu` | ps(1), proc_pid_stat(5) |
| 32 | `process.list.top_mem` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.process.list.top_mem` | ps(1), proc_pid_status(5) |
| 33 | `process.lookup.name` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.process.lookup.name` | ps(1), proc_pid_comm(5) |
| 34 | `process.tree.view` | READ / filesystem-read, resource-usage, secret-exposure | C | `linux.process.tree.view` | pstree(1), proc_pid_stat(5) |
| 35 | `memory.summary` † | READ / filesystem-read, spawn | C | `linux.memory.summary` | free(1), proc_meminfo(5) |
| 36 | `cpu.hardware.info` | READ / filesystem-read, secret-exposure, spawn | C | `linux.cpu.hardware.info` | lscpu(1) |
| 37 | `package.installed.check` | READ / filesystem-read, secret-exposure, spawn | C | `linux.package.installed.check` | dpkg-query(1) |
| 38 | `package.search.local` | READ / filesystem-read, resource-usage, secret-exposure, spawn | C | `linux.package.search.local` | apt-cache(8) |
| 39 | `user.session.who` | READ / filesystem-read, secret-exposure, spawn | C | `linux.user.session.who` | who(1), utmp(5) |
| 40 | `user.identity.info` | READ / — | C | `linux.user.identity.info` | getuid(2), getgid(2), getgroups(2) |
| 41 | `diagnosis.disk_full` | READ / resource-usage | P | `linux.diagnosis.disk_full` | baseline v3 diagnostic guide |
| 42 | `diagnosis.high_load` | READ / resource-usage | P | `linux.diagnosis.high_load` | baseline v3 diagnostic guide |
| 43 | `diagnosis.service_crash` | READ / resource-usage | P | `linux.diagnosis.service_crash` | baseline v3 diagnostic guide |
| 44 | `diagnosis.dns_failure` | READ / resource-usage | P | `linux.diagnosis.dns_failure` | baseline v3 diagnostic guide |
| 45 | `service.restart` † | CHANGE / ipc, persistent-mutation, requires-privilege, resource-usage, spawn | P | `linux.service.restart` | systemctl(1) |
| 46 | `service.reload` | CHANGE / ipc, persistent-mutation, requires-privilege, resource-usage, spawn | P | `linux.service.reload` | systemctl(1) |
| 47 | `archive.extract.safe` | CHANGE / filesystem-read, filesystem-write, persistent-mutation, resource-usage, secret-exposure, spawn | P | `linux.archive.extract.safe` | tar(1), unzip(1) |
| 48 | `file.compress.archive` | CHANGE / filesystem-read, filesystem-write, persistent-mutation, resource-usage, secret-exposure, spawn | P | `linux.file.compress.archive` | tar(1) |

† Walking skeleton F0-C. Rincian rights, namespace, socket/IPC, scope, output, fixture dan oracle terdapat pada pasangan record JSON. Tidak ada resep executable yang siap dipakai.
