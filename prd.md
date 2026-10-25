# PRD — AgentHandoff

| Item | Detail |
|---|---|
| Nama Produk | **AgentHandoff** |
| Tagline | *Never lose context when switching AI coding agents.* |
| Versi Dokumen | 1.0 |
| Tanggal | 25 Oktober 2026 |
| Status | Draft — siap dikembangkan |
| Tipe Produk | Open Source CLI Tool |
| Lisensi | MIT |
| Bahasa / Stack Utama | Python 3.11+ (tanpa dependensi eksternal untuk core MVP) |
| Platform | Windows, macOS, Linux |
| Repository | GitHub (nama repo: `agenthandoff`) |

---

## 1. Ringkasan Produk

**AgentHandoff** adalah CLI open source yang menyimpan, merangkum, dan memindahkan konteks pekerjaan antar AI coding agent — seperti Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Windsurf, dan OpenCode.

Saat developer berpindah agent, AgentHandoff menangkap keadaan project (tujuan, progress, keputusan teknis, file yang berubah, git state, dan next steps), lalu menuliskannya ke file konteks native yang otomatis dibaca agent tujuan saat startup:

| Agent Tujuan | File yang Ditulis |
|---|---|
| Claude Code | `CLAUDE.md` |
| Codex & agent berbasis standar AGENTS.md | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | `.cursor/rules/agent-handoff.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Windsurf | `.windsurf/rules/agent-handoff.md` |
| Agent apapun (netral) | `.agent-handoff/HANDOFF.md` |

Hasilnya: agent baru bisa langsung melanjutkan pekerjaan tanpa developer menjelaskan ulang project dari nol.

---

## 2. Latar Belakang & Masalah

### 2.1 Perubahan perilaku developer

Developer di 2026 tidak lagi memakai satu AI coding agent saja. Mereka berpindah-pindah karena:

- Limit/kuota satu agent habis → pindah ke agent lain
- Satu agent lebih bagus untuk tugas tertentu (satu untuk planning, satu untuk coding, satu untuk review)
- Ada agent gratis vs berbayar — dipakai bergantian
- Mencoba agent baru yang sedang hype
- Bekerja di beberapa mesin / environment berbeda

### 2.2 Masalah inti

Setiap kali berpindah agent, **konteks pekerjaan hilang**:

- Agent baru tidak tahu tujuan akhir project
- Agent baru tidak tahu apa yang sudah selesai dan belum
- Keputusan teknis (dan *alasannya*) harus dijelaskan ulang
- File mana yang sedang diubah dan kenapa, tidak tercatat
- TODO dan next steps tersebar di chat lama yang tidak bisa diakses agent baru

### 2.3 Dampak (pain points terukur)

1. **Waktu terbuang** — developer menghabiskan 5–30 menit setiap perpindahan hanya untuk *briefing ulang*.
2. **Keputusan berulang / konflik** — agent baru mengusulkan pendekatan yang sudah ditolak sebelumnya, karena tidak tahu riwayatnya.
3. **Pekerjaan dobel atau hilang** — task yang sudah selesai dikerjakan ulang; task penting terlupakan.
4. **Kualitas turun** — agent bekerja tanpa konteks = hasil generik, lebih banyak error & revisi.
5. **Tidak ada standar** — setiap agent punya format file konteks sendiri-sendiri (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, dst) dan tidak saling kompatibel.

### 2.4 Validasi permintaan

Kebutuhan ini muncul secara organik di komunitas developer — termasuk diskusi di GitHub Community yang secara eksplisit meminta *"Open-Source Context Protocol & Session Journal for AI Coding Agents"* untuk mengatasi hilangnya konteks saat berpindah antar AI coding agent. Belum ada tools dominan yang menyelesaikan ini secara sederhana, lokal, dan agent-agnostic. **Itulah celah AgentHandoff.**

---

## 3. Tujuan Produk

### 3.1 Tujuan utama (v1 / MVP)

1. Developer dapat **menangkap (capture)** konteks sesi kerja dalam **≤ 10 detik** dengan satu perintah.
2. Developer dapat **mengekspor (export)** konteks tersebut ke format agent tujuan dalam **satu perintah**.
3. Agent tujuan **langsung memahami** konteks tersebut tanpa prompt tambahan dari developer.
4. Semua data tersimpan **lokal** di dalam repo project (`/.agent-handoff/`) — tanpa server, tanpa akun, tanpa API key.

### 3.2 Tujuan jangka menengah (v1.x – v2)

1. Menjadi **format standar terbuka** untuk handoff antar agent (`session.json` terdokumentasi & stabil).
2. Membaca **riwayat sesi native** masing-masing agent (bukan hanya input manual).
3. Ekosistem **plugin/adapter komunitas** — kontributor bisa menambah dukungan agent baru lewat satu file adapter.
4. Adopsi komunitas: kontributor eksternal, masuk awesome-lists, jadi rujukan saat orang membahas "switching AI agents".

### 3.3 Non-tujuan (yang TIDAK dikerjakan)

- ❌ Bukan AI agent itu sendiri (tidak menulis kode, tidak memanggil LLM di core MVP)
- ❌ Bukan layanan cloud / SaaS (tidak ada server, sync cloud ditunda jauh)
- ❌ Bukan pengganti git (git tetap sumber kebenaran untuk kode)
- ❌ Bukan project management tool (bukan Jira/Trello; hanya konteks sesi)
- ❌ Tidak mengumpulkan telemetri / data pengguna

---

## 4. Target Pengguna

### 4.1 Persona utama — "Multi-Agent Developer" (target #1)

| Aspek | Detail |
|---|---|
| Siapa | Developer / indie hacker / freelancer yang memakai ≥ 2 AI coding agent |
| Kebiasaan | Claude Code pagi, Codex siang, Cursor malam — tergantung kuota & tugas |
| Pain terbesar | Capek briefing ulang; konteks hilang; keputusan teknis tidak tercatat |
| Yang dia hargai | Cepat, CLI, lokal, tidak mengunci ke satu vendor, bisa di-commit ke git |
| Cara menemukannya | GitHub, Hacker News, Reddit (r/ClaudeAI, r/ChatGPTCoding), X/Twitter dev community |

### 4.2 Persona sekunder

| Persona | Kebutuhan |
|---|---|
| **Tech Lead / Tim kecil** | Anggota tim (dan agent-nya) melanjutkan pekerjaan orang lain tanpa meeting panjang; handoff antar manusia sekaligus antar agent |
| **Open Source Contributor** | Maintainer/contributor memahami status pekerjaan terakhir sebuah repo dengan cepat |
| **Pelajar / Bootcamp student** | Sering ganti tools gratisan; butuh catatan progress belajar & project yang rapi |

### 4.3 Bukan target pengguna

- Pengguna non-teknis (tidak memakai AI coding agent)
- Perusahaan enterprise dengan kebutuhan compliance/SaaS di v1 (mungkin v3+)
- Pengguna satu agent yang tidak pernah berpindah (manfaatnya kecil untuk mereka)

---

## 5. Proposisi Nilai (Value Proposition)

> **"Pindah AI agent dalam 10 detik. Tanpa briefing ulang."**

| | Cara lama (manual) | Dengan AgentHandoff |
|---|---|---|
| Waktu briefing ulang | 5–30 menit per perpindahan | ±10 detik (2 perintah) |
| Keputusan teknis tercatat | Tidak (hilang di chat lama) | Ya, beserta alasannya |
| Format antar agent | Copy-paste manual, tidak standar | Otomatis ke file native tiap agent |
| Privasi | Upload ke layanan pihak ketiga | 100% lokal, di dalam repo |
| Riwayat | Tidak ada | Ter-versioning bersama git |

**Prinsip produk (product principles):**

1. **Local-first** — data tidak pernah meninggalkan mesin pengguna.
2. **Agent-agnostic** — netral, tidak memihak agent manapun.
3. **Zero-config untuk mulai** — perintah pertama harus berhasil tanpa setup apapun.
4. **Plain-text & git-friendly** — semua output bisa dibaca manusia dan di-commit.
5. **Tidak merusak** — tidak pernah menimpa tulisan pengguna di luar blok handoff.
6. **Sederhana > lengkap** — fitur sedikit tapi sangat reliable, mengalahkan fitur banyak tapi rapuh.

---

## 6. Ruang Lingkup (Scope)

### 6.1 MVP — v0.1 (WAJIB, target rilis pertama)

| # | Fitur | Deskripsi |
|---|---|---|
| F1 | `handoff capture` | Menangkap snapshot sesi: goal, agent asal, keputusan, done, todo, notes + git snapshot otomatis (branch, commit terakhir, file berubah, riwayat commit) |
| F2 | `handoff export --to <agent>` | Menulis konteks ke file native agent tujuan: `claude`, `codex`/`agents`, `gemini`, `cursor`, `copilot`, `windsurf`, `markdown`. Mendukung `--to all` |
| F3 | `handoff show` | Menampilkan handoff saat ini di terminal |
| F4 | Penyimpanan lokal terstruktur | `.agent-handoff/session.json` (sumber data) + `.agent-handoff/HANDOFF.md` (versi human-readable) |
| F5 | Export aman & idempotent | Blok handoff ditandai marker `<!-- agent-handoff:begin/end -->`; export ulang mengganti blok lama, tidak menduplikasi, tidak menghapus tulisan pengguna di luar blok |
| F6 | `handoff import-log` | Mengekstrak keputusan/todo/done dari file log/chat bebas dengan awalan `Decision:`, `TODO:`, `Done:` (termasuk Bahasa Indonesia: `Keputusan:`, `Selanjutnya:`, `Selesai:`) |
| F7 | Scan TODO otomatis | `--scan-todos` mengumpulkan komentar `TODO/FIXME` dari source code ke daftar next steps |
| F8 | Merge sesi | Capture berulang memperbarui sesi yang ada (todo yang dicatat di `--done` otomatis keluar dari daftar todo) |

### 6.2 v0.2 – v0.5 (setelah MVP tervalidasi)

| # | Fitur | Deskripsi |
|---|---|---|
| F9 | `handoff init` | Setup wizard: membuat `.agent-handoff/`, memilih agent yang dipakai, opsi gitignore |
| F10 | `handoff status` | Ringkasan singkat 5 baris: goal, progress, todo tersisa, terakhir diupdate |
| F11 | Baca riwayat sesi native — Claude Code | Parser sesi `~/.claude/projects/**.jsonl` → ekstrak goal/keputusan/file diubah otomatis |
| F12 | Baca riwayat sesi native — Codex & Gemini | Parser riwayat sesi masing-masing agent |
| F13 | `--summarize` (opsional, bawa API key sendiri) | Ringkasan otomatis sesi panjang memakai LLM pilihan pengguna (OpenAI/Anthropic/Ollama lokal). Core tetap jalan tanpa fitur ini |
| F14 | Multi-handoff / riwayat | Arsip handoff sebelumnya di `.agent-handoff/history/` + `handoff log` |
| F15 | Template per bahasa/framework | Konteks tambahan otomatis: stack terdeteksi (package.json, pyproject.toml, go.mod, dst) |

### 6.3 v1.0+ (jangka panjang)

| # | Fitur | Deskripsi |
|---|---|---|
| F16 | Spesifikasi format terbuka | Dokumen standar `HANDOFF-SPEC.md` agar tools lain bisa membaca/menulis format yang sama |
| F17 | Plugin adapter komunitas | `handoff export --to <nama>` dari package/adapter pihak ketiga |
| F18 | Watch mode | `handoff watch` — auto-capture berkala selama sesi berjalan |
| F19 | Integrasi editor | Ekstensi VS Code: tombol "Handoff" + panel status |
| F20 | Diff antar handoff | `handoff diff` — apa yang berubah sejak handoff terakhir |

## 7. User Stories & Kriteria Penerimaan

### US-1 — Capture konteks
> Sebagai developer yang baru selesai sesi dengan Claude Code, saya ingin menangkap keadaan pekerjaan saya dengan satu perintah, agar tidak ada konteks yang hilang.

**Kriteria penerimaan:**
- [ ] `handoff capture --goal "..." --from claude` berjalan ≤ 10 detik di repo biasa
- [ ] Git snapshot tercatat otomatis (branch, file berubah, 10 commit terakhir) bila berada di repo git; tetap berfungsi (tanpa error) di folder non-git
- [ ] File `.agent-handoff/session.json` dan `HANDOFF.md` terbuat / terupdate
- [ ] Capture kedua menggabungkan data (merge), bukan menimpa keputusan/todo sebelumnya

### US-2 — Export ke agent tujuan
> Sebagai developer yang kehabisan kuota Claude dan ingin lanjut di Codex, saya ingin mengekspor konteks ke `AGENTS.md` agar Codex langsung tahu harus melanjutkan apa.

**Kriteria penerimaan:**
- [ ] `handoff export --to codex` menulis blok handoff ke `AGENTS.md` (dibuat bila belum ada)
- [ ] Isi tulisan pengguna yang sudah ada di `AGENTS.md` **tidak terhapus**
- [ ] Export dijalankan 2x berturut-turut → tetap hanya ada **1 blok** handoff (idempotent)
- [ ] `--to all` mengekspor ke semua target yang didukung sekaligus
- [ ] Target tidak dikenal → error yang jelas + daftar target valid

### US-3 — Melihat status
> Sebagai developer yang membuka project setelah seminggu, saya ingin melihat ringkasan sesi terakhir dengan cepat.

- [ ] `handoff show` menampilkan HANDOFF.md di terminal
- [ ] Bila belum ada sesi → pesan ramah yang menjelaskan cara memulai (bukan error mentah)

### US-4 — Import dari log/chat
> Sebagai developer yang sudah punya catatan di file teks/chat, saya ingin mengimpornya tanpa mengetik ulang.

- [ ] `handoff import-log catatan.txt` mengekstrak baris `Decision:`/`TODO:`/`Done:` (EN & ID)
- [ ] Hasil impor ter-merge ke sesi aktif dan tampil di `handoff show`

### US-5 — Agent tujuan memahami konteks (uji kualitas)
> Sebagai pengguna, saya ingin agent baru benar-benar melanjutkan pekerjaan, bukan sekadar membaca file.

- [ ] Dalam pengujian manual dengan 3 agent berbeda, agent dapat menjawab dengan benar: (a) tujuan project, (b) yang sudah selesai, (c) langkah berikutnya — hanya dari file hasil export, tanpa prompt tambahan

---

## 8. Alur Pengguna (User Flow)

### 8.1 Alur utama — pindah agent

```text
[Selesai sesi di Agent A]
        │
        ▼
$ handoff capture --goal "…" --from claude \
    --decision "…" --todo "…" --done "…"
        │   (git state tercatat otomatis)
        ▼
[.agent-handoff/session.json + HANDOFF.md terupdate]
        │
        ▼
$ handoff export --to codex
        │
        ▼
[AGENTS.md berisi blok konteks]
        │
        ▼
[Buka Agent B di project yang sama]
        │
        ▼
Agent B membaca file konteksnya saat startup
→ langsung melanjutkan dari next steps ✅
```

### 8.2 Alur alternatif
- **Tanpa flag lengkap:** `handoff capture` saja tetap valid — hanya git snapshot + timestamp.
- **Dari catatan lama:** `handoff import-log log.txt` → `handoff export --to gemini`.
- **Cek cepat:** `handoff show`.

---

## 9. Kebutuhan Fungsional (Functional Requirements)

| ID | Kebutuhan | Prioritas |
|---|---|---|
| FR-01 | CLI tersedia via `pip install agenthandoff` dan perintah `handoff` | Must |
| FR-02 | Perintah: `capture`, `export`, `show`, `import-log` (MVP) | Must |
| FR-03 | Git snapshot otomatis; graceful degradation di folder non-git | Must |
| FR-04 | Format penyimpanan JSON terdokumentasi (`session.json` skema v1) | Must |
| FR-05 | Export ke 7 target: claude, codex/agents, gemini, cursor, copilot, windsurf, markdown | Must |
| FR-06 | Blok export bermarker, idempotent, menjaga konten pengguna | Must |
| FR-07 | Merge semantik: `--done` menghapus item sama dari todo; tidak ada duplikat todo/done | Must |
| FR-08 | Semua perintah mendukung `--path` untuk menunjuk root project lain | Should |
| FR-09 | Output terminal ringkas, informatif, ada indikator sukses/gagal yang jelas | Should |
| FR-10 | Bekerja offline penuh (MVP core) | Must |
| FR-11 | Encoding UTF-8, mendukung teks Bahasa Indonesia & emoji | Must |
| FR-12 | `--help` lengkap untuk setiap perintah | Must |

## 10. Kebutuhan Non-Fungsional

| Aspek | Target |
|---|---|
| **Performa** | Capture/export ≤ 2 detik di repo ≤ 10.000 file (tidak termasuk scan-todos) |
| **Dependensi** | Core MVP: **0 dependensi eksternal** (Python standard library saja) |
| **Privasi** | Tidak ada network call, telemetri, atau pengumpulan data di core |
| **Keamanan data** | Tidak pernah menghapus/menimpa konten pengguna di luar blok handoff; file ditulis atomik sebisa mungkin |
| **Kompatibilitas** | Python 3.11+; Windows/macOS/Linux; path dengan spasi & karakter non-ASCII |
| **Keandalan** | `session.json` rusak → error yang bisa dipahami + saran pemulihan, bukan crash traceback mentah ke pengguna awam |
| **Aksesibilitas CLI** | Pesan error menjelaskan *apa yang salah* + *cara memperbaikinya* |
| **Dokumentasi** | Setiap fitur publik terdokumentasi di README + `--help` |

---

## 11. Desain Data — Skema `session.json` (v1)

```json
{
  "project": "nama-project",
  "goal": "Menyelesaikan fitur login",
  "source_agent": "claude",
  "created_at": "2026-10-25T10:00:00+07:00",
  "updated_at": "2026-10-25T12:30:00+07:00",
  "decisions": [
    { "text": "Pakai JWT", "reason": "stateless, cocok untuk API" }
  ],
  "todos": ["Tambahkan refresh token", "Tulis test untuk /login"],
  "done": ["Endpoint /login selesai"],
  "notes": "Catatan bebas…",
  "git": {
    "is_repo": true,
    "branch": "feat/login",
    "last_commit": "a1b2c3d feat: login endpoint",
    "changed_files": ["src/auth.py"],
    "changed_count": 1,
    "recent_commits": ["a1b2c3d feat: login endpoint"],
    "diff_stat": " src/auth.py | 40 ++++"
  }
}
```

**Aturan skema:**
- Field baru hanya boleh *ditambahkan* (backward compatible); perubahan breaking menaikkan versi skema.
- `HANDOFF.md` selalu di-generate dari `session.json` — JSON adalah sumber kebenaran tunggal.

---

## 12. Tampilan Output Handoff (`HANDOFF.md`)

Dokumen yang dibaca manusia & agent, berisi urut:

1. **Header** — project, agent terakhir, waktu update
2. **🎯 Goal**
3. **🌿 Git state** — branch, commit terakhir, file berubah, commit terbaru
4. **✅ Done**
5. **🧭 Decisions (and why)**
6. **⏭️ Next steps / TODO** (format checkbox markdown)
7. **📝 Notes**
8. Footer penanda generated-by

---

## 13. Metrik Keberhasilan

### 13.1 Metrik produk (kualitas)

| Metrik | Target |
|---|---|
| Waktu capture → export selesai | ≤ 10 detik (alur manual terukur) |
| Uji US-5 (agent memahami konteks) | Lolos di ≥ 3 agent berbeda |
| Bug "konten pengguna terhapus" | **0** (kriteria blocking untuk rilis) |
| Test coverage core (capture/export/merge) | ≥ 80% |

### 13.2 Metrik adopsi (open source)

| Fase | Target |
|---|---|
| 2 minggu pertama | Rilis v0.1 di PyPI + GitHub; 100 star pertama; tampil di ≥ 2 awesome-list (PR diajukan) |
| Bulan 1 | 500 star; ≥ 5 kontributor eksternal; ≥ 10 issue organik (request/bug dari pengguna nyata) |
| Bulan 3 | 2.000+ star; adapter/format dibahas atau dipakai project lain; undangan tulis blog/kolaborasi komunitas |
| Berkelanjutan | Issue dijawab ≤ 48 jam; rilis minor tiap 2–4 minggu selama 6 bulan pertama |

### 13.3 Sinyal validasi (yang dicari, bukan sekadar angka)

- Orang asing membuat PR tanpa diminta
- Ada yang membuka issue "support agent X please" → bukti permintaan nyata
- Disebut di postingan/video orang lain tanpa kita minta
- Ada yang fork untuk keperluan sendiri dan membintangi repo

---

## 14. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Agent mengubah format file konteksnya | Adapter rusak | Adapter dibuat kecil & terpisah per agent; mudah di-update via PR komunitas; versi format dicatat |
| Vendor agent merilis fitur handoff bawaan | Kompetisi berat | Fokus pada **agent-agnostic & lokal**: vendor hanya akan mendukung ekosistemnya sendiri; AgentHandoff menjembatani *antar* vendor. Posisi ini justru menguat |
| Dianggap "cuma file markdown" | Sulit viral | Tonjolkan otomatisasi: git snapshot, parsing riwayat sesi, merge semantik, idempotent export. Demo visual "pindah agent 10 detik" sebagai materi promosi utama |
| Adopsi lambat di awal | Motivasi turun | Launch terencana (Hacker News, Reddit, dev.to, komunitas ID), demo GIF, dogfooding pada repo sendiri + repo publik lain |
| Kualitas ringkasan manual rendah | Agent tetap bingung | Struktur template yang memaksa informasi penting (goal/decisions/next steps); roadmap parser sesi otomatis (F11–F13) |
| Nama/format ditiru project besar | Persaingan | Bergerak cepat, bangun komunitas & standar terbuka (F16) — standar yang diadopsi duluan sulit digeser |

---

## 15. Kompetitor & Pembeda

| Alternatif | Kekurangannya | Pembeda AgentHandoff |
|---|---|---|
| Copy-paste manual antar agent | Lambat, tidak standar, mudah lupa | 2 perintah, format konsisten |
| Menulis `CLAUDE.md`/`AGENTS.md` manual per agent | Harus memelihara banyak file yang isinya sama | Satu sumber (`session.json`) → semua format |
| Fitur memory bawaan tiap agent | Terkunci di satu vendor, tidak bisa dipindah | Netral, memindahkan konteks *antar* vendor |
| Git commit message saja | Tidak menangkap keputusan/todo/alasan | Konteks sesi lengkap & terstruktur |
| Notion/docs eksternal | Di luar repo, agent tidak otomatis membaca | Di dalam repo, file yang memang dibaca agent saat startup |

---

## 16. Keputusan Terbuka (Open Questions)

| # | Pertanyaan | Keputusan sementara |
|---|---|---|
| Q1 | Perlukah LLM summarization di MVP? | **Tidak.** MVP full-manual + git otomatis. LLM = opsional v0.4 (F13), bawa API key sendiri |
| Q2 | Satu `session.json` per repo atau per branch? | Per repo dulu (sederhana); per branch masuk backlog v1 |
| Q3 | Default `CLAUDE.md` dkk ikut di-commit atau gitignore? | Ikut ter-commit **direkomendasikan** (itu gunanya untuk tim), tapi `.agent-handoff/` diberi opsi gitignore saat `init` |
| Q4 | Nama perintah: `handoff` atau `agenthandoff`? | `handoff` (pendek); package PyPI: `agenthandoff` |
| Q5 | Bahasa dokumentasi utama? | Inggris (audiens GitHub global) + README ringkas Bahasa Indonesia |

---

## 17. Definisi "Selesai" untuk Rilis v0.1 (Definition of Done)

- [ ] Semua fitur F1–F8 terimplementasi & lulus test
- [ ] 0 bug kategori "menghapus konten pengguna"
- [ ] `pip install` dari PyPI (atau TestPyPI saat RC) berhasil di Windows/macOS/Linux
- [ ] README berisi: masalah, demo (GIF/asciinema), instalasi 1 baris, contoh 3 perintah, daftar agent yang didukung
- [ ] `LICENSE` (MIT), `CONTRIBUTING.md`, `CHANGELOG.md` tersedia
- [ ] CI (GitHub Actions): test otomatis di 3 OS × Python 3.11/3.12/3.13
- [ ] Dogfooding: repo AgentHandoff sendiri memakai AgentHandoff (ada `.agent-handoff/` nyata di repo)
- [ ] Materi launch siap: postingan Hacker News/Reddit/dev.to + GIF demo ≤ 15 detik

---

*Dokumen ini hidup (living document). Perubahan scope dicatat di CHANGELOG dan revisi PRD diberi nomor versi baru.*
