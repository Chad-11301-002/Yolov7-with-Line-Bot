# YOLOv7 影像辨識 LINE Bot

此專案是一個使用 YOLOv7 進行物件偵測的 LINE Bot，透過上傳圖片，Bot 會回傳包含物件偵測結果的圖片與對應的物件熱量資訊。

## 功能介紹

- 使用 YOLOv7 模型進行物件偵測
- 支援多種食物類別辨識並提供對應熱量資訊
- 上傳圖片至 Imgur 並回傳圖片連結

## 系統需求

- Python 3.x
- Flask
- YOLOv7
- LINE Messaging API
- Imgur API
- SQLite3

## 安裝步驟

1. **克隆此專案到本地端**：
   git clone [https://github.com/your-username/yolov7-linebot.git](https://github.com/Chad-11301-002/Yolov7-with-Line-Bot.git)
   cd yolov7-linebot


2. 安裝相依套件：
   使用 pip 安裝所需的 Python 套件：  
   pip install -r requirements.txt
  

3. 設定環境變數：
   建立一個 .env 檔案，並填入下列環境變數：
   
   LINE_CHANNEL_ACCESS_TOKEN=你的LINE_CHANNEL_ACCESS_TOKEN  
   LINE_CHANNEL_SECRET=你的LINE_CHANNEL_SECRET  
   IMGUR_CLIENT_ID=你的IMGUR_CLIENT_ID  
   YOLO_PATH=你的YOLOv7程式路徑  
   WEIGHTS_PATH=你的YOLOv7模型權重路徑  
   DB_PATH=你的資料庫路徑  


5. 建立資料庫：  
   將包含食物熱量資訊的 foods.db 放入資料庫目錄，並確保其結構符合程式要求。


7. 啟動 Flask 應用程式：  
   使用下列指令啟動應用程式：  
   python app-cn.py


9. 設置 LINE Bot Webhook：  
   在 LINE Developers 中設置 Webhook URL，格式為：  
   https://你的伺服器域名/callback


## YOLOv7 使用方式  
本專案依賴 YOLOv7 來進行物件偵測。請確保已經安裝並配置 YOLOv7，並且已經準備好所需的模型權重檔案。  

範例  
使用者透過 LINE 傳送一張圖片，Bot 會回傳偵測到的物件和對應的熱量資訊，如下範例：  
  
輸入：一張包含食物的圖片  
回應：偵測後的圖片連結  
偵測結果：  
半熟蛋 (60 大卡)  
牛肉麵 (500 大卡)  
總熱量：560 大卡  
  
貢獻  
歡迎提交 Pull Request 或 Issues。如果您發現問題或有新功能需求，請隨時提交。  
  
授權  
本專案使用 MIT License。  


---


# YOLOv7 Image Detection LINE Bot

This project is a LINE Bot that uses the YOLOv7 model for object detection. Users can upload images, and the bot will return the detection results along with calorie information for the detected objects.

## Features

- Object detection using the YOLOv7 model
- Supports multiple food categories and provides corresponding calorie information
- Uploads images to Imgur and returns the image link

## Requirements

- Python 3.x
- Flask
- YOLOv7
- LINE Messaging API
- Imgur API
- SQLite3

## Installation Steps

1. **Clone the repository**:
   git clone [https://github.com/your-username/yolov7-linebot.git](https://github.com/Chad-11301-002/Yolov7-with-Line-Bot.git)
   cd yolov7-linebot


2. Install dependencies:  
   Use pip to install the required Python packages:  
   pip install -r requirements.txt  
  
  
4. Set up environment variables:  
   Create a .env file and add the following environment variables:  
  
   LINE_CHANNEL_ACCESS_TOKEN=your_LINE_CHANNEL_ACCESS_TOKEN    
   LINE_CHANNEL_SECRET=your_LINE_CHANNEL_SECRET    
   IMGUR_CLIENT_ID=your_IMGUR_CLIENT_ID    
   YOLO_PATH=your_YOLOv7_script_path  
   WEIGHTS_PATH=your_YOLOv7_model_weights_path  
   DB_PATH=your_database_path  
  
       
6. Set up the database:   
   Place the foods.db containing food calorie information in the database directory, ensuring it has the necessary structure.  
     
  
7. Start the Flask application:  
   Run the following command to start the app:  
   python app-en.py  
     
     
8. Set up the LINE Bot Webhook:  
   In LINE Developers, configure the Webhook URL in the following format:  
   https://your-server-domain/callback  
  
  
## YOLOv7 Usage  
This project relies on YOLOv7 for object detection. Make sure you have installed and configured YOLOv7, and have the necessary model weights ready.  
  
Example  
A user sends an image through LINE, and the bot responds with the detected objects and their calorie information, as shown below:  
  
Input: An image containing food
Response: A link to the processed image  
Detection result:  
Soft-boiled egg (60 kcal)  
Beef noodles (500 kcal)  
Total calories: 560 kcal  
  
Contributions  
Contributions via Pull Requests or Issues are welcome. If you find any issues or have feature requests, feel free to submit them.  
  
License  
This project is licensed under the MIT License.
