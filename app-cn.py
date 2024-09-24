import os
import subprocess
import uuid
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage, ImageSendMessage
from PIL import Image
from io import BytesIO
import requests
import threading
import queue
from dotenv import load_dotenv
import sqlite3

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 從環境變數獲取 LINE Bot 憑證
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 定義存儲檢測圖像的目錄
IMAGES_DIR = 'static/images'
os.makedirs(IMAGES_DIR, exist_ok=True)

# 創建圖像處理任務隊列
image_queue = queue.Queue()

# 處理圖像的背景線程
def process_images():
    while True:
        task = image_queue.get()
        if task is None:
            break
        image_path, event = task
        process_single_image(image_path, event)
        image_queue.task_done()

# 啟動背景線程
threading.Thread(target=process_images, daemon=True).start()

# LINE Bot 的 Webhook 回調函數
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    logger.info(f"請求體: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理圖片訊息事件
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        image_data = BytesIO(message_content.content)
        image = Image.open(image_data)

        filename = f"{uuid.uuid4()}.jpg"
        image_path = os.path.join(IMAGES_DIR, filename)
        image.save(image_path)

        # 將圖像處理任務放入隊列
        image_queue.put((image_path, event))

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您的圖片已收到，正在處理中..."))
    except Exception as e:
        logger.error(f"處理圖片時出錯: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="處理圖片時出錯，請重試"))

# 查詢食物熱量的數據庫函數
def get_calories_by_name(name):
    
    db_path = os.getenv('DB_PATH')
    conn = sqlite3.connect(f'{db_path}/foods.db')

    cursor = conn.cursor()

    cursor.execute("SELECT calories, unit FROM foods WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0], result[1]
    else:
        return None, None

# 處理單張圖像的函數
def process_single_image(image_path, event):
    try:
        result_image_path, labels_path = run_yolo_detection(image_path)
        
        if os.path.exists(result_image_path):
            imgur_url = upload_to_imgur(result_image_path)
            
            if imgur_url:
                labels, total_calories, unit = extract_labels_from_results(labels_path)

                image_message = ImageSendMessage(
                    original_content_url=imgur_url,
                    preview_image_url=imgur_url
                )
                line_bot_api.push_message(event.source.user_id, [
                    image_message,
                    TextSendMessage(text=f"識別結果: {labels}\n總熱量: {total_calories} kcal\n*因餐點製作材料與方式皆有不同\n熱量資訊僅為參考*")
                ])
            else:
                line_bot_api.push_message(event.source.user_id, TextSendMessage(text="上傳圖片到 Imgur 失敗，請重試"))
        else:
            line_bot_api.push_message(event.source.user_id, TextSendMessage(text="未生成結果圖片，請重試"))
    except Exception as e:
        logger.error(f"處理單張圖片時出錯: {e}")
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text="處理圖片時出錯，請重試"))
    finally:
        # 清理臨時文件
        cleanup_files(image_path, result_image_path, labels_path)

# 執行 YOLO 模型進行物件偵測
def run_yolo_detection(image_path):
    yolo_path = os.getenv('YOLO_PATH')
    weights_path = os.getenv('WEIGHTS_PATH')
    
    command = f"python {yolo_path}/detect.py --weights {weights_path} --source {image_path} --save-txt --save-conf"
    subprocess.run(command, shell=True, check=True)

    result_dir = os.path.join('runs', 'detect')
    exp_folders = [f for f in os.listdir(result_dir) if os.path.isdir(os.path.join(result_dir, f))]
    latest_exp_folder = max(exp_folders, key=lambda f: os.path.getctime(os.path.join(result_dir, f)))

    result_image_path = os.path.join(result_dir, latest_exp_folder, os.path.basename(image_path))
    labels_path = os.path.join(result_dir, latest_exp_folder, 'labels', f'{os.path.splitext(os.path.basename(image_path))[0]}.txt')

    return result_image_path, labels_path

# 上傳圖片到 Imgur
def upload_to_imgur(image_path):
    url = "https://api.imgur.com/3/upload"
    
    with open(image_path, "rb") as image_file:
        files = {'image': image_file}
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}',
        }
        response = requests.post(url, files=files, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data['data']['link']
        else:
            logger.error(f"Imgur 上傳失敗: {response.text}")
            return None

# 從 YOLO 檢測結果提取標籤
def extract_labels_from_results(labels_path):
    class_names = {
        0: '半熟蛋', 1: '肉圓', 2: '牛肉麵', 3: '滷白菜', 4: '滷肉飯',
        5: '香菇雞湯', 6: '涼拌小黃瓜', 7: '涼麵', 8: '炸雞排', 9: '蛋餅',
        10: '土魠魚羹', 11: '炒泡麵', 12: '炒米粉', 13: '絲瓜', 14: '雞肉飯'
    }

    label_units = []
    total_calories = 0

    if os.path.exists(labels_path):
        with open(labels_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                class_id = int(parts[0])
                label = class_names.get(class_id, '未知')
                calories, unit = get_calories_by_name(label)  # 從資料庫獲取熱量數據
                if calories:
                    total_calories += calories
                    label_units.append(f"{label} ({calories} {unit})")
                else:
                    label_units.append(f"{label} (熱量信息不存在)")

    return ', '.join(label_units), total_calories, '大卡'

# 清理臨時文件
def cleanup_files(*file_paths):
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"清理文件時出錯 {file_path}: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
