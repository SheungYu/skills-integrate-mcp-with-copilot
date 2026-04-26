"""High School Management System API."""

from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

current_dir = Path(__file__).parent
data_dir = current_dir / "data"
db_path = data_dir / "activities.sqlite"
app.mount("/static", StaticFiles(directory=str(current_dir / "static")), name="static")


SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_user(connection: sqlite3.Connection, email: str) -> int:
    row = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        return int(row["id"])

    connection.execute(
        "INSERT INTO users (email, name, grade_level) VALUES (?, ?, ?)",
        (email, email.split("@")[0].replace(".", " ").title(), "Unknown"),
    )
    created = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    return int(created["id"])


def create_schema(connection: sqlite3.Connection) -> None:
    # Foundational schema for issue #8; additional APIs can be layered on top.
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            grade_level TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL,
            max_participants INTEGER NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            workflow_state TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activity_participants (
            activity_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (activity_id, user_id),
            FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            club_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            club_id INTEGER,
            activity_id INTEGER,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            payload TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id),
            FOREIGN KEY (activity_id) REFERENCES activities(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER,
            user_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS finance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );
        """
    )


def seed_data(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) AS count FROM activities").fetchone()
    if existing and int(existing["count"]) > 0:
        return

    for name, details in SEED_ACTIVITIES.items():
        connection.execute(
            """
            INSERT INTO activities (name, description, schedule, max_participants)
            VALUES (?, ?, ?, ?)
            """,
            (name, details["description"], details["schedule"], details["max_participants"]),
        )

        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ?",
            (name,),
        ).fetchone()
        activity_id = int(activity["id"])

        for email in details["participants"]:
            user_id = ensure_user(connection, email)
            connection.execute(
                """
                INSERT OR IGNORE INTO activity_participants (activity_id, user_id)
                VALUES (?, ?)
                """,
                (activity_id, user_id),
            )


def initialize_database() -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        create_schema(connection)
        seed_data(connection)
        connection.commit()


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                a.id,
                a.name,
                a.description,
                a.schedule,
                a.max_participants,
                u.email AS participant_email
            FROM activities a
            LEFT JOIN activity_participants ap ON ap.activity_id = a.id
            LEFT JOIN users u ON u.id = ap.user_id
            ORDER BY a.name, u.email
            """
        ).fetchall()

    activities: dict[str, dict] = {}
    for row in rows:
        name = row["name"]
        if name not in activities:
            activities[name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
        if row["participant_email"]:
            activities[name]["participants"].append(row["participant_email"])

    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity."""
    with get_connection() as connection:
        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        user_id = ensure_user(connection, email)
        exists = connection.execute(
            """
            SELECT 1 FROM activity_participants
            WHERE activity_id = ? AND user_id = ?
            """,
            (int(activity["id"]), user_id),
        ).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        connection.execute(
            "INSERT INTO activity_participants (activity_id, user_id) VALUES (?, ?)",
            (int(activity["id"]), user_id),
        )
        connection.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity."""
    with get_connection() as connection:
        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        deleted = connection.execute(
            """
            DELETE FROM activity_participants
            WHERE activity_id = ? AND user_id = ?
            """,
            (int(activity["id"]), int(user["id"])),
        )
        if deleted.rowcount == 0:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        connection.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
