# PLAN — AgentHandoff

> Rencana pengembangan & peluncuran AgentHandoff dari nol sampai rilis publik dan tumbuh di GitHub.
> Dokumen pendamping: [`prd.md`](./prd.md) (apa & kenapa produk ini dibuat). Dokumen ini menjawab **bagaimana & kapan**.

| Item | Detail |
|---|---|
| Produk | AgentHandoff — *Never lose context when switching AI coding agents* |
| Versi Plan | 1.0 — 25 Oktober 2026 |
| Target Rilis MVP | v0.1.0 dalam **±3 minggu** (kerja paruh waktu) / ±7–10 hari (fokus penuh) |
| Stack | Python 3.11+, standard library only (core), pytest, GitHub Actions |
| Lisensi | MIT |

---

## 1. Ringkasan Eksekutif

**Strategi dalam satu kalimat:** bangun MVP sekecil mungkin yang menyelesaikan satu masalah dengan sangat baik (pindah agent tanpa kehilangan konteks), rilis cepat, lalu tumbuhkan lewat komunitas — bukan lewat fitur.

**Urutan besar:**

```text
Fase 0  Persiapan repo              (Hari 1)
Fase 1  Core: capture & storage     (Hari 2–3)
Fase 2  Export multi-agent          (Hari 4–5)
Fase 3  Import-log, scan, polish    (Hari 6–7)
Fase 4  Test, CI, dokumentasi       (Hari 8–10)
Fase 5  Rilis v0.1 + Launch         (Hari 11–14)
Fase 6  Iterasi berbasis feedback   (Minggu 3–8)
Fase 7  Standar & ekosistem         (Bulan 3+)
```

**Prinsip eksekusi:**
1. **Selesai > sempurna.** v0.1 boleh kasar asal tidak merusak data pengguna.
2. **Dogfooding sejak hari pertama** — project ini dikelola memakai AgentHandoff sendiri.
3. **Setiap fase menghasilkan sesuatu yang bisa didemokan**, bukan hanya kode.
4. **Waktu promosi = waktu ngoding.** Project open source yang bagus tapi tidak diluncurkan, tidak akan ditemukan orang.

---

## 2. Arsitektur Teknis

### 2.1 Gambaran sistem

```text
┌──────────────────────── CLI (handoff) ────────────────────────┐
│  capture │ export │ show │ import-log │ status │ init        │
└────┬─────────┬────────┬─────────┬────────────┬───────────────┘
     │         │        │         │            │
     ▼         ▼        ▼         ▼            ▼
┌─────────┐ ┌──────────┐ ┌───────┐ ┌────────┐ ┌────────────────┐
│ gitutil │ │ adapters │ │ render│ │ import │ │  core.Session  │
│ (git    │ │ per-agent│ │  .md  │ │ parser │ │ (dataclass +   │
│ snapshot│ │ writers  │ │       │ │        │ │  merge logic)  │
└────┬────┘ └────┬─────┘ └───┬───┘ └───┬────┘ └──────┬─────────┘
     └───────────┴───────────┴─────────┴─────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ .agent-handoff/session.json  │ ← sumber kebenaran
              │ .agent-handoff/HANDOFF.md    │ ← generated
              │ CLAUDE.md / AGENTS.md / dll  │ ← blok export
              └──────────────────────────────┘
```

### 2.2 Struktur repository

```text
agenthandoff/
├── README.md                  # wajah project (sangat penting untuk star)
├── LICENSE                    # MIT
├── CHANGELOG.md
├── CONTRIBUTING.md
├── prd.md                     # dokumen ini & pasangannya
├── plan.md
├── pyproject.toml             # packaging; entry point: handoff = agenthandoff.cli:main
├── .github/
│   ├── workflows/ci.yml       # test 3 OS × Python 3.11–3.13
│   ├── ISSUE_TEMPLATE/        # bug report, feature request, "agent support request"
│   └── PULL_REQUEST_TEMPLATE.md
├── src/agenthandoff/
│   ├── __init__.py            # versi
│   ├── cli.py                 # argparse: capture/export/show/import-log/status/init
│   ├── core.py                # Session dataclass, capture, save/load, render, merge
│   ├── gitutil.py             # git snapshot via subprocess (tanpa dependensi)
│   ├── adapters.py            # peta agent → file native + penulis blok idempotent
│   └── importer.py            # parser log/chat (F6) & scan TODO (F7)
├── tests/
│   ├── test_core.py           # capture, merge, save/load round-trip
│   ├── test_adapters.py       # idempotency, menjaga konten pengguna, semua target
│   ├── test_gitutil.py        # repo git & folder non-git
│   ├── test_importer.py       # parser EN/ID, scan TODO
│   └── test_cli.py            # perintah end-to-end (tmp_path)
├── examples/
│   ├── demo.sh                # skrip demo otomatis (untuk rekaman GIF)
│   ├── sample-log.txt         # contoh log untuk import-log
│   └── sample-HANDOFF.md      # contoh output
└── docs/
    ├── ROADMAP.md
    ├── FORMAT.md              # spesifikasi skema session.json v1
    └── LAUNCH.md              # checklist & naskah peluncuran
```

