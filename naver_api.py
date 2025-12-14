import requests
import time
import hmac
import hashlib
import base64
import datetime
from urllib.parse import urlparse
import pandas as pd
from io import StringIO

def get_naver_header(method, uri, api_key, secret_key, customer_id):
    ts = str(int(time.time() * 1000))
    msg = f"{ts}.{method}.{uri}"
    sign = base64.b64encode(hmac.new(secret_key.encode(), msg.encode(), hashlib.sha256).digest()).decode()
    return {
        "Content-Type": "application/json", "X-Timestamp": ts, 
        "X-API-KEY": api_key, "X-Customer": customer_id, "X-Signature": sign
    }

def download_naver_report(target_acc):
    try:
        base_url = "https://api.searchad.naver.com"
        stat_dt = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        # 1. 생성
        uri = "/stat-reports"
        headers = get_naver_header("POST", uri, target_acc['key'], target_acc['secret'], target_acc['id'])
        res = requests.post(base_url + uri, headers=headers, json={"reportTp": "AD", "statDt": stat_dt})

        if res.status_code != 200:
            raise Exception(f"리포트 생성 실패: {res.text}")

        jid = res.json()["reportJobId"]

        # 2. 대기
        durl = None
        for i in range(10):
            time.sleep(2)
            uri_chk = f"/stat-reports/{jid}"
            h = get_naver_header("GET", uri_chk, target_acc['key'], target_acc['secret'], target_acc['id'])
            r = requests.get(base_url + uri_chk, headers=h)
            if r.json()["status"] == "BUILT":
                durl = r.json()["downloadUrl"]
                break

        if not durl:
            raise Exception("다운로드 URL 확보 실패")

        # 3. 다운로드 & 변환
        parsed = urlparse(durl)
        h_dl = get_naver_header("GET", parsed.path, target_acc['key'], target_acc['secret'], target_acc['id'])
        file_res = requests.get(durl, headers=h_dl)

        df = pd.read_csv(StringIO(file_res.text), sep='\t')
        rename_map = {'statDt':'날짜', 'salesAmt':'광고비(원)', 'convAmt':'전환매출액(원)', 'impCnt':'노출수', 'clkCnt':'클릭수'}
        df.rename(columns=rename_map, inplace=True)

        return df, stat_dt

    except Exception as e:
        raise Exception(f"네이버 API 오류: {e}")