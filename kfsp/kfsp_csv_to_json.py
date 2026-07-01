import csv, json

rows = []
with open("kfsp_centers.csv", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames          # 원본 헤더 순서 보존
    for i, r in enumerate(reader):
        obj = {"id": str(i)}                 # Azure 인덱싱용 키 (추가 필드)
        for col in fieldnames:               # 원본 6개 필드를 그대로 복사
            obj[col] = r[col]
        rows.append(obj)

with open("kfsp_centers.json", "w", encoding="utf-8") as out:
    json.dump(rows, out, ensure_ascii=False, indent=2)