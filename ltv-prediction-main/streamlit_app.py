import streamlit as st
import numpy as np
import pandas as pd
from datetime import date
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

st.title("📈 LTV Prediction")

st.markdown('''
    **This dashboard will help you to figure out your users' Lifetime Value.**

    Last Update: 2024-05-09
    
    Just type in some numbers that you most likely got from your Google Play Store or Apple App Store.
    
    **How it works:**
    
    - the program tries to find a curve for the given points of your retention rate
    - please be gentle as there is no sanity check right now :)
    - e.g. your day 30 retention shouldn't be greater than your day 1 retention, etc.
    - then the program calculates many different scenarios and tries to find a point in time to satisfy your ROAS goal
    - e.g. ROAS goal of 120% would mean that you spend 1 USD and get back 1.20 USD
    - if the Break-Even Day variable is 0, that means that the algorithm couldn't find a point where you are running ROI positive with the given numbers  
    - this program is right now in an early version, so don't spend your entire marketing budget on these values :)
    - let me know if you have found a bug or have some feature requests ;)
    
    Made by Sven Jürgens
    
    https://www.linkedin.com/in/svenjuergens/  
    http://svenjuergens-consulting.com/
    
    ''')

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Retention Rates")

    day_1_retention = st.number_input('Type in your Day 1 retention %', min_value=0.0, max_value=100.0, value=30.5)
    day_7_retention = st.number_input('Type in your Day 7 retention %', min_value=0.0, max_value=100.0, value=10.5)
    day_30_retention = st.number_input('Type in your Day 30 retention %', min_value=0.0, max_value=100.0, value=3.5)

with col2:
    st.header("ARPDAU, CPI, ROAS")

    arpdau = st.number_input('Type in your ARPDAU USD', min_value=0.0, max_value=100.0, value=0.5)
    arpdau = float(arpdau)

    cpi = st.number_input('Type in your CPI USD', min_value=0.0, max_value=100.0, value=1.0)
    cpi = float(cpi)

    roas = st.number_input('Type in your ROAS goal %', min_value=0.0, max_value=500.0, value=120.0)
    roas = int(roas)

st.header("Predicted Day in the future")
end_day = st.number_input('Type in the end day for your prediction, e.g. 30, 60, 360', min_value=0, max_value=360, value=90)

# Read the CSV file into DataFrame
url_retention = "https://raw.githubusercontent.com/svenjuergens84/ltv-prediction/main/final_retention_clean_row_grouped.csv"
grouped_df = pd.read_csv(url_retention, usecols=['geo', 'day', 'genre_name', 'value'])
grouped_df = grouped_df.rename(columns={'value': 'retention_value'})

# Get unique genre and geo names
genre_names = grouped_df['genre_name'].unique()
geo_names = grouped_df['geo'].unique()

url_arpdau = "https://raw.githubusercontent.com/svenjuergens84/ltv-prediction/main/final_arpdau_clean_row_grouped.csv"
grouped_arpdau_df = pd.read_csv(url_arpdau, usecols=['metric', 'geo', 'genre_name', 'value'])
grouped_arpdau_df = grouped_arpdau_df.rename(columns={'value': 'arpdau_value'})

st.header("Game Retention Benchmarks")
st.write("❤️ The benchmarks are shared by the awesome folks at https://gameanalytics.com")
st.write("If you don't have a game, just leave it as default. This will not influence your LTV calculation")

# Streamlit UI components for selecting genre and geo
selected_genre = st.selectbox("Select your game genre:", genre_names)
selected_geo = st.selectbox("Select your main geo:", geo_names)

def filter_data(selected_genre, selected_geo):
    filtered_data = grouped_df[(grouped_df['genre_name'] == selected_genre) & 
                               (grouped_df['geo'] == selected_geo) & 
                               (grouped_df['day'].isin([1, 7, 28]))]
    return filtered_data.sort_values(by='day')

# Call the filter function to get filtered DataFrame
selected_data = filter_data(selected_genre, selected_geo)

