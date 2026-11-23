# Lapor Pak — Visitor Management System

Aplikasi web manajemen keluar masuk tamu berbasis **Python Flask**, **SQLite**, dan **Tailwind CSS** dengan nuansa warna biru, hitam, putih, dan ungu.

## Struktur Folder

```text
lapor_pak/
├── app.py              # Routes dan logika aplikasi Flask
├── db.py               # Inisiasi database SQLite dan data awal
├── requirements.txt    # Daftar dependensi Python
├── lapor_pak.db        # File database SQLite (otomatis dibuat saat pertama kali jalan)
└── templates/
    ├── base.html       # Layout dasar & navbar Tailwind CSS
    ├── login.html      # Halaman login Satpam & Direktur
    ├── satpam.html     # Dashboard Satpam (Check-in, Monitoring, Check-out)
    └── direktur.html   # Dashboard Direktur (Approval Masuk/Tolak & Riwayat)
```

## Cara Menjalankan

1. **Install dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

2. **(Opsional) Inisiasi database secara manual:**
   ```bash
   python db.py
   ```
   *(Database `lapor_pak.db` juga otomatis dibuat saat `app.py` dijalankan.)*

3. **Jalankan aplikasi:**
   ```bash
   python app.py
   ```

4. **Buka di browser:**
   Akses `http://127.0.0.1:5000`

## Akun Demo Bawaan

| Role | Username | Password |
| :--- | :--- | :--- |
| **Satpam** | `satpam1` | `satpam123` |
| **Direktur** | `direktur1` | `direktur123` |
