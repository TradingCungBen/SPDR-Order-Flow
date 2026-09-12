import requests
import pandas as pd
import io
import datetime

FILE_NAME = "SPDR_Data_MT5.csv"
url = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

try:
    print(f"[{datetime.datetime.now()}] Bắt đầu kết nối đến API SPDR...")
    response = requests.get(url, headers=headers, timeout=20)
    
    if response.status_code == 200:
        print("Tải file Excel thành công! Đang tiến hành làm sạch...")
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='US GLD Historical Archive', header=0)
        
        # 1. Trích xuất đúng 2 cột cốt lõi
        df_sach = df[['Date', 'Tonnes of Gold']].copy()
        
        # 2. Làm sạch và định dạng
        df_sach['Tonnes of Gold'] = pd.to_numeric(df_sach['Tonnes of Gold'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Tonnes of Gold'])
        df_sach['Date'] = pd.to_datetime(df_sach['Date'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Date'])
        
        # 3. Sắp xếp ngày từ quá khứ đến hiện tại (Bắt buộc để tính VSA chuẩn 100%)
        df_sach = df_sach.sort_values(by='Date', ascending=True).reset_index(drop=True)
        
        # 4. Tính toán mức Gom/Xả hàng ngày
        df_sach['Thay đổi (Tấn)'] = df_sach['Tonnes of Gold'].diff().round(2)
        df_sach['Thay đổi (Tấn)'] = df_sach['Thay đổi (Tấn)'].fillna(0)
        
        # 5. Lọc dữ liệu từ 2024 để đưa vào MT5
        df_gan_day = df_sach[df_sach['Date'] >= '2024-01-01'].copy()
        
        if not df_gan_day.empty:
            # Ghi ra file CSV tinh gọn
            df_gan_day.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
            print(f"[{datetime.datetime.now()}] HOÀN TẤT! Đã đóng gói thành công {len(df_gan_day)} ngày giao dịch ra file CSV.")
        else:
            print("CẢNH BÁO: Bảng dữ liệu trống, không có thông tin từ năm 2024!")
            
    else:
        print(f"Lỗi truy cập API! Server từ chối với Mã lỗi HTTP: {response.status_code}")
        
except requests.exceptions.Timeout:
    print("Lỗi mạng: Quá thời gian chờ (Timeout). Máy chủ SPDR phản hồi quá chậm.")
except Exception as e:
    print(f"Lỗi hệ thống nghiêm trọng: {e}")