### 2.3 Keputusan teknis kunci

| # | Keputusan | Alasan |
|---|---|---|
| T1 | Python + standard library saja untuk core | Instalasi tidak pernah gagal karena dependensi; jalan di mana saja |
| T2 | `session.json` = sumber kebenaran tunggal; semua output di-generate darinya | Konsistensi antar format; mudah di-diff & di-versioning |
| T3 | Blok export bermarker HTML comment + replace, bukan append | Idempotent; aman untuk tulisan pengguna (target 0 insiden data hilang) |
| T4 | Git dipanggil via `subprocess`, bukan library | 0 dependensi; perilaku sama dengan git yang dikenal pengguna |
| T5 | Adapter = data (dict nama→path) + 1 fungsi penulis generik | Menambah agent baru cukup 1 baris → ramah kontributor pertama |
| T6 | Argparse (bawaan) bukan framework CLI eksternal | Konsisten dengan T1; kebutuhan CLI masih sederhana |
| T7 | Semua path memakai `pathlib`, encoding UTF-8 eksplisit | Aman lintas OS, nama file non-ASCII, teks Bahasa Indonesia/emoji |

---

## 3. Rencana Per Fase

### FASE 0 — Persiapan (Hari 1) ✅ fondasi sebagian sudah dibuat

**Tujuan:** repo siap dikerjakan & siap dilihat publik sejak commit pertama.

- [ ] `git init`, repo GitHub dibuat (public), deskripsi repo memakai tagline
- [ ] Struktur folder sesuai §2.2; `pyproject.toml` dengan entry point `handoff`
- [ ] `LICENSE` MIT, `.gitignore` (Python + `.agent-handoff/` opsional per-project pengguna)
- [ ] README kerangka dulu: judul, tagline, masalah, "coming soon" + cara ikut berkontribusi
- [ ] GitHub: label issue (`good first issue`, `help wanted`, `new-agent-request`, `bug`, `docs`), issue template, milestone v0.1
- [ ] Commit pertama: *"feat: project scaffold"*

**Deliverable:** repo publik yang terlihat serius meski belum ada fitur.

---

### FASE 1 — Core: Capture & Storage (Hari 2–3)

**Tujuan:** `capture → session.json + HANDOFF.md` bekerja end-to-end.

| Task | Detail | Estimasi |
|---|---|---|
| 1.1 | `core.Session` dataclass + `capture()` (merge keputusan/todo/done/notes/goal) | 2 j |
| 1.2 | `gitutil.git_snapshot()` — branch, last commit, changed files, 10 commits, diff stat; aman di folder non-git | 1,5 j |
| 1.3 | `save_session()` / `load_session()` + render `HANDOFF.md` | 1,5 j |
| 1.4 | CLI `capture` (flag: `--goal --from --decision --todo --done --notes --path`) & `show` | 2 j |
| 1.5 | Test: capture dasar, merge (done menghapus todo), folder non-git, round-trip save/load | 2 j |

**Kriteria lulus fase:** di repo contoh, capture 2x dengan data berbeda menghasilkan `HANDOFF.md` gabungan yang benar; test hijau.

**Demo checkpoint 🎬:** rekam terminal singkat capture pertama — bahan konten "building in public" #1.

---

### FASE 2 — Export Multi-Agent (Hari 4–5)

**Tujuan:** fitur pembeda utama — menulis ke file native setiap agent, dengan aman.

