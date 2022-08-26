mkdir -p ~/.streamlit/

echo "[theme]
primaryColor='#E694FF'
backgroundColor='#00172B'
secondaryBackgroundColor='#0083B8'
font = 'sans serif'
[server]
headless = true
port = $PORT
enableCORS = false
" > ~/.streamlit/config.toml