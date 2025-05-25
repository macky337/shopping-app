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

# ポートを公開
EXPOSE 8501

# コンテナ起動時に Streamlit を起動（IPv6/IPv4両方でバインド）
CMD ["bash", "-lc", "streamlit run app.py --server.port $PORT --server.address ::"]
