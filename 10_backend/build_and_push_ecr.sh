#!/usr/bin/env bash
set -e

########################################
# 1. 환경 변수
########################################
AWS_ACCOUNT_ID="864785582947"
REGION="ap-northeast-2"
REPO_NAME="caffein/backend"
IMAGE_TAG="latest"

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"

echo "ECR URI  : $ECR_URI"
echo "Region   : $REGION"
echo "Repo     : $REPO_NAME"
echo

########################################
# 2. ECR 로그인
########################################
echo "ECR 로그인 중..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
echo "ECR 로그인 완료"
echo

########################################
# 3. buildx 플랫폼 빌드 + Push
########################################
echo "Docker 이미지를 linux/amd64 플랫폼으로 빌드 후 ECR로 Push합니다..."

docker buildx build \
  --platform linux/amd64 \
  -t "$ECR_URI" \
  --push \
  .

echo "=== 완료 ==="
echo "ECR에 amd64 이미지가 업로드되었습니다."
