import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lapor_pak.db")


def get_db_connection():
    """Membuka koneksi ke database SQLite dengan row_factory dict-like."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Menginisialisasi tabel database dan mengisi data awal jika masih kosong."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabel pengguna (Satpam & Direktur)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('satpam', 'direktur')),
            created_at TEXT NOT NULL
        )
        """
    )

    # Tabel data kunjungan tamu
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            purpose TEXT NOT NULL,
            host_name TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Menunggu'
                CHECK(status IN ('Menunggu', 'Diizinkan', 'Ditolak', 'Selesai')),
            check_in_time TEXT NOT NULL,
            decision_time TEXT,
            decision_by TEXT,
            rejection_reason TEXT,
            check_out_time TEXT,
            recorded_by TEXT NOT NULL
        )
        """
    )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Seed akun default jika tabel users masih kosong
    user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        default_users = [
            (
                "satpam1",
                generate_password_hash("satpam123"),
                "Budi Santoso",
                "satpam",
                now_str,
            ),
            (
                "direktur1",
                generate_password_hash("direktur123"),
                "Hendra Wijaya",
                "direktur",
                now_str,
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO users (username, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            default_users,
        )

    # Seed contoh data tamu jika tabel visitors masih kosong
    visitor_count = cursor.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    if visitor_count == 0:
        sample_visitors = [
            (
                "LP-0001",
                "Andi Pratama",
                "PT Nusantara Digital",
                "081234567890",
                "Presentasi kerja sama sistem IT",
                "Divisi Operasional",
                "Membawa 1 laptop dan kartu identitas",
                "Menunggu",
                now_str,
                None,
                None,
                None,
                None,
                "Budi Santoso",
            ),
            (
                "LP-0002",
                "Siti Rahmawati",
                "CV Maju Bersama",
                "081987654321",
                "Pengiriman dokumen kontrak vendor",
                "Bagian Keuangan",
                "Sudah konfirmasi via telepon",
                "Diizinkan",
                now_str,
                now_str,
                "Hendra Wijaya",
                None,
                None,
                "Budi Santoso",
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO visitors (
                visitor_code, name, company, phone, purpose, host_name, notes,
                status, check_in_time, decision_time, decision_by,
                rejection_reason, check_out_time, recorded_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sample_visitors,
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database berhasil diinisialisasi di: {DB_PATH}")
