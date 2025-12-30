from flask import Flask, render_template, request
from deepface import DeepFace
import os
import requests
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- Telegram Bot Configuration ---
BOT_TOKEN = "8337250631:AAHIBu2ct732ydIzaqPraad-Zv-8pU9Fxyk"
CHAT_ID = "1146292630"  # your Telegram chat ID

# --- Paths ---
DB_PATH = "dataset"  # folder containing known persons' images
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Telegram Notification Function ---
def send_telegram_notification(status, message, image_path=None):
    emoji_map = {"success": "✅", "alert": "🚨", "error": "⚠️"}
    full_message = f"{emoji_map.get(status, 'ℹ️')} {message}"

    try:
        # Send text message
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": full_message}
        )

        # Send image if available
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID},
                    files={"photo": img}
                )
    except Exception as e:
        print("⚠️ Telegram Error:", e)

# --- Main Route ---
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            return render_template("index.html", result={
                "success": False,
                "message": "⚠️ Please upload an image first."
            })

        filename = secure_filename(file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(image_path)

        try:
            # --- Use DeepFace Verification ---
            match_found = False
            threshold = 0.35  # lower = stricter match

            for person_folder in os.listdir(DB_PATH):
                person_path = os.path.join(DB_PATH, person_folder)
                if not os.path.isdir(person_path):
                    continue

                for db_img in os.listdir(person_path):
                    db_img_path = os.path.join(person_path, db_img)
                    try:
                        result = DeepFace.verify(img1_path=image_path, img2_path=db_img_path, enforce_detection=False)
                        distance = result.get("distance", 1.0)
                        if distance < threshold:
                            match_found = True
                            person_name = person_folder
                            break
                    except Exception as e:
                        print("Comparison error:", e)
                if match_found:
                    break

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if match_found:
                msg = f"Access Granted ✅\nPerson: {person_name}\nTime: {timestamp}"
                send_telegram_notification("success", msg, image_path)
                return render_template("index.html", result={
                    "success": True,
                    "message": f"✅ Authorized Person Detected",
                    "image_url": "/" + image_path,
                    "color": "green"
                })
            else:
                msg = f"🚨 Unauthorized Person Detected!\nTime: {timestamp}"
                send_telegram_notification("alert", msg, image_path)
                return render_template("index.html", result={
                    "success": False,
                    "message": "🚨 Unauthorized Person Detected!",
                    "image_url": "/" + image_path,
                    "color": "red"
                })

        except Exception as e:
            msg = f"⚠️ Error processing image: {str(e)}"
            send_telegram_notification("error", msg)
            return render_template("index.html", result={
                "success": False,
                "message": f"⚠️ Error: {str(e)}",
                "color": "red"
            })

    # On refresh, reset view
    return render_template("index.html", result=None)


if __name__ == "__main__":
    app.run(debug=True)
