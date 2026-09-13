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
        
        # Lấy cả cột Date, Tonnes và Ounces (để tính toán cho chuẩn)
        df_sach = df[['Date', 'Tonnes of Gold', 'Total Ounces of Gold in the Trust']].copy()
        
        # Làm sạch dữ liệu rác (Holiday)
        df_sach['Tonnes of Gold'] = pd.to_numeric(df_sach['Tonnes of Gold'], errors='coerce')
        df_sach['Total Ounces of Gold in the Trust'] = pd.to_numeric(df_sach['Total Ounces of Gold in the Trust'], errors='coerce')
        
        df_sach = df_sach.dropna(subset=['Tonnes of Gold'])
        df_sach = df_sach.dropna(subset=['Total Ounces of Gold in the Trust'])
        
        df_sach['Date'] = pd.to_datetime(df_sach['Date'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Date'])
        
        # Sắp xếp thời gian
        df_sach = df_sach.sort_values(by='Date', ascending=True).reset_index(drop=True)
        
        # FIX LỖI LỆCH DỮ LIỆU: Tính Delta từ Ounce trước, sau đó mới chia ra Tấn
        # Hằng số chuẩn quốc tế: 1 Tonne = 32,150.746568 Ounces
        df_sach['Thay đổi Ounce'] = df_sach['Total Ounces of Gold in the Trust'].diff()
        df_sach['Thay đổi (Tấn)'] = (df_sach['Thay đổi Ounce'] / 32150.746568).round(2)
        
        # Điền 0 cho ngày đầu tiên
        df_sach['Thay đổi (Tấn)'] = df_sach['Thay đổi (Tấn)'].fillna(0)
        
        # Cắt lấy dữ liệu từ 2024 và dọn dẹp các cột thừa
        df_gan_day = df_sach[df_sach['Date'] >= '2024-01-01'].copy()
        df_gan_day = df_gan_day[['Date', 'Tonnes of Gold', 'Thay đổi (Tấn)']]
        
        if not df_gan_day.empty:
            df_gan_day.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
            print(f"[{datetime.datetime.now()}] HOÀN TẤT! Đã đóng gói thành công {len(df_gan_day)} ngày giao dịch ra file CSV.")
        else:
            print("CẢNH BÁO: Bảng dữ liệu trống!")
            
    else:
        print(f"Lỗi truy cập API! Mã lỗi: {response.status_code}")
        
except Exception as e:
    print(f"Lỗi hệ thống: {e}")
