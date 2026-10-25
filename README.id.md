# AgentHandoff 🇮🇩

**Tidak kehilangan konteks saat berpindah AI coding agent.**

[English](README.md) · **[Bahasa Indonesia]**

> Pindah AI agent dalam 10 detik. Tanpa briefing ulang.

Claude Code pagi, Codex siang, Cursor malam? Setiap perpindahan biasanya bikin
kamu menjelaskan ulang tujuan project, apa yang sudah selesai, dan keputusan
teknis yang sudah diambil — 5 sampai 30 menit terbuang.

AgentHandoff menyimpan konteks sesi sekali, lalu menuliskannya ke file yang
dibaca agent berikutnya saat startup. Dua perintah, ±10 detik, 100% lokal.

```bash
pip install agenthandoff

handoff capture --goal "Menyelesaikan fitur login" --from claude \
    --decision "Pakai JWT :: stateless, cocok untuk API" \
    --todo "Tambahkan refresh token" \
    --done "Endpoint /login selesai"

handoff export --to codex     # menulis AGENTS.md
```

Buka Codex di folder yang sama → ia langsung tahu tujuan, yang sudah selesai,
dan langkah berikutnya. Tanpa prompt tambahan.

## Kenapa perlu

- **Briefing ulang mahal.** 5–30 menit hilang di setiap perpindahan agent.
- **Keputusan hilang.** Agent baru mengusulkan pendekatan yang sudah kamu tolak,
  karena tidak tahu riwayatnya.
- **Format tidak standar.** `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
  `.cursor/rules/`, `.github/copilot-instructions.md` — semuanya beda.
  AgentHandoff: satu sumber (`session.json`) → semua format.

## File yang ditulis

| Target (`--to`) | File | Dibaca oleh |
| --- | --- | --- |
| `claude` | `CLAUDE.md` | Claude Code |
| `codex` / `agents` | `AGENTS.md` | Codex, OpenCode, agent standar AGENTS.md |
| `gemini` | `GEMINI.md` | Gemini CLI |
| `cursor` | `.cursor/rules/agent-handoff.mdc` | Cursor |
| `copilot` | `.github/copilot-instructions.md` | GitHub Copilot |
| `windsurf` | `.windsurf/rules/agent-handoff.md` | Windsurf |
| `markdown` | `.agent-handoff/HANDOFF.md` | Semua agent / manusia |
| `all` | semuanya | — |

## Perintah

| Perintah | Fungsi |
| --- | --- |
| `handoff capture` | Rekam/perbarui sesi (goal, keputusan, todo, done, catatan) + snapshot git otomatis. Capture berulang **digabung**, bukan ditimpa. |
| `handoff export --to <agent>` | Tulis blok konteks ke file native agent (atau `--to all`). |
| `handoff show` | Tampilkan handoff saat ini (`--json` untuk data mentah). |
| `handoff status` | Ringkasan lima baris: goal, progress, todo tersisa, agent terakhir, terakhir diupdate. |
| `handoff import-log <file>` | Ekstrak baris `Keputusan:` / `Selanjutnya:` / `Selesai:` (juga versi Inggris `Decision:` / `TODO:` / `Done:`) dari log/chat. |
| `handoff scan-todos` | Intip komentar `TODO`/`FIXME` yang akan diambil `capture --scan-todos`. |
| `handoff init` | Siapkan `.agent-handoff/` (+ opsi `--gitignore`). |

Semua perintah mendukung `--path DIR` dan `--quiet`.

## Aman, tidak merusak

- Blok hasil export ditandai `<!-- agent-handoff:begin/end -->`.
- Export ulang **mengganti** blok lama: idempotent, tidak pernah dobel.
- Tulisanmu di luar marker **tidak pernah** diubah atau dihapus.
- Penulisan file atomik; file CRLF dan path non-ASCII tetap aman.
- Marker setengah jadi → export berhenti dengan pesan jelas, bukan menebak.

## Non-tujuan

Bukan AI agent, bukan layanan cloud/SaaS, bukan pengganti git, bukan project
management tool. Tidak ada telemetri, tidak ada network call di core.

## Lisensi

[MIT](LICENSE). Kontribusi sangat terbuka — **menambah agent baru cukup satu
baris** di `src/agenthandoff/adapters.py`. Lihat [CONTRIBUTING.md](CONTRIBUTING.md).

---

**Kalau ini menghemat satu kali briefing ulang, satu ⭐ membantu developer lain menemukannya.**
