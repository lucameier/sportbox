import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path
import json
import hashlib
import csv

USERS_FILE = Path("users.json")
CONFIG_FILE = Path("config.json")
DEFECTS_FILE = Path("defekte_verluste.csv")
WISHES_FILE = Path("materialwuensche.csv")

ADMIN_PLACEHOLDER = "CHANGE_ME_ADMIN"
ADMIN_DEFAULT_PASSWORD = "test123"  # nach Deployment ändern


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_admin_user(data: dict) -> bool:
    users = data.setdefault("users", {})
    admin = users.get("admin")
    if not admin:
        users["admin"] = {
            "password": hash_password(ADMIN_DEFAULT_PASSWORD),
            "approved": True,
            "is_admin": True,
            "full_name": "Administrator",
            "kontakt": "",
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
        }
        return True
    placeholder_hash = hash_password(ADMIN_PLACEHOLDER)
    if admin.get("password") == placeholder_hash and ADMIN_DEFAULT_PASSWORD != ADMIN_PLACEHOLDER:
        admin["password"] = hash_password(ADMIN_DEFAULT_PASSWORD)
        admin.setdefault("approved", True)
        admin.setdefault("is_admin", True)
        admin.setdefault("full_name", "Administrator")
        admin.setdefault("kontakt", "")
        admin.setdefault("created_at", datetime.utcnow().isoformat())
        admin.setdefault("is_active", True)
        return True
    return False


def ensure_user_defaults(data: dict) -> bool:
    changed = False
    users = data.setdefault("users", {})
    for info in users.values():
        if info.setdefault("approved", False) is False:
            pass
        if info.setdefault("is_admin", False) is False:
            pass
        if info.setdefault("full_name", "") == "":
            pass
        if info.setdefault("kontakt", "") == "":
            pass
        if "created_at" not in info:
            info["created_at"] = datetime.utcnow().isoformat()
            changed = True
        if "is_active" not in info:
            info["is_active"] = True
            changed = True
    return changed


