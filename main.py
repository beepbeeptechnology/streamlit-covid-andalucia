from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd
import altair as alt
import io
import requests


# cached data import function
@st.cache
def get_data(url, today_date):
    source = requests.get(url, verify=False).content
    source_data = pd.read_csv(io.StringIO(source.decode('utf-8')))
    data_dict = {"data_date": today_date, "data": source_data}
    return data_dict

# add header with last data refresh time
today_date = datetime.now()
today_date_hour_rounded = today_date.replace(second=0, microsecond=0, minute=0)

# page header
st.title('Covid-19: Andalucía')
device_type = st.radio('Dispositivo', ['Mobile', 'Desktop'], index=0)

# get data from url
source_csv_url = "https://www.juntadeandalucia.es/institutodeestadisticaycartografia/badea/stpivot/stpivot/Print?cube=387d5cdb-7026-4f4b-beb2-fb7e511cc485&type=3&foto=si&ejecutaDesde=&codConsulta=39409&consTipoVisua=JP"
source_data = get_data(source_csv_url, today_date_hour_rounded)
source_csv_data = source_data['data']
today_date = source_data['data_date']

# set chart defaults based on device
if device_type == 'Desktop':
    chart_width = 680
    chart_height = 400
    trellis_chart_width = 300
    trellis_chart_height = 200
    trellis_chart_columns = 2
    title_font_size = 20
    intial_date_from = today_date - timedelta(days=90)

else:
    chart_width = 310
    chart_height = 250
    trellis_chart_width = 260
    trellis_chart_height = 200
    trellis_chart_columns = 1
    title_font_size = 20

    intial_date_from = today_date - timedelta(days=45)

# get column names as list
source_csv_columns = source_csv_data.columns.tolist()[0]
source_csv_columns_list = source_csv_columns.split(';')

# split column on semicolon
source_csv_column_name = source_csv_data.columns[0]
split_data = source_csv_data[source_csv_column_name].str.split(';', expand=True)

# rename columns
split_data.columns = source_csv_columns_list

# drop empty column
clean_dataframe = split_data.drop(split_data.columns[4], axis=1)

# split out day, month, year
clean_dataframe[['d', 'm', 'y']] = clean_dataframe['Fecha diagnóstico'].str.split('/', expand=True)
clean_dataframe['fecha_iso'] = clean_dataframe['y'] + "-" + clean_dataframe['m'] + "-" + clean_dataframe['d']
clean_dataframe['fecha'] = clean_dataframe['fecha_iso'].astype('datetime64')

# correct data types and drop input date column
clean_dataframe['Valor'] = clean_dataframe['Valor'].astype('int')
clean_dataframe = clean_dataframe.drop(['Fecha diagnóstico'], axis=1)

# set min/max dates for sidebar selector
min_date = clean_dataframe['fecha'].min()
max_date = clean_dataframe['fecha'].max()
date_from = st.date_input('Fecha desde', value=intial_date_from, min_value=min_date, max_value=max_date, key='date_from')

time_from = datetime.min.time()
datetime_from = datetime.combine(date_from, time_from)

# get metrics for sidebar selector
metrics = list(clean_dataframe['Medida'].unique())
metric_selected = st.selectbox('Medida', metrics, index=1, key='metric_selected')

# header: latest data
st.markdown(f"`Última fecha de datos: {max_date.date()}`")

# filter for date and metric selected
clean_dataframe_date = clean_dataframe[(clean_dataframe['fecha'] >= datetime_from)]
clean_dataframe_out = clean_dataframe_date[clean_dataframe_date['Medida'] == metric_selected]


# Andalucia
andalucia = clean_dataframe_out[clean_dataframe_out['Territorio'] == 'Andalucía']

# Andalucia chart
andalucia_chart = alt.Chart(andalucia).mark_bar().encode(
    x=alt.X('fecha:T', title='Fecha'),
    y=alt.Y('Valor:Q', title=metric_selected),
    tooltip=[alt.Tooltip('Territorio:O', title='Territorio'),
             alt.Tooltip('fecha:T', title='Fecha', format='%a %d %b %Y'),
             alt.Tooltip('Valor:Q', format='.0f', title=metric_selected)]
).properties(width=chart_width, height=chart_height)

# Andalucia page content
st.markdown(f"## Andalucía: {metric_selected}")
st.write(andalucia_chart)

# Provincias data
provincias = clean_dataframe_out[clean_dataframe_out['Territorio'] != 'Andalucía']

# Provincias chart
facet_spacing = {"row": 50, "column": 20}

provincias_chart = alt.Chart(provincias).mark_bar().encode(
    x=alt.X('fecha:T', title='Fecha'),
    y=alt.Y('Valor:Q', title=metric_selected),
    tooltip=[alt.Tooltip('Territorio:O', title='Provincia'),
             alt.Tooltip('fecha:T', title='Fecha', format='%a %d %b %Y'),
             alt.Tooltip('Valor:Q', format='.0f', title=metric_selected)],
    facet=alt.Facet('Territorio:O', columns=trellis_chart_columns, title=None, header=alt.Header(labelFontSize=20), spacing=facet_spacing)
).properties(
    width=trellis_chart_width, height=trellis_chart_height
)

# only show single province if on desktop
if device_type == 'Desktop':
    # Single province
    st.markdown(f"## Provincia Unica: {metric_selected}")

    provincia_list = provincias['Territorio'].unique()
    provincia_selected = st.selectbox('Seleccione una provincia', options=provincia_list, index=3)
    single_provincia = provincias[provincias['Territorio'] == provincia_selected]


    #Single province chart
    single_provincia_chart = alt.Chart(single_provincia).mark_bar().encode(
        x=alt.X('fecha:T', title='Fecha'),
        y=alt.Y('Valor:Q', title=metric_selected),
        tooltip=[alt.Tooltip('Territorio:O', title='Provincia'),
                 alt.Tooltip('fecha:T', title='Fecha', format='%a %d %b %Y'),
                 alt.Tooltip('Valor:Q', format='.0f', title=metric_selected)]
    ).properties(width=chart_width, height=chart_height, title=provincia_selected
    ).configure_title(fontSize=title_font_size)

    st.write(single_provincia_chart)

# Page content: Multiple Provinces
st.markdown(f"## Provincias: {metric_selected}")
st.write(provincias_chart)



# Page footer
st.markdown(f"`Datos actualizados:  {today_date_hour_rounded} UTC`")

st.markdown("> #### Fuente de Datos: [Junta de Andalucía: Consejería de Salud y Familias](https://www.juntadeandalucia.es/institutodeestadisticaycartografia/badea/operaciones/consulta/anual/39409?CodOper=b3_2314&codConsulta=39409)")
st.markdown("> [![View Source on GitHub](https://assets.website-files.com/5eb1d49f3ed8c28a5a54769f/5eb7085ea11928da1d01a2d7_Github%20Icon.svg)](https://github.com/beepbeeptechnology/streamlit-covid-andalucia) View Source on GitHub ([beepbeep.technology](https://beepbeep.technology))")







