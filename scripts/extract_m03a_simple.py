from pathlib import Path
import tarfile

project_root = Path(__file__).resolve().parents[1]

archive_path = (project_root/ "data"/ "raw"/ "M03A"/ "M03A_20260101.tar.gz")

output_dir = (project_root/ "data"/ "staging"/ "M03A")

output_dir.mkdir(parents=True, exist_ok=True)

with tarfile.open(archive_path, "r:gz") as tar:
    tar.extractall(output_dir)

print("解壓縮完成")