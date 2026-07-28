import json
from pathlib import Path
import pandas as pd

# 1. 路徑設定 (只需要測試一天的資料即可)
# 先設定好三個變數(這邊指的是檔案)：引用path 套件的功能，不需要讓每次都打這麼長一段路徑名稱。

input_dir = Path("data/staging/M03A/20260101")
json_path = Path("data/metadata/gantries_2026_detailed.json")
output_path = Path("data/interim/M03A/M03A_20260101.csv")

# 2. 讀取門架 JSON

with json_path.open("r", encoding="utf-8") as f:
    gantry_data = json.load(f)

# JSON 的 key 就是所有合法門架代號，直接在這邊做成一個門架set。
gantry_set = set(gantry_data)
print("合法門架數量：", len(gantry_set))

# 3. 讀取一天內所有 CSV

columns = ["TimeStamp","GantryID","Direction","VehicleType","Volume",]
# 「遞迴搜尋指定資料夾及其所有子資料夾內的所有 .csv 檔案，並將搜尋結果依照檔名排序後，存入 files 變數中。」
files = sorted(input_dir.rglob("*.csv"))
print("CSV 檔案數量：", len(files))

dfs = []

for file in files:
    df_part = pd.read_csv(file,header=None,names=columns,)
    dfs.append(df_part)

# 將一天的 288 個 CSV 合併
df = pd.concat(dfs,ignore_index=True,)
print("原始資料筆數：", len(df))

# 4. A：時間
time = pd.to_datetime(df["TimeStamp"],errors="coerce",)

A = (time.notna() & (time.dt.minute % 5 == 0) & (time.dt.second == 0))

# 5. B：門架

# B1：門架代號格式正確
B1 = df["GantryID"].str.fullmatch(r"^\d{2}[A-Z]{1,2}\d{3,4}[NSEW]$",na=False,)

# B2：門架確實存在於 JSON
B2 = df["GantryID"].isin(gantry_set)
B = B1 & B2

# 6. C：方向
C1 = df["Direction"].isin({"N", "S", "E", "W"})

# Direction 必須與 GantryID 最後一碼相同
C2 = (df["Direction"] == df["GantryID"].str[-1])

C = C1 & C2

direction_mismatch = df[C1 & ~C2][["GantryID", "Direction"]].drop_duplicates()

print(direction_mismatch)

# 7. D：車種
D = df["VehicleType"].isin({31, 32, 41, 42, 5})


# 8. E：車流量
volume = pd.to_numeric(df["Volume"],errors="coerce",)

E = (volume.notna()& (volume >= 0) & (volume % 1 == 0))

# 9. 合併清洗條件
condition = A & B & C & D & E
clean = df[condition].copy()
error = df[~condition].copy()

# 10. 清洗後型別
clean["TimeStamp"] = pd.to_datetime(clean["TimeStamp"])
clean["Volume"] = pd.to_numeric(clean["Volume"]).astype(int)


# 11. 顯示結果

print()
print("清洗結果")
print("原始資料：", len(df))
print("合法資料：", len(clean))
print("異常資料：", len(error))

print()
print("各條件不合格數量")
print("A 時間錯誤：", (~A).sum())
print("B1 門架格式錯誤：", (~B1).sum())
print("B2 門架不存在：", (~B2).sum())
print("C 方向錯誤：", (~C).sum())
print("D 車種錯誤：", (~D).sum())
print("E 數量錯誤：", (~E).sum())


# 12. 輸出清洗結果

output_path.parent.mkdir(parents=True,exist_ok=True,)

clean.to_csv(output_path,index=False,encoding="utf-8-sig",)

print()
print("清洗完成：", output_path)