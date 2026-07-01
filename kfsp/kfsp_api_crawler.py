import csv
import time
import requests

INDEX = "https://www.kfsp.or.kr/home/kor/helpSearch/index.do?menuPos=31"
BASE  = "https://www.kfsp.or.kr/home/kor/helpSearch"
EP_SIDO = f"{BASE}/selectSidoDataList.ajax"
EP_SGG  = f"{BASE}/selectSggDataList.ajax"
EP_HELP = f"{BASE}/selectHelpSearchDataList.ajax"

OUTPUT = "kfsp_centers.csv"
POLITE_DELAY = 1.0
SGG_PARAM = "sgg"  # 기관 조회 파라미터 (확인됨)

# 시군구 목록 조회 시 보낼 '시도 코드' 파라미터 이름 후보 (맞는 것을 자동 탐색)
SGG_QUERY_PARAM_CANDIDATES = ["ctpvCd", "sido", "sidoCd", "ctpv"]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": INDEX,
}

session = requests.Session()
session.headers.update(HEADERS)
_sgg_query_param = None  # 한 번 찾으면 고정


def post_json(url, data=None):
    r = session.post(url, data=data or {}, timeout=15)
    r.raise_for_status()
    return r.json()


def get_list(payload):
    if isinstance(payload, dict):
        return payload.get("list", [])
    return payload if isinstance(payload, list) else []


def detect_code_name_keys(items):
    """코드 필드(숫자 값 중 가장 긴 것)와 이름 필드(한글 값)를 자동 인식."""
    if not items:
        return None, None
    sample = items[0]
    digit_fields = [(k, str(v)) for k, v in sample.items()
                    if str(v).strip() and str(v).replace("-", "").isdigit()]
    code_key = max(digit_fields, key=lambda kv: len(kv[1]))[0] if digit_fields else None
    name_key = None
    for k, v in sample.items():
        if any("\uac00" <= ch <= "\ud7a3" for ch in str(v)):
            name_key = k
            break
    return code_key, name_key


def fetch_sgg_list(sido_code):
    """시군구 목록을 가져온다. 올바른 파라미터 이름을 자동으로 찾아 고정."""
    global _sgg_query_param
    if _sgg_query_param:
        return get_list(post_json(EP_SGG, {_sgg_query_param: sido_code}))
    for p in SGG_QUERY_PARAM_CANDIDATES:
        lst = get_list(post_json(EP_SGG, {p: sido_code}))
        if lst:
            _sgg_query_param = p
            print(f"[자동인식] 시군구 조회 파라미터 = '{p}'")
            return lst
        time.sleep(0.3)
    return []


def main():
    # 0) 세션 준비
    print("0) 세션 준비: index.do 방문")
    r0 = session.get(INDEX, timeout=15)
    print("   status:", r0.status_code, "| cookies:", session.cookies.get_dict(), "\n")

    rows = []

    # 1) 시도 목록
    sido_list = get_list(post_json(EP_SIDO))
    sido_ck, sido_nk = detect_code_name_keys(sido_list)
    print(f"[자동인식] 시도 → 코드='{sido_ck}', 이름='{sido_nk}' (총 {len(sido_list)}개)\n")

    sgg_ck = sgg_nk = None
    printed_sgg = False

    for sido in sido_list:
        sido_code = sido.get(sido_ck)      # 10자리 전체 코드 (예: 1100000000)
        sido_name = sido.get(sido_nk, "")
        time.sleep(POLITE_DELAY)

        # 2) 시군구 목록 (10자리 코드 + 올바른 파라미터 자동 탐색)
        sgg_list = fetch_sgg_list(sido_code)
        if not printed_sgg and sgg_list:
            sgg_ck, sgg_nk = detect_code_name_keys(sgg_list)
            print(f"[자동인식] 시군구 → 코드='{sgg_ck}', 이름='{sgg_nk}'")
            print(f"  시군구 샘플: {sgg_list[:2]}\n")
            printed_sgg = True

        for sgg in sgg_list:
            sgg_code = sgg.get(sgg_ck)
            sgg_name = sgg.get(sgg_nk, "")
            time.sleep(POLITE_DELAY)

            # 3) 기관 목록
            help_list = get_list(post_json(EP_HELP, {SGG_PARAM: sgg_code}))
            for it in help_list:
                rows.append({
                    "기관명": it.get("fcltyNm", ""),
                    "시도": sido_name,
                    "시군구": sgg_name,
                    "주소": it.get("fcltyAddr", ""),
                    "전화": it.get("cttpcCn", ""),
                    "유형": it.get("fcltyClNm", ""),
                })
            print(f"[{sido_name} {sgg_name}] {len(help_list)}건")

    print(f"\n수집된 원본 행: {len(rows)}건")

    # 중복 제거
    seen, unique = set(), []
    for r in rows:
        key = (r["기관명"], r["주소"])
        if r["기관명"] and key not in seen:
            seen.add(key)
            unique.append(r)

    fields = ["기관명", "시도", "시군구", "주소", "전화", "유형"]
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(unique)

    print(f"저장 완료: {len(unique)}건 → {OUTPUT}")

    if not _sgg_query_param:
        print("\n⚠ 시군구 조회 파라미터를 못 찾았어요. DevTools에서 시도 선택 후 "
              "selectSggDataList 요청의 Payload(보낸 값) 이름을 확인해 "
              "SGG_QUERY_PARAM_CANDIDATES 맨 앞에 추가하세요.")


if __name__ == "__main__":
    main()
