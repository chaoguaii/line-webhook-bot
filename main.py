from flask import Flask, request, jsonify
import requests
import os
import google.auth
from googleapiclient.discovery import build
from google.cloud import bigquery  # สำหรับ BigQuery
from dotenv import load_dotenv

# โหลด Environment Variables
load_dotenv()

app = Flask(__name__)

# Environment Variables
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # ID ของ Google Sheets
SHEET_NAME = os.getenv("SHEET_NAME", "Data")   # ชื่อ sheet สำหรับข้อมูลทั่วไป
MATERIAL_COSTS_SHEET = "MATERIAL_COSTS"         # ชื่อ sheet สำหรับ MATERIAL_COSTS

# สำหรับ BigQuery
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE")

print("LINE_ACCESS_TOKEN:", LINE_ACCESS_TOKEN)

# เก็บข้อมูล session ของผู้ใช้
USER_SESSIONS = {}

# ตารางราคาวัสดุ (จะถูกโหลดจาก Google Sheets)
MATERIAL_COSTS = {}

def load_material_costs():
    """
    ดึงข้อมูลวัสดุและราคาจาก Google Sheets จาก sheet MATERIAL_COSTS
    โดยคาดว่าข้อมูลเริ่มที่แถวที่ 2 โดย:
      - คอลัมน์ A: Material (ชื่อวัสดุ)
      - คอลัมน์ B: Cost (ราคา)
    """
    print("Start loading MATERIAL_COSTS...")
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    credentials, _ = google.auth.default(scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    range_name = f"{MATERIAL_COSTS_SHEET}!A2:B"
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    print("Result from Sheets API:", result)
    values = result.get("values", [])
    costs = {}
    for row in values:
        if len(row) >= 2:
            material = row[0].strip()
            try:
                cost = float(row[1].strip())
            except ValueError:
                cost = 0
            costs[material] = cost
    print("Loaded MATERIAL_COSTS:", costs)
    return costs

@app.route("/", methods=["GET"])
def home():
    return "LINE Webhook is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data = request.json
        print("📩 Received:", data)
        for event in data.get("events", []):
            user_id = event["source"]["userId"]
            if "message" in event:
                message_text = event["message"]["text"].strip()
                print(f"📩 ข้อความจาก {user_id}: {message_text}")

                # คำสั่งสำหรับ Contact และ FAQ
                if message_text.lower() == "ติดต่อเรา":
                    send_contact_menu(user_id)
                    continue
                if message_text.upper().startswith("FAQ"):
                    process_faq(user_id, message_text)
                    continue
                # คำสั่งสำหรับ สินค้าและบริการ
                if message_text.lower() == "สินค้าและบริการ":
                    send_services_menu(user_id)
                    continue
                if message_text in ["บริการของเรา", "สินค้าตัวอย่าง", "กระบวนการผลิตสินค้า"]:
                    process_services(user_id, message_text)
                    continue
                # คำสั่งเริ่มต้นการคำนวณ
                if message_text.lower() == "คำนวณราคา":
                    start_questionnaire(user_id)
                else:
                    process_response(user_id, message_text)
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "Method Not Allowed"}), 405

# ------------------ ฟังก์ชันสำหรับ Contact & FAQ ------------------

def send_contact_menu(user_id):
    text = (
        "📞 ติดต่อเรา\n\n"
        "โปรดพิมพ์ FAQ ที่ต้องการ:\n"
        "FAQ 1: Email\n"
        "FAQ 2: โทรศัพท์\n"
        "FAQ 3: เวลาทำการ\n"
        "FAQ 4: ที่อยู่\n"
        "FAQ 5: พิกัด"
    )
    send_message(user_id, text)

