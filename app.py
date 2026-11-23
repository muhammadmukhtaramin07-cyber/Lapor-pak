import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from db import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lapor-pak-dev-secret-key-2026")

# Pastikan database dan tabel sudah siap saat aplikasi dijalankan
init_db()


def login_required(role=None):
    """Decorator untuk memastikan pengguna sudah login dan memiliki role yang sesuai."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("Silakan login terlebih dahulu untuk mengakses halaman ini.", "error")
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                flash("Anda tidak memiliki akses ke halaman tersebut.", "error")
                if session.get("role") == "satpam":
                    return redirect(url_for("satpam_dashboard"))
                return redirect(url_for("direktur_dashboard"))

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def get_visitor_stats(conn):
    """Mengambil ringkasan statistik tamu berdasarkan status."""
    rows = conn.execute(
        "SELECT status, COUNT(*) AS total FROM visitors GROUP BY status"
    ).fetchall()
    counts = {row["status"]: row["total"] for row in rows}
    total_all = sum(counts.values())
    return {
        "total": total_all,
        "menunggu": counts.get("Menunggu", 0),
        "diizinkan": counts.get("Diizinkan", 0),
        "ditolak": counts.get("Ditolak", 0),
        "selesai": counts.get("Selesai", 0),
    }


@app.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "satpam":
            return redirect(url_for("satpam_dashboard"))
        return redirect(url_for("direktur_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username dan password wajib diisi.", "error")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Selamat datang, {user['full_name']}!", "success")
            return redirect(url_for("index"))

        flash("Username atau password salah.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah keluar dari sistem.", "info")
    return redirect(url_for("login"))


# ==========================================
# ROUTES ROLE: SATPAM
# ==========================================
@app.route("/satpam")
@login_required(role="satpam")
def satpam_dashboard():
    status_filter = request.args.get("status", "Semua")
    search_query = request.args.get("q", "").strip()

    conn = get_db_connection()
    stats = get_visitor_stats(conn)

    query = "SELECT * FROM visitors WHERE 1=1"
    params = []

    if status_filter != "Semua":
        query += " AND status = ?"
        params.append(status_filter)

    if search_query:
        query += " AND (name LIKE ? OR company LIKE ? OR visitor_code LIKE ? OR host_name LIKE ?)"
        like_val = f"%{search_query}%"
        params.extend([like_val, like_val, like_val, like_val])

    query += " ORDER BY id DESC"
    visitors = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "satpam.html",
        visitors=visitors,
        stats=stats,
        status_filter=status_filter,
        search_query=search_query,
    )


@app.route("/satpam/checkin", methods=["POST"])
@login_required(role="satpam")
def satpam_checkin():
    name = request.form.get("name", "").strip()
    company = request.form.get("company", "").strip()
    phone = request.form.get("phone", "").strip()
    purpose = request.form.get("purpose", "").strip()
    host_name = request.form.get("host_name", "").strip()
    notes = request.form.get("notes", "").strip()

    if not name or not purpose:
        flash("Nama tamu dan keperluan kunjungan wajib diisi.", "error")
        return redirect(url_for("satpam_dashboard"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()

    next_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM visitors"
    ).fetchone()["next_id"]
    visitor_code = f"LP-{next_id:04d}"

    conn.execute(
        """
        INSERT INTO visitors (
            visitor_code, name, company, phone, purpose, host_name, notes,
            status, check_in_time, recorded_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Menunggu', ?, ?)
        """,
        (
            visitor_code,
            name,
            company or "-",
            phone or "-",
            purpose,
            host_name or "-",
            notes or "-",
            now_str,
            session.get("full_name", "Satpam"),
        ),
    )
    conn.commit()
    conn.close()

    flash(
        f"Tamu {name} ({visitor_code}) berhasil dicatat. Menunggu persetujuan Direktur.",
        "success",
    )
    return redirect(url_for("satpam_dashboard"))


@app.route("/satpam/checkout/<int:visitor_id>", methods=["POST"])
@login_required(role="satpam")
def satpam_checkout(visitor_id):
    conn = get_db_connection()
    visitor = conn.execute(
        "SELECT * FROM visitors WHERE id = ?", (visitor_id,)
    ).fetchone()

    if not visitor:
        conn.close()
        flash("Data tamu tidak ditemukan.", "error")
        return redirect(url_for("satpam_dashboard"))

    if visitor["status"] != "Diizinkan":
        conn.close()
        flash(
            "Check-out hanya dapat dilakukan untuk tamu yang berstatus Diizinkan.",
            "error",
        )
        return redirect(url_for("satpam_dashboard"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        UPDATE visitors
        SET status = 'Selesai', check_out_time = ?
        WHERE id = ?
        """,
        (now_str, visitor_id),
    )
    conn.commit()
    conn.close()

    flash(
        f"Check-out tamu {visitor['name']} ({visitor['visitor_code']}) berhasil dicatat pada {now_str}.",
        "success",
    )
    return redirect(url_for("satpam_dashboard"))


# ==========================================
# ROUTES ROLE: DIREKTUR
# ==========================================
@app.route("/direktur")
@login_required(role="direktur")
def direktur_dashboard():
    status_filter = request.args.get("status", "Semua")
    search_query = request.args.get("q", "").strip()

    conn = get_db_connection()
    stats = get_visitor_stats(conn)

    # Daftar tamu yang sedang menunggu keputusan Direktur
    waiting_visitors = conn.execute(
        "SELECT * FROM visitors WHERE status = 'Menunggu' ORDER BY id ASC"
    ).fetchall()

    # Riwayat & monitoring seluruh tamu
    query = "SELECT * FROM visitors WHERE 1=1"
    params = []

    if status_filter != "Semua":
        query += " AND status = ?"
        params.append(status_filter)

    if search_query:
        query += " AND (name LIKE ? OR company LIKE ? OR visitor_code LIKE ? OR host_name LIKE ?)"
        like_val = f"%{search_query}%"
        params.extend([like_val, like_val, like_val, like_val])

    query += " ORDER BY id DESC"
    all_visitors = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "direktur.html",
        waiting_visitors=waiting_visitors,
        all_visitors=all_visitors,
        stats=stats,
        status_filter=status_filter,
        search_query=search_query,
    )


@app.route("/direktur/decide/<int:visitor_id>", methods=["POST"])
@login_required(role="direktur")
def direktur_decide(visitor_id):
    decision = request.form.get("decision", "").strip()
    rejection_reason = request.form.get("rejection_reason", "").strip()

    if decision not in ("approve", "reject"):
        flash("Keputusan tidak valid.", "error")
        return redirect(url_for("direktur_dashboard"))

    conn = get_db_connection()
    visitor = conn.execute(
        "SELECT * FROM visitors WHERE id = ?", (visitor_id,)
    ).fetchone()

    if not visitor:
        conn.close()
        flash("Data tamu tidak ditemukan.", "error")
        return redirect(url_for("direktur_dashboard"))

    if visitor["status"] != "Menunggu":
        conn.close()
        flash("Keputusan sudah diberikan sebelumnya untuk tamu ini.", "error")
        return redirect(url_for("direktur_dashboard"))

    new_status = "Diizinkan" if decision == "approve" else "Ditolak"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    director_name = session.get("full_name", "Direktur")

    conn.execute(
        """
        UPDATE visitors
        SET status = ?,
            decision_time = ?,
            decision_by = ?,
            rejection_reason = ?
        WHERE id = ?
        """,
        (
            new_status,
            now_str,
            director_name,
            rejection_reason if decision == "reject" and rejection_reason else None,
            visitor_id,
        ),
    )
    conn.commit()
    conn.close()

    action_label = "diizinkan masuk" if decision == "approve" else "ditolak"
    flash(
        f"Tamu {visitor['name']} ({visitor['visitor_code']}) telah {action_label}.",
        "success",
    )
    return redirect(url_for("direktur_dashboard"))


# ==========================================
# API STATS (OPSIONAL UNTUK MONITORING)
# ==========================================
@app.route("/api/visitors/stats")
@login_required()
def api_visitor_stats():
    conn = get_db_connection()
    stats = get_visitor_stats(conn)
    conn.close()
    return jsonify(stats)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
