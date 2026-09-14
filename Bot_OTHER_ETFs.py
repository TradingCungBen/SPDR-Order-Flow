import requests
import pandas as pd
import io
import datetime
import yfinance as yf

FILE_NAME = "OTHER_ETFs_MT5.csv"
STATUS_FILE = "ETF_Status.txt" 

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*'
}

fund_status = {}

def get_gldm():
    try:
        url = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gldm&exchange=NYSE&lang=en"
        res = requests.get(url, headers=headers, timeout=20)
        
        if res.status_code == 200:
            excel_data = pd.read_excel(io.BytesIO(res.content), sheet_name=None)
            df = pd.DataFrame()
            
            for sheet_name, sheet_df in excel_data.items():
                cols = [str(c).strip().lower() for c in sheet_df.columns]
                if 'date' in cols and any('ounce' in c and 'total' in c for c in cols):
                    df = sheet_df
                    break
            
            if df.empty:
                fund_status['GLDM'] = "LOI: Khong tim thay cot Total Ounce"
                return pd.DataFrame()
            
            date_col = [c for c in df.columns if str(c).strip().lower() == 'date'][0]
            ounce_col = [c for c in df.columns if 'ounce' in str(c).strip().lower() and 'total' in str(c).strip().lower()][0]
            
            df['Total Ounces'] = pd.to_numeric(df[ounce_col], errors='coerce')
            df['Date'] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=['Date', 'Total Ounces'])
            df = df.rename(columns={'Total Ounces': 'Ounces_GLDM'})
            fund_status['GLDM'] = "OK"
            return df[['Date', 'Ounces_GLDM']]
        else:
            fund_status['GLDM'] = f"LOI API: {res.status_code}"
    except Exception as e:
        fund_status['GLDM'] = f"LOI: {str(e)[:20]}"
    return pd.DataFrame()

def get_iau():
    try:
        url = "https://www.ishares.com/us/products/239561/ishares-gold-trust-fund/1467271812596.ajax?fileType=csv&fileName=IAU_holdings&dataType=fund"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text), skiprows=9)
            df['Date'] = pd.to_datetime(df['As Of'], errors='coerce')
            df['Ounces_IAU'] = pd.to_numeric(df['Ounces'], errors='coerce')
            df = df.dropna(subset=['Date', 'Ounces_IAU'])
            fund_status['IAU'] = "OK"
            return df[['Date', 'Ounces_IAU']]
    except Exception as e:
        fund_status['IAU'] = f"LOI: {str(e)[:20]}"
    return pd.DataFrame()

def get_sgol():
    fund_status['SGOL'] = "Chua hoat dong"
    return pd.DataFrame()

# ================= CHƯƠNG TRÌNH CHÍNH =================
df_gldm = get_gldm()
df_iau  = get_iau()
df_sgol = get_sgol()

now_str = datetime.datetime.now().strftime('%Y.%m.%d %H:%M')
status_msg = f"Cap nhat: {now_str} UTC | "
for fund, status in fund_status.items():
    status_msg += f"[{fund}: {status}] "

with open(STATUS_FILE, "w", encoding="utf-8") as f:
    f.write(status_msg)

df_master = df_gldm.copy()

if not df_master.empty:
    if not df_iau.empty:
        df_master = pd.merge(df_master, df_iau, on='Date', how='left')
    else:
        df_master['Ounces_IAU'] = 0

    if not df_sgol.empty:
        df_master = pd.merge(df_master, df_sgol, on='Date', how='left')
    else:
        df_master['Ounces_SGOL'] = 0

    # 1. Tính Tổng Ounce
    df_master['Total_Ounces_ROW'] = df_master['Ounces_GLDM'].fillna(0) + df_master['Ounces_IAU'].fillna(0) + df_master['Ounces_SGOL'].fillna(0)
    df_master = df_master.sort_values(by='Date', ascending=True).reset_index(drop=True)
    df_master['Thay_Doi_Ounces'] = df_master['Total_Ounces_ROW'].diff()

    # 2. Tính các cột chuẩn (hold, ton)
    df_master['hold'] = (df_master['Total_Ounces_ROW'] / 32150.746568).round(2)
    df_master['ton'] = (df_master['Thay_Doi_Ounces'] / 32150.746568).round(2)
    df_master['ton'] = df_master['ton'].fillna(0)

    # 3. Tích hợp dữ liệu Giá Vàng để tính USD Flow
    print("Đang tải dữ liệu Giá vàng (XAUUSD) từ Yahoo Finance...")
    try:
        gold = yf.download("XAUUSD=X", start="2024-01-01", progress=False)
        gold_close = pd.DataFrame(gold['Close']).reset_index()
        gold_close.columns = ['Date', 'Gold_Price']
        gold_close['Date'] = pd.to_datetime(gold_close['Date']).dt.tz_localize(None).dt.normalize()
        
        df_master = pd.merge(df_master, gold_close, on='Date', how='left')
        df_master['Gold_Price'] = df_master['Gold_Price'].ffill().bfill()
        
        # Dòng tiền = Ounce thay đổi * Giá đóng cửa
        df_master['usd_flow'] = (df_master['Thay_Doi_Ounces'] * df_master['Gold_Price']).round(2)
        df_master['usd_flow'] = df_master['usd_flow'].fillna(0)
    except Exception as e:
        print(f"Lỗi tải giá vàng: {e}")
        df_master['usd_flow'] = 0

    # 4. Cắt dữ liệu và chốt 4 cột xuất file
    df_final = df_master[df_master['Date'] >= '2024-01-01'].copy()
    
    # Bố cục chuẩn quốc tế
    df_final = df_final[['Date', 'hold', 'ton', 'usd_flow']]

    if not df_final.empty:
        df_final.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
        print(f"[{datetime.datetime.now()}] HOÀN TẤT! Đã đóng gói ra {FILE_NAME}")
