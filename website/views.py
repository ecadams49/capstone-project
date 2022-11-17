from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from . import db
import json
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import io
from io import BytesIO
import pmdarima as pm
from pmdarima.model_selection import train_test_split
import altair as alt
import os
import pandas_datareader.data as web
import arch

from rq import Queue
from worker import conn

q = Queue(connection=conn)

views = Blueprint('views', __name__)

from flask import Flask, request
import requests
# app = Flask(__name__)

@views.route('/getmsg/', methods=['GET'])
def respond():
    # Retrieve the name from the url parameter /getmsg/?name=
    name = request.args.get("name", None)

    # For debugging
    print(f"Received: {name}")

    response = {}

    # Check if the user sent a name at all
    if not name:
        response["ERROR"] = "No name found. Please send a name."
    # Check if the user entered a number
    elif str(name).isdigit():
        response["ERROR"] = "The name can't be numeric. Please send a string."
    else:
        response["MESSAGE"] = f"Welcome {name} to our awesome API!"

    # Return the response in json format
    return jsonify(response)


@views.route('/post/', methods=['POST'])
def post_something():
    name = request.form.get('name')
    print(name)
    # You can add the test cases you made in the previous function, but in our case here you are just testing the POST functionality
    if name:
        return jsonify({
            "Message": f"Welcome {name} to our awesome API!",
            # Add this option to distinct the POST request
            "METHOD": "POST"
        })
    else:
        return jsonify({
            "ERROR": "No name found. Please send a name."
        })

@views.route('/coins', methods=['POST'])
def get_coins():

    return jsonify(get_coins_dict())
    

def get_coins_dict():
    currencies=requests.get('https://api.coingecko.com/api/v3/exchange_rates')
    rates=currencies.json()['rates']
    keys=rates.keys()
    currency_names={}
    for key in keys:
        name=rates[key]['name']
        if name=='US Dollar':
            continue
        if name=='Ether':
            name='Ethereum'
        if rates[key]['type']!='commodity':
            currency_names[name]=(key,rates[key]['type'])
    
    return currency_names

@views.route('/model', methods=['POST'])
def call_model():
    coin_value=request.json[0]
    #daily_forecasts=model(coin_value,'daily')
    daily_forecasts = q.enqueue(model,coin_value,'daily')
    daily_forecasts_id = daily_forecasts.id
    print('daily forecasts', daily_forecasts)
    print('daily forecast id', daily_forecasts_id)
    #chart_daily=get_chart('daily')
    chart_daily = q.enqueue(get_chart,'daily')
    chart_daily_id = chart_daily.id
    #monthly_forecasts=model(coin_value,'monthly')
    monthly_forecasts = q.enqueue(model,coin_value,'monthly')
    monthly_forecasts_id = monthly_forecasts.id
    #chart_monthly=get_chart('monthly')
    chart_monthly = q.enqueue(get_chart,'monthly')
    chart_monthly_id = chart_monthly.id
   
    return jsonify({'daily_forecasts_id':daily_forecasts_id, 'monthly_forecasts_id':monthly_forecasts_id,
                    'chart_daily_id':chart_daily_id,'chart_monthly_id':chart_monthly_id})

@views.route('/job', methods=['GET'])
def get_job_id():
    # Retrieve the name from the url parameter /job?name=
    id = request.args.get("id", None)
    job = q.fetch_job(id)
    state = job.is_finished
    print('id', id)
    print('job', job)
    print('state', state)
    if job.is_finished:
        return jsonify({'id':id, 'result':job.result})
    return jsonify({'id':id,'state':state})

@views.route('/')
@login_required
def home():
    # A welcome message to test our server
    return render_template('home.html',user=current_user)

def daily_prices(coin):
    for cn in get_coins_dict().values():
        if cn[0]==coin:
            if cn[1]=='crypto':
                coin=cn[0].upper() + '-USD'
            elif cn[1]=='fiat':
                coin=cn[0].upper() + 'USD=X'
    
    n=1500
    try:
        start_date=datetime.now()+relativedelta(years=-6)
        end_date=datetime.now()
        get = web.DataReader(coin, 'yahoo', start=start_date, end=end_date)
        df_get = pd.DataFrame(get['Adj Close']).rename(columns={'Adj Close':'Price'}).dropna()
        if len(df_get)>=n:
            coin_ts=df_get.query('Price.notnull()')
    except:
        pass

    return coin_ts

