#!/bin/bash

export PATH=$PATH:/usr/bin
export CHROME_BIN=/usr/bin/chromium
export CHROMEDRIVER_PATH=/usr/bin/chromedriver

streamlit run market_dashboard.py --server.port=$PORT --server.enableCORS=false
