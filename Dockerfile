FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係を先にコピーしてキャッシュ利用
COPY requirements.txt ./
# 必要最小限のツールをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/* \
    # pipでパッケージインストール
    && pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# プロジェクトの .streamlit/config.toml をコンテナ内ユーザー設定へコピー
RUN mkdir -p /root/.streamlit && cp .streamlit/config.toml /root/.streamlit/config.toml

# デフォルトポート設定
ENV PORT=8501
# ポートを公開
EXPOSE 8501

# コンテナ起動時に Streamlit を起動（JSON 形式でシグナルハンドリング対応）
CMD ["bash", "-lc", "streamlit run app.py --server.address=0.0.0.0 --server.port $PORT --server.headless true --server.enableCORS false --server.enableXsrfProtection false"]
