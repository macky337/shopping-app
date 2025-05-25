#!/bin/bash

mkdir -p ~/.streamlit/

echo "[server]
headless = true
enableCORS = false
enableXsrfProtection = false
address = \"0.0.0.0\"
port = ${PORT:-8501}
" > ~/.streamlit/config.toml

# 設定後に Streamlit アプリを起動して永続化
exec streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
