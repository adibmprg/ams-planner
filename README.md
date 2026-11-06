# AMS Planner

Penyusun urutan cetak yang sadar filamen, untuk printer dengan AMS 4 slot (misalnya Bambu Lab A1 mini + AMS lite).
Program ini membaca warna dan jenis filamen langsung dari file G-code/3MF, menyimpan riwayat filamen untuk dipilih cepat,
lalu menghitung urutan cetak yang meminimalkan waktu ganti spool dan jumlah kunjungan operator.

## Cara tercepat: langsung buka HTML (tanpa instalasi)

Klik dua kali **`AMSPlanner.html`** (atau unduh file itu saja dari GitHub, lalu buka di Safari/Chrome/Firefox).
Semua proses berjalan di browser: membaca G-code/3MF, riwayat filamen (tersimpan di browser, bisa diekspor/impor sebagai JSON),
dan perencanaan. Tidak perlu Python atau internet.

Di bagian **4. Plan**, pilihan bawaan **Auto** menjalankan semua algoritma (FIFO, greedy, ILS, GA, dan enumerasi eksak
bila jumlah job ≤ 8), menampilkan tabel perbandingannya, lalu memakai urutan terbaik. Algoritma lain tetap bisa dicoba:
klik “view plan” pada baris tabel, atau pilih satu algoritma di menu Method. Tombol **Load example batch** memuat
12 job contoh dari paper (FIFO 425 s → 212,5 s).

## Versi Python (opsional, untuk command line dan reproduksi paper)

- Python 3.9 atau lebih baru (Python bawaan Command Line Tools di Mac sudah cukup; `xcode-select --install` bila belum ada).
- NumPy opsional, hanya untuk pemuatan spool optimal-eksak: `pip3 install numpy`.

```bash
# Membuka AMSPlanner.html lewat server lokal (http://127.0.0.1:8765)
python3 -m amsplanner serve

# Command line; --method auto (bawaan) membandingkan semua algoritma
python3 -m amsplanner plan ~/Downloads/*.gcode.3mf --ams "PLA:#000000,PLA:#FFFFFF,PLA:#FF0000,PLA:#808080"
```

## Input yang didukung

| File | Yang terbaca otomatis |
|---|---|
| `.gcode` | warna, jenis, slot yang dipakai (dari M620/T), estimasi waktu |
| `.gcode.3mf` (sudah di-slice) | per plate: warna, jenis, estimasi waktu (`slice_info.config`) |
| `.3mf` proyek Bambu (belum di-slice) | warna dan jenis (`project_settings.config`), filamen per part (`model_settings.config`) dan warna hasil painting (`paint_color`) |
| `.3mf` dari software CAD | warna yang dipakai model (colour group 3MF); jenis filamen dipilih dari riwayat, atau warna dipetakan ke spool terdekat di riwayat |
| Lainnya / tidak terbaca | diisi manual, cukup klik dari riwayat filamen |

Riwayat filamen: versi HTML menyimpannya di browser (localStorage, bisa ekspor/impor JSON); versi command line di `~/Library/Application Support/AMSPlanner/filament_history.json`.

## Waktu ganti spool

Nilai waktu ganti per kunjungan (hasil pengukuran pada A1 mini + AMS lite) ada di `amsplanner/model.py` dan di bagian atas skrip `AMSPlanner.html` (`SWITCH_TIME_S`):
1 spool = 46 s, 2 = 74,5 s, 3 = 103 s, 4 = 134,7 s (rata-rata 10 percobaan). Ubah nilainya kalau printer atau operator Anda berbeda.

## Mereproduksi hasil paper

```bash
python3 experiments/run_experiments.py   # sekitar 4–5 menit di 2 core
python3 experiments/analyze.py
python3 experiments/case_study.py
python3 experiments/figures.py && python3 experiments/fig_arch.py
```

Hasilnya tersimpan di `results/` dan gambarnya di `figs/`. Folder `samples/` berisi file uji yang meniru struktur file
Bambu Studio. Sebelum submit, uji juga dengan file asli Anda.
