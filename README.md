# line-webhook-bot

This project uses a Virtual Environment (venv) to manage Python libraries in VS Code.

## step

:one: สร้างโปรเจค และนำขึ้น Git สำหรับเชื่อมต่อกับ Google Cloud เพื่อ run โปรเจคผ่าน google cloud  
:two: สร้างโปรเจคบน Google Cloud เพื่อเชื่อมต่อกับโปรเจคบน Git  

## step dev code

:one: create file main.py สำหรับสร้าง code หลักในการเชื่อมต่อกับ line หรือ flow ต่างๆ ที่ต้องการ  
:two: create file requirement.txt สำหรับระบุ library ที่จำเป็นต่อโปรเจค  
:three: สร้าง environment สำหรับติดตั้ง library ที่จำเป็น [วิธีการสร้าง environment](#-Installation-and-Setup)!  
:four: run คำสั่ง

```bash
pip install -r requirements.txt
```

>เพื่อติดตั้ง package ทั้งหมด  

:sos: กรณีที่ติดตั้งแล้วแต่ยังไม่สามารถใช้งาน library ได้ ให้ตรวจสอบให้แน่ใจว่า โปรเจคเลือกใช้งาน environment ถูกต้อง

:five: เมื่อดำเนินการขั้นตอน 1-4 เรียบร้อยแล้ว ให้ push project ขึ้น git ด้วยคำสั่ง

```bash
git status
git add .
git commit -am "code main.py and library require"
git push
```

---

### :triangular_flag_on_post: Installation and Setup

:one: **Clone or Download the Project**

```bash
git clone https://github.com/chaoguaii/line-webhook-bot.git
cd line-webhook-bot
```

:two: **Create a Virtual Environment**

- **Windows (PowerShell):**

```bash
python -m venv venv
```

- **Mac/Linux:**

```bash
python3 -m venv venv
```

:three: **Activate the Virtual Environment**

- **Windows (PowerShell):**

```bash
  venv\Scripts\Activate
```

- **Mac/Linux:**

```bash
  source venv/bin/activate
```

> Once activated successfully, you will see (venv) prefixed to the command line.

:four: **Install Dependencies**

```bash
pip install -r requirements.txt
```

:five: **Configure the Python Interpreter in VS Code**

- Press  `Ctrl + Shift + P`
- Type `"Python: Select Interpreter"`
- Select `venv` (for example, `.\venv\Scripts\python.exe` or `./venv/bin/python`)

### :package: Key Commands

| Command                                  | Description                             |
|-----------------------------------------|--------------------------------------|
| `python -m venv venv`                     | Create Virtual Environment              |
| `venv\Scripts\Activate`                    | Activate venv (Windows)             |
| `source venv/bin/activate`                 | Activate venv (Mac/Linux)            |
| `deactivate`                              | Deactivate venv                      |
| `pip install -r requirements.txt`         | Install dependencies                 |
| `pip freeze > requirements.txt`           | Save dependencies                  |

### :pencil: Note

If you encounter an issue with activating `venv` on Windows, run the following command:

```bash
Set-ExecutionPolicy Unrestricted -Scope Process
```
