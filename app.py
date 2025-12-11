from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# ***************************************************************
# ******* ⚠️ คำเตือน: ค่าเหล่านี้เป็นค่าคาดเดาจาก Mobile View *******
# ******* หากโค้ดล้มเหลว (โดยเฉพาะ Report) โปรดตรวจสอบค่าอีกครั้ง *******
# ***************************************************************
USERNAME_FIELD_ID = "email"        # ID เดิม: โค้ดถูกแก้ให้ใช้ By.NAME, "email"
PASSWORD_FIELD_ID = "pass"         # ID เดิม: โค้ดถูกแก้ให้ใช้ By.NAME, "pass"
LOGIN_BUTTON_XPATH = '//button[@name="login"]' # XPath ของปุ่ม Login
LIKE_BUTTON_XPATH = '//div[@aria-label="ถูกใจ"]' # XPath ของปุ่ม Like (จะไม่ถูกใช้หากเลือก 'report')
REPORT_MENU_BUTTON_XPATH = '//div[@aria-label="การตั้งค่าโปรไฟล์"]' # ปุ่ม 'จุดสามจุด' (โอกาสผิดพลาดสูง)
REPORT_OPTION_XPATH = '//span[text()="ค้นหาการสนับสนุนหรือรายงานโปรไฟล์"]' # ตัวเลือกรายงาน (อิงข้อความตรงๆ)
# ***************************************************************

app = Flask(__name__)

# โค้ด HTML สำหรับหน้าเว็บไซต์ (Frontend Template)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Facebook Automation Tool</title>
<style>
    body { font-family: Arial, sans-serif; padding: 20px; background-color: #f0f2f5; }
    .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,.1); }
    h2 { color: #1877f2; }
    input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 8px 0; display: inline-block; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
    button { background-color: #42b72a; color: white; padding: 12px 20px; margin-top: 15px; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; }
    button:hover { background-color: #36a420; }
    pre { background-color: #ffebe8; color: #cc0000; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; border: 1px solid #cc0000; }
    .warning { color: red; font-weight: bold; margin-bottom: 15px; }
</style>
</head>
<body>
    <div class="container">
        <h2>Facebook Automation (Render.com)</h2>
        <p class="warning">🚨 คำเตือน: การใช้เครื่องมือนี้เสี่ยงต่อการถูกระงับบัญชี (ผิดกฎ Facebook)</p>
        <form method="POST" action="/run_automation">
            <label>Username (เบอร์/อีเมล):</label>
            <input type="text" name="username" required value="runcodev1@gmail.com"> 
            
            <label>Password (รหัสผ่าน):</label>
            <input type="password" name="password" required value="test_2025"> <label>ลิงก์เป้าหมาย (โพสต์/โปรไฟล์):</label>
            <input type="text" name="target_link" required>
            
            <label>เลือกฟังก์ชัน:</label><br>
            <input type="radio" name="action" value="like" checked> 1. กดไลค์โพสต์<br>
            <input type="radio" name="action" value="report"> 2. รายงานโปรไฟล์<br><br>
            
            <button type="submit">เริ่มทำงานอัตโนมัติ</button>
        </form>
        <h3>ผลลัพธ์:</h3>
        <pre>{{ message }}</pre>
    </div>
</body>
</html>
"""

def get_webdriver():
    """ตั้งค่า WebDriver สำหรับสภาพแวดล้อมเซิร์ฟเวอร์ Headless"""
    chrome_options = Options()
    
    # การตั้งค่าที่จำเป็นสำหรับ Render.com และ Headless Linux
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080") 
    
    try:
        # Render/Heroku Buildpack มักจะติดตั้ง Chrome ไว้ใน Path
        return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return None

def run_selenium_task(username, password, target_link, action):
    driver = get_webdriver()
    if driver is None:
        return "❌ ข้อผิดพลาด: ไม่สามารถเริ่มต้น WebDriver ได้ (ตรวจสอบการตั้งค่า Build Command)"
        
    wait = WebDriverWait(driver, 15)
    result_message = ""

    try:
        # 1. เข้าสู่ระบบ (ใช้ Mobile URL)
        driver.get("https://m.facebook.com") 
        
        # รอกรอก Username และ Password (ใช้ By.NAME แทน By.ID)
        wait.until(EC.presence_of_element_located((By.NAME, USERNAME_FIELD_ID))).send_keys(username)
        driver.find_element(By.NAME, PASSWORD_FIELD_ID).send_keys(password)
        driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH).click()
        
        time.sleep(5) 

        if driver.current_url.startswith("https://m.facebook.com/login"):
            return "❌ การเข้าสู่ระบบล้มเหลว! (ติด 2FA/CAPTCHA หรือรหัสผ่านผิด) ลองตรวจสอบรหัสผ่านอีกครั้ง"

        # 2. ไปยังลิงก์เป้าหมาย
        driver.get(target_link)
        time.sleep(3) 

        # 3. เลือกฟังก์ชัน
        if action == "like":
            # โค้ดสำหรับ 'กดไลค์'
            like_button = wait.until(EC.element_to_be_clickable((By.XPATH, LIKE_BUTTON_XPATH)))
            like_button.click()
            result_message = f"✅ กดไลค์โพสต์: {target_link} สำเร็จ!"

        elif action == "report":
            # โค้ดสำหรับ 'รายงาน'
            report_menu = wait.until(EC.element_to_be_clickable((By.XPATH, REPORT_MENU_BUTTON_XPATH)))
            report_menu.click()
            
            report_option = wait.until(EC.element_to_be_clickable((By.XPATH, REPORT_OPTION_XPATH)))
            report_option.click()
            
            # *********** ข้ามขั้นตอนการคลิกรายงานที่เหลือ ***********
            result_message = f"✅ เริ่มต้นการรายงานโปรไฟล์: {target_link} (เข้าสู่หน้าต่างรายงานแล้ว แต่ต้องมีการคลิกเหตุผลต่อในโค้ด)"

    except Exception as e:
        result_message = f"❌ เกิดข้อผิดพลาดในการรันโค้ด: {e}"
        result_message += "\n(โค้ดล้มเหลวในการหา Element หรือถูก Facebook บล็อก)"

    finally:
        if driver:
            driver.quit() 
        return result_message

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, message="กรุณากรอกข้อมูลและเลือกฟังก์ชัน")

@app.route('/run_automation', methods=['POST'])
def run_automation():
    username = request.form['username']
    password = request.form['password']
    target_link = request.form['target_link']
    action = request.form['action']
    
    message = run_selenium_task(username, password, target_link, action)
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
