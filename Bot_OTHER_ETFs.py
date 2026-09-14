import requests
import pandas as pd
import io
import datetime

FILE_NAME = "OTHER_ETFs_MT5.csv"
STATUS_FILE = "ETF_Status.txt" 

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

fund_status = {}

def get_gldm():
    try:
        url = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gldm&exchange=NYSE&lang=en"
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            df = pd.read_excel(io.BytesIO(res.content), header=0)
            df['Total Ounces'] = pd.to_numeric(df['Total Ounces of Gold in the Trust'], errors='coerce')
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date', 'Total Ounces'])
            df = df.rename(columns={'Total Ounces': 'Ounces_GLDM'})
            fund_status['GLDM'] = "OK"
            return df[['Date', 'Ounces_GLDM']]
    except Exception as e:
        pass
    fund_status['GLDM'] = "LOI (Mat ket noi)"
    return pd.DataFrame(columns=['Date', 'Ounces_GLDM'])

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
        pass
    fund_status['IAU'] = "LOI (Bi chan/Bao tri)"
    return pd.DataFrame(columns=['Date', 'Ounces_IAU'])

def get_sgol():
    # Khung chờ mở rộng cho SGOL sau này
    fund_status['SGOL'] = "Chua hoat dong"
    return pd.DataFrame(columns=['Date', 'Ounces_SGOL'])

# ================= CHƯƠNG TRÌNH CHÍNH =================
df_gldm = get_gldm()
df_iau  = get_iau()
df_sgol = get_sgol()

# --- GHI BÁO CÁO RA FILE TEXT ---
now_str = datetime.datetime.now().strftime('%Y.%m.%d %H:%M')
status_msg = f"Cap nhat: {now_str} UTC | "
for fund, status in fund_status.items():
    status_msg += f"[{fund}: {status}] "

with open(STATUS_FILE, "w", encoding="utf-8") as f:
    f.write(status_msg)
print("Báo cáo trạng thái:", status_msg)

# --- XỬ LÝ DỮ LIỆU ---
df_master = df_gldm.copy()
if not df_iau.empty:
    df_master = pd.merge(df_master, df_iau, on='Date', how='left')
else:
    df_master['Ounces_IAU'] = 0

if not df_sgol.empty:
    df_master = pd.merge(df_master, df_sgol, on='Date', how='left')
else:
    df_master['Ounces_SGOL'] = 0

# Tính tổng
df_master['Total_Ounces_ROW'] = df_master['Ounces_GLDM'].fillna(0) + df_master['Ounces_IAU'].fillna(0) + df_master['Ounces_SGOL'].fillna(0)
df_master = df_master.sort_values(by='Date', ascending=True).reset_index(drop=True)

df_master['Thay_Doi_Ounces'] = df_master['Total_Ounces_ROW'].diff()
df_master['Thay đổi (Tấn)'] = (df_master['Thay_Doi_Ounces'] / 32150.746568).round(2)
df_master['Tổng Vàng (Tấn)'] = (df_master['Total_Ounces_ROW'] / 32150.746568).round(2)
df_master['Thay đổi (Tấn)'] = df_master['Thay đổi (Tấn)'].fillna(0)

# Cắt dữ liệu từ 2024
df_final = df_master[df_master['Date'] >= '2024-01-01'].copy()
df_final = df_final[['Date', 'Tổng Vàng (Tấn)', 'Thay đổi (Tấn)']]

if not df_final.empty:
    df_final.to_csv(FILE_NAME, index=False, date_format='%Y.%m.%d')