def process_faq(user_id, message_text):
    faq = message_text.strip().upper()
    if faq == "FAQ 1":
        send_message(user_id, "📧 Email: bestwellplastic@gmail.com")
    elif faq == "FAQ 2":
        send_message(user_id, "📞 โทรศัพท์: 02 813 8773")
    elif faq == "FAQ 3":
        send_message(user_id, "⏰ เวลาทำการ:\nวันจันทร์ – วันเสาร์\nเวลา 8.00 - 17.00 น.\n(ปิดทำการทุกวันอาทิตย์)")
    elif faq == "FAQ 4":
        send_message(user_id, "🏠 ที่อยู่:\n135/3 หมู่ 13 ซอยเพชรเกษม 91 แยก12\nต.อ้อมน้อย, อ.กระทุ่มแบน, จ.สมุทรสาคร 74130")
    elif faq == "FAQ 5":
        send_location(user_id)
    else:
        send_message(user_id, "❌ ไม่พบ FAQ ที่ต้องการ กรุณาพิมพ์ใหม่ เช่น 'FAQ 1'")

def send_location(user_id):
    location_msg = {
        "type": "location",
        "title": "บริษัท เบสท์ เวลล์ พลาสติก จำกัด",
        "address": "135/3-4 หมู่ 13 ถ.เพชรเกษม 91 ต.อ้อมน้อย อ.กระทุ่มแบน จ.สมุทรสาคร",
        "latitude": 13.697285427411833,
        "longitude": 100.31582319730443
    }
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    message = {"to": user_id, "messages": [location_msg]}
    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=message)
    print(f"📤 ส่ง location ไปที่ {user_id}: {location_msg}")
    print(f"📡 LINE Response: {response.status_code} {response.text}")

# ------------------ ฟังก์ชันสำหรับ สินค้าและบริการ ------------------

def send_services_menu(user_id):
    flex_message = {
        "type": "flex",
        "altText": "สินค้าและบริการ",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "สินค้าและบริการ", "weight": "bold", "size": "lg", "align": "center"},
                    {"type": "text", "text": "โปรดเลือกหนึ่งในตัวเลือกด้านล่าง:", "size": "sm", "margin": "md", "align": "center"},
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "บริการของเรา", "text": "บริการของเรา"}, "margin": "lg"},
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "สินค้าตัวอย่าง", "text": "สินค้าตัวอย่าง"}, "margin": "md"},
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "กระบวนการผลิตสินค้า", "text": "กระบวนการผลิตสินค้า"}, "margin": "md"}
                ]
            }
        }
    }
    send_flex_message(user_id, flex_message)

