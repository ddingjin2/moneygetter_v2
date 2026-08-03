# Toss Invest integration status

- Date: 2026-05-31.
- Official product page: https://corp.tossinvest.com/ko/open-api
- Developer guide: https://developers.tossinvest.com/docs
- OpenAPI document URL discovered from the developer guide bundle: https://openapi.tossinvest.com/openapi-docs/latest/openapi.json

## Current implementation

- Added `scripts/toss_invest_client.py`.
- Added `config/toss_invest_config.example.json`.
- Added `tests/test_toss_invest_client.py`.
- Supported commands:
  - `check-env`: show masked Toss Invest environment/config status.
  - `fetch-openapi`: try to fetch and summarize the official OpenAPI spec.
  - `preview-orders`: summarize generated order CSV/latest_state.json without submitting.
  - `submit-orders`: intentionally blocked.

## Safety status

Live order submission is not implemented. This is intentional. The next safe step is to obtain approved Toss Invest Open API access, fetch the official OpenAPI spec from the same environment, verify authentication and account/balance read endpoints, then add order submission behind a separate safety review.

## Commands

```bash
python scripts/toss_invest_client.py check-env
python scripts/toss_invest_client.py fetch-openapi
python scripts/toss_invest_client.py preview-orders
```
