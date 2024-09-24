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

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get LINE Bot credentials from environment variables
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Define the directory to store detected images
IMAGES_DIR = 'static/images'
os.makedirs(IMAGES_DIR, exist_ok=True)

# Create a task queue for image processing
image_queue = queue.Queue()

# Background thread to process images
def process_images():
    while True:
        task = image_queue.get()
        if task is None:
            break
        image_path, event = task
        process_single_image(image_path, event)
        image_queue.task_done()

# Start background thread
threading.Thread(target=process_images, daemon=True).start()

# Callback function for the LINE Bot webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Handle image message events
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        image_data = BytesIO(message_content.content)
        image = Image.open(image_data)

        filename = f"{uuid.uuid4()}.jpg"
        image_path = os.path.join(IMAGES_DIR, filename)
        image.save(image_path)

        # Add image processing task to the queue
        image_queue.put((image_path, event))

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Your image has been received and is being processed..."))
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="An error occurred while processing the image, please try again."))

# Database function to query food calories
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

# Function to process a single image
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
                    TextSendMessage(text=f"Recognition result: {labels}\nTotal calories: {total_calories} kcal\n*The calorie information is for reference only as ingredients and preparation methods may vary*")
                ])
            else:
                line_bot_api.push_message(event.source.user_id, TextSendMessage(text="Failed to upload image to Imgur, please try again"))
        else:
            line_bot_api.push_message(event.source.user_id, TextSendMessage(text="No result image generated, please try again"))
    except Exception as e:
        logger.error(f"Error processing single image: {e}")
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text="An error occurred while processing the image, please try again."))
    finally:
        # Clean up temporary files
        cleanup_files(image_path, result_image_path, labels_path)

# Function to run YOLO detection
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

# Function to upload image to Imgur
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
            logger.error(f"Imgur upload failed: {response.text}")
            return None

# Function to extract labels from YOLO detection results
def extract_labels_from_results(labels_path):
    class_names = {
        0: 'Soft-boiled egg', 1: 'Meatball', 2: 'Beef noodles', 3: 'Braised cabbage', 4: 'Braised pork rice',
        5: 'Mushroom chicken soup', 6: 'Cucumber salad', 7: 'Cold noodles', 8: 'Fried chicken cutlet', 9: 'Egg pancake',
        10: 'Fish soup', 11: 'Fried instant noodles', 12: 'Fried rice noodles', 13: 'Sponge gourd', 14: 'Chicken rice'
    }

    label_units = []
    total_calories = 0

    if os.path.exists(labels_path):
        with open(labels_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                class_id = int(parts[0])
                label = class_names.get(class_id, 'Unknown')
                calories, unit = get_calories_by_name(label)  # Get calorie data from the database
                if calories:
                    total_calories += calories
                    label_units.append(f"{label} ({calories} {unit})")
                else:
                    label_units.append(f"{label} (Calorie info not available)")

    return ', '.join(label_units), total_calories, 'kcal'

# Function to clean up temporary files
def cleanup_files(*file_paths):
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
