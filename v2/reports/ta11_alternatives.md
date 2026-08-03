# TA11 대안 검증: 수익 분해 + 미국 시장

유니버스: 유동성 상위 150종목, 상하위 5% 롱숏, 일간 리밸런스.

## 1. 수익 분해 - 알파가 어디 있나
- open_to_open: t+1 시가 진입 -> t+2 시가 청산 (기존 가정)
- intraday_only: t+1 시가 진입 -> t+1 종가 청산
- overnight_only: t+1 종가 진입 -> t+2 시가 청산
- alpha_bps = 회전율 1단위당 수익. 이 값이 실행비용보다 커야 생존.

| market | leg | period | alpha_bps | gross_sharpe | gross_ann | avg_turnover |
| --- | --- | --- | --- | --- | --- | --- |
| KOSPI | open_to_open | train | 19.5942 | 2.1890 | 0.7461 | 1.5109 |
| KOSPI | open_to_open | test | 17.8657 | 1.9093 | 0.6633 | 1.4732 |
| KOSPI | intraday_only | train | 15.6684 | 2.3255 | 0.6545 | 1.6575 |
| KOSPI | intraday_only | test | 12.2225 | 1.7900 | 0.5377 | 1.7459 |
| KOSPI | overnight_only | train | 2.5617 | 0.6078 | 0.1070 | 1.6575 |
| KOSPI | overnight_only | test | 3.0452 | 0.7376 | 0.1340 | 1.7459 |
| US_SP500 | open_to_open | train | 2.2510 | 0.3721 | 0.1027 | 1.8104 |
| US_SP500 | open_to_open | test | 2.2388 | 0.4260 | 0.1063 | 1.8839 |
| US_SP500 | intraday_only | train | 0.6510 | 0.1349 | 0.0315 | 1.9195 |
| US_SP500 | intraday_only | test | 3.5922 | 0.8882 | 0.1809 | 1.9983 |
| US_SP500 | overnight_only | train | 1.4545 | 0.4756 | 0.0704 | 1.9195 |
| US_SP500 | overnight_only | test | -1.7602 | -0.5937 | -0.0886 | 1.9983 |

## 2. 비용 사다리
| market | leg | cost_bps | period | sharpe | ann_return | win_rate | max_dd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KOSPI | open_to_open | 0 | train | 2.1890 | 0.7461 | 0.5603 | -0.3427 |
| KOSPI | open_to_open | 0 | test | 1.9093 | 0.6633 | 0.5590 | -0.2280 |
| KOSPI | open_to_open | 3 | train | 1.8539 | 0.6318 | 0.5441 | -0.3763 |
| KOSPI | open_to_open | 3 | test | 1.5885 | 0.5519 | 0.5557 | -0.2566 |
| KOSPI | open_to_open | 10 | train | 1.0718 | 0.3653 | 0.5228 | -0.4640 |
| KOSPI | open_to_open | 10 | test | 0.8403 | 0.2920 | 0.5279 | -0.3194 |
| KOSPI | open_to_open | 18 | train | 0.1781 | 0.0607 | 0.4833 | -0.5829 |
| KOSPI | open_to_open | 18 | test | -0.0143 | -0.0050 | 0.4984 | -0.4582 |
| KOSPI | open_to_open | 25 | train | -0.6035 | -0.2058 | 0.4539 | -0.7535 |
| KOSPI | open_to_open | 25 | test | -0.7615 | -0.2649 | 0.4689 | -0.6593 |
| US_SP500 | intraday_only | 0 | train | 0.1349 | 0.0315 | 0.4722 | -0.5827 |
| US_SP500 | intraday_only | 0 | test | 0.8882 | 0.1809 | 0.4950 | -0.1669 |
| US_SP500 | intraday_only | 2 | train | -0.2796 | -0.0653 | 0.4652 | -0.6678 |
| US_SP500 | intraday_only | 2 | test | 0.3937 | 0.0802 | 0.4851 | -0.2073 |
| US_SP500 | intraday_only | 5 | train | -0.9014 | -0.2104 | 0.4513 | -0.7821 |
| US_SP500 | intraday_only | 5 | test | -0.3481 | -0.0709 | 0.4520 | -0.3193 |
| US_SP500 | intraday_only | 10 | train | -1.9372 | -0.4522 | 0.4165 | -0.9055 |
| US_SP500 | intraday_only | 10 | test | -1.5843 | -0.3227 | 0.4255 | -0.5864 |
| US_SP500 | open_to_open | 0 | train | 0.3721 | 0.1027 | 0.4920 | -0.4800 |
| US_SP500 | open_to_open | 0 | test | 0.4260 | 0.1063 | 0.4901 | -0.4283 |
| US_SP500 | open_to_open | 2 | train | 0.0415 | 0.0114 | 0.4771 | -0.5968 |
| US_SP500 | open_to_open | 2 | test | 0.0454 | 0.0113 | 0.4801 | -0.4807 |
| US_SP500 | open_to_open | 5 | train | -0.4545 | -0.1254 | 0.4602 | -0.7351 |
| US_SP500 | open_to_open | 5 | test | -0.5254 | -0.1311 | 0.4603 | -0.5505 |
| US_SP500 | open_to_open | 10 | train | -1.2809 | -0.3535 | 0.4344 | -0.8795 |
| US_SP500 | open_to_open | 10 | test | -1.4765 | -0.3685 | 0.4354 | -0.6528 |

## Caveats
- 미국: adj OHLC 사용(배당/분할 조정). S&P500 현 구성 기준이라 생존편향 있음.
- 미국 비용: 증권거래세 없음, 수수료 ~0, 스프레드 대형주 1~2bp. 공매도는 대차 가능.
- intraday_only / overnight_only 는 매일 전량 청산이라 회전율 정의가 다름(진입+청산 = 1.0).
