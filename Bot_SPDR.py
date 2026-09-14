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
        
        df_sach = df[['Date', 'Tonnes of Gold', 'Total Ounces of Gold in the Trust']].copy()
        df_sach['Tonnes of Gold'] = pd.to_numeric(df_sach['Tonnes of Gold'], errors='coerce')
        df_sach['Total Ounces'] = pd.to_numeric(df_sach['Total Ounces of Gold in the Trust'], errors='coerce')
        
        df_sach = df_sach.dropna(subset=['Tonnes of Gold', 'Total Ounces'])
        df_sach['Date'] = pd.to_datetime(df_sach['Date'], errors='coerce')
        df_sach = df_sach.dropna(subset=['Date'])
        
        df_sach = df_sach.sort_values(by='Date', ascending=True).reset_index(drop=True)
        df_sach['Thay_Doi_Ounce'] = df_sach['Total Ounces'].diff()
        
        df_sach['hold'] = df_sach['Tonnes of Gold'].round(2)
        df_sach['ton'] = (df_sach['Thay_Doi_Ounce'] / 32150.746568).round(2)
        df_sach['ton'] = df_sach['ton'].fillna(0)
        
        # --- BẢN VÁ LỖI YAHOO FINANCE ---
        print("Đang tải dữ liệu Giá vàng (GC=F) từ Yahoo Finance...")
        try:
            # Dùng Ticker().history() để vượt tường lửa thay vì download()
            gold_ticker = yf.Ticker("GC=F")
            gold = gold_ticker.history(start="2024-01-01")
            
            if not gold.empty:
                gold_close = gold[['Close']].reset_index()
                gold_close.columns = ['Date', 'Gold_Price']
                gold_close['Date'] = pd.to_datetime(gold_close['Date']).dt.tz_localize(None).dt.normalize()
                
                df_sach = pd.merge(df_sach, gold_close, on='Date', how='left')
                df_sach['Gold_Price'] = df_sach['Gold_Price'].ffill().bfill()
                
                # Tính USD Flow
                df_sach['usd_flow'] = (df_sach['Thay_Doi_Ounce'] * df_sach['Gold_Price']).round(2)
            else:
                print("[LỖI] Yahoo Finance trả về dữ liệu rỗng!")
                df_sach['usd_flow'] = 0
        except Exception as e:
            print(f"[LỖI] Không thể tải giá vàng: {e}")
            df_sach['usd_flow'] = 0
            
        df_sach['usd_flow'] = df_sach['usd_flow'].fillna(0)
        
        df_gan_day = df_sach[df_sach['Date'] >= '2024-01-01'].copy()
        df_gan_day = df_gan_day[['Date', 'hold', 'ton', 'usd_flow']]
        
        if not df_gan_day.empty:
            df_gan_day.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
            print(f"[{datetime.datetime.now()}] HOÀN TẤT! Đã đóng gói ra {FILE_NAME}.")
            
    else:
        print(f"Lỗi truy cập API SPDR! Mã lỗi: {response.status_code}")
except Exception as e:
    print(f"Lỗi hệ thống: {e}")
