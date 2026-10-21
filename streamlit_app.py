import csv
import hashlib
import html
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

USERS_FILE = Path("users.json")
CONFIG_FILE = Path("config.json")
DEFECTS_FILE = Path("defekte_verluste.csv")
WISHES_FILE = Path("materialwuensche.csv")
MATERIALS_FILE = Path("materials.json")
VISITS_FILE = Path("besuche.csv")

ADMIN_PLACEHOLDER = "CHANGE_ME_ADMIN"
ADMIN_DEFAULT_PASSWORD = "test123"  # nach Deployment ändern

LOCK_CSS = """
<style>
.lock-wrap {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    padding: 14px 18px;
    background: linear-gradient(180deg, #f3f5f9 0%, #e7ebf3 100%);
    border: 1px solid #d4d9e4;
    border-radius: 14px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
    margin: 0.4rem 0 0.8rem 0;
}
.lock-digit {
    width: 56px;
    height: 72px;
    border-radius: 10px;
    background: linear-gradient(180deg, #ffffff 0%, #dfe4ee 100%);
    border: 1px solid #c6ccda;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    font-weight: 700;
    color: #202636;
    text-shadow: 0 1px 0 rgba(255,255,255,0.7);
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.08);
    font-family: "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.lock-divider {
    width: 6px;
    height: 56px;
    border-radius: 999px;
    background: #b6bdcc;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
}
</style>
"""

RULES_MARKDOWN = """
**Wer darf die Sportbox benutzen?**

- Die Sportbox ist für Kinder und Jugendliche aus Henggart und deren Begleitpersonen.
- Den Zahlencode gibt es erst, nachdem die Regeln hier bestätigt wurden.
- Der Code darf nicht an Unbeteiligte weitergegeben werden.

**So funktioniert die Ausleihe**

1. Regeln bestätigen und den Code ablesen.
2. Box mit dem Code öffnen.
3. Material auswählen und sorgfältig herausnehmen.
4. Nach dem Spielen:
   - Alles vollständig wieder zurücklegen
   - Stark verschmutztes Material kurz reinigen
   - Box wieder schliessen und Zahlen verdrehen

**Sorgfältiger Umgang mit dem Material**

- Geht mit allen Sachen so um, als wären es eure eigenen.
- Verwendet das Material nur für den vorgesehenen Zweck.
- Kein mutwilliges Beschädigen des Materials.

**Defekte und Verluste**

- Meldet Defekte oder Verluste möglichst rasch über das Formular auf dieser Seite.
- Nur so können wir Material reparieren oder ersetzen.

**Sicherheit**

- Achtet auf andere Kinder, Velos, Autos und Fenster.
- Kein Spielen auf der Strasse oder an gefährlichen Orten.
"""

