from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from datetime import datetime, date, timedelta
import sqlite3
import os

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev')

# Expose PWA files at root (required paths)
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

# Health check for PWA (detect home network availability)
@app.route('/api/ping')
def ping():
    return jsonify({"status": "ok"})

# --- Konfiguracja bazy danych ---
DATABASE = 'steps_app.db'
DAILY_STEP_LIMIT = 11000  # Nowa stała dla limitu kroków

# Definicja użytkowników
def get_users(cursor):
    cursor.execute("SELECT id, name FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    users = {row['id']: row['name'] for row in rows}
    users_inv = {v: k for k, v in users.items()}
    return users, users_inv


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Tabela użytkowników - nie jest potrzebna, jeśli są na sztywno, ale lepiej mieć
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        # Wstawienie domyślnych użytkowników, jeśli ich nie ma
        # seed default users only if empty
        # Force exactly two users: Weronika and Mich (no others allowed)
        cursor.execute("DELETE FROM users WHERE name NOT IN ('Weronika', 'Mich')")

        cursor.execute("SELECT name FROM users")
        existing = {row[0] for row in cursor.fetchall()}

        if 'Weronika' not in existing:
            cursor.execute("INSERT INTO users (name) VALUES ('Weronika')")
        if 'Mich' not in existing:
            cursor.execute("INSERT INTO users (name) VALUES ('Mich')")

        # Tabela kroków - zmieniamy, by używać user_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                step_count INTEGER NOT NULL,
                log_date DATE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, log_date)
            )
        ''')
        db.commit()
        db.close()


# --- Routery Flask ---

def compute_winner(a, b, name_a, name_b):
    if a > b:
        return name_a, a - b
    if b > a:
        return name_b, b - a
    return None, 0


def get_default_date(cursor, users):
    today = date.today()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM daily_steps WHERE log_date = ?", (today.isoformat(),))
    users_logged_today = cursor.fetchone()[0]
    return today + timedelta(days=1) if users_logged_today == len(users) else today


def get_last_day_summary(cursor, users):
    cursor.execute("SELECT MAX(log_date) FROM daily_steps")
    row = cursor.fetchone()
    if not row or not row[0]:
        return None

    last_date = date.fromisoformat(row[0])
    cursor.execute("""
        SELECT u.name, ds.step_count
        FROM daily_steps ds
        JOIN users u ON ds.user_id = u.id
        WHERE ds.log_date = ?
        ORDER BY ds.step_count DESC
    """, (last_date.isoformat(),))

    entries = cursor.fetchall()
    if len(entries) != len(users):
        return None

    winner, diff = compute_winner(
        entries[0]['step_count'],
        entries[1]['step_count'],
        entries[0]['name'],
        entries[1]['name']
    )

    return {
        'date': last_date,
        'date_weekday': last_date.strftime('%A'),
        'entries': [{'name': e['name'], 'step_count': e['step_count']} for e in entries],
        'winner': winner,
        'diff': diff
    }


def get_full_history(cursor, users_inv):
    cursor.execute("SELECT DISTINCT log_date FROM daily_steps ORDER BY log_date DESC")
    dates = [r['log_date'] for r in cursor.fetchall()]
    result = []

    for d in dates:
        cursor.execute("""
            SELECT user_id, step_count
            FROM daily_steps
            WHERE log_date = ?
        """, (d,))

        rows = cursor.fetchall()
        data = {'date': date.fromisoformat(d), 'date_weekday': day_of_week_filter(d)}

        w = 0
        m = 0
        for r in rows:
            if r['user_id'] == users_inv.get('Weronika'):
                w = r['step_count']
            elif r['user_id'] == users_inv.get('Mich'):
                m = r['step_count']

        winner, _ = compute_winner(w, m, 'Weronika', 'Mich')
        data.update({'Weronika': w, 'Mich': m, 'winner_day': winner})
        result.append(data)

    return result


def get_dashboard_data(cursor):
    USERS, USERS_INV = get_users(cursor)
    today = date.today()

    default_date = get_default_date(cursor, USERS)
    last_day_summary = get_last_day_summary(cursor, USERS)
    full_history = get_full_history(cursor, USERS_INV)

    # --- Logika ustawiania domyślnej daty dla formularza ---
    cursor.execute("""
                SELECT COUNT(DISTINCT user_id) 
                FROM daily_steps 
                WHERE log_date = ?
            """, (today.isoformat(),))
    users_logged_today = cursor.fetchone()[0]

    if users_logged_today == len(USERS):  # Jeśli obaj użytkownicy wpisali kroki na dzisiaj
        default_date = today + timedelta(days=1)
    else:
        default_date = today

    # Pobierz dane dla formularza dla aktualnie sugerowanej daty
    current_form_data = {}
    for user_id, user_name in USERS.items():
        cursor.execute("SELECT step_count FROM daily_steps WHERE user_id = ? AND log_date = ?",
                       (user_id, default_date.isoformat()))
        entry = cursor.fetchone()
        current_form_data[user_id] = entry['step_count'] if entry else ''

    # 1. Podsumowanie ostatniego dnia z wpisami
    last_logged_date = None
    cursor.execute("SELECT MAX(log_date) FROM daily_steps")
    max_date_row = cursor.fetchone()
    if max_date_row and max_date_row[0]:
        last_logged_date = date.fromisoformat(max_date_row[0])

    last_day_summary = None
    if last_logged_date:
        cursor.execute("""
                    SELECT u.name, ds.step_count 
                    FROM daily_steps ds 
                    JOIN users u ON ds.user_id = u.id 
                    WHERE ds.log_date = ?
                    ORDER BY ds.step_count DESC
                """, (last_logged_date.isoformat(),))
        last_day_entries = cursor.fetchall()

        if len(last_day_entries) == len(USERS):
            winner_name, diff = compute_winner(
                last_day_entries[0]['step_count'],
                last_day_entries[1]['step_count'],
                last_day_entries[0]['name'],
                last_day_entries[1]['name']
            )

            last_day_summary = {
                'date': last_logged_date,
                'date_weekday': last_logged_date.strftime('%A'),
                'entries': [{'name': row['name'], 'step_count': row['step_count']} for row in last_day_entries],
                'winner': winner_name,
                'diff': diff
            }

    # 2. Cała historia
    cursor.execute("SELECT DISTINCT log_date FROM daily_steps ORDER BY log_date DESC")
    unique_dates = [row['log_date'] for row in cursor.fetchall()]

    formatted_full_history = []
    for date_str in unique_dates:
        cursor.execute("""
            SELECT u.name, ds.step_count, ds.user_id
            FROM daily_steps ds 
            JOIN users u ON ds.user_id = u.id 
            WHERE ds.log_date = ?
            ORDER BY u.id ASC
        """, (date_str,))
        daily_entries = cursor.fetchall()

        row_data = {
            'date': date.fromisoformat(date_str),
            'date_weekday': day_of_week_filter(date_str)
        }

        weronika_steps = 0
        mich_steps = 0

        for entry in daily_entries:
            if entry['user_id'] == USERS_INV['Weronika']:
                weronika_steps = entry['step_count']
            elif entry['user_id'] == USERS_INV['Mich']:
                mich_steps = entry['step_count']

        row_data['Weronika'] = weronika_steps
        row_data['Mich'] = mich_steps

        winner_day, _ = compute_winner(weronika_steps, mich_steps, 'Weronika', 'Mich')
        row_data['winner_day'] = winner_day

        formatted_full_history.append(row_data)

    # 3. Podsumowanie dla tabelki porównawczej
    comparison_data = []
    for user_id, user_name in USERS.items():
        cursor.execute("""
                    SELECT ds.step_count, ds.log_date
                    FROM daily_steps ds
                    WHERE ds.user_id = ?
                    ORDER BY ds.log_date DESC
                    LIMIT 1
                """, (user_id,))
        latest_entry = cursor.fetchone()

        current_steps = latest_entry['step_count'] if latest_entry else 0
        percentage = (current_steps / DAILY_STEP_LIMIT) * 100 if DAILY_STEP_LIMIT > 0 else 0

        comparison_data.append({
            'name': user_name,
            'user_id': user_id,
            'latest_steps': current_steps,
            'latest_date': latest_entry['log_date'] if latest_entry else 'Brak wpisu',
            'percentage': round(percentage, 1),
            'progress_color': 'green' if percentage >= 100 else ('orange' if percentage >= 50 else 'red')
        })

    # 4. Globalne podsumowanie
    global_total_steps = {}
    for user_id, user_name in USERS.items():
        cursor.execute("SELECT SUM(step_count) FROM daily_steps WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        global_total_steps[user_id] = total if total else 0

    global_winner = None
    global_diff = 0
    total_weronika = global_total_steps.get(USERS_INV["Weronika"], 0)
    total_mich = global_total_steps.get(USERS_INV["Mich"], 0)

    global_winner, global_diff = compute_winner(total_weronika, total_mich, "Weronika", "Mich")

    return {
        'users': USERS,
        'default_date': default_date,
        'daily_limit': DAILY_STEP_LIMIT,
        'last_day_summary': last_day_summary,
        'full_history': full_history,
        'comparison_data': comparison_data,
        'global_total_steps': global_total_steps,
        'global_winner': global_winner,
        'global_diff': global_diff,
        'current_form_data': current_form_data
    }


def make_serializable(data):
    if isinstance(data, dict):
        return {str(k): make_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_serializable(v) for v in data]
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    return data


# --- Routery Flask ---

@app.route('/', methods=('GET', 'POST'))
def index():
    conn = get_db()
    cursor = conn.cursor()
    error = None

    try:
        if request.method == 'POST':
            try:
                log_date_str = request.form['log_date']
                log_date = date.fromisoformat(log_date_str)

                messages = []
                entries_processed = 0

                for user_id, user_name in USERS.items():
                    step_count_key = f'step_count_{user_id}'
                    step_count_str = request.form.get(step_count_key, '').strip()

                    if not step_count_str:
                        continue

                    try:
                        step_count = int(step_count_str)
                    except ValueError:
                        flash(f"Liczba kroków dla {user_name} musi być liczbą całkowitą.", 'error')
                        continue

                    original_step_count = step_count

                    if step_count > DAILY_STEP_LIMIT:
                        step_count = DAILY_STEP_LIMIT
                        flash(f"Wprowadzono więcej niż {DAILY_STEP_LIMIT} kroków dla {user_name}. Zapisano {DAILY_STEP_LIMIT}.", 'warning')

                    cursor.execute("SELECT * FROM daily_steps WHERE user_id = ? AND log_date = ?",
                                   (user_id, log_date.isoformat()))
                    existing_entry = cursor.fetchone()

                    if existing_entry:
                        cursor.execute("UPDATE daily_steps SET step_count = ? WHERE user_id = ? AND log_date = ?",
                                       (step_count, user_id, log_date.isoformat()))
                        if original_step_count <= DAILY_STEP_LIMIT:
                            messages.append(f"Zaktualizowano kroki dla {user_name} na dzień {log_date.strftime('%d.%m.%Y')}.")
                    else:
                        cursor.execute("INSERT INTO daily_steps (user_id, step_count, log_date) VALUES (?, ?, ?)",
                                       (user_id, step_count, log_date.isoformat()))
                        if original_step_count <= DAILY_STEP_LIMIT:
                            messages.append(f"Dodano kroki dla {user_name} na dzień {log_date.strftime('%d.%m.%Y')}.")

                    entries_processed += 1

                if entries_processed > 0:
                    conn.commit()
                    for msg in messages:
                        flash(msg, 'success')
                    return redirect(url_for('index'))
                else:
                    flash("Nie wprowadzono żadnych kroków. Proszę wypełnić przynajmniej jedno pole.", 'error')

            except ValueError:
                error = "Liczba kroków lub data jest niepoprawna."
                flash(error, 'error')
            except sqlite3.Error as e:
                error = f"Błąd bazy danych: {e}"
                flash(error, 'error')

        data = get_dashboard_data(cursor)
        users, users_inv = get_users(cursor)
        return render_template('index.html',
                               users=users,
                               users_inv=users_inv,
                               default_date=data['default_date'].isoformat(),
                               daily_limit=data['daily_limit'],
                               last_day_summary=data['last_day_summary'],
                               full_history=data['full_history'],
                               comparison_data=data['comparison_data'],
                               global_total_steps=data['global_total_steps'],
                               global_winner=data['global_winner'],
                               global_diff=data['global_diff'],
                               current_form_data=data['current_form_data'],
                               error=error)

    finally:
        conn.close()


@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nazwa użytkownika jest wymagana', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
        conn.commit()
        flash('Dodano użytkownika', 'success')
    except sqlite3.IntegrityError:
        flash('Użytkownik już istnieje', 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash('Usunięto użytkownika', 'success')
    finally:
        conn.close()
    return redirect(url_for('index'))


@app.route('/api/data', methods=['GET'])
def api_data():
    conn = get_db()
    cursor = conn.cursor()
    try:
        data = get_dashboard_data(cursor)
        return jsonify(make_serializable(data))
    finally:
        conn.close()


@app.route('/api/sync', methods=['POST'])
def api_sync():
    req_data = request.get_json(silent=True) or {}
    # Accept multiple payload shapes:
    # 1) { unsynced_entries: [...] } (current)
    # 2) { entries: [...] }
    # 3) [...] (raw list)
    if isinstance(req_data, list):
        unsynced_entries = req_data
    else:
        unsynced_entries = req_data.get('unsynced_entries') or req_data.get('entries') or []

    conn = get_db()
    cursor = conn.cursor()
    try:
        for entry in unsynced_entries:
            # tolerate missing keys / wrong types
            try:
                user_id = int(entry.get('user_id'))
                log_date_str = entry.get('log_date')
                step_count = int(entry.get('step_count'))
            except Exception:
                continue

            if not user_id or not log_date_str:
                continue

            if step_count > DAILY_STEP_LIMIT:
                step_count = DAILY_STEP_LIMIT
            if step_count < 0:
                step_count = 0

            # Upsert
            cursor.execute("SELECT id FROM daily_steps WHERE user_id = ? AND log_date = ?", (user_id, log_date_str))
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE daily_steps SET step_count = ? WHERE user_id = ? AND log_date = ?",
                    (step_count, user_id, log_date_str)
                )
            else:
                cursor.execute(
                    "INSERT INTO daily_steps (user_id, step_count, log_date) VALUES (?, ?, ?)",
                    (user_id, step_count, log_date_str)
                )
        conn.commit()

        data = get_dashboard_data(cursor)
        return jsonify(make_serializable(data))
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')


@app.route('/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json')


# --- Filtry Jinja2 ---
@app.template_filter('day_of_week')
def day_of_week_filter(value):
    if isinstance(value, str):
        dt_object = date.fromisoformat(value)
    elif isinstance(value, date):
        dt_object = value
    else:
        return ""

    weekdays = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    return weekdays[dt_object.weekday()]


# --- Uruchamianie aplikacji ---
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