| Task | Detail | Estimasi |
|---|---|---|
| 2.1 | `adapters.TARGETS`: claude, codex, agents, gemini, cursor, copilot, windsurf, markdown | 1 j |
| 2.2 | Penulis blok bermarker `agent-handoff:begin/end`: buat / sisipkan / ganti; header khusus Cursor (`.mdc` frontmatter) | 2,5 j |
| 2.3 | CLI `export --to <agent\|all>`; error jelas untuk target tak dikenal | 1 j |
| 2.4 | Test idempotency (export 2x = 1 blok), konten pengguna di luar blok utuh, semua target terbuat | 2 j |

**Kriteria lulus fase:** skenario US-2 lolos penuh; **0 kasus konten pengguna hilang** pada seluruh test.

**⚠️ Gerbang kualitas:** fase ini tidak boleh dilewati dengan test merah. Kepercayaan = nyawa tools yang menulis ke file orang.

---

### FASE 3 — Import, Scan & Polish (Hari 6–7)

| Task | Detail | Estimasi |
|---|---|---|
| 3.1 | `import-log`: parser `Decision:/TODO:/Done:` + padanan Bahasa Indonesia | 1,5 j |
| 3.2 | `--scan-todos` pada capture: kumpulkan `TODO/FIXME` (batasi 50 item, abaikan `.git`, `node_modules`, dll) | 1,5 j |
| 3.3 | Pesan error ramah (belum ada sesi, JSON rusak, bukan direktori valid) + `--help` lengkap | 1,5 j |
| 3.4 | `examples/sample-log.txt` + `demo.sh`; uji manual di Windows/macOS/Linux (atau CI matrix) | 1,5 j |

**Kriteria lulus fase:** alur lengkap PRD §8 berjalan; semua kriteria US-1 s/d US-4 tercentang.

---

### FASE 4 — Test, CI, Dokumentasi (Hari 8–10)

| Task | Detail |
|---|---|
| 4.1 | GitHub Actions: pytest di Ubuntu/macOS/Windows × Python 3.11/3.12/3.13 |
| 4.2 | Coverage core ≥ 80% (`pytest-cov` hanya di CI, bukan dependensi runtime) |
| 4.3 | README final (lihat §5 struktur wajib) + GIF demo ≤ 15 detik (asciinema / rekaman terminal) |
| 4.4 | `CONTRIBUTING.md` (cara menambah adapter = contoh kontribusi pertama), `CHANGELOG.md`, `docs/FORMAT.md` |
| 4.5 | Uji instalasi bersih: `pip install .` di environment baru, jalankan 3 perintah utama |
| 4.6 | **Uji US-5**: export ke 3 agent nyata, verifikasi agent bisa menjawab goal/done/next steps tanpa prompt tambahan |

**Kriteria lulus fase:** seluruh *Definition of Done* PRD §17 yang berkaitan dengan kode & docs tercentang.

---

### FASE 5 — Rilis v0.1 & Launch (Hari 11–14) 🚀

**Rilis (Hari 11):**
- [ ] Bump versi `0.1.0`, tag `v0.1.0`, GitHub Release dengan catatan rilis yang menjual manfaat (bukan daftar commit)
- [ ] Publish ke PyPI: `pip install agenthandoff`
- [ ] Pastikan badge README menyala hijau (CI, PyPI version, license, stars)

**Launch (Hari 12–14, jangan semua di hari yang sama):**

| Hari | Kanal | Materi |
|---|---|---|
| 12 | X/Twitter + komunitas dev Indonesia | Thread "building in public": masalah → demo GIF → link |
| 13 | dev.to / Medium | Artikel tutorial: "How I Switch Between Claude Code and Codex Without Losing Context" |
| 13 | Reddit r/ClaudeAI, r/ChatGPTCoding, r/commandline | Post cerita pengalaman (bukan iklan mentah), balas semua komentar |
| 14 | Hacker News (Show HN) | Judul: `Show HN: AgentHandoff – move context between AI coding agents in 10 seconds` |
| 14 | Product Hunt | Jadwalkan; siapkan banner + GIF |
| Berjalan | Awesome-lists | PR ke awesome-claude-code, awesome-ai-coding, awesome-cli-apps, dll |

**Aturan launch:**
- Balas **setiap** komentar/issue dalam ≤ 24 jam pada 2 minggu pertama.
- Setiap feedback dicatat sebagai issue (publik melihat project hidup).
- Minta star dengan sopan di akhir demo: *"If this saves you briefing time, a ⭐ helps others find it."*

---

