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

# setup.sh を実行可能に
RUN chmod +x setup.sh

# ポートを公開
EXPOSE 8501

# デプロイ後の起動コマンド：Streamlit を外部アクセス（0.0.0.0）で起動
CMD ["bash", "-c", "bash setup.sh && exec streamlit run app.py"]
