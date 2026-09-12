import requests
import pandas as pd
import io
import datetime

# Tên file sẽ được tạo ra ngay trên mây (GitHub)
FILE_NAME = "SPDR_Data_MT5.csv"

url = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    print("Đang kết nối đến quỹ SPDR từ Đám mây...")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        
        print("Tải dữ liệu thành công! Đang xử lý...")
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='US GLD Historical Archive', header=0)
        
        # Làm sạch dữ liệu
        df_sach = df[['Date', 'Tonnes of Gold']].dropna()
        df_sach['Tonnes of Gold'] = pd.to_numeric(df_sach['Tonnes of Gold'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Tonnes of Gold'])
        df_sach['Date'] = pd.to_datetime(df_sach['Date'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Date'])
        
        # Tính toán VSA
        df_sach['Thay đổi (Tấn)'] = df_sach['Tonnes of Gold'].diff().round(2)
        df_gan_day = df_sach[df_sach['Date'] >= '2024-01-01'].copy()
        
        # Lưu file CSV trực tiếp lên GitHub
        df_gan_day.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
        
        print(f"[{datetime.datetime.now()}] HOÀN TẤT! Đã tạo file CSV trên Đám mây.")
    else:
        print(f"Lỗi mạng! Mã lỗi: {response.status_code}")
except Exception as e:
    print(f"Lỗi hệ thống: {e}")
