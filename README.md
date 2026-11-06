# AMS Planner

Penyusun urutan cetak yang sadar filamen, untuk printer dengan AMS 4 slot (misalnya Bambu Lab A1 mini + AMS lite).
Program ini membaca warna dan jenis filamen langsung dari file G-code/3MF, menyimpan riwayat filamen untuk dipilih cepat,
lalu menghitung urutan cetak yang meminimalkan waktu ganti spool dan jumlah kunjungan operator.

## Kebutuhan (Mac)

- macOS dengan Python 3.9 atau lebih baru. Python bawaan Command Line Tools sudah cukup. Cek dengan `python3 --version`.
  Kalau belum ada, jalankan `xcode-select --install`.
- NumPy bersifat opsional, hanya untuk pemuatan spool optimal-eksak: `pip3 install numpy`.

## Menjalankan

Ekstrak folder ini, buka Terminal di dalam folder `amsplanner`, lalu:

```bash
# Antarmuka web lokal (browser terbuka otomatis di http://127.0.0.1:8765)
python3 -m amsplanner serve

# Atau lewat command line
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

Riwayat filamen disimpan di `~/Library/Application Support/AMSPlanner/filament_history.json`.

## Waktu ganti spool

Nilai waktu ganti per kunjungan (hasil pengukuran pada A1 mini + AMS lite) ada di `amsplanner/model.py`:
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