def process_services(user_id, message_text):
    if message_text == "บริการของเรา":
        flex_message = {
            "type": "flex",
            "altText": "บริการของเรา",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "size": "md", "text": "บริการของเรา", "align": "center", "weight": "bold"},
                        {"margin": "md", "type": "text", "text": "1. ออกแบบและผลิตแม่พิมพ์"},
                        {"margin": "md", "type": "text", "text": "2. รับผลิตชิ้นส่วนพลาสติก"},
                        {"margin": "md", "type": "text", "text": "3. บริการให้คำปรึกษา"},
                        {"margin": "lg", "type": "separator"},
                        {"type": "box", "layout": "vertical", "margin": "xl", "contents": [
                            {"type": "text", "align": "center", "weight": "bold", "size": "md", "text": "เปลี่ยนไอเดียของคุณให้เป็นจริง", "color": "#1DB446"},
                            {"type": "text", "margin": "md", "align": "center", "weight": "bold", "size": "md", "text": "ออกแบบและผลิตไปกับเรา", "color": "#1DB446"}
                        ]}
                    ]
                }
            }
        }
        send_flex_message(user_id, flex_message)
    elif message_text == "สินค้าตัวอย่าง":
        flex_message = {
            "template": {
                "columns": [
                    {
                        "defaultAction": {"label": "View detail", "type": "uri", "uri": "https://bestwellplastic.com/product-category/best-seller/"},
                        "imageBackgroundColor": "#000000",
                        "actions": [{"type": "uri", "uri": "https://bestwellplastic.com/product-category/best-seller/", "label": "View detail"}],
                        "text": "เปลี่ยนแนวคิดให้เป็นบรรจุภัณฑ์ที่จับต้องได้",
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2025/03/1678569-247x296.jpg",
                        "title": "BEST SELLER"
                    },
                    {
                        "text": "สร้างสรรค์ดีไซน์ พัฒนาแบรนด์ ผ่าน Packaging ที่ใช่",
                        "defaultAction": {"uri": "https://bestwellplastic.com/product-category/packaging/", "label": "View detail", "type": "uri"},
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/packing-247x296.png",
                        "actions": [{"uri": "https://bestwellplastic.com/product-category/packaging/", "label": "View detail", "type": "uri"}],
                        "title": "Packaging",
                        "imageBackgroundColor": "#FFFFFF"
                    },
                    {
                        "imageBackgroundColor": "#000000",
                        "actions": [{"type": "uri", "uri": "https://bestwellplastic.com/product-category/fanpart/", "label": "View detail"}],
                        "title": "FAN PART",
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2022/08/fan-cat-copy.jpg",
                        "defaultAction": {"uri": "https://bestwellplastic.com/product-category/fanpart/", "label": "View detail", "type": "uri"},
                        "text": "ออกแบบเพื่อการใช้งานยาวนาน เย็นได้เต็มประสิทธิภาพ"
                    },
                    {
                        "defaultAction": {"uri": "https://bestwellplastic.com/product-category/car-accessory/", "label": "View detail", "type": "uri"},
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/Car-Accessory-247x296.png",
                        "title": "Car Accessory",
                        "actions": [{"type": "uri", "uri": "https://bestwellplastic.com/product-category/car-accessory/", "label": "View detail"}],
                        "imageBackgroundColor": "#000000",
                        "text": "ออกแบบเพื่อความแกร่ง ผลิตเพื่อความมั่นใจ"
                    },
                    {
                        "actions": [{"type": "uri", "uri": "https://bestwellplastic.com/product-category/pump-motor-parts/", "label": "View detail"}],
                        "defaultAction": {"uri": "https://bestwellplastic.com/product-category/pump-motor-parts/", "label": "View detail", "type": "uri"},
                        "text": "นวัตกรรมที่พัฒนาเพื่อการทำงานที่เสถียรและทรงพลัง",
                        "title": "Pump motor parts",
                        "imageBackgroundColor": "#000000",
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/pum-247x296.png"
                    },
                    {
                        "title": "a Christmas tree",
                        "imageBackgroundColor": "#000000",
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/crismas-247x296.png",
                        "defaultAction": {"type": "uri", "label": "View detail", "uri": "https://bestwellplastic.com/product-category/spare-a-christmas-tree/"},
                        "text": "ส่งต่อความสุขผ่านต้นคริสต์มาสที่สมบูรณ์แบบ",
                        "actions": [{"uri": "https://bestwellplastic.com/product-category/spare-a-christmas-tree/", "type": "uri", "label": "View detail"}]
                    },
                    {
                        "actions": [{"label": "View detail", "type": "uri", "uri": "https://bestwellplastic.com/product-category/agricultural/"}],
                        "defaultAction": {"type": "uri", "uri": "https://bestwellplastic.com/product-category/agricultural/", "label": "View detail"},
                        "title": "Agricultural",
                        "imageBackgroundColor": "#000000",
                        "text": "ขับเคลื่อนการเกษตรด้วยนวัตกรรมและดีไซน์ล้ำสมัย",
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/Agricultural-equipment-1-247x296.png"
                    },
                    {
                        "title": "Auto Parts",
                        "text": "ทนทานทุกการใช้งาน ยาวนานทุกการขับเคลื่อน",
                        "actions": [{"type": "uri", "label": "View detail", "uri": "https://bestwellplastic.com/product-category/auto-parts/"}],
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/Auto-Parts-247x296.png",
                        "imageBackgroundColor": "#000000",
                        "defaultAction": {"uri": "https://bestwellplastic.com/product-category/auto-parts/", "label": "View detail", "type": "uri"}
                    },
                    {
                        "title": "Packing media",
                        "text": "แข็งแกร่งทุกชิ้นงาน รองรับทุกสภาวะการใช้งาน",
                        "defaultAction": {"type": "uri", "label": "View detail", "uri": "https://bestwellplastic.com/product-category/packing-media/"},
                        "actions": [{"uri": "https://bestwellplastic.com/product-category/packing-media/", "label": "View detail", "type": "uri"}],
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2021/08/sddsfd-247x296.png",
                        "imageBackgroundColor": "#000000"
                    },
                    {
                        "thumbnailImageUrl": "https://bestwellplastic.com/wp-content/uploads/2018/09/Sanitary-product-247x296.png",
                        "actions": [{"type": "uri", "uri": "https://bestwellplastic.com/product-category/sanitary-product/", "label": "View detail"}],
                        "defaultAction": {"type": "uri", "uri": "https://bestwellplastic.com/product-category/sanitary-product/", "label": "View detail"},
                        "imageBackgroundColor": "#000000",
                        "title": "Sanitary product",
                        "text": "ก้าวล้ำด้วยเทคโนโลยี สะอาดทุกสัมผัส"
                    }
                ],
                "imageSize": "cover",
                "type": "carousel",
                "imageAspectRatio": "rectangle"
            },
            "altText": "this is a carousel template",
            "type": "template"
        }
        send_flex_message(user_id, flex_message)
    elif message_text == "กระบวนการผลิตสินค้า":
        flex_message = {
            "type": "flex",
            "altText": "Steps to order and design a mold",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "align": "center", "text": "ขั้นตอนการสั่งผลิตและออกแบบแม่พิมพ์", "size": "sm", "weight": "bold"},
                        {"type": "text", "margin": "sm", "text": "1. เปิด PO (Purchase Order)"},
                        {"type": "text", "margin": "sm", "text": "2. ชำระเงิน"},
                        {"type": "text", "margin": "sm", "text": "3. เริ่มการผลิต"},
                        {"type": "text", "margin": "sm", "text": "4. ใช้ระยะเวลาการผลิต 15-30 วัน"},
                        {"type": "text", "margin": "sm", "text": "5. บรรจุและจัดส่ง"},
                        {"margin": "lg", "type": "separator"},
                        {"layout": "vertical", "contents": [
                            {"type": "text", "align": "center", "weight": "bold", "size": "sm", "text": "เปลี่ยนไอเดียของคุณให้เป็นจริง", "color": "#1DB446"},
                            {"type": "text", "margin": "md", "align": "center", "color": "#1DB446", "weight": "bold", "size": "sm", "text": "ออกแบบและผลิตไปกับเรา"}
                        ], "margin": "xl", "type": "box"}
                    ]
                }
            }
        }
        send_flex_message(user_id, flex_message)
    else:
        send_message(user_id, "❌ ไม่พบตัวเลือก กรุณาพิมพ์ใหม่ เช่น 'บริการของเรา', 'สินค้าตัวอย่าง' หรือ 'กระบวนการผลิตสินค้า'")

