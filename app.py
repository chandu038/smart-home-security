from flask import Flask, render_template, request
from deepface import DeepFace
import os, requests, secrets
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

BOT_TOKEN = "8337250631:AAHIBu2ct732ydIzaqPraad-Zv-8pU9Fxyk"
CHAT_ID = "1146292630"

DB_PATH = "dataset"  
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def send_telegram_notification(status, message, image_path=None):
    emoji_map = {"success": "✅", "alert": "🚨", "error": "⚠️"}
    full_message = f"{emoji_map.get(status,'ℹ️')} {message}"
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": full_message})
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as img:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                              data={"chat_id": CHAT_ID}, files={"photo": img})
    except: pass

@app.route("/", methods=["GET","POST"])
def home():
    if request.method=="POST":
        result = None
        mode = request.form.get("mode")
        file = request.files.get("file")
        person_name_input = request.form.get("person_name","").strip()

        if not file or file.filename=="":
            result={"success":False,"message":"⚠️ Please upload an image first.","image_url":None}
            return render_template("index.html", result=result)

        filename = secure_filename(file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(image_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Add new face
            if mode=="add" and person_name_input:
                new_person_folder = os.path.join(DB_PATH, "NewPerson")
                os.makedirs(new_person_folder, exist_ok=True)
                save_path = os.path.join(new_person_folder, f"{person_name_input}_{filename}")
                os.rename(image_path, save_path)
                msg = f"✅ New Face Saved Successfully!\nTime: {timestamp}"
                send_telegram_notification("success", msg, save_path)
                result = {"success":True, "message":"✅ New Face Added and Saved","image_url":"/"+save_path.replace("\\","/")}

            # Verify face
            else:
                match_found=False
                threshold=0.35
                for person_folder in os.listdir(DB_PATH):
                    folder_path = os.path.join(DB_PATH, person_folder)
                    if not os.path.isdir(folder_path): continue
                    for db_img in os.listdir(folder_path):
                        db_img_path = os.path.join(folder_path, db_img)
                        try:
                            res = DeepFace.verify(img1_path=image_path, img2_path=db_img_path, enforce_detection=False)
                            if res.get("distance",1.0)<threshold:
                                match_found=True
                                person_name = person_folder
                                break
                        except: pass
                    if match_found: break

                if match_found:
                    msg = f"Access Granted ✅\nPerson: {person_name}\nTime: {timestamp}"
                    send_telegram_notification("success", msg, image_path)
                    result = {"success":True,"message":f"✅ Authorized Person Detected!","image_url":"/"+image_path.replace("\\","/")}
                else:
                    msg = f"🚨 Unauthorized Person Detected!\nTime: {timestamp}"
                    send_telegram_notification("alert", msg, image_path)
                    result = {"success":False,"message":"🚨 Unauthorized Person Detected!","image_url":"/"+image_path.replace("\\","/")}
        except Exception as e:
            msg=f"⚠️ Error processing image: {str(e)}"
            send_telegram_notification("error", msg)
            result={"success":False,"message":f"⚠️ Error: {str(e)}","image_url":None}

        return render_template("index.html", result=result)

    # GET request (page load or refresh) -> no alerts
    return render_template("index.html")

if __name__=="__main__":
    app.run(debug=True)
