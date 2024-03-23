import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
st.set_page_config(page_title="Nesrine PFE", layout="wide")

#Creating tabs
data_tab, result_tab = st.tabs(["Data","Results"])

def get_number_inputs(label1="Number 1", label2="Number 2", are_disabled=False):
  
  col1, col2 = st.columns(2)

  with col1:
      num1 = st.number_input(label1, disabled=are_disabled)

  with col2:
      num2 = st.number_input(label2,disabled=are_disabled)

  return num1, num2

def get_date_inputs(label1="Date one", label2="Date two"):

  col1, col2 = st.columns(2)

  with col1:
      date1 = st.date_input(label1)

  with col2:
      date2 = st.date_input(label2)

  return date1, date2

def get_file_inputs(label1="File one", label2="File two"):
  col1, col2 = st.columns(2)

  with col1:
      file1 = st.file_uploader(label1,type=['csv', 'txt'])

  with col2:
      file2 = st.file_uploader(label2,type=['csv', 'txt'])

  return file1, file2

def get_radio_checkboxes(options):

  chosen_option = st.radio("select mode",options, horizontal=True)

  return chosen_option

def generate_data(num_points=100):
  x = list(range(num_points))
  y1 = [i**2 for i in x]  # Sample data for plot 1 (squared values)
  y2 = [i for i in x]    # Sample data for plot 2 (linear values)
  return x, y1, y2

with data_tab:
    col1, col2 = st.container().columns(2)
    is_batteriespeichers = True
    with col1:
        uploaded_file1, uploaded_file2 = get_file_inputs("Upload File 1","Upload File 2")
        from_date,to_date = get_date_inputs("Von","Bis")
        chosen_option = get_radio_checkboxes(["Batteriespeichers","PV-anlage"])
        is_batteriespeichers = True if chosen_option == "Batteriespeichers" else False
        if(is_batteriespeichers):
            maximale_lack_leistung,maximale_entlade_leistung = get_number_inputs("Maximale lack leistung","maximale entlade leistung", are_disabled=not is_batteriespeichers)
            SOC_min,SOC_max = get_number_inputs("SOCmin","SOCmax", are_disabled=not is_batteriespeichers)
            lade_wirduns_grad,entlade_wirdruns_grad=get_number_inputs("ladewirdungsgrad","entladewirdungsgrad", are_disabled=not is_batteriespeichers)
            energiespezifische_anscchffglaste, betries_und_wastungsten = get_number_inputs("energiespezifische_anscchffglaste","betries_und_wastungsten")
            ensatzdostn, maximale_netzbezugleistung = get_number_inputs("ensatzdostn","maximale_netzbezugleistung")
            strompreis = st.number_input("strompreis", disabled=not is_batteriespeichers)
        if(not is_batteriespeichers):
            maximale_enspeisengreze = st.number_input("maximale_enspeisengreze", disabled=is_batteriespeichers)
            eimspeise_vergutung = st.number_input("eimspeise_vergutung", disabled=is_batteriespeichers)
    with col2:
        # plot_width = st.slider('Plot Width (inches)', min_value=5.0, max_value=15.0, value=10.0)
        # plot_height = st.slider('Plot Height (inches)', min_value=3.0, max_value=8.0, value=5.0)

        fig, ax = plt.subplots(figsize=(12, 4))

        x, y1, y2 = generate_data()

        ax.plot(x, y1, label='Squared Values', color='blue')
        ax.plot(x, y2, label='Linear Values', color='red')

        ax.set_xlabel('X-axis')
        ax.set_ylabel('Y-axis')
        fig.suptitle('Comparison of Squared vs. Linear Values')

        ax.legend()

        st.pyplot(fig)



        st.write("### Simulation sergebmisse")
        data = {"Beschrlibung":
                ["Jahrenhastlast",
                 "Jahresenrgereverbrand",
                 "Batteriedapazitat",
                 "Eigenverbranchentei",
                 "eigenverbrauchsenteil mit BSS",
                 "Netzeinspeusung",
                 "Gescente PV-erzeugung",
                 "Bezug dus PVA",
                 "Bezug aus BSS",
                 "Bezug aus Netz"
                 ],
                 "Werk":[
                    "KW",
                    "Kwh/a",
                    "dwh",
                    "%",
                    "%",
                    "dwh",
                    "dwh",
                    "kwh",
                    "kwh",
                    "kwh",
                 ]
            }
        data_frame = pd.DataFrame(data, columns=("Beschrlibung","Werk"))
        st.table(data_frame)


with result_tab:
    st.write("## Hello from results!")

# st.success("Nesrine's app started")