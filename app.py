from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any, Iterator

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, send_from_directory, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

DATABASE = "steps_app.db"
DAILY_STEP_LIMIT = 11000
DEFAULT_USERS = ("Weronika", "Mich")

WEEKDAYS_PL = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
]


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                step_count INTEGER NOT NULL,
                log_date DATE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, log_date)
            )
            """
        )

        placeholders = ", ".join("?" for _ in DEFAULT_USERS)
        cursor.execute(f"DELETE FROM users WHERE name NOT IN ({placeholders})", DEFAULT_USERS)

        cursor.execute("SELECT name FROM users")
        existing = {row[0] for row in cursor.fetchall()}
        for user in DEFAULT_USERS:
            if user not in existing:
                cursor.execute("INSERT INTO users (name) VALUES (?)", (user,))

        conn.commit()


init_db()


def get_users(cursor: sqlite3.Cursor) -> tuple[dict[int, str], dict[str, int]]:
    cursor.execute("SELECT id, name FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    users = {row["id"]: row["name"] for row in rows}
    users_inv = {name: user_id for user_id, name in users.items()}
    return users, users_inv


def clamp_steps(step_count: int) -> int:
    return max(0, min(step_count, DAILY_STEP_LIMIT))


def compute_winner(a: int, b: int, name_a: str, name_b: str) -> tuple[str | None, int]:
    if a > b:
        return name_a, a - b
    if b > a:
        return name_b, b - a
    return None, 0


def upsert_daily_steps(cursor: sqlite3.Cursor, user_id: int, log_date: str, step_count: int) -> bool:
    cursor.execute(
        "SELECT id FROM daily_steps WHERE user_id = ? AND log_date = ?",
        (user_id, log_date),
    )
    exists = cursor.fetchone() is not None
    if exists:
        cursor.execute(
            "UPDATE daily_steps SET step_count = ? WHERE user_id = ? AND log_date = ?",
            (step_count, user_id, log_date),
        )
    else:
        cursor.execute(
            "INSERT INTO daily_steps (user_id, step_count, log_date) VALUES (?, ?, ?)",
            (user_id, step_count, log_date),
        )
    return exists


def get_default_date(cursor: sqlite3.Cursor, users: dict[int, str]) -> date:
    today = date.today()
    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM daily_steps WHERE log_date = ?",
        (today.isoformat(),),
    )
    users_logged_today = cursor.fetchone()[0]
    if users_logged_today == len(users):
        return today + timedelta(days=1)
    return today


def day_of_week_filter(value: str | date) -> str:
    if isinstance(value, str):
        try:
            dt_object = date.fromisoformat(value)
        except ValueError:
            return ""
    elif isinstance(value, date):
        dt_object = value
    else:
        return ""
    return WEEKDAYS_PL[dt_object.weekday()]


def get_last_day_summary(cursor: sqlite3.Cursor, users: dict[int, str]) -> dict[str, Any] | None:
    cursor.execute("SELECT MAX(log_date) FROM daily_steps")
    row = cursor.fetchone()
    if not row or not row[0]:
        return None

    last_date = date.fromisoformat(row[0])
    cursor.execute(
        """
        SELECT u.name, ds.step_count
        FROM daily_steps ds
        JOIN users u ON ds.user_id = u.id
        WHERE ds.log_date = ?
        ORDER BY ds.step_count DESC
        """,
        (last_date.isoformat(),),
    )
    entries = cursor.fetchall()
    if len(entries) != len(users):
        return None

    winner, diff = compute_winner(
        entries[0]["step_count"],
        entries[1]["step_count"],
        entries[0]["name"],
        entries[1]["name"],
    )

    return {
        "date": last_date,
        "date_weekday": day_of_week_filter(last_date),
        "entries": [{"name": e["name"], "step_count": e["step_count"]} for e in entries],
        "winner": winner,
        "diff": diff,
    }


def get_full_history(cursor: sqlite3.Cursor, users_inv: dict[str, int]) -> list[dict[str, Any]]:
    cursor.execute("SELECT DISTINCT log_date FROM daily_steps ORDER BY log_date DESC")
    dates = [r["log_date"] for r in cursor.fetchall()]
    history: list[dict[str, Any]] = []

    weronika_id = users_inv.get("Weronika")
    mich_id = users_inv.get("Mich")

    for d in dates:
        cursor.execute(
            "SELECT user_id, step_count FROM daily_steps WHERE log_date = ?",
            (d,),
        )
        rows = cursor.fetchall()

        weronika_steps = 0
        mich_steps = 0
        for row in rows:
            if row["user_id"] == weronika_id:
                weronika_steps = row["step_count"]
            elif row["user_id"] == mich_id:
                mich_steps = row["step_count"]

        winner_day, _ = compute_winner(weronika_steps, mich_steps, "Weronika", "Mich")
        history.append(
            {
                "date": date.fromisoformat(d),
                "date_weekday": day_of_week_filter(d),
                "Weronika": weronika_steps,
                "Mich": mich_steps,
                "winner_day": winner_day,
            }
        )

    return history


def get_comparison_data(cursor: sqlite3.Cursor, users: dict[int, str]) -> list[dict[str, Any]]:
    comparison: list[dict[str, Any]] = []
    for user_id, user_name in users.items():
        cursor.execute(
            """
            SELECT step_count, log_date
            FROM daily_steps
            WHERE user_id = ?
            ORDER BY log_date DESC
            LIMIT 1
            """,
            (user_id,),
        )
        latest = cursor.fetchone()

        current_steps = latest["step_count"] if latest else 0
        percentage = (current_steps / DAILY_STEP_LIMIT) * 100 if DAILY_STEP_LIMIT > 0 else 0
        comparison.append(
            {
                "name": user_name,
                "user_id": user_id,
                "latest_steps": current_steps,
                "latest_date": latest["log_date"] if latest else "Brak wpisu",
                "percentage": round(percentage, 1),
                "progress_color": "green" if percentage >= 100 else ("orange" if percentage >= 50 else "red"),
            }
        )
    return comparison


def get_global_summary(cursor: sqlite3.Cursor, users: dict[int, str], users_inv: dict[str, int]) -> tuple[dict[int, int], str | None, int]:
    global_total_steps: dict[int, int] = {}
    for user_id in users:
        cursor.execute("SELECT SUM(step_count) FROM daily_steps WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        global_total_steps[user_id] = total or 0

    total_weronika = global_total_steps.get(users_inv.get("Weronika", -1), 0)
    total_mich = global_total_steps.get(users_inv.get("Mich", -1), 0)
    global_winner, global_diff = compute_winner(total_weronika, total_mich, "Weronika", "Mich")
    return global_total_steps, global_winner, global_diff


def get_current_form_data(cursor: sqlite3.Cursor, users: dict[int, str], default_date: date) -> dict[int, int | str]:
    current_form_data: dict[int, int | str] = {}
    for user_id in users:
        cursor.execute(
            "SELECT step_count FROM daily_steps WHERE user_id = ? AND log_date = ?",
            (user_id, default_date.isoformat()),
        )
        entry = cursor.fetchone()
        current_form_data[user_id] = entry["step_count"] if entry else ""
    return current_form_data


def get_dashboard_data(cursor: sqlite3.Cursor) -> dict[str, Any]:
    users, users_inv = get_users(cursor)
    default_date = get_default_date(cursor, users)

    last_day_summary = get_last_day_summary(cursor, users)
    full_history = get_full_history(cursor, users_inv)
    comparison_data = get_comparison_data(cursor, users)
    global_total_steps, global_winner, global_diff = get_global_summary(cursor, users, users_inv)
    current_form_data = get_current_form_data(cursor, users, default_date)

    return {
        "users": users,
        "users_inv": users_inv,
        "default_date": default_date,
        "daily_limit": DAILY_STEP_LIMIT,
        "last_day_summary": last_day_summary,
        "full_history": full_history,
        "comparison_data": comparison_data,
        "global_total_steps": global_total_steps,
        "global_winner": global_winner,
        "global_diff": global_diff,
        "current_form_data": current_form_data,
    }


def make_serializable(data: Any) -> Any:
    if isinstance(data, dict):
        return {str(k): make_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [make_serializable(v) for v in data]
    if isinstance(data, (date, datetime)):
        return data.isoformat()
    return data


def save_steps_from_form(cursor: sqlite3.Cursor, form_data: dict[str, str]) -> bool:
    users, _ = get_users(cursor)

    log_date_str = form_data.get("log_date", "")
    try:
        log_date = date.fromisoformat(log_date_str)
    except ValueError:
        flash("Data jest niepoprawna.", "error")
        return False

    entries_processed = 0
    for user_id, user_name in users.items():
        key = f"step_count_{user_id}"
        value = form_data.get(key, "").strip()
        if not value:
            continue

        try:
            raw_steps = int(value)
        except ValueError:
            flash(f"Liczba kroków dla {user_name} musi być liczbą całkowitą.", "error")
            continue

        saved_steps = clamp_steps(raw_steps)
        if raw_steps > DAILY_STEP_LIMIT:
            flash(
                f"Wprowadzono więcej niż {DAILY_STEP_LIMIT} kroków dla {user_name}. Zapisano {DAILY_STEP_LIMIT}.",
                "warning",
            )
        elif raw_steps < 0:
            flash(f"Wprowadzono ujemną liczbę kroków dla {user_name}. Zapisano 0.", "warning")

        existed = upsert_daily_steps(cursor, user_id, log_date.isoformat(), saved_steps)
        action = "Zaktualizowano" if existed else "Dodano"
        flash(f"{action} kroki dla {user_name} na dzień {log_date.strftime('%d.%m.%Y')}.", "success")
        entries_processed += 1

    if entries_processed == 0:
        flash("Nie wprowadzono żadnych kroków. Proszę wypełnić przynajmniej jedno pole.", "error")
        return False

    return True


def parse_sync_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("unsynced_entries") or payload.get("entries") or []
    return []


@app.route("/manifest.json")
def manifest() -> Any:
    return send_from_directory("static", "manifest.json")


@app.route("/sw.js")
def service_worker() -> Any:
    return send_from_directory("static", "sw.js")


@app.route("/api/ping")
def ping() -> Any:
    return jsonify({"status": "ok"})


@app.route("/", methods=("GET", "POST"))
def index() -> Any:
    error = None
    with db_connection() as conn:
        cursor = conn.cursor()

        if request.method == "POST":
            try:
                should_commit = save_steps_from_form(cursor, request.form)
                if should_commit:
                    conn.commit()
                    return redirect(url_for("index"))
            except sqlite3.Error as exc:
                error = f"Błąd bazy danych: {exc}"
                flash(error, "error")

        data = get_dashboard_data(cursor)
        return render_template(
            "index.html",
            users=data["users"],
            users_inv=data["users_inv"],
            default_date=data["default_date"].isoformat(),
            daily_limit=data["daily_limit"],
            last_day_summary=data["last_day_summary"],
            full_history=data["full_history"],
            comparison_data=data["comparison_data"],
            global_total_steps=data["global_total_steps"],
            global_winner=data["global_winner"],
            global_diff=data["global_diff"],
            current_form_data=data["current_form_data"],
            error=error,
        )


@app.route("/api/data", methods=["GET"])
def api_data() -> Any:
    with db_connection() as conn:
        data = get_dashboard_data(conn.cursor())
    return jsonify(make_serializable(data))


@app.route("/api/sync", methods=["POST"])
def api_sync() -> Any:
    entries = parse_sync_entries(request.get_json(silent=True) or {})

    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            for entry in entries:
                try:
                    user_id = int(entry.get("user_id"))
                    log_date = date.fromisoformat(entry.get("log_date", "")).isoformat()
                    step_count = clamp_steps(int(entry.get("step_count")))
                except (TypeError, ValueError):
                    continue

                upsert_daily_steps(cursor, user_id, log_date, step_count)

            conn.commit()
            data = get_dashboard_data(cursor)
            return jsonify(make_serializable(data))
        except sqlite3.Error as exc:
            return jsonify({"error": str(exc)}), 400


@app.template_filter("day_of_week")
def day_of_week_jinja_filter(value: str | date) -> str:
    return day_of_week_filter(value)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