### FASE 6 — Iterasi Berbasis Feedback (Minggu 3–8)

Diprioritaskan dari issue nyata pengguna, urutan bawaan:

| Versi | Isi | Pemicu |
|---|---|---|
| v0.2 | `handoff init` wizard + `handoff status` ringkas; perbaikan bug launch | Feedback minggu pertama |
| v0.3 | Parser riwayat sesi Claude Code (`.jsonl`) → capture semi-otomatis | Fitur paling diminta di polling issue |
| v0.4 | Parser Codex/Gemini; opsi `--summarize` (LLM opsional, API key pengguna / Ollama) | Setelah v0.3 tervalidasi |
| v0.5 | Riwayat handoff (`history/`), `handoff log`, deteksi stack project otomatis | Permintaan tim kecil |

**Ritme:** rilis minor tiap 2 minggu; setiap rilis diumumkan singkat (X + GitHub Release). Issue `good first issue` selalu tersedia ≥ 5 buah untuk menyambut kontributor.

**Metrik pantau (mingguan):** star growth, jumlah kontributor baru, issue organik baru, waktu respon issue, unduhan PyPI.

---

### FASE 7 — Standar & Ekosistem (Bulan 3+)

| Inisiatif | Tujuan |
|---|---|
| `docs/FORMAT.md` → spesifikasi terbuka v1 | Tools lain bisa membaca/menulis format AgentHandoff; kita jadi standarnya |
| Plugin adapter eksternal | Agent baru didukung komunitas tanpa menunggu maintainer |
| Ekstensi VS Code (eksperimental) | Menjangkau pengguna non-CLI |
| `handoff watch` & `diff` | Retensi pengguna berat |
| Kolaborasi: blog tamu, podcast dev, integrasi disebut di dokumentasi agent lain | Distribusi jangka panjang |

**Titik keputusan (Bulan 3):** evaluasi metrik PRD §13.2.
- Star & kontribusi tumbuh → lanjut Fase 7 penuh.
- Dipakai tapi tidak tumbuh → perbaiki README/demo/distribusi dulu sebelum tambah fitur.
- Sepi total setelah 2x launch jujur → pivot positioning (mis. fokus "session journal untuk tim") atau arsipkan dengan pelajaran tertulis. **Tidak menambah fitur ke project yang belum tervalidasi.**

---

## 4. Jadwal Ringkas (Kalender)

| Minggu | Fokus | Hasil yang Terlihat Publik |
|---|---|---|
| 1 (Hari 1–7) | Fase 0–3 | Repo publik, postingan building-in-public #1–2, capture/export bekerja |
| 2 (Hari 8–14) | Fase 4–5 | CI hijau, README + GIF, **v0.1.0 rilis**, launch multi-kanal |
| 3–4 | Fase 6 awal | v0.2, issue pengguna pertama dibalas & dirilis |
| 5–8 | Fase 6 | v0.3–v0.4, parser sesi otomatis |
| Bulan 3 | Evaluasi + Fase 7 | Keputusan lanjut/pivot berbasis data |

> Versi fokus-penuh: kompres Minggu 1–2 menjadi 7–10 hari dengan urutan yang sama. Jangan memotong Fase 4 (test) & gerbang kualitas Fase 2.

---

## 5. Struktur Wajib README (Penentu Star)

README adalah halaman penjualan. Urutan baku:

1. **Logo/judul + tagline** + badge (CI, PyPI, license, stars)
2. **Satu kalimat masalah** yang langsung "kena": *"Switching from Claude Code to Codex mid-task? Your new agent knows nothing."*
3. **GIF demo ≤ 15 detik**: capture → export → agent lain melanjutkan
4. **Quick start** — 3 perintah saja:
   ```bash
   pip install agenthandoff
   handoff capture --goal "Add login" --from claude --todo "Add refresh token"
   handoff export --to codex
   ```
5. **Tabel agent yang didukung** (dengan file tujuannya)
6. **Contoh output** `HANDOFF.md`
7. **Kenapa bukan copy-paste / memory bawaan** (tabel pembeda PRD §15, versi ringkas)
8. **Roadmap** publik (mengundang kontribusi)
9. **Contributing** — tonjolkan: "Menambah agent baru = 1 baris di `adapters.py`. Perfect first PR."
10. **License** + ucapan terima kasih + ajakan star

---

## 6. Strategi Pertumbuhan Star (Realistis)

