#!/bin/sh
# .env 값으로 웹 페이지용 설정 파일(config.js)을 만든다.
# 브라우저에 공개돼도 되는 API 키만 넣고, 비밀 키(AMPLITUDE_SECRET_KEY)는 절대 넣지 않는다.
# 사용법: sh scripts/build-config.sh
set -e
cd "$(dirname "$0")/.."
[ -f .env ] || { echo ".env 파일이 없습니다. .env.example을 복사해서 만드세요." >&2; exit 1; }
AMPLITUDE_API_KEY=$(grep -E '^AMPLITUDE_API_KEY=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
[ -n "$AMPLITUDE_API_KEY" ] || { echo "AMPLITUDE_API_KEY 값이 비어 있습니다." >&2; exit 1; }
cat > config.js <<JS
// 자동 생성 파일 — 직접 수정하지 말고 .env 수정 후 'sh scripts/build-config.sh' 실행
window.APP_CONFIG = {
  amplitudeApiKey: "$AMPLITUDE_API_KEY"
};
JS
echo "config.js 생성 완료"
