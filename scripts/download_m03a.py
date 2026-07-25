from pathlib import Path
from datetime import datetime, timedelta
import requests
import time
import random

output_dir = Path("../data/raw/M03A")
output_dir.mkdir(parents=True, exist_ok=True)

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 5, 31)

base_url = ("https://tisvcloud.freeway.gov.tw/history/TDCS/M03A/M03A_{}.tar.gz")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

current_date = start_date
start = time.time()

while current_date <= end_date:
    date_str = current_date.strftime("%Y%m%d")
    file_url = base_url.format(date_str)

    res = requests.get(file_url,headers=headers,verify=False,timeout=15)

    if res.status_code == 200:
        file_path = output_dir / f"M03A_{date_str}.tar.gz"

        with file_path.open("wb") as f:
            f.write(res.content)

        print(f"下載成功：{file_path}")
    else:
        print(
            f"下載失敗：{date_str}，"
            f"狀態碼：{res.status_code}"
        )

    current_date += timedelta(days=1)

    if current_date <= end_date:
        time.sleep(random.uniform(1, 2.5))

end = time.time()

total_time = end - start
days = (end_date - start_date).days + 1

print(f"總耗時：{total_time:.2f} 秒")
print(f"平均每個檔案：{total_time / days:.2f} 秒")