# PR-7.A.1.5 투자자 flow 데이터 소스 선행 조사

Updated: 2026-04-25 KST

## 범위 / 전제

- 목적: PR-7.A.1 파일럿의 3개 제약(개인 부재, 금액 부재, point-in-time 미검증)을 완화할 수 있는 **후보 소스 존재 여부만 조사**.
- 금지 준수:
  - 전체 종목 수집 안 함
  - 새 signal 정의 안 함
  - 백테스트 안 함
  - 전략 설계 안 함
  - `pykrx` 재시도 안 함
- 관측 시각: `2026-04-25 01:00:54 +09:00`
- Git 브랜치: `option_a_investor_flow`
- 참고: 현재 워크트리에는 PR-7.A.1 산출물로 보이는 미추적 파일이 이미 있었고, 이번 작업에서는 건드리지 않았다.

## Step 1. FinanceDataReader 투자자별 매매 기능 확인

### 실행 시도

```bash
uv add financedatareader
python -c "import FinanceDataReader as fdr"
```

실제 출력:

```text
$ uv add financedatareader
error: No `pyproject.toml` found in current directory or any parent directory

$ python -c "import FinanceDataReader as fdr"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'FinanceDataReader'
```

### 문서 확인

- 공식 README: [FinanceDataReader README](https://github.com/FinanceData/FinanceDataReader)
- README에 노출된 주요 API는 `DataReader`, `StockListing`, `SnapDataReader`.
- README 예시는 가격 데이터, 상장목록, 지수 구성종목, 재무제표 중심이다.
- README에서 투자자별 매매동향 / 개인·외국인·기관 순매수 전용 API는 확인하지 못했다.

### 판단

| 항목 | 결과 |
| --- | --- |
| 개인 순매수 | ❌ 문서상 미노출 |
| 외국인 순매수 | ❌ 문서상 미노출 |
| 기관 순매수 | ❌ 문서상 미노출 |
| 금액(원) 단위 | ❌ 투자자 flow API 미확인 |
| 주식수 단위 | ❌ 투자자 flow API 미확인 |
| 2020-01 ~ 현재 커버 | 가격 데이터는 가능해 보이나, 투자자 flow는 확인 실패 |
| 호출 제한 / 속도 | 문서상 별도 명시 확인 실패 |

짧은 분석:
- 이번 리포지토리에서는 설치 자체가 불가했고, 공식 문서 기준으로도 투자자별 매매 데이터 소스 후보로는 부적합하다.
- `DataReader('005930', ...)`의 실제 반환 컬럼 샘플은 패키지 미설치로 확인 실패했다.

## Step 2. Naver 다른 엔드포인트 탐색

### 시장 전체 엔드포인트 존재 여부

확인 URL:

- [Naver `item/frgn.naver`](https://finance.naver.com/item/frgn.naver?code=005930)
- [Naver `sise/investorDealTrendDay.naver`](https://finance.naver.com/sise/investorDealTrendDay.naver)
- [Naver robots.txt](https://finance.naver.com/robots.txt)

실행 코드:

```python
resp = requests.get("https://finance.naver.com/sise/investorDealTrendDay.naver")
html = resp.content.decode("euc-kr", errors="replace")
table = pd.read_html(StringIO(html))[0]
print("contains_code_param", "code=" in html)
print(list(table.columns))
```

실제 출력 샘플:

```text
status 200
contains_code_param False
columns= [('날짜', '날짜'), ('개인', '개인'), ('외국인', '외국인'), ('기관계', '기관계'),
          ('기관', '금융투자'), ('기관', '보험'), ('기관', '투신 (사모)'), ('기관', '은행'),
          ('기관', '기타금융기관'), ('기관', '연기금등'), ('기타법인', '기타법인')]
```

직접 확인한 HTML 일부:

```html
<h4 class="top_tlt2"><span class="head">일자별 순매수</span> <span class="top_tlt_guide">(단위:억원)</span></h4>
```

### 종목별 대체 URL 패턴 탐색

실행 코드:

```python
candidates = [
    "https://finance.naver.com/item/investorDealTrendDay.naver?code=005930",
    "https://finance.naver.com/item/investorDealTrend.naver?code=005930",
    "https://finance.naver.com/item/investor.naver?code=005930",
    "https://finance.naver.com/item/frgn.naver?code=005930",
]
```

실제 출력 샘플:

```text
URL https://finance.naver.com/item/investorDealTrendDay.naver?code=005930
status 404

URL https://finance.naver.com/item/investorDealTrend.naver?code=005930
status 404

URL https://finance.naver.com/item/investor.naver?code=005930
status 404

URL https://finance.naver.com/item/frgn.naver?code=005930
status 200
```

### robots.txt 확인

실제 출력 샘플:

```text
User-agent: *
Disallow: /
User-agent: yeti
Disallow: /
Allow: /sise/
Allow: /research/
Allow: /marketindex/
Allow: /fund/
Allow: /template/head_js.naver
Allow: /world/
Allow: /item/board.naver?code=*
```

### 판단

| 항목 | 결과 |
| --- | --- |
| 종목별 개인 순매수 페이지 | ❌ 확인 실패. 후보 `/item/...` 패턴은 모두 404 |
| 시장 전체 개인/외국인/기관계 | ✅ `sise/investorDealTrendDay.naver` 존재 |
| 금액 단위 | ✅ `(단위:억원)` 명시 |
| HTML 파싱 가능성 | △ 헤더 파싱은 가능, 관측 시점의 본문 행은 비어 있었음 |
| robots 측면 | `/sise/`는 허용. `/item/frgn.naver`는 허용 목록에 없음 |

짧은 분석:
- Naver 대체 엔드포인트는 **시장 전체 개인 순매수(금액)** 확인용으로는 의미가 있다.
- 하지만 **종목별 개인 순매수 대체 소스**는 이번 탐색에서 찾지 못했다.

## Step 3. Naver `frgn.naver` 원본 HTML 재파싱

확인 URL:

- [Naver `frgn.naver` 삼성전자](https://finance.naver.com/item/frgn.naver?code=005930&page=1)

실행 코드:

```python
resp = requests.get("https://finance.naver.com/item/frgn.naver", params={"code": "005930", "page": 1})
html = resp.content.decode("euc-kr", errors="replace")
table = pd.read_html(StringIO(html), flavor="lxml")[3]
print(list(table.columns))
print(table.head(5).to_string())
```

실제 출력 샘플:

```text
columns= [('날짜', '날짜'), ('종가', '종가'), ('전일비', '전일비'), ('등락률', '등락률'),
          ('거래량', '거래량'), ('기관', '순매매량'), ('외국인', '순매매량'),
          ('외국인', '보유주수'), ('외국인', '보유율')]

           날짜        종가        전일비     등락률         거래량         기관        외국인
           날짜        종가        전일비     등락률         거래량       순매매량       순매매량          보유주수     보유율
0         NaN       NaN        NaN     NaN         NaN        NaN        NaN           NaN     NaN
1  2026.04.24  219500.0  하락  5,000  -2.23%  19165257.0   -66031.0 -4887720.0  2.873765e+09  49.16%
2  2026.04.23  224500.0  상승  7,000  +3.22%  34525485.0   677286.0  3298847.0  2.878653e+09  49.24%
```

### 현재 parser가 버리는 컬럼

현재 `scripts/explore_naver_investor_flow.py`는 raw 9개 컬럼 중 아래 7개만 최종 보존한다.

- `date`
- `close`
- `volume`
- `foreign_net_buy_shares`
- `institutional_net_buy_shares`
- `foreign_holding_shares`
- `foreign_holding_ratio`

버리는 컬럼:

- `price_change` (`전일비`)
- `change_rate` (`등락률`)

### 판단

| 확인 포인트 | 결과 |
| --- | --- |
| 외국인 매수 / 매도 / 순매수 분리 | ❌ 순매매량만 존재 |
| 기관 매수 / 매도 / 순매수 분리 | ❌ 순매매량만 존재 |
| 개인 컬럼 | ❌ 없음 |
| 금액 컬럼 | ❌ 없음 |
| 현재 parser가 숨긴 투자자 컬럼 | ❌ 없음 |
| 현재 parser가 버린 컬럼 | `전일비`, `등락률`만 버림 |

짧은 분석:
- 현재 parser는 핵심 투자자 컬럼을 놓치고 있지 않다.
- `frgn.naver` 자체가 애초에 개인/금액/매수·매도 분리 컬럼을 주지 않는다.

## Step 4. Point-in-time 공개 시각 실측

### 4-1. Naver `frgn.naver` 관측

실행 코드:

```bash
Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
```

```python
resp = requests.get("https://finance.naver.com/item/frgn.naver", params={"code": "005930", "page": 1})
html = resp.content.decode("euc-kr", errors="replace")
print(next(line.strip() for line in html.splitlines() if '<em class="date">' in line))
```

실제 출력:

```text
2026-04-25 01:00:54 +09:00
<em class="date">2026.04.24 <span>기준(KRX 장마감)</span></em>
```

같은 페이지 1행 데이터:

```text
2026.04.24
```

해석:

- 관측 시각은 **2026-04-25 토요일 01:00 KST**.
- 가장 최근 평일은 **2026-04-24 금요일**.
- 이 시점에 Naver `frgn.naver`는 이미 **2026-04-24 데이터**를 표시하고 있었다.
- 즉, **최소한 T+1 캘린더일 새벽에는 전일 데이터가 공개되어 있음**은 확인된다.
- 하지만 이 단일 관측만으로 **금요일 15:30 직후에 바로 올라왔는지**, **자정 이후 올라왔는지**는 결론낼 수 없다.

### 4-2. KRX 공식 공개 시각 근거 탐색

확인 출처:

- [KRX 메인 공개 페이지 (`main.jspx`)](https://data.krx.co.kr/contents/MDC/MAIN/main.jspx)
- [KRX 공개 인덱스 페이지 (`main/index.cmd?vsView=Y`)](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?vsView=Y)

공식 페이지/검색 스니펫에서 확인한 문구:

- `직전영업일 투자자별 매매동향`

이 문구는 KRX 공개 메인 위젯 기준으로 투자자별 매매동향이 **당일 실시간이 아니라 직전영업일 기준**으로 노출됨을 시사한다.

추가로 직접 GET 한 결과:

```python
requests.get("https://data.krx.co.kr/contents/MMC/ISIF/isif/MMCISIF003.cmd?tabIndex=3")
```

실제 출력 샘플:

```text
<!DOCTYPE html>
<script type='text/javascript'>
alert('로그인 또는 회원가입이 필요합니다.');
location.href='/contents/MMC/COMS/client/MMCCOMS001.cmd?...';
</script>
```

즉:

- KRX에는 공식적으로 `투자자별 거래실적`, `투자자별 거래실적(개별종목)` 메뉴가 존재한다.
- 하지만 direct GET 기준으로는 로그인 redirect가 걸려 있어, **공식 문서의 세부 공개 시각 정책**까지는 이번 조사에서 확인 실패했다.

### 4-3. PIT 결론

| 항목 | 판단 |
| --- | --- |
| 보수 가정 `T일 flow는 T+1 장 시작 후 사용 가능` | ✅ 이번 조사 기준 성립 가능성이 높음 |
| 근거 1 | Naver가 2026-04-25 01:00 KST에 2026-04-24 장마감 기준값을 이미 표시 |
| 근거 2 | KRX 공개 메인 위젯 문구가 `직전영업일 투자자별 매매동향` |
| 반증 여부 | ❌ 이번 조사에서는 찾지 못함 |
| 남은 불확실성 | 금요일 15:30 직후 공개인지, 자정 이후 공개인지 미확정 |
| 더 보수적 대안 `T+2` | 가능은 하지만 과보수적일 수 있음. 생산 적용 전 평일 장마감 후 재관찰이 더 우선 |

짧은 분석:
- **이번 조사만으로도 T+1 open 가정은 충분히 방어 가능**하다.
- 다만 **단일 관측이며, 토요일 새벽 관측**이라는 한계가 있으므로 리포트/후속 PR에서 이 점을 명시해야 한다.

## Step 5. KRX 정보데이터시스템 직접 조회 가능성

확인 출처:

- [KRX 공개 인덱스 페이지 (`vsView=Y`)](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?vsView=Y)
- [KRX 메인 공개 페이지 (`main.jspx`)](https://data.krx.co.kr/contents/MDC/MAIN/main.jspx)
- direct GET: `https://data.krx.co.kr/contents/MMC/ISIF/isif/MMCISIF003.cmd?tabIndex=3`

### 확인 결과

| 항목 | 결과 |
| --- | --- |
| 투자자별 거래실적 페이지 존재 | ✅ 공개 인덱스 메뉴에서 확인 |
| 투자자별 거래실적(개별종목) 페이지 존재 | ✅ 공개 인덱스 메뉴에서 확인 |
| direct GET 무인증 접근 | ❌ 로그인 / 회원가입 redirect |
| API/JSON endpoint | 확인 실패 |
| CSV/XLS 다운로드 지원 | 확인 실패 |
| 금액 단위 | 확인 실패 |
| 개인 제공 여부 | 확인 실패 |
| 전체 종목 확장 가능성 | ✅ 메뉴상 전종목 / 개별종목 둘 다 존재 |

짧은 분석:
- **공식 소스 후보로서의 존재 자체는 가장 강하다.**
- 하지만 **이번 세션의 direct GET 관측만으로는 자동화 가능성(API/CSV/무인증)**을 검증하지 못했다.

## Step 6. 종합 표

| 소스 | 개인 net | 외국인 net | 기관 net | 금액 단위 | 주식수 단위 | 전체 종목 | 대량수집 가능 | 공개 시각 |
|---|---|---|---|---|---|---|---|---|
| Naver `frgn.naver` | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | △ HTML 스크래핑은 가능하나 rate limit / robots 리스크 | 관측: 2026-04-25 01:00 KST에 2026-04-24 장마감 기준값 존재. T+1 가정 가능 |
| FinanceDataReader | ❌ 문서상 투자자 API 미노출 | ❌ 문서상 투자자 API 미노출 | ❌ 문서상 투자자 API 미노출 | ❌ | ❌ | ❌ 투자자 flow 기준 | 해당 데이터 없음 | 해당 데이터 없음 |
| Naver (다른 엔드포인트) | ✅ 시장 전체만 | ✅ 시장 전체만 | ✅ 시장 전체만 | ✅ `(단위:억원)` | ❌ | ❌ 종목별 엔드포인트 미발견 | ❌ 종목 universe 대체 불가 | 확인 실패 |
| KRX 정보데이터시스템 | 확인 실패* | 확인 실패* | 확인 실패* | 확인 실패* | 확인 실패* | ✅ 메뉴상 전종목/개별종목 존재 | 확인 실패* | 공식 메인 위젯은 `직전영업일` 표기 |

\* KRX direct GET이 로그인 / 회원가입 redirect로 끝나 세부 필드를 이번 조사에서 검증하지 못함.

## Codex 권고안

나라면 **KRX 정보데이터시스템을 1순위 소스 후보**로 본다.

이유:

- 공식 소스라서 source-of-truth 설명력이 가장 높다.
- 공개 메인 페이지 기준으로 `직전영업일 투자자별 매매동향` 표기가 있어 PIT 설명도 가장 낫다.
- 메뉴상 `투자자별 거래실적(개별종목)`이 존재해, 이번 파일럿의 핵심 제약(개인 / 금액 / PIT) 중 최소 2개 이상을 풀 가능성이 가장 높다.

단, 이번 조사에서 **무인증 direct query / CSV / API**를 검증하지 못했다.

따라서 의사결정은 아래처럼 보는 게 맞다:

- **즉시 계속 수집 가능한 안정 소스**: 아직 없음
- **가장 유망한 다음 검증 대상**: KRX 정보데이터시스템
- **현 소스 유지 시 결론**: Naver `frgn.naver`는 외국인/기관 주식수 net용으로만 쓸 수 있고, 개인/금액 제약은 해소되지 않음

불확실성 명시:

- Step 4 결론은 **단일 관측** 기반이다.
- 평일 장마감 직후(예: 2026-04-27 15:30~18:00 KST) 재관찰이 들어가면 PIT 확신도가 더 올라간다.
- KRX는 공식 소스이지만, 이번 세션에서는 **로그인 장벽 때문에 자동화 가능성 검증이 미완료** 상태다.

## 출처

- FinanceDataReader README: [https://github.com/FinanceData/FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)
- Naver `frgn.naver`: [https://finance.naver.com/item/frgn.naver?code=005930](https://finance.naver.com/item/frgn.naver?code=005930)
- Naver 시장 전체 투자자별: [https://finance.naver.com/sise/investorDealTrendDay.naver](https://finance.naver.com/sise/investorDealTrendDay.naver)
- Naver robots.txt: [https://finance.naver.com/robots.txt](https://finance.naver.com/robots.txt)
- KRX 메인 공개 페이지: [https://data.krx.co.kr/contents/MDC/MAIN/main.jspx](https://data.krx.co.kr/contents/MDC/MAIN/main.jspx)
- KRX 공개 인덱스 페이지: [https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?vsView=Y](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?vsView=Y)
