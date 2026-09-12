import requests
import pandas as pd
import io
import datetime

FILE_NAME = "SPDR_Data_MT5.csv"
url = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"

# Cập nhật Header xịn hơn để đóng giả trình duyệt web đời mới nhất
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

try:
    print(f"[{datetime.datetime.now()}] Bắt đầu kết nối đến API SPDR...")
    
    # NÂNG CẤP 1: Thêm timeout=20 để tự ngắt nếu server SPDR bị sập, tránh treo GitHub
    response = requests.get(url, headers=headers, timeout=20)
    
    if response.status_code == 200:
        print("Tải file Excel thành công! Đang tiến hành làm sạch...")
        
        # Đọc dữ liệu
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='US GLD Historical Archive', header=0)
        
        # Chỉ lấy 2 cột cần thiết để tiết kiệm RAM
        df_sach = df[['Date', 'Tonnes of Gold']].copy()
        
        # Xử lý dữ liệu bẩn (Ép chữ US Holiday thành NaN, sau đó xóa)
        df_sach['Tonnes of Gold'] = pd.to_numeric(df_sach['Tonnes of Gold'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Tonnes of Gold'])
        
        # Chuẩn hóa định dạng thời gian
        df_sach['Date'] = pd.to_datetime(df_sach['Date'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Date'])
        
        # NÂNG CẤP 2 (QUAN TRỌNG NHẤT): Ép bảng dữ liệu sắp xếp theo Thời gian (Từ cũ tới mới)
        # Việc này đảm bảo hàm diff() luôn lấy (Ngày hôm nay - Ngày hôm qua) cực kỳ chuẩn xác
        df_sach = df_sach.sort_values(by='Date', ascending=True).reset_index(drop=True)
        
        # Tính toán Dòng tiền (VSA)
        df_sach['Thay đổi (Tấn)'] = df_sach['Tonnes of Gold'].diff().round(2)
        
        # NÂNG CẤP 3: Xử lý giá trị trống ở dòng ngày đầu tiên của lịch sử
        df_sach['Thay đổi (Tấn)'] = df_sach['Thay đổi (Tấn)'].fillna(0)
        
        # Cắt lấy dữ liệu từ năm 2024 trở đi
        df_gan_day = df_sach[df_sach['Date'] >= '2024-01-01'].copy()
        
        # NÂNG CẤP 4: Lớp bảo vệ cuối cùng - Kiểm tra xem bảng có dữ liệu không trước khi xuất file
        if not df_gan_day.empty:
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