def load_users() -> dict:
    if not USERS_FILE.exists():
        USERS_FILE.write_text(
            json.dumps(
                {
                    "users": {
                        "admin": {
                            "password": hash_password(ADMIN_DEFAULT_PASSWORD),
                            "approved": True,
                            "is_admin": True,
                            "full_name": "Administrator",
                            "kontakt": ""
                        }
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    with USERS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    changed = ensure_admin_user(data)
    if ensure_user_defaults(data):
        changed = True
    if changed:
        save_users(data)
    return data


def save_users(data: dict) -> None:
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps({"current_code": "0000"}, indent=2),
            encoding="utf-8",
        )
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data: dict) -> None:
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def authenticate(username: str, password: str):
    users = load_users().get("users", {})
    user = users.get(username)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if user["password"] != hash_password(password):
        return None
    return user


def register_user(username: str, password: str, full_name: str, kontakt: str):
    data = load_users()
    users = data.setdefault("users", {})
    if username in users:
        return False, "Benutzername ist bereits vergeben."
    users[username] = {
        "password": hash_password(password),
        "approved": False,
        "is_admin": False,
        "full_name": full_name,
        "kontakt": kontakt,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
    }
    save_users(data)
    return True, "Registrierung erfolgreich. Dein Konto muss zuerst freigeschaltet werden."


def append_row_to_csv(path: Path, fieldnames, row: dict):
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


st.set_page_config(
    page_title="Sportbox Henggart",
    layout="wide"
)

if "user" not in st.session_state:
    st.session_state.user = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "is_approved" not in st.session_state:
    st.session_state.is_approved = False

st.title("Sportbox Henggart")

with st.sidebar:
    st.header("Anmeldung")

    if st.session_state.user is None:
        login_tab, reg_tab = st.tabs(["Login", "Registrierung"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Benutzername")
                password = st.text_input("Passwort", type="password")
                submitted = st.form_submit_button("Login")

            if submitted:
                user = authenticate(username, password)
                if user is None:
                    st.error("Login fehlgeschlagen.")
                else:
                    st.session_state.user = username
                    st.session_state.is_admin = user.get("is_admin", False)
                    st.session_state.is_approved = user.get("approved", False)
                    st.success(f"Angemeldet als {username}")
                    st.rerun()

        with reg_tab:
            with st.form("reg_form"):
                reg_username = st.text_input("Gewünschter Benutzername")
                reg_fullname = st.text_input("Vollständiger Name")
                reg_kontakt = st.text_input("Kontakt (E-Mail / Handy, optional)")
                reg_password = st.text_input("Passwort", type="password")
                reg_password2 = st.text_input("Passwort wiederholen", type="password")
                reg_rules = st.checkbox("Ich halte mich an die Regeln")
                reg_submitted = st.form_submit_button("Registrieren")

            if reg_submitted:
                if reg_password != reg_password2:
                    st.error("Passwörter stimmen nicht überein.")
                elif not reg_username:
                    st.error("Benutzername darf nicht leer sein.")
                elif not reg_password:
                    st.error("Passwort darf nicht leer sein.")
                elif not reg_rules:
                    st.error("Bitte bestätige, dass du dich an die Regeln hältst.")
                else:
                    ok, msg = register_user(
                        reg_username,
                        reg_password,
                        reg_fullname,
                        reg_kontakt
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    else:
        st.write(f"Angemeldet als **{st.session_state.user}**")
        if st.session_state.is_admin:
            st.info("Admin-Konto")
        elif not st.session_state.is_approved:
            st.warning("Dein Konto wurde noch nicht freigeschaltet.")

        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.is_admin = False
            st.session_state.is_approved = False
            st.rerun()

user = st.session_state.user
is_admin = st.session_state.is_admin
is_approved = st.session_state.is_approved or is_admin

if is_admin:
    tab_info, tab_material, tab_defekt, tab_wunsch, tab_code, tab_admin = st.tabs(
        [
            "Regeln & Infos",
            "Material",
            "Defekte / Verluste melden",
            "Material wünschen",
            "Aktueller Code",
            "Admin"
        ]
    )
else:
    tab_info, tab_material, tab_defekt, tab_wunsch, tab_code = st.tabs(
        [
            "Regeln & Infos",
            "Material",
            "Defekte / Verluste melden",
            "Material wünschen",
            "Aktueller Code"
        ]
    )

with tab_info:
    st.subheader("Regeln für die Nutzung")
    if Path("bild.png").exists():
        st.image("bild.png", caption="Aktueller Inhalt und Ordnung", use_container_width=True)
    st.markdown("""
**Wer darf die Sportbox benutzen?**

- Die Sportbox ist für Kinder und Jugendliche aus Henggart und deren Begleitpersonen.
- Die Nutzung ist nur für registrierte Personen erlaubt.
- Der aktuelle Zahlencode darf nicht an Unbeteiligte weitergegeben werden.

**So funktioniert die Ausleihe**

1. Box mit dem aktuellen Code öffnen.
2. Material auswählen und sorgfältig herausnehmen.
3. Nach dem Spielen:
   - Alles vollständig wieder zurücklegen
   - Stark verschmutztes Material kurz reinigen
   - Box wieder schliessen und Zahlen verdrehen

**Sorgfältiger Umgang mit dem Material**

- Geht mit allen Sachen so um, als wären es eure eigenen.
- Verwendet das Material nur für den vorgesehenen Zweck.
- Kein mutwilliges Beschädigen des Materials.

**Defekte und Verluste**

- Meldet Defekte oder Verluste möglichst rasch über das Formular in diesem Tool.
- Nur so können wir Material reparieren oder ersetzen.

**Sicherheit**

- Achtet auf andere Kinder, Velos, Autos und Fenster.
- Kein Spielen auf der Strasse oder an gefährlichen Orten.

**Kontakt**

Bei Fragen oder Rückmeldungen:
- an Luca per WhatsApp: +41 xx xxx xx xx
- oder per E-Mail: xxxxx@xxxx.ch
""")

with tab_material:
    st.subheader("Aktuelle Ausstattung der Sportbox")
    data = [
        ["Tischtennis", "Tischtennisbälle PONGORI TTB100 (weiss)", 72, "Bälle"],
        ["Tischtennis", "Tischtennisschläger PONGORI PPR 100", 5, "Schläger"],
        ["Unihockey", "Unihockeybälle OROKS 100 (gelb)", 3, "Bälle"],
        ["Tennis", "Tennisbälle Head Pro (Dose à 4)", 1, "Dose"],
        ["Fussball", "Fussball KIPSTA Hybrid FIFA Basic, Grösse 5 (weiss)", 1, "Ball"],
        ["Fussball", "Mini-Fussball KIPSTA Sunny 300, Grösse 1 (rosa)", 1, "Ball"],
        ["Basketball", "Basketball TARMAK R100, Grösse 7 (orange)", 1, "Ball"],
        ["Basketball", "Basketball TARMAK R100, Grösse 5 (gelb)", 1, "Ball"],
        ["Volleyball", "Kinder-Volleyball ALLSIX, Grösse 1 (blau)", 1, "Ball"],
        ["Volleyball", "Beachvolleyball KIPSTA BV100, Grösse 5 (bunt)", 1, "Ball"],
        ["Badminton", "Badmintonschläger DECATHLON BR 100 (rot)", 6, "Schläger"],
        ["Badminton", "Kunststoff-Federbälle PSC 100, Dose à 6", 2, "Dosen"],
        ["Training", "Trainingshütchen KIPSTA Essential (Set)", 40, "Hütchen"],
        ["Zubehör", "Ballpumpe KIPSTA Essentiel", 1, "Pumpe"],
        ["Zubehör", "Plastikpfeife KIPSTA", 1, "Pfeife"],
        ["Winter", "Schlitten Po-Rutscher Wedze 'Funny Slide'", 5, "Po-Rutscher"],
    ]
    df = pd.DataFrame(data, columns=["Kategorie", "Artikel", "Anzahl", "Einheit"])
    st.dataframe(df, use_container_width=True)

with tab_defekt:
    st.subheader("Defekt oder Verlust melden")
    st.markdown("Bitte melde Defekte oder Verluste, damit wir Material reparieren oder ersetzen können.")

    with st.form("defekt_form"):
        name = st.text_input("Dein Name")
        kontakt = st.text_input("Kontakt (WhatsApp / E-Mail, optional)")
        datum = st.date_input("Datum", value=date.today())
        art = st.selectbox("Art der Meldung", ["Defekt", "Verlust"])
        material = st.selectbox(
            "Betroffenes Material",
            [
                "Tischtennisbälle",
                "Tischtennisschläger",
                "Unihockeyball",
                "Tennisball",
                "Fussball Gr. 5",
                "Mini-Fussball Gr. 1",
                "Basketball Gr. 7",
                "Basketball Gr. 5",
                "Kinder-Volleyball",
                "Beachvolleyball",
                "Badmintonschläger",
                "Badminton-Federball",
                "Trainingshütchen",
                "Ballpumpe",
                "Plastikpfeife",
                "Schlitten Po-Rutscher",
                "Anderes"
            ]
        )
        anzahl = st.number_input("Anzahl betroffen", min_value=1, step=1, value=1)
        beschreibung = st.text_area(
            "Kurz beschreiben, was passiert ist",
            help="Z.B. wann, wie, bei welchem Spiel etc."
        )
        submitted = st.form_submit_button("Meldung senden")

        if submitted:
            row = {
                "timestamp": str(st.session_state.get("timestamp_now", "")) or pd.Timestamp.utcnow().isoformat(),
                "name": name,
                "kontakt": kontakt,
                "datum": str(datum),
                "art": art,
                "material": material,
                "anzahl": anzahl,
                "beschreibung": beschreibung,
                "user": user or "",
            }
            append_row_to_csv(
                DEFECTS_FILE,
                fieldnames=[
                    "timestamp",
                    "name",
                    "kontakt",
                    "datum",
                    "art",
                    "material",
                    "anzahl",
                    "beschreibung",
                    "user",
                ],
                row=row,
            )
            st.success("Danke! Deine Meldung wurde gespeichert.")
            st.write("**Zusammenfassung deiner Meldung:**")
            st.write(f"- Name: {name}")
            st.write(f"- Kontakt: {kontakt}")
            st.write(f"- Datum: {datum}")
            st.write(f"- Art: {art}")
            st.write(f"- Material: {material}")
            st.write(f"- Anzahl: {anzahl}")
            st.write(f"- Beschreibung: {beschreibung}")

with tab_wunsch:
    st.subheader("Materialwunsch einreichen")
    st.markdown("Du hast eine Idee, welches Material in der Sportbox noch fehlt? Sende uns deinen Wunsch.")

    with st.form("wunsch_form"):
        name_w = st.text_input("Dein Name")
        klasse_w = st.text_input("Klasse / Gruppe (optional)")
        wunsch = st.text_area("Was wünschst du dir? Hast du einen Link zum Produkt?")
        begruendung = st.text_area("Warum wäre das sinnvoll?")
        submitted_w = st.form_submit_button("Wunsch senden")

        if submitted_w:
            row = {
                "timestamp": pd.Timestamp.utcnow().isoformat(),
                "name": name_w,
                "klasse": klasse_w,
                "wunsch": wunsch,
                "begruendung": begruendung,
                "user": user or "",
            }
            append_row_to_csv(
                WISHES_FILE,
                fieldnames=[
                    "timestamp",
                    "name",
                    "klasse",
                    "wunsch",
                    "begruendung",
                    "user",
                ],
                row=row,
            )
            st.success("Danke für deinen Vorschlag! Er wurde gespeichert.")
            st.write("**Dein Wunsch:**")
            st.write(f"- Name: {name_w}")
            st.write(f"- Klasse / Gruppe: {klasse_w}")
            st.write(f"- Wunsch: {wunsch}")
            st.write(f"- Begründung: {begruendung}")

with tab_code:
    st.subheader("Aktueller Code der Sportbox")

    if user is None:
        st.warning("Bitte zuerst einloggen, um den aktuellen Code zu sehen.")
    elif not is_approved:
        st.warning("Dein Konto wurde noch nicht freigeschaltet. Bitte wende dich an die zuständige Person.")
    else:
        cfg = load_config()
        st.info("Bitte gib den Code nicht an Unbeteiligte weiter.")
        st.code(cfg.get("current_code", "----"), language="text")

if is_admin:
    with tab_admin:
        st.subheader("Admin-Bereich")

        st.markdown("### Nutzerverwaltung")
        data_users = load_users()
        users = data_users.get("users", {})
        non_admin_users = {u: v for u, v in users.items() if not v.get("is_admin", False)}

        all_rows = []
        for username, info in users.items():
            all_rows.append(
                {
                    "username": username,
                    "full_name": info.get("full_name", ""),
                    "kontakt": info.get("kontakt", ""),
                    "approved": info.get("approved", False),
                    "is_admin": info.get("is_admin", False),
                    "is_active": info.get("is_active", True),
                    "created_at": info.get("created_at", ""),
                    "password": info.get("password", ""),
                }
            )

        if all_rows:
            st.dataframe(pd.DataFrame(all_rows), use_container_width=True)

        if not non_admin_users:
            st.info("Keine registrierten Nutzer (ausser Admin).")
        else:
            with st.form("approve_users_form"):
                approved_states = {}
                active_states = {}
                st.write("**Freigabe und Aktiv-Status**")
                for username, info in non_admin_users.items():
                    label = f"{username}"
                    full_name = info.get("full_name", "").strip()
                    if full_name:
                        label += f" ({full_name})"
                    col_user, col_approved, col_active = st.columns([3, 1, 1])
                    with col_user:
                        st.write(label)
                    with col_approved:
                        approved_states[username] = st.checkbox(
                            "Freigabe",
                            value=info.get("approved", False),
                            key=f"approved_{username}"
                        )
                    with col_active:
                        active_states[username] = st.checkbox(
                            "Aktiv",
                            value=info.get("is_active", True),
                            key=f"active_{username}"
                        )
                submit_approvals = st.form_submit_button("Änderungen speichern")

                if submit_approvals:
                    for username, state in approved_states.items():
                        users[username]["approved"] = state
                    for username, state in active_states.items():
                        users[username]["is_active"] = state
                    data_users["users"] = users
                    save_users(data_users)
                    st.success("Nutzer aktualisiert.")

        st.markdown("### Code der Sportbox")
        cfg = load_config()
        current_code = cfg.get("current_code", "0000")

        with st.form("code_form"):
            new_code = st.text_input("Aktueller Code", value=current_code)
            save_code = st.form_submit_button("Code speichern")

            if save_code:
                cfg["current_code"] = new_code.strip()
                save_config(cfg)
                st.success("Code aktualisiert.")

        st.divider()
        st.markdown("### Defekte / Verluste")
        if DEFECTS_FILE.exists():
            try:
                df_defects = pd.read_csv(DEFECTS_FILE)
                if df_defects.empty:
                    st.info("Noch keine Defekt- oder Verlustmeldungen.")
                else:
                    st.dataframe(df_defects, use_container_width=True)
            except Exception:
                st.error("Defekt-/Verlustdatei konnte nicht gelesen werden.")
        else:
            st.info("Noch keine Defekt- oder Verlustmeldungen.")

        st.markdown("### Materialwünsche")
        if WISHES_FILE.exists():
            try:
                df_wishes = pd.read_csv(WISHES_FILE)
                if df_wishes.empty:
                    st.info("Noch keine Materialwünsche.")
                else:
                    st.dataframe(df_wishes, use_container_width=True)
            except Exception:
                st.error("Materialwunschdatei konnte nicht gelesen werden.")
        else:
            st.info("Noch keine Materialwünsche.")
