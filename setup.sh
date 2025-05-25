#!/bin/bash

mkdir -p ~/.streamlit/

echo "[server]
headless = true
enableCORS = false
enableXsrfProtection = false
address = \"0.0.0.0\"
port = ${PORT:-8501}
" > ~/.streamlit/config.toml
