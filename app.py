import os
import json
import sqlite3
import uuid
import hmac
from datetime import datetime, date
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps, UnidentifiedImageError
import requests
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "wardrobe.db"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
# Reject pathological image dimensions before they can exhaust a small hosting instance.
Image.MAX_IMAGE_PIXELS = 12_000_000

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or "closethaven-local-development-only-change-before-deploy"
if os.getenv("APP_ENV", "development").lower() == "production" and not os.getenv("FLASK_SECRET_KEY"):
    raise RuntimeError("FLASK_SECRET_KEY must be set in production.")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("APP_ENV", "development").lower() == "production"

CATEGORIES = {
    "Tops": ["T-shirt", "Shirt", "Blouse", "Top", "Sweater", "Kurti", "Kurta"],
    "Bottoms": ["Jeans", "Trousers", "Skirt", "Shorts", "Palazzo", "Leggings"],
    "Dresses & Sets": ["Dress", "Jumpsuit", "Co-ord set", "Saree", "Salwar suit", "Ethnic set", "Traditional wear"],
    "Footwear": ["Sneakers", "Flats", "Heels", "Boots", "Sandals"],
    "Accessories": ["Bag", "Watch", "Jewellery", "Belt", "Scarf", "Other"]
}
ALL_SUBCATEGORIES = [x for values in CATEGORIES.values() for x in values]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS garments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            color TEXT DEFAULT '',
            season TEXT DEFAULT 'All season',
            image TEXT DEFAULT '',
            status TEXT DEFAULT 'available',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outfits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            garment_ids TEXT NOT NULL,
            occasion TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outfit_id INTEGER,
            plan_date TEXT NOT NULL,
            event TEXT NOT NULL,
            status TEXT DEFAULT 'planned',
            FOREIGN KEY(outfit_id) REFERENCES outfits(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS wears (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outfit_id INTEGER,
            worn_on TEXT NOT NULL,
            garment_ids TEXT NOT NULL,
            FOREIGN KEY(outfit_id) REFERENCES outfits(id) ON DELETE SET NULL
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM garments").fetchone()[0]
        if count == 0:
            # Small starter inventory makes the demo usable immediately. Users can delete it.
            seed = [
                ("White cotton shirt","Tops","Shirt","White","All season","","available"),
                ("Blue straight jeans","Bottoms","Jeans","Blue","All season","","available"),
                ("Black tailored trousers","Bottoms","Trousers","Black","All season","","available"),
                ("Sage green kurta","Dresses & Sets","Traditional wear","Sage","All season","","available"),
                ("Neutral sneakers","Footwear","Sneakers","White","All season","","available"),
                ("Tan shoulder bag","Accessories","Bag","Tan","All season","","available"),
                ("Small gold hoops","Accessories","Jewellery","Gold","All season","","available"),
            ]
            now = datetime.now().isoformat(timespec="seconds")
            con.executemany("""INSERT INTO garments
                (name,category,subcategory,color,season,image,status,created_at)
                VALUES (?,?,?,?,?,?,?,?)""", [(*g, now) for g in seed])

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_garments(include_laundry=True):
    with db() as con:
        if include_laundry:
            rows = con.execute("SELECT * FROM garments ORDER BY created_at DESC").fetchall()
        else:
            rows = con.execute("SELECT * FROM garments WHERE status='available' ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def get_outfits():
    with db() as con:
        rows = con.execute("SELECT * FROM outfits ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def valid_image_file(path):
    try:
        with Image.open(path) as image:
            if image.format not in ("JPEG", "PNG", "WEBP"):
                return False
            image.verify()
        return True
    except Exception:
        return False

def process_garment_image(source_path):
    """Create a small web-ready preview without memory-heavy background removal."""
    try:
        with Image.open(source_path) as opened:
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((900, 900), Image.Resampling.LANCZOS)
            # JPEG keeps uploaded previews substantially smaller than full-size PNGs.
            if image.mode not in ("RGB", "L"):
                background = Image.new("RGB", image.size, "white")
                if "A" in image.getbands():
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image.convert("RGB"))
                image = background
            else:
                image = image.convert("RGB")
            output = UPLOAD_DIR / f"{uuid.uuid4().hex}.jpg"
            image.save(output, format="JPEG", quality=82, optimize=True)
        return output.name
    except Exception as exc:
        app.logger.warning("Image processing failed; retaining original upload: %s", exc)
        return None

def classify_with_gemini(image_path):
    """Optional vision categorisation. Returns None when API is unavailable."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        from PIL import Image
        client = genai.Client(api_key=key)
        img = Image.open(image_path)
        prompt = """Identify this single clothing/fashion item. Return ONLY valid JSON with keys:
        name (short item name), category (one of Tops, Bottoms, Dresses & Sets, Footwear, Accessories),
        subcategory (short practical type), color (main color), season (All season, Summer, Winter, Monsoon).
        Be conservative. If uncertain, use the closest category."""
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=[prompt, img]
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        if data.get("category") not in CATEGORIES:
            data["category"] = "Tops"
        if data.get("subcategory") not in CATEGORIES[data["category"]]:
            data["subcategory"] = CATEGORIES[data["category"]][0]
        return data
    except Exception as exc:
        app.logger.warning("Gemini categorisation unavailable: %s", exc)
        return None

def get_live_weather(city):
    """Fetch current conditions from Open-Meteo; return None when lookup fails."""
    if not city:
        return None
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city, "count": 1, "language": "en", "format": "json"},
                           timeout=8).json()
        places = geo.get("results") or []
        if not places:
            return None
        place = places[0]
        data = requests.get("https://api.open-meteo.com/v1/forecast",
                            params={"latitude": place["latitude"], "longitude": place["longitude"],
                                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,weather_code,wind_speed_10m"},
                            timeout=8).json()
        current = data.get("current") or {}
        if not current:
            return None
        code = current.get("weather_code")
        labels = {0:"clear",1:"mainly clear",2:"partly cloudy",3:"overcast",
                  45:"foggy",48:"foggy",51:"light drizzle",53:"drizzle",55:"heavy drizzle",
                  61:"light rain",63:"rain",65:"heavy rain",71:"light snow",73:"snow",
                  75:"heavy snow",80:"rain showers",81:"rain showers",82:"heavy showers",
                  95:"thunderstorm",96:"thunderstorm with hail",99:"thunderstorm with hail"}
        return (f"Live conditions in {place.get('name', city)}: {labels.get(code, 'current conditions')}, "
                f"{current.get('temperature_2m', 'N/A')}°C, feels like {current.get('apparent_temperature', 'N/A')}°C, "
                f"humidity {current.get('relative_humidity_2m', 'N/A')}%, precipitation {current.get('precipitation', 0)} mm.")
    except Exception as exc:
        app.logger.warning("Live weather lookup unavailable: %s", exc)
        return None

def build_outfit_suggestions(event, weather, preference, garments):
    """Ground suggestions in available inventory; Gemini is optional for ranking/explanations."""
    available = [g for g in garments if g["status"] == "available"]
    tops = [g for g in available if g["category"] == "Tops"]
    bottoms = [g for g in available if g["category"] == "Bottoms"]
    dresses = [g for g in available if g["category"] == "Dresses & Sets"]
    shoes = [g for g in available if g["category"] == "Footwear"]
    accessories = [g for g in available if g["category"] == "Accessories"]

    candidates = []
    for top in tops:
        for bottom in bottoms:
            candidates.append([top, bottom])
    for dress in dresses:
        candidates.append([dress])
    if not candidates and available:
        candidates = [[g] for g in available if g["category"] not in ("Accessories", "Footwear")]

    # Basic transparent ranking. Avoid recently worn items where possible.
    with db() as con:
        recent = con.execute("SELECT garment_ids FROM wears ORDER BY worn_on DESC LIMIT 5").fetchall()
    recent_ids = set()
    for row in recent:
        try: recent_ids.update(json.loads(row["garment_ids"]))
        except Exception: pass

    ranked = sorted(candidates, key=lambda combo: (
        -sum(1 for g in combo if g["id"] not in recent_ids),
        -len(combo)
    ))
    results = []
    for i, combo in enumerate(ranked[:3]):
        chosen = combo[:]
        if shoes:
            chosen.append(shoes[i % len(shoes)])
        if accessories:
            chosen.append(accessories[i % len(accessories)])
        reasons = []
        if any(g["id"] not in recent_ids for g in combo):
            reasons.append("Prioritises pieces that have not appeared in your most recent wear log.")
        reasons.append("Uses only items currently marked available.")
        if weather:
            reasons.append(f"Weather context considered: {weather}.")
        if preference:
            reasons.append(f"Preference considered: {preference}.")
        results.append({
            "name": f"{event.title()} look {i+1}",
            "garments": chosen,
            "reason": " ".join(reasons)
        })
    return results

def try_gemini_style(event, weather, preference, suggestions):
    key = os.getenv("GEMINI_API_KEY")
    if not key or not suggestions:
        return suggestions
    try:
        from google import genai
        client = genai.Client(api_key=key)
        compact = [{"name": s["name"], "items": [g["name"] for g in s["garments"]]} for s in suggestions]
        prompt = f"""You are a practical wardrobe stylist. Improve the short explanation for these inventory-grounded outfit options.
        Event: {event}; weather: {weather or 'not supplied'}; preference: {preference or 'none'}.
        Do not add, remove or rename garments. Return ONLY JSON array of objects with keys name and reason.
        Options: {json.dumps(compact)}"""
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        enriched = json.loads(raw)
        for i, item in enumerate(enriched[:len(suggestions)]):
            if item.get("reason"):
                suggestions[i]["reason"] = item["reason"]
    except Exception as exc:
        app.logger.warning("Gemini styling unavailable: %s", exc)
    return suggestions

@app.before_request
def require_demo_access():
    access_password = os.getenv("ACCESS_PASSWORD", "")
    if not access_password:
        return None
    if request.endpoint in ("access", "static", "health"):
        return None
    if not session.get("closethaven_access"):
        return redirect(url_for("access", next=request.path))
    return None

@app.route("/access", methods=["GET", "POST"])
def access():
    if request.method == "POST":
        supplied = request.form.get("password", "")
        if hmac.compare_digest(supplied, os.getenv("ACCESS_PASSWORD", "")):
            session["closethaven_access"] = True
            return redirect(request.args.get("next") or url_for("index"))
        flash("That access code is not correct.", "error")
    return render_template("access.html")

@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "current_year": datetime.now().year,
            "access_protected": bool(os.getenv("ACCESS_PASSWORD"))}

@app.route("/")
def index():
    garments = get_garments()
    available = [g for g in garments if g["status"] == "available"]
    with db() as con:
        wears = con.execute("SELECT COUNT(*) FROM wears").fetchone()[0]
        planned = con.execute("SELECT COUNT(*) FROM plans WHERE status='planned'").fetchone()[0]
    return render_template("index.html", garment_count=len(garments), available_count=len(available),
                           wears=wears, planned=planned)

@app.route("/wardrobe")
def wardrobe():
    garments = get_garments()
    selected = request.args.get("category", "")
    if selected:
        garments = [g for g in garments if g["category"] == selected]
    return render_template("wardrobe.html", garments=garments, selected=selected)

@app.route("/garments/add", methods=["POST"])
def add_garment():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "")
    subcategory = request.form.get("subcategory", "").strip()
    if not name or category not in CATEGORIES or not subcategory:
        flash("Please provide a name, category and item type.", "error")
        return redirect(url_for("wardrobe"))
    image_name = ""
    recognised_image = request.form.get("recognised_image", "").strip()
    if recognised_image and Path(recognised_image).name == recognised_image and (UPLOAD_DIR / recognised_image).is_file():
        image_name = recognised_image
    file = request.files.get("image")
    if file and file.filename and not image_name:
        if not allowed_file(file.filename):
            flash("Use a JPG, PNG or WEBP image.", "error")
            return redirect(url_for("wardrobe"))
        raw_name = f"{uuid.uuid4().hex}.{secure_filename(file.filename).rsplit('.', 1)[1].lower()}"
        raw_path = UPLOAD_DIR / raw_name
        file.save(raw_path)
        if not valid_image_file(raw_path):
            raw_path.unlink(missing_ok=True)
            flash("The selected file is not a valid JPG, PNG or WEBP image.", "error")
            return redirect(url_for("wardrobe"))
        image_name = process_garment_image(raw_path) or raw_name
        if image_name != raw_name:
            raw_path.unlink(missing_ok=True)
    with db() as con:
        con.execute("""INSERT INTO garments(name,category,subcategory,color,season,image,status,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
            (name, category, subcategory, request.form.get("color","").strip(),
             request.form.get("season","All season"), image_name, "available",
             datetime.now().isoformat(timespec="seconds")))
    flash("Garment added to your wardrobe.", "success")
    return redirect(url_for("wardrobe"))

@app.route("/garments/recognise", methods=["POST"])
def recognise_garment():
    file = request.files.get("image")
    if not file or not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Upload a JPG, PNG or WEBP image."}), 400
    ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
    image_name = f"{uuid.uuid4().hex}.{ext}"
    path = UPLOAD_DIR / image_name
    file.save(path)
    if not valid_image_file(path):
        path.unlink(missing_ok=True)
        return jsonify({"error": "The selected file is not a valid JPG, PNG or WEBP image."}), 400
    # Compress first, then send the smaller image to the optional Gemini classifier.
    processed = process_garment_image(path)
    if processed:
        path.unlink(missing_ok=True)
        image_name = processed
    data = classify_with_gemini(UPLOAD_DIR / image_name)
    if not data:
        return jsonify({"image": image_name, "message": "Photo prepared. AI recognition is unavailable, so review the details manually."})
    data["image"] = image_name
    return jsonify(data)

@app.route("/garments/<int:garment_id>/status", methods=["POST"])
def garment_status(garment_id):
    status = request.form.get("status")
    if status not in ("available", "laundry"):
        flash("Invalid garment status.", "error")
    else:
        with db() as con:
            con.execute("UPDATE garments SET status=? WHERE id=?", (status, garment_id))
        flash("Garment availability updated.", "success")
    return redirect(request.referrer or url_for("wardrobe"))

@app.route("/garments/<int:garment_id>/delete", methods=["POST"])
def delete_garment(garment_id):
    with db() as con:
        row = con.execute("SELECT image FROM garments WHERE id=?", (garment_id,)).fetchone()
        con.execute("DELETE FROM garments WHERE id=?", (garment_id,))
    if row and row["image"]:
        try: (UPLOAD_DIR / row["image"]).unlink(missing_ok=True)
        except Exception: pass
    flash("Garment removed.", "success")
    return redirect(url_for("wardrobe"))

@app.route("/stylist", methods=["GET", "POST"])
def stylist():
    suggestions = []
    details = {}
    if request.method == "POST":
        details = {
            "event": request.form.get("event", "Everyday"),
            "weather": request.form.get("weather", "").strip(),
            "location": request.form.get("location", "").strip(),
            "preference": request.form.get("preference", "").strip()
        }
        if not details["weather"] and details.get("location"):
            details["weather"] = get_live_weather(details["location"]) or ""
            if not details["weather"]:
                flash("Live weather could not be retrieved. Add weather manually or try another city.", "error")
        suggestions = build_outfit_suggestions(details["event"], details["weather"],
                                               details["preference"], get_garments())
        suggestions = try_gemini_style(details["event"], details["weather"],
                                        details["preference"], suggestions)
        if not suggestions:
            flash("Your available wardrobe does not yet contain enough outfit pieces. Add garments first.", "error")
    return render_template("stylist.html", suggestions=suggestions, details=details)

@app.route("/outfits/save", methods=["POST"])
def save_outfit():
    name = request.form.get("name", "Saved outfit").strip() or "Saved outfit"
    ids = request.form.get("garment_ids", "[]")
    try:
        parsed = [int(x) for x in json.loads(ids)]
    except Exception:
        parsed = []
    if not parsed:
        flash("No garments selected to save.", "error")
        return redirect(url_for("stylist"))
    with db() as con:
        existing = con.execute(f"SELECT id,status FROM garments WHERE id IN ({','.join('?'*len(parsed))})", parsed).fetchall()
        valid = [r["id"] for r in existing if r["status"] == "available"]
        if not valid:
            flash("Those items are no longer available. Generate a new outfit.", "error")
            return redirect(url_for("stylist"))
        con.execute("INSERT INTO outfits(name,garment_ids,occasion,notes,created_at) VALUES(?,?,?,?,?)",
                    (name, json.dumps(valid), request.form.get("occasion",""), "Generated by ClosetHaven",
                     datetime.now().isoformat(timespec="seconds")))
    flash("Outfit saved. You can now schedule it.", "success")
    return redirect(url_for("planner"))

@app.route("/planner", methods=["GET", "POST"])
def planner():
    if request.method == "POST":
        outfit_id = request.form.get("outfit_id")
        plan_date = request.form.get("plan_date")
        event = request.form.get("event", "").strip()
        if not outfit_id or not plan_date or not event:
            flash("Choose an outfit, date and event.", "error")
        else:
            with db() as con:
                outfit = con.execute("SELECT garment_ids FROM outfits WHERE id=?", (outfit_id,)).fetchone()
                if outfit:
                    ids = json.loads(outfit["garment_ids"])
                    if ids:
                        marks = ",".join("?" * len(ids))
                        unavailable = con.execute(f"SELECT COUNT(*) FROM garments WHERE id IN ({marks}) AND status!='available'", ids).fetchone()[0]
                    else: unavailable = 0
                    if unavailable:
                        flash("This outfit contains an item in laundry. Choose another outfit.", "error")
                    else:
                        con.execute("INSERT INTO plans(outfit_id,plan_date,event,status) VALUES(?,?,?,'planned')",
                                    (outfit_id, plan_date, event))
                        flash("Outfit scheduled.", "success")
            return redirect(url_for("planner"))
    with db() as con:
        plans = con.execute("""SELECT p.*, o.name AS outfit_name FROM plans p
            LEFT JOIN outfits o ON p.outfit_id=o.id ORDER BY p.plan_date""").fetchall()
    return render_template("planner.html", outfits=get_outfits(), plans=[dict(p) for p in plans])

@app.route("/plans/<int:plan_id>/worn", methods=["POST"])
def confirm_worn(plan_id):
    with db() as con:
        plan = con.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        if not plan:
            flash("Plan not found.", "error")
            return redirect(url_for("planner"))
        if plan["status"] == "worn":
            flash("This plan is already marked as worn.", "success")
            return redirect(url_for("planner"))
        outfit = con.execute("SELECT garment_ids FROM outfits WHERE id=?", (plan["outfit_id"],)).fetchone()
        ids = json.loads(outfit["garment_ids"]) if outfit else []
        con.execute("INSERT INTO wears(outfit_id,worn_on,garment_ids) VALUES(?,?,?)",
                    (plan["outfit_id"], date.today().isoformat(), json.dumps(ids)))
        con.execute("UPDATE plans SET status='worn' WHERE id=?", (plan_id,))
    flash("Wear history updated after your confirmation.", "success")
    return redirect(url_for("planner"))

@app.route("/panic", methods=["GET", "POST"])
def panic():
    suggestions = []
    details = {}
    if request.method == "POST":
        details = {
            "event": request.form.get("event", "Last-minute event"),
            "weather": request.form.get("weather", "").strip(),
            "location": request.form.get("location", "").strip(),
            "preference": request.form.get("preference", "").strip(),
            "when": request.form.get("when", "").strip()
        }
        if not details["weather"] and details.get("location"):
            details["weather"] = get_live_weather(details["location"]) or ""
            if not details["weather"]:
                flash("Live weather could not be retrieved. Add weather manually or try another city.", "error")
        suggestions = build_outfit_suggestions(details["event"], details["weather"],
                                               details["preference"], get_garments())
        suggestions = try_gemini_style(details["event"], details["weather"],
                                        details["preference"], suggestions)
        if not suggestions:
            flash("No suitable combinations found. Add available tops, bottoms or dresses first.", "error")
    return render_template("panic.html", suggestions=suggestions, details=details)

@app.route("/impact")
def impact():
    garments = get_garments()
    with db() as con:
        wear_rows = con.execute("SELECT garment_ids FROM wears").fetchall()
        wears = len(wear_rows)
        plan_count = con.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    counts = {}
    for row in wear_rows:
        try:
            for gid in json.loads(row["garment_ids"]):
                counts[gid] = counts.get(gid, 0) + 1
        except Exception: pass
    most_used = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    names = {g["id"]: g["name"] for g in garments}
    return render_template("impact.html", garments=len(garments), wears=wears, plan_count=plan_count,
                           most_used=[(names.get(gid, "Removed item"), n) for gid,n in most_used])

@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "ClosetHaven"})

@app.errorhandler(413)
def too_large(_):
    flash("Image is too large. Maximum upload size is 8 MB.", "error")
    return redirect(request.referrer or url_for("wardrobe"))

init_db()

if __name__ == "__main__":
    if os.getenv("APP_ENV", "development").lower() == "production" and not os.getenv("FLASK_SECRET_KEY"):
        raise RuntimeError("Set FLASK_SECRET_KEY in the hosting environment before production startup.")
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")))