def send_flex_message(user_id, flex_message):
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    message = {"to": user_id, "messages": [flex_message]}
    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=message)
    print(f"📤 ส่ง Flex Message ไปที่ {user_id}: {flex_message}")
    print(f"📡 LINE Response: {response.status_code} {response.text}")

# ------------------ ฟังก์ชันสำหรับการคำนวณต้นทุนและข้อมูลส่วนตัว ------------------

def start_questionnaire(user_id):
    USER_SESSIONS[user_id] = {"step": 1}
    send_message(
        user_id,
        "✨ เริ่มต้นการคำนวณต้นทุน ✨\n\n"
        "กรุณาเลือกวัสดุที่ต้องการผลิต:\n"
        "ABS, PC, Nylon, PP, PE, PVC, PET, PMMA, POM, PU"
    )

def process_response(user_id, message_text):
    if user_id not in USER_SESSIONS:
        send_message(user_id, "⚠️ กรุณาเริ่มคำนวณโดยพิมพ์ 'คำนวณราคา'")
        return
    step = USER_SESSIONS[user_id]["step"]
    if step == 1:
        # ใช้การเปรียบเทียบแบบไม่คำนึง case
        material_input = message_text.strip().upper()
        valid_materials = {mat.upper(): mat for mat in MATERIAL_COSTS.keys()}
        if material_input not in valid_materials:
            send_message(user_id,
                "❌ วัสดุไม่ถูกต้อง กรุณาเลือกจาก:\nABS, PC, Nylon, PP, PE, PVC, PET, PMMA, POM, PU")
            return
        USER_SESSIONS[user_id]["material"] = valid_materials[material_input]
        USER_SESSIONS[user_id]["step"] = 2
        send_message(user_id, "กรุณากรอกขนาดชิ้นงาน (กว้างxยาวxสูง) cm\nตัวอย่าง: 10.5x4.5x3")
    elif step == 2:
        USER_SESSIONS[user_id]["size"] = message_text
        USER_SESSIONS[user_id]["step"] = 3
        send_message(user_id, "กรุณากรอกจำนวนที่ต้องการผลิต (ตัวเลข)")
    elif step == 3:
        try:
            USER_SESSIONS[user_id]["quantity"] = int(message_text)
            USER_SESSIONS[user_id]["step"] = 4
            calculate_cost(user_id)
        except ValueError:
            send_message(user_id, "❌ กรุณากรอกจำนวนที่ถูกต้อง เช่น 100")
    elif step == 4:
        if message_text.strip() == "ต้องการ":
            send_message(user_id,
                "กรุณากรอกข้อมูลส่วนตัวของคุณ\nรูปแบบ: ชื่อ-สกุล, เบอร์โทร, ชื่อบริษัท, อีเมล")
            USER_SESSIONS[user_id]["step"] = 5
        else:
            send_message(user_id,
                "ไม่ได้เลือกใบเสนอราคา\nหากต้องการใบเสนอราคา 'กรุณาทำรายการ' ใหม่")
            del USER_SESSIONS[user_id]
    elif step == 5:
        info_parts = [part.strip() for part in message_text.split(",")]
        if len(info_parts) != 4:
            send_message(user_id,
                "❌ กรุณากรอกข้อมูลส่วนตัวให้ครบถ้วนในรูปแบบ:\nชื่อ-สกุล, เบอร์โทร, ชื่อบริษัท, อีเมล")
            return
        full_name, tel, company, email = info_parts
        USER_SESSIONS[user_id]["user_info"] = {
            "full_name": full_name,
            "tel": tel,
            "company": company,
            "email": email
        }
        try:
            write_to_sheet(
                user_id,
                USER_SESSIONS[user_id]["material"],
                USER_SESSIONS[user_id]["size"],
                USER_SESSIONS[user_id]["quantity"],
                USER_SESSIONS[user_id]["volume"],
                USER_SESSIONS[user_id]["weight_kg"],
                USER_SESSIONS[user_id]["total_cost"],
                full_name, tel, company, email
            )
            write_to_bigquery(
                user_id,
                USER_SESSIONS[user_id]["material"],
                USER_SESSIONS[user_id]["size"],
                USER_SESSIONS[user_id]["quantity"],
                USER_SESSIONS[user_id]["volume"],
                USER_SESSIONS[user_id]["weight_kg"],
                USER_SESSIONS[user_id]["total_cost"],
                full_name, tel, company, email
            )
            send_message(user_id,
                "🎉 ข้อมูลครบถ้วนแล้ว\nใบเสนอราคาจะส่งให้ทางอีเมลที่ระบุ\n(ภายใน 2-3 วันทำการ)")
            # เพิ่มส่วนส่งลิงก์ Google Form เพื่อรับข้อเสนอแนะ
            google_form_link = "https://forms.gle/8ytZXHVEmWPZAKmc7"  # เปลี่ยน URL ให้ถูกต้อง
            send_message(user_id,
                f"โปรดให้ข้อเสนอแนะกับเราได้ที่: {google_form_link}")
        except Exception as e:
            send_message(user_id,
                f"⚠️ เกิดข้อผิดพลาดในการบันทึกข้อมูลลง Google Sheets/BigQuery: {e}")
        del USER_SESSIONS[user_id]