def filter_arpdau_data(selected_genre, selected_geo):
    filtered_data = grouped_arpdau_df[(grouped_arpdau_df['genre_name'] == selected_genre) & 
                               (grouped_arpdau_df['geo'] == selected_geo)]
    return filtered_data

selected_arpdau_data = filter_arpdau_data(selected_genre, selected_geo)

benchmark_x = selected_data["day"]
benchmark_y = selected_data["retention_value"]/100
benchmark_arpdau = selected_arpdau_data[selected_arpdau_data['metric'] == 'arpdau']['arpdau_value'].values[0]

# Display the filtered DataFrame
st.write(selected_data)
st.write(selected_arpdau_data)

today = str(date.today()) #prepare the "today" variable with the US formatted date --> for writing it into the file name

x = [1, 7, 30] #days, e.g. 1, 7, 14, 30
y = [float(day_1_retention)/100,
     float(day_7_retention)/100,
     float(day_30_retention)/100]

currency = "$"

def PrintCurrentSettings(arpdau, cpi, roas, x_values, y_values):
    print("CURRENT SETTINGS:")
    print("ARPDAU $: " + str(arpdau))
    print("CPI $: " + str(cpi))
    print("ROAS Goal %: " + str(roas))
    print("RETENTION RATES: " + str(y_values))
    print("DAYS: " + str(x_values))
    print("----------")

def PowerLawFunction(x, a, b):
    return a * x** -b

def FindNewY(a, b, x):
    #y = ax^b
    new_y = a * x** -b
    return new_y

def GetLTV(arpdau, end_day, x_values, y_values):
    sum_list = []
    sum_list.append(1)
    for i in range(1, end_day):
        y_value = FindNewY(GetParametersOfCurveFit(x_values, y_values)[0], GetParametersOfCurveFit(x_values, y_values)[1], i)
        sum_list.append(y_value)
    ltv = sum(sum_list) * arpdau
    ltv = round(ltv, 3)
    return ltv

def GetStandardDayLTV(arpdau, x_values, y_values):
    ltv_dict = {}
    print("")
    print("LTV OVERVIEW:")
    day_list = [1, 3, 7, 14, 30, 60, 90, 360] #provide a list with days that should be printed out 
    sum_list = []
    sum_list.append(1)
    for day in range(1, 721): #provide a range that should be searched by to find the LTV per day (should be higher than max num of day_list)
        y_value = FindNewY(GetParametersOfCurveFit(x_values, y_values)[0], GetParametersOfCurveFit(x_values, y_values)[1], day)
        sum_list.append(y_value)
    for x in day_list:
        ltv_estimate = sum(sum_list[0:x+1]) * arpdau
        ltv_dict[x] = round(ltv_estimate, 2)
        print("LTV (D" + str(x) + ") $: " + str(round(ltv_estimate, 2)))
    print("----------")
    return ltv_dict

def GetDetailedDayLTV(arpdau, x_values, y_values, end_day_obj):
    ltv_dict = {}
    sum_list = []
    sum_list.append(1)
    for day in range(1, 721): 
        y_value = FindNewY(GetParametersOfCurveFit(x_values, y_values)[0], GetParametersOfCurveFit(x_values, y_values)[1], day)
        sum_list.append(y_value)
    for x in range(end_day_obj):
        ltv_estimate = sum(sum_list[0:x+1]) * arpdau
        ltv_dict[x] = round(ltv_estimate, 2)
    return ltv_dict

def GetLifetimeDays(end_day, x_values, y_values):
    sum_list = []
    for i in range(1, end_day):
        y_value = FindNewY(GetParametersOfCurveFit(x_values, y_values)[0], GetParametersOfCurveFit(x_values, y_values)[1], i)
        sum_list.append(y_value)
    lifetime = round(sum(sum_list), 3)
    return lifetime

def ROASCalculator(ltv, cpi):
    roas = round(ltv / cpi * 100, 3)
    return roas

