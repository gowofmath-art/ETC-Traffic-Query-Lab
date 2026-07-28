import json
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd


# 1. 基本路徑與清洗規則
raw_dir = Path("data/raw/M03A")
staging_dir = Path("data/staging/M03A")
interim_dir = Path("data/interim/M03A")
json_path = Path("data/metadata/gantries_2026_detailed.json")

columns = ["TimeStamp","GantryID","Direction","VehicleType","Volume"]
vehicle_types = {31, 32, 41, 42, 5}
directions = {"N", "S", "E", "W"}
gantry_pattern = (r"^\d{2}[A-Z]{1,2}\d{3,4}[NSEW]$")


# 2. 讀取門架 JSON
with json_path.open("r", encoding="utf-8") as f:
    gantry_data = json.load(f)

gantry_set = set(gantry_data)

print("合法門架數量：", len(gantry_set))


# 3. 日期產生器
def date_range(start, end):
    """
    產生開始日期到結束日期，
    包含首尾兩天。
    """

    start = datetime.strptime(start, "%Y%m%d")
    end = datetime.strptime(end, "%Y%m%d")
    date = start

    while date <= end:
        yield date.strftime("%Y%m%d")
        date += timedelta(days=1)

# 4. 解壓縮一天
def extract_day(date):
    """
    將指定日期的 tar.gz
    解壓到 staging/M03A。
    """

    archive_path = (raw_dir/ f"M03A_{date}.tar.gz")
    day_dir = staging_dir / date

    if not archive_path.exists():
        print("找不到壓縮檔：", archive_path)
        return False

    # 如果前一次留下相同日期資料，
    # 先刪除，避免舊檔與新檔混在一起
    if day_dir.exists():
        shutil.rmtree(day_dir)

    staging_dir.mkdir(parents=True,exist_ok=True,)
    print("開始解壓縮：", archive_path.name)

    try:
        with tarfile.open(archive_path,"r:gz",) as tar:
            tar.extractall(staging_dir)

    except (tarfile.TarError, OSError) as e:
        print("解壓縮失敗：", e)

        if day_dir.exists():
            shutil.rmtree(day_dir)
        return False

    files = list(day_dir.rglob("*.csv"))

    print("解壓完成，CSV 數量：", len(files))

    if len(files) != 288:
        print("警告：正常一天應有 288 個 CSV")
    return True

# 5. 聚合並清洗一天
def clean_day(date):
    """
    讀取一天內所有 CSV，
    合併、清洗並輸出成單一 CSV。
    """

    input_dir = staging_dir / date
    output_path = (interim_dir/ f"M03A_{date}.csv")
    files = sorted(input_dir.rglob("*.csv"))
    if not files:
        print("找不到 CSV：", input_dir)
        return False

    dfs = []
    for file in files:
        df_part = pd.read_csv(file,header=None,names=columns,)
        dfs.append(df_part)

    # 聚合一天的所有 CSV
    df = pd.concat(dfs,ignore_index=True,)

    # A：時間
    time = pd.to_datetime(df["TimeStamp"],errors="coerce",)
    A = (time.notna()& (time.dt.minute % 5 == 0) & (time.dt.second == 0))

    # B：門架
    B1 = df["GantryID"].str.fullmatch(gantry_pattern,na=False,)
    B2 = df["GantryID"].isin(gantry_set)
    B = B1 & B2

    # C：方向
    C = df["Direction"].isin(directions)

    # D：車種
    D = df["VehicleType"].isin(vehicle_types)

    # E：車流量
    volume = pd.to_numeric(df["Volume"],errors="coerce",)
    E = (volume.notna() & (volume >= 0) & (volume % 1 == 0))

    # 合併所有清洗條件
    condition = A & B & C & D & E
    clean = df[condition].copy()
    error = df[~condition].copy()

    # 統一清洗後型別
    clean["TimeStamp"] = pd.to_datetime(clean["TimeStamp"])
    clean["Volume"] = pd.to_numeric(clean["Volume"]).astype(int)

    # 建立輸出資料夾
    interim_dir.mkdir(parents=True,exist_ok=True,)

    clean.to_csv(output_path,index=False,encoding="utf-8-sig",)

    print("原始資料：", len(df))
    print("合法資料：", len(clean))
    print("異常資料：", len(error))

    print("A 時間錯誤：", (~A).sum())
    print("B1 門架格式錯誤：", (~B1).sum())
    print("B2 門架不存在：", (~B2).sum())
    print("C 方向錯誤：", (~C).sum())
    print("D 車種錯誤：", (~D).sum())
    print("E 數量錯誤：", (~E).sum())

    print("輸出完成：", output_path)

    return True

# 6. 清除一天的暫存資料
def remove_staging_day(date):
    """
    每日清洗成功後，
    刪除已解壓的小 CSV。
    """
    day_dir = staging_dir / date

    if day_dir.exists():
        shutil.rmtree(day_dir)
        print("已刪除暫存：", day_dir)


# 7. 處理一天
def process_day(date):
    """
    完整處理單日：
    解壓縮 → 聚合清洗 → 清除暫存
    """

    print()
    print("=" * 50)
    print("開始處理：", date)
    print("=" * 50)

    output_path = (interim_dir/ f"M03A_{date}.csv")

    # 已經成功輸出的日期直接跳過
    if output_path.exists():
        print("已經處理完成，跳過：", output_path)
        return True

    if not extract_day(date):
        print("處理失敗：", date)
        return False

    if not clean_day(date):
        print("處理失敗：", date)
        return False

    # 只有成功清洗後才刪除 staging
    remove_staging_day(date)

    print("完成日期：", date)

    return True

# 8. 批次處理日期
failed_dates = []

for date in date_range("20260101","20260531",):
    success = process_day(date)
    if not success:
        failed_dates.append(date)


# 9. 顯示批次結果
print()
print("=" * 50)
print("批次處理完成")
print("失敗日期數量：", len(failed_dates))

if failed_dates:
    print("失敗日期：", failed_dates)