Star tidak datang dari kode saja. Tuas yang direncanakan:

| Tuas | Cara |
|---|---|
| **Nama & tagline yang bisa dicari** | Orang men-search masalahnya; repo description & topics GitHub memakai kata: `ai-coding-agent`, `claude-code`, `codex`, `context`, `handoff`, `developer-tools`, `cli` |
| **Demo visual** | GIF di README + setiap postingan sosial; tanpa GIF, konversi star turun jauh |
| **Good first issues selalu tersedia** | Kontributor pertama hampir selalu kembali memberi star & membagikan |
| **Hadir di tempat masalah dibahas** | Menjawab diskusi "how do you switch agents?" di Reddit/HN/GitHub Discussions dengan solusi tulus (bukan spam) |
| **Awesome-lists & newsletter dev** | PR awesome-list; kirim ke newsletter Python/dev-tools setelah v0.2 |
| **Dogfooding yang terlihat** | Folder `.agent-handoff/` asli di repo ini = bukti hidup setiap pengunjung |
| **Rilis konsisten** | Tiap minor release = momen pengumuman baru = gelombang star baru |
| **README Bahasa Indonesia** (sekunder) | Menangkap komunitas dev ID tanpa mengorbankan audiens global |

**Target bertahap:** 100 ⭐ (2 minggu) → 500 ⭐ (bulan 1) → 2.000 ⭐ (bulan 3). Angka adalah kompas, bukan tujuan — tujuan sebenarnya: pengguna & kontributor nyata (PRD §13.3).

---

## 7. Manajemen Risiko Teknis & Proyek

| Risiko | Prob. | Mitigasi (dari rencana ini) |
|---|---|---|
| Bug menimpa file pengguna | Rendah, dampak fatal | Gerbang Fase 2, test idempotency wajib, blok bermarker, tidak ada operasi hapus |
| Format agent berubah | Sedang | Adapter terisolasi; issue template khusus "agent format changed"; rilis patch cepat |
| Vendor merilis fitur serupa | Sedang | Positioning antar-vendor & local-first (PRD §14); kecepatan komunitas |
| Sepi kontributor | Sedang | `good first issue` terkurasi, CONTRIBUTING sangat ramah, respon ≤ 48 jam |
| Scope membengkak (ingin langsung ada AI-nya) | Tinggi | PRD §3.3 non-tujuan; LLM ditunda ke v0.4 sebagai opsi, core tetap sederhana |
| Burnout maintainer tunggal | Sedang | Ritme rilis 2-mingguan yang ringan; dokumentasi keputusan; rekrut co-maintainer dari kontributor aktif di bulan 2–3 |

---

## 8. Checklist Akhir Sebelum Rilis v0.1

Gabungan gerbang semua fase — rilis hanya bila semua tercentang:

- [ ] F1–F8 (PRD §6.1) selesai, test hijau di 3 OS
- [ ] 0 bug penghapus konten pengguna; export terbukti idempotent
- [ ] Uji US-5 lolos di 3 agent berbeda
- [ ] `pip install agenthandoff` bersih dari PyPI
- [ ] README mengikuti §5 + GIF demo tampil
- [ ] LICENSE, CONTRIBUTING, CHANGELOG, FORMAT.md terbit
- [ ] GitHub Release v0.1.0 + tag
- [ ] Naskah launch 4 kanal siap (docs/LAUNCH.md)
- [ ] ≥ 5 issue `good first issue` terbuka untuk pendatang
- [ ] Repo ini sendiri memakai AgentHandoff (dogfooding terlihat)

---

## 9. Langkah Berikutnya (Eksekusi Langsung)

1. **Selesaikan Fase 1** — `core.py` + `gitutil.py` + CLI `capture`/`show` (fondasi sudah dimulai).
2. **Fase 2** — `adapters.py` + test idempotency (gerbang kualitas).
3. Ikuti fase berurutan; rekam GIF demo di akhir Fase 4.
4. Rilis & launch sesuai Fase 5 — *jangan menunda launch menunggu "sempurna"*.

> Prinsip penutup: **Rilis jelek yang dipakai 10 orang > rilis sempurna yang tidak pernah keluar.**
> Sempurnakan bersama pengguna, di depan publik.

---

*Plan ini ditinjau ulang di setiap akhir fase. Perubahan besar dicatat di sini dengan versi & tanggal baru.*
