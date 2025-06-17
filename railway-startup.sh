#!/bin/bash
# Railway専用の起動スクリプト

set -e

echo "🚀 Starting RAGFlow on Railway..."

# 環境変数の設定
export PYTHONPATH=/ragflow
export NODE_ENV=production
export TIMEZONE=Asia/Tokyo

# ポート設定（RailwayはPORT環境変数を自動設定）
if [ -n "$PORT" ]; then
    echo "Using Railway provided port: $PORT"
    export SVR_HTTP_PORT=$PORT
else
    echo "Using default port: 9380"
    export SVR_HTTP_PORT=9380
fi

# ログディレクトリの作成
mkdir -p /ragflow/logs

echo "📚 Loading Sunzi Art of War data..."
# 孫子の兵法データが正しく配置されているか確認
if [ -d "/ragflow/data/sonshi" ]; then
    echo "✅ Sunzi data found"
    ls -la /ragflow/data/sonshi/
else
    echo "⚠️  Sunzi data not found, creating directory..."
    mkdir -p /ragflow/data/sonshi
fi

echo "🔧 Starting RAGFlow API server..."
# RAGFlowのAPIサーバーを起動
cd /ragflow
python api/ragflow_server.py --host 0.0.0.0 --port $SVR_HTTP_PORT

echo "🎉 RAGFlow started successfully!"