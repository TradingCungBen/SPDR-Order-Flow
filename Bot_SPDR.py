import requests
import pandas as pd
import io
import datetime
import yfinance as yf

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

        # 1. Trích xuất và làm sạch dữ liệu
        df_sach = df[['Date', 'Tonnes of Gold', 'Total Ounces of Gold in the Trust']].copy()

        df_sach['Tonnes of Gold'] = pd.to_numeric(df_sach['Tonnes of Gold'], errors='coerce')
        df_sach['Total Ounces'] = pd.to_numeric(df_sach['Total Ounces of Gold in the Trust'], errors='coerce')

        df_sach = df_sach.dropna(subset=['Tonnes of Gold', 'Total Ounces'])
        df_sach['Date'] = pd.to_datetime(df_sach['Date'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Date'])

        # Sắp xếp thời gian
        df_sach = df_sach.sort_values(by='Date', ascending=True).reset_index(drop=True)

        # 2. Tính toán các cột tiêu chuẩn: hold, ton
        df_sach['Thay_Doi_Ounce'] = df_sach['Total Ounces'].diff()

        df_sach['hold'] = df_sach['Tonnes of Gold'].round(2)
        df_sach['ton'] = (df_sach['Thay_Doi_Ounce'] / 32150.746568).round(2)
        df_sach['ton'] = df_sach['ton'].fillna(0)

        # 3. Tích hợp Dữ liệu Giá Vàng (yfinance) để tính USD Flow
        print("Đang tải dữ liệu Giá vàng (XAUUSD) từ Yahoo Finance...")
        gold = yf.download("XAUUSD=X", start="2024-01-01", progress=False)

        # Khắc phục triệt để cấu trúc MultiIndex của yfinance
        gold_close = pd.DataFrame(gold['Close']).reset_index()
        gold_close.columns = ['Date', 'Gold_Price']
        gold_close['Date'] = pd.to_datetime(gold_close['Date']).dt.tz_localize(None).dt.normalize()

        # 4. Ghép dữ liệu và Tính usd_flow
        df_sach = pd.merge(df_sach, gold_close, on='Date', how='left')

        # Điền giá vàng cho các ngày bị khuyết (Lấp bằng giá ngày hôm trước)
        df_sach['Gold_Price'] = df_sach['Gold_Price'].ffill().bfill()

        # Công thức dòng tiền: Lượng Ounce thay đổi * Giá Vàng
        df_sach['usd_flow'] = (df_sach['Thay_Doi_Ounce'] * df_sach['Gold_Price']).round(2)
        df_sach['usd_flow'] = df_sach['usd_flow'].fillna(0)

        # 5. Cắt dữ liệu từ 2024 và đổi tên cột theo form chuẩn
        df_gan_day = df_sach[df_sach['Date'] >= '2024-01-01'].copy()

        # Sắp xếp đúng 4 cột chuẩn quốc tế
        df_gan_day = df_gan_day[['Date', 'hold', 'ton', 'usd_flow']]

        if not df_gan_day.empty:
            df_gan_day.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
            print(f"[{datetime.datetime.now()}] HOÀN TẤT! Đã đóng gói {len(df_gan_day)} ngày giao dịch ra {FILE_NAME}.")
        else:
            print("CẢNH BÁO: Bảng dữ liệu trống!")

    else:
        print(f"Lỗi truy cập API! Mã lỗi: {response.status_code}")

except Exception as e:
    print(f"Lỗi hệ thống: {e}")