def CalculateBreakEvenDay(x_values, y_values, roas_goal, arpdau, cpi):
    print("")
    print("BREAK EVEN DAY OVERVIEW:")
    sum_list = []
    sum_list.append(1)
    for i in range(1, 721):
        y_value = FindNewY(GetParametersOfCurveFit(x_values, y_values)[0], GetParametersOfCurveFit(x_values, y_values)[1], i)
        sum_list.append(y_value)
        ltv = sum(sum_list) * arpdau
        roas = ROASCalculator(ltv, cpi)
        if roas >= roas_goal:
            break_even_day = i
            print("Break Even Day with ROAS goal of " + str(roas_goal) + "%: D" + str(break_even_day))
            print("LTV: $" + str(round(ltv, 3)))
            print("ROAS: " + str(roas) + "%")
            break
        else:
            break_even_day = 0
    print("----------")
    return break_even_day

def GetParametersOfCurveFit(x_values, y_values):
    parameters = curve_fit(PowerLawFunction, x_values, y_values)
    a = parameters[0][0]
    b = parameters[0][1]
    return [a, b]

PrintCurrentSettings(arpdau, cpi, roas, x, y)

print("")

print("POWER CURVE PARAMETER:")
print("a: " + str(GetParametersOfCurveFit(x, y)[0]))
print("b: " + str(GetParametersOfCurveFit(x, y)[1]))
print("----------")

print("LTV OVERVIEW:")
print("LTV: $" + str(GetLTV(arpdau, end_day, x, y)))
print("LTV Lifetime: " + str(GetLifetimeDays(end_day, x, y)))
print("ROAS: " + str(ROASCalculator(GetLTV(arpdau, end_day, x, y), cpi)) + "%")
print("----------")

break_even_day = CalculateBreakEvenDay(x, y, roas, arpdau, cpi)

df_ltv_values = pd.DataFrame.from_dict(GetDetailedDayLTV(arpdau, x, y, end_day), orient='index')

def display_results():
    st.header('📊 Results')

    st.subheader("Input Parameters")
    st.write("**Day 1 Retention:** ", day_1_retention)
    st.write("**Day 7 Retention:** ", day_7_retention)
    st.write("**Day 30 Retention:** ", day_30_retention)
    st.write("**ARPDAU:** ", currency + str(arpdau))
    st.write("**CPI:** ", currency + str(cpi))
    st.write("**ROAS Goal:** ", str(roas) + "%")

    st.subheader("Predicted Metrics")
    st.write("**Power Curve Parameters:**")
    st.write("a: " + str(GetParametersOfCurveFit(x, y)[0]))
    st.write("b: " + str(GetParametersOfCurveFit(x, y)[1]))

    st.write("**LTV:** ", currency + str(GetLTV(arpdau, end_day, x, y)))
    st.write("**LTV Lifetime:** ", str(GetLifetimeDays(end_day, x, y)))
    st.write("**ROAS:** ", str(ROASCalculator(GetLTV(arpdau, end_day, x, y), cpi)) + "%")
    st.write("**Break Even Day:** ", str(break_even_day) if break_even_day else "Not reached within 720 days")

    st.subheader("LTV Overview")
    ltv_dict = GetStandardDayLTV(arpdau, x, y)
    for day, ltv in ltv_dict.items():
        st.write(f"LTV (D{day}): ${ltv}")

    st.subheader("Detailed LTV Values")
    st.write(df_ltv_values)

    st.subheader("Retention Rate Curves")
    fig, ax = plt.subplots()
    days_range = np.arange(1, end_day + 1)
    fitted_curve = PowerLawFunction(days_range, GetParametersOfCurveFit(x, y)[0], GetParametersOfCurveFit(x, y)[1])
    ax.plot(days_range, fitted_curve, label='Fitted Retention Curve')
    ax.scatter(x, y, color='red', label='Input Data')
    ax.set_xlabel('Days')
    ax.set_ylabel('Retention Rate')
    ax.set_title('Retention Rate Curve')
    ax.legend()
    st.pyplot(fig)

display_results()

st.markdown("Benchmark data used in this application is sourced from [GameAnalytics](https://gameanalytics.com).")




