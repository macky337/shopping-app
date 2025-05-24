#!/bin/bash

mkdir -p ~/.streamlit/

echo "[server]
headless = true
enableCORS = false
enableXsrfProtection = false
address = \"0.0.0.0\"
" > ~/.streamlit/config.toml

# Add port configuration separately to ensure proper expansion of PORT variable
if [ -z "${PORT}" ]; then
    echo "port = 8501" >> ~/.streamlit/config.toml
else
    echo "port = ${PORT}" >> ~/.streamlit/config.toml
fi