def monthly_prices(coin):
    coin_ts=daily_prices(coin).reset_index().query('Price.notnull()')
    coin_ts = pd.DataFrame(coin_ts.groupby(pd.Grouper(key='Date',freq='M')).mean(),columns=['Price'])

    return coin_ts

def model(coin,freq):
    if freq.lower()=='daily' or freq.lower()=="d":
        freq='daily'
        f=30  # Length of Forecast Period in days.
        n=1
        data=daily_prices(coin)
        #t=2192 # Maximum of 6 years of daily prices.
        #if len(data)<t:
        t=len(data)
        #start_graph=-t+f+1460
        #coin_model=pm.AutoARIMA(max_p=10, max_q=10, maxiter=50, suppress_warnings=True,trace=False)
        #train = data[-t+f:-f]
        train=data
        coin_model=pm.auto_arima(train,max_p=10, max_q=10, maxiter=50, suppress_warnings=True,trace=False)
        var='Daily Price'
    elif freq.lower()=='monthly' or freq.lower()=="m":
        freq='monthly'
        f=12  # Length of Forecast Period in months.
        n=2
        data=monthly_prices(coin)
        #t=72  # Maximum of 6 years of monthly prices.
        #if len(data)<t:
        t=len(data)
        #start_graph=-t+f+12
        #coin_model=pm.AutoARIMA(seasonal=True,m=12,max_p=10, max_q=10, maxiter=50, suppress_warnings=True,trace=False)
        #train = data[-t+f:-f]
        train=data
        coin_model=pm.auto_arima(train,seasonal=True,m=12, max_p=10, max_q=10, maxiter=50, suppress_warnings=True,trace=False)
        var='Average Monthly Price'
 
    coin_predict = coin_model.predict_in_sample()
    #coin_predict_df = pd.DataFrame(coin_predict,index=train.index,columns=[var])
    coin_predict_df = pd.DataFrame(coin_predict,index=train.index).rename(columns={'predicted_mean':var})

    forecasts = coin_model.predict(n_periods=f)
    
    if len(data)==len(train):
        forecast_date_list=[]
        base=data.index[-1]
        for i in range(f):
            if freq.lower()=='daily' or freq.lower()=="d":
                new_date=base + timedelta(days=i+1)
            elif freq.lower()=='monthly' or freq.lower()=="m":
                new_date=base + relativedelta(months=i+1)
            forecast_date_list.append(new_date)
    else:
        forecast_date_list=data.index[-f:]

    #forecasts_df=pd.DataFrame(forecasts,index=forecast_date_list,columns=[var])
    forecasts_df=pd.DataFrame(forecasts,columns=[var])
    forecasts_df['Date']=forecast_date_list
    forecasts_df=forecasts_df.set_index('Date')
    #forecasts_df.index.name='Date'

    train["Label"]='True Values'
    coin_predict_df["Label"]='Model Predictions'
    forecasts_df["Label"]='Forecasts'
    full_df=pd.concat([train.reset_index(),
                       coin_predict_df.reset_index().rename(columns={var:'Price'}),
                       forecasts_df.reset_index().rename(columns={var:'Price'}) 
                      ])

    labels = full_df['Label'].unique()
    colours = ['blue', 'red', 'green']

    chart_start_date=forecast_date_list[0] + relativedelta(years=-n)
    chart=alt.Chart(full_df[full_df.Date>=chart_start_date]).mark_line().\
                    encode(alt.X('Date:T'),
                           alt.Y('Price:Q', title=(coin+' Price ($)')),
                           alt.Color('Label',scale=alt.Scale(domain=labels, range=colours)),
                           #alt.OpacityValue(0.7),
                           tooltip=[alt.Tooltip('Label'),
                                    alt.Tooltip('Date'),
                                    alt.Tooltip('Price')
                                   ]
                          ).\
                    properties(title=var+'s').\
                    interactive()
                    #).add_selection(select_date).\
                    # transform_filter(select_date)

    chart.save("chart_"+freq+".json")
    
    return forecasts_df.drop(columns=['Label']).to_html()

def get_chart(freq):
    if freq.lower()=='daily' or freq.lower()=="d":
        freq='daily'
    elif freq.lower()=='monthly' or freq.lower()=="m":
        freq='monthly'

    #with open("chart_"+freq+".html", "r") as f:
    #    return f.read()
    
    with open("chart_"+freq+".json", "rb") as f:
        j = json.load(f)
        return j
    
    