# Zeichen der Kontaktadresse, damit sie nicht als Klartext im HTML steht.
CONTACT_CHAR_CODES = (
    107,
    111,
    110,
    116,
    97,
    107,
    116,
    64,
    108,
    117,
    99,
    97,
    109,
    101,
    105,
    101,
    114,
    46,
    99,
    104,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            "created_at": utc_now(),
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
        admin.setdefault("created_at", utc_now())
        admin.setdefault("is_active", True)
        return True
    return False


def load_users() -> dict:
    if not USERS_FILE.exists():
        data = {"users": {}}
        ensure_admin_user(data)
        save_users(data)
        return data
    with USERS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if ensure_admin_user(data):
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


def load_materials() -> list:
    if not MATERIALS_FILE.exists():
        MATERIALS_FILE.write_text(
            json.dumps([], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    with MATERIALS_FILE.open("r", encoding="utf-8") as f:
        materials = json.load(f)
    if not isinstance(materials, list):
        materials = []
    normalized = []
    for item in materials:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "kategorie": item.get("kategorie", ""),
                "name": item.get("name", ""),
                "marke": item.get("marke", ""),
                "menge": item.get("menge", ""),
                "einheit": item.get("einheit", ""),
                "preis": item.get("preis", ""),
                "details": item.get("details", ""),
                "bild": item.get("bild", ""),
            }
        )
    return normalized


def save_materials(materials: list) -> None:
    with MATERIALS_FILE.open("w", encoding="utf-8") as f:
        json.dump(materials, f, indent=2, ensure_ascii=False)


def material_options(materials: list) -> list:
    names = [item.get("name", "").strip() for item in materials]
    names = [name for name in names if name]
    if not names:
        return ["Anderes"]
    return names + ["Anderes"]


def group_materials(materials: list) -> dict:
    grouped = {}
    for item in materials:
        category = (item.get("kategorie") or "").strip() or "Weiteres"
        grouped.setdefault(category, []).append(item)
    return grouped


def authenticate_admin(username: str, password: str):
    user = load_users().get("users", {}).get(username.strip())
    if not user or not user.get("is_admin"):
        return None
    if not user.get("is_active", True):
        return None
    if user.get("password") != hash_password(password):
        return None
    return user


def log_event(ereignis: str) -> None:
    append_row_to_csv(
        VISITS_FILE,
        fieldnames=["timestamp", "ereignis"],
        row={"timestamp": utc_now(), "ereignis": ereignis},
    )


def append_row_to_csv(path: Path, fieldnames, row: dict):
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def render_lock(code: str) -> None:
    digits = list(code)
    html_digits = []
    for index, digit in enumerate(digits):
        html_digits.append(f"<div class='lock-digit'>{html.escape(digit)}</div>")
        if index < len(digits) - 1:
            html_digits.append("<div class='lock-divider'></div>")
    st.markdown(LOCK_CSS, unsafe_allow_html=True)
    st.markdown(
        f"<div class='lock-wrap'>{''.join(html_digits)}</div>",
        unsafe_allow_html=True,
    )


def render_contact() -> None:
    codes = ",".join(str(code) for code in CONTACT_CHAR_CODES)
    st.html(
        """
        <div data-nosnippet>
          <strong>Kontakt</strong><br>
          Bei Fragen oder Rückmeldungen per E-Mail:<br>
          <strong id="sportbox-mail"></strong>
        </div>
        <script>
          const target = document.getElementById("sportbox-mail");
          if (target) {
            target.textContent = String.fromCharCode(%s);
          }
        </script>
        """
        % codes,
        unsafe_allow_javascript=True,
    )


def render_rules() -> None:
    st.subheader("Regeln")
    text_col, image_col = st.columns([1.25, 0.75], gap="large")
    with text_col:
        st.markdown(RULES_MARKDOWN)
        render_contact()
    with image_col:
        image_path = Path("bild.png")
        if image_path.exists():
            st.image(
                str(image_path),
                caption="Aktueller Inhalt und Ordnung",
                width="stretch",
            )


def render_code_gate() -> None:
    st.subheader("Zahlencode")
    if not st.session_state.rules_accepted:
        st.markdown(
            "Der Code bleibt verborgen, bis du die Regeln gelesen und bestätigt hast."
        )
        agrees = st.checkbox(
            "Ich habe die Regeln gelesen und halte mich daran.",
            key="rules_checkbox",
        )
        if st.button(
            "Regeln bestätigen",
            type="primary",
            disabled=not agrees,
            key="confirm_rules",
            help="Zuerst das Kästchen aktivieren.",
            width="stretch",
        ):
            if agrees:
                st.session_state.rules_accepted = True
                log_event("code")
                st.rerun()
        return

    cfg = load_config()
    current_code = str(cfg.get("current_code", "----")).strip() or "----"
    st.success("Regeln bestätigt. Bitte gib den Code nicht weiter.")
    render_lock(current_code)
    st.caption(
        "Nach dem Spielen alles zurücklegen, die Box schliessen und die Zahlen verdrehen."
    )
    if st.button("Code ausblenden", key="hide_code"):
        st.session_state.rules_accepted = False
        st.session_state.rules_checkbox = False
        st.rerun()


def render_material_card(item: dict) -> None:
    name = (item.get("name") or "").strip() or "Ohne Namen"
    marke = (item.get("marke") or "").strip()
    menge = item.get("menge", "")
    einheit = (item.get("einheit") or "").strip()
    preis = (item.get("preis") or "").strip()
    details = (item.get("details") or "").strip()
    bild = (item.get("bild") or "").strip()
    menge_text = f"{menge} {einheit}".strip()

    with st.container(border=True):
        st.markdown(f"**{name}**")
        if marke:
            st.caption(marke)
        if bild:
            st.image(bild, width="stretch")
        meta = [part for part in (menge_text, preis) if part]
        if meta:
            st.write(" · ".join(meta))
        if details:
            st.caption(details)


def render_materials() -> None:
    st.subheader("Aktuelle Ausstattung")
    items = load_materials()
    if not items:
        st.info("Aktuell ist kein Material eingetragen.")
        return

    st.caption(f"{len(items)} Gegenstände in der Box")
    for category, category_items in group_materials(items).items():
        st.markdown(f"### {category}")
        columns = st.columns(3, gap="medium")
        for index, item in enumerate(category_items):
            with columns[index % 3]:
                render_material_card(item)


def render_defect_form() -> None:
    st.subheader("Defekt oder Verlust melden")
    st.markdown(
        "Bitte melde Defekte oder Verluste, damit wir Material reparieren oder ersetzen können."
    )

    with st.form("defekt_form"):
        name = st.text_input("Dein Name")
        kontakt = st.text_input("Kontakt (E-Mail, optional)")
        datum = st.date_input("Datum", value=date.today())
        art = st.selectbox("Art der Meldung", ["Defekt", "Verlust"])
        materials = load_materials()
        material = st.selectbox("Betroffenes Material", material_options(materials))
        anzahl = st.number_input("Anzahl betroffen", min_value=1, step=1, value=1)
        beschreibung = st.text_area(
            "Kurz beschreiben, was passiert ist",
            help="Z.B. wann, wie, bei welchem Spiel etc.",
        )
        submitted = st.form_submit_button("Meldung senden")

    if submitted:
        row = {
            "timestamp": utc_now(),
            "name": name,
            "kontakt": kontakt,
            "datum": str(datum),
            "art": art,
            "material": material,
            "anzahl": anzahl,
            "beschreibung": beschreibung,
            "user": "",
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


def render_wish_form() -> None:
    st.subheader("Materialwunsch einreichen")
    st.markdown(
        "Du hast eine Idee, welches Material in der Sportbox noch fehlt? Sende uns deinen Wunsch."
    )

    with st.form("wunsch_form"):
        name_w = st.text_input("Dein Name", key="wish_name")
        kontakt_w = st.text_input(
            "Kontakt (E-Mail, optional)",
            key="wish_kontakt",
        )
        wunsch = st.text_area("Was wünschst du dir? Hast du einen Link zum Produkt?")
        begruendung = st.text_area("Warum wäre das sinnvoll?")
        submitted_w = st.form_submit_button("Wunsch senden")

    if submitted_w:
        row = {
            "timestamp": utc_now(),
            "name": name_w,
            "kontakt": kontakt_w,
            "wunsch": wunsch,
            "begruendung": begruendung,
            "user": "",
        }
        append_row_to_csv(
            WISHES_FILE,
            fieldnames=[
                "timestamp",
                "name",
                "kontakt",
                "wunsch",
                "begruendung",
                "user",
            ],
            row=row,
        )
        st.success("Danke für deinen Vorschlag! Er wurde gespeichert.")
        st.write("**Dein Wunsch:**")
        st.write(f"- Name: {name_w}")
        st.write(f"- Kontakt: {kontakt_w}")
        st.write(f"- Wunsch: {wunsch}")
        st.write(f"- Begründung: {begruendung}")


def render_admin() -> None:
    st.caption("Code, Material und eingegangene Meldungen.")

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
    st.markdown("### Material verwalten")
    materials = load_materials()
    df_materials = pd.DataFrame(materials)
    material_columns = [
        "kategorie",
        "name",
        "marke",
        "menge",
        "einheit",
        "preis",
        "details",
        "bild",
    ]
    if df_materials.empty:
        df_materials = pd.DataFrame(columns=material_columns)
    else:
        df_materials = df_materials.reindex(columns=material_columns)

    with st.form("materials_form"):
        edited_materials = st.data_editor(
            df_materials,
            num_rows="dynamic",
            width="stretch",
        )
        save_materials_btn = st.form_submit_button("Material speichern")

    if save_materials_btn:
        cleaned = []
        for row in edited_materials.to_dict(orient="records"):
            cleaned_row = {}
            empty_row = True
            for col in material_columns:
                value = row.get(col, "")
                if pd.isna(value):
                    value = ""
                if isinstance(value, str):
                    value = value.strip()
                if value != "":
                    empty_row = False
                cleaned_row[col] = value
            if empty_row:
                continue
            menge = cleaned_row.get("menge", "")
            try:
                if menge != "":
                    cleaned_row["menge"] = int(float(menge))
            except (ValueError, TypeError):
                pass
            cleaned.append(cleaned_row)
        save_materials(cleaned)
        st.success("Material gespeichert.")

    st.divider()
    st.markdown("### Defekte / Verluste")
    if DEFECTS_FILE.exists():
        try:
            df_defects = pd.read_csv(DEFECTS_FILE)
            if df_defects.empty:
                st.info("Noch keine Defekt- oder Verlustmeldungen.")
            else:
                st.dataframe(df_defects, width="stretch")
        except Exception:
            st.error("Defekt-/Verlustdatei konnte nicht gelesen werden.")
    else:
        st.info("Noch keine Defekt- oder Verlustmeldungen.")

    st.markdown("### Aufrufe")
    if VISITS_FILE.exists():
        try:
            df_visits = pd.read_csv(VISITS_FILE)
            if df_visits.empty:
                st.info("Noch keine Aufrufe.")
            else:
                labels = {"aufruf": "Seitenaufruf", "code": "Code angesehen"}
                shown = df_visits.copy()
                if "ereignis" in shown.columns:
                    shown["ereignis"] = shown["ereignis"].map(
                        lambda value: labels.get(value, value)
                    )
                shown = shown.rename(
                    columns={"timestamp": "Zeitpunkt", "ereignis": "Ereignis"}
                )
                if "Zeitpunkt" in shown.columns:
                    shown = shown.iloc[::-1]
                st.dataframe(shown, width="stretch", hide_index=True)
        except Exception:
            st.error("Aufrufdatei konnte nicht gelesen werden.")
    else:
        st.info("Noch keine Aufrufe.")

    st.markdown("### Materialwünsche")
    if WISHES_FILE.exists():
        try:
            df_wishes = pd.read_csv(WISHES_FILE)
            if df_wishes.empty:
                st.info("Noch keine Materialwünsche.")
            else:
                st.dataframe(df_wishes, width="stretch")
        except Exception:
            st.error("Materialwunschdatei konnte nicht gelesen werden.")
    else:
        st.info("Noch keine Materialwünsche.")


def render_admin_access() -> None:
    if st.session_state.is_admin and st.session_state.user:
        st.caption(f"Angemeldet als {st.session_state.user}")
        if st.button("Abmelden", key="admin_logout"):
            st.session_state.user = None
            st.session_state.is_admin = False
            st.rerun()
        render_admin()
        return

    st.caption("Anmeldung nur für die Betreuung der Box.")
    with st.form("admin_login_form"):
        username = st.text_input("Benutzername", key="admin_username")
        password = st.text_input("Passwort", type="password", key="admin_password")
        submitted = st.form_submit_button("Anmelden", width="stretch")
    if submitted:
        user = authenticate_admin(username, password)
        if user is None:
            st.error("Anmeldung fehlgeschlagen.")
        else:
            st.session_state.user = username.strip()
            st.session_state.is_admin = True
            st.rerun()


def init_session() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("is_admin", False)
    st.session_state.setdefault("rules_accepted", False)
    if not st.session_state.get("visit_logged"):
        log_event("aufruf")
        st.session_state.visit_logged = True


st.set_page_config(
    page_title="Sportbox Henggart",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
st.html(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsed"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapseButton"] {
      display: none !important;
    }
    </style>
    """
)

st.title("Sportbox Henggart")
st.markdown(
    "Gemeinsames Sportmaterial für Kinder und Jugendliche aus Henggart. "
    "Den Zahlencode siehst du erst, nachdem du die Regeln bestätigt hast."
)

with st.container(border=True):
    render_rules()

with st.container(border=True):
    render_code_gate()

st.divider()

tab_material, tab_defekt, tab_wunsch, tab_admin = st.tabs(
    ["Material", "Defekt / Verlust", "Materialwunsch", "Verwaltung"]
)

with tab_material:
    render_materials()

with tab_defekt:
    render_defect_form()

with tab_wunsch:
    render_wish_form()

with tab_admin:
    render_admin_access()
