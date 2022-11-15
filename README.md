# TDI capstone-project

### 1.	A clear business objective:
  *	World fiat currencies are being traded everyday against one another to the tune of trillions of dollars per day. Meanwhile, cryptocurrency has become a popular investment, and can also serve as a useful alternative to fiat currency for money transfers and will likely be part of the future of money.
  *	Foreign exchange rate forecasts is the cornerstone of most, if not all, international business and banking decisions. They are necessary to evaluate the foreign denominated cash flows involved in international transactions. Thus, foreign exchange rate forecasting is very important to evaluate the benefits and risks attached to the international business environment. Speculations based on foreign exchange rate forecasts provide the opportunity to create sizeable profits for businesses and banks.
  *	With respect to governments, a key role of central banks is to conduct monetary policy, to achieve price stability (low and stable inflation) for example, and to help manage economic fluctuations. Foreign exchange rate movement is regularly monitored by central banks for macroeconomic analysis and market surveillance purposes and these forecasts are an essential input in the monetary policy decision-making process.

### 2.	Data ingestion:
  *	A list of fiat and crypto currency names and symbols is extracted from CoinGecko (https://www.coingecko.com/).
  *	Six years of historical, time-series data of the daily Adjusted Closing Price for any currency in the list of currencies are extracted from Yahoo Finance. For the fiat currencies, the price is the exchange rate against the US dollar.
  *	Average monthly prices are calculated from the daily adjusted closing prices.

### 3.	Visualizations:
  *	Altair is used to generate the graphs in the website.

### 4. Machine Learning Algorithm:
  *	The initial Machine Learning algorithm utilized to forecast the currencies is an ARIMA model, using python’s auto_arima function.
  *	Also exploring integrating this with a GARCH model.

### 5.	A deliverable:
  *	Developed an interactive website (https://capstone-eric.herokuapp.com/) in which a user can select any one of over fifty fiat and crypto currencies and generate thirty (30) daily and twelve (12) monthly forecasts of prices for the currency selected. The forecasted price values, as well as interactive graphs of the time-series data vs the model predicted values, inclusive of the forecasts, are displayed. The website also includes user authentication.
