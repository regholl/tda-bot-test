mkdir -p ~/.streamlit/

echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
[theme]\n\
primaryColor = #E694FF\n\
backgroundColor = #00172B\n\
secondaryBackgroundColor = #0083B8\n\
textColor = #FFF\n\
font = sans serif\n\
" > ~/.streamlit/config.toml