def calculate_cost(user_id):
    material = USER_SESSIONS[user_id]["material"]
    size = USER_SESSIONS[user_id]["size"]
    quantity = USER_SESSIONS[user_id]["quantity"]
    try:
        dimensions = list(map(float, size.split("x")))
        if len(dimensions) != 3:
            raise ValueError("Invalid dimensions")
        volume = dimensions[0] * dimensions[1] * dimensions[2]
        USER_SESSIONS[user_id]["volume"] = volume
    except Exception as e:
        send_message(user_id,
            "❌ ขนาดชิ้นงานไม่ถูกต้อง\nโปรดใช้รูปแบบ เช่น 10.5x4.5x3")
        return
    material_cost_per_kg = MATERIAL_COSTS.get(material, 150)
    density = 1.05  # g/cm³
    weight_kg = (volume * density) / 1000
    total_cost = weight_kg * quantity * material_cost_per_kg
    USER_SESSIONS[user_id]["weight_kg"] = weight_kg
    USER_SESSIONS[user_id]["total_cost"] = total_cost
    result_text = (
        "✨ คำนวณต้นทุนสำเร็จ ✨\n\n"
        f"วัสดุ: {material}\n"
        f"ขนาด: {size} cm³\n"
        f"ปริมาตร: {volume:.2f} cm³\n"
        f"น้ำหนัก: {weight_kg:.2f} kg\n"
        f"จำนวน: {quantity} ชิ้น\n"
        f"ต้นทุนรวม: {total_cost:,.2f} บาท\n\n"
        "✅ ข้อมูลครบถ้วนแล้ว\n"
        "ต้องการใบเสนอราคาหรือไม่?\n"
        "หากต้องการให้พิมพ์ 'ต้องการ'"
    )
    send_message(user_id, result_text)
    USER_SESSIONS[user_id]["step"] = 4

