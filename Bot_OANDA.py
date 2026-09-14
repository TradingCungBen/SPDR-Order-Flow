import requests
import pandas as pd
import datetime
import os

FILE_NAME = "OANDA_Sentiment_MT5.csv"
# Token được bảo mật qua GitHub Secrets
TOKEN = os.environ.get("OANDA_TOKEN", "") 
INSTRUMENT = "XAU_USD" # Mã giao dịch Vàng trên OANDA

def get_oanda_sentiment():
    # Sử dụng Practice API của OANDA (Miễn phí)
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{INSTRUMENT}/positionBook"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            buckets = data.get('positionBook', {}).get('buckets', [])
            
            # Tính tổng khối lượng Long và Short từ các mức giá
            long_pct = sum(float(b.get('longCountPercent', 0)) for b in buckets)
            short_pct = sum(float(b.get('shortCountPercent', 0)) for b in buckets)
            
            # Chuẩn hóa về thang 100%
            total = long_pct + short_pct
            if total > 0:
                long_pct = round((long_pct / total) * 100, 2)
                short_pct = round((short_pct / total) * 100, 2)
                
            return long_pct, short_pct
        else:
            print(f"Lỗi API OANDA ({res.status_code}): {res.text}")
            return None, None
    except Exception as e:
        print(f"Lỗi kết nối OANDA API: {e}")
        return None, None

def update_oanda_csv():
    long_pct, short_pct = get_oanda_sentiment()
    if long_pct is None:
        return
        
    # ton = Chênh lệch phe Mua và Bán
    net_sentiment = round(long_pct - short_pct, 2)
    today_str = datetime.datetime.now().strftime('%Y.%m.%d')
    
    # Mở kho CSV cũ hoặc tạo mới nếu chưa có
    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
    else:
        df = pd.DataFrame(columns=['Date', 'hold', 'ton'])
        
    # Xóa dòng của ngày hôm nay (nếu bạn chạy test thủ công nhiều lần trong ngày)
    df = df[df['Date'] != today_str]
    
    # Nối dữ liệu mới
    new_row = pd.DataFrame({'Date': [today_str], 'hold': [long_pct], 'ton': [net_sentiment]})
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Sắp xếp và lưu file (Khớp chuẩn MT5)
    df = df.sort_values(by='Date').reset_index(drop=True)
    df.to_csv(FILE_NAME, index=False)
    
    print(f"[{today_str}] OANDA Sentiment XAU_USD: Long={long_pct}%, Short={short_pct}%, Net={net_sentiment}%")

if __name__ == "__main__":
    if not TOKEN:
        print("LỖI: Chưa cấu hình OANDA_TOKEN. Hãy thêm vào GitHub Secrets.")
    else:
        update_oanda_csv()