def write_to_sheet(user_id, material, size, quantity, volume, weight_kg, total_cost, full_name, tel, company, email):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    credentials, project_id = google.auth.default(scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    values = [
        [user_id, material, size, quantity, volume, f"{weight_kg:.2f}", f"{total_cost:,.2f}", full_name, tel, company, email]
    ]
    body = {'values': values}
    range_name = f"{SHEET_NAME}!A1"
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption="RAW",
        body=body
    ).execute()
    updated_cells = result.get('updates', {}).get('updatedCells', 0)
    print(f"{updated_cells} cells appended to Google Sheets.")

def write_to_bigquery(user_id, material, size, quantity, volume, weight_kg, total_cost, full_name, tel, company, email):
    client = bigquery.Client()
    project = client.project
    table_id = f"{project}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    rows_to_insert = [{
        "user_id": user_id,
        "material": material,
        "size": size,
        "quantity": quantity,
        "volume": volume,
        "weight_kg": weight_kg,
        "total_cost": total_cost,
        "full_name": full_name,
        "tel": tel,
        "company": company,
        "email": email
    }]
    errors = client.insert_rows_json(table_id, rows_to_insert)
    if errors:
        raise Exception(f"BigQuery insert errors: {errors}")
    else:
        print("Data inserted into BigQuery successfully.")

def send_message(user_id, text):
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    message = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=message)
    print(f"📤 ส่งข้อความไปที่ {user_id}: {text}")
    print(f"📡 LINE Response: {response.status_code} {response.text}")

if __name__ != "__main__":
    # เมื่อถูก import (เช่นโดย WSGI server บน Cloud Run) ให้โหลด MATERIAL_COSTS ทันที
    MATERIAL_COSTS = load_material_costs()

if __name__ == "__main__":
    # สำหรับ local ให้โหลด MATERIAL_COSTS ก่อนเริ่มแอป
    MATERIAL_COSTS = load_material_costs()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
