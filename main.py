import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
st.set_page_config(page_title="BSS-Optimierungstool", layout="wide")

#Registerkarten erstellen
data_tab, result_tab = st.tabs(["Eingangsdaten","Ergebnisse"])

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
      file1 = st.file_uploader(label1,type=['csv', 'txt','xlsx'])

  with col2:
      file2 = st.file_uploader(label2,type=['csv', 'txt', 'xlsx'])

  return file1, file2

def get_radio_checkboxes(options):

  chosen_option = st.radio("Systemkomponent auswählen",options, horizontal=True)

  return chosen_option

def generate_data(num_points=100):
  x = list(range(num_points))
  y1 = [i**2 for i in x]  # Sample data for plot 1 (squared values)
  y2 = [i for i in x]    # Sample data for plot 2 (linear values)
  return x, y1, y2

with data_tab:
    col1, col2 = st.container().columns(2)
    is_Batteriespeicher = True
    with col1:
        uploaded_file1, uploaded_file2 = get_file_inputs("Lastprofildaten herunterladen","PV-Erzeugungsdaten herunterladen")
        from_date,to_date = get_date_inputs("Von","Bis")
        chosen_option = get_radio_checkboxes(["Batteriespeicher","PV-Anlage","Netzbetreiber"])
        is_Batteriespeicher = True if chosen_option == "Batteriespeicher" else False
        if(is_Batteriespeicher):
            Maximale_Ladeleistung,Maximale_Entladeleistung = get_number_inputs("Maximale Ladeleistung [kW]","Maximale Entladeleistung [kW]", are_disabled=not is_Batteriespeicher)
            SOC_min,SOC_max = get_number_inputs("SOCmin","SOCmax", are_disabled=not is_Batteriespeicher)
            Ladewirkunsgrad,Entladewirkunsgrad=get_number_inputs("Ladewirkungsgrad [%]","Entladewirkungsgrad[%]", are_disabled=not is_Batteriespeicher)
            Energiespezifische_Anschaffungskosten, Betriebs_und_Wartungskosten = get_number_inputs("Energiespezifische Anschaffungskosten [€/kWh]","Betriebs- und Wartungskosten [€]")
            Ersatzkosten = get_number_inputs("Ersatzkosten[€]")
            Strompreis = st.number_input("Strompreis", disabled=not is_Batteriespeicher)
        if(not is_Batteriespeicher):
            Maximale_Einspeisegrenze = st.number_input("Maximale_Einspeisegrenze [kW]", disabled=is_Batteriespeicher)
            Einspeisevergütung = st.number_input("Einspeisevergütung [€/kWh]", disabled=is_Batteriespeicher)
    with col2:
        # plot_width = st.slider('Plot Width (inches)', min_value=5.0, max_value=15.0, value=10.0)
        # plot_height = st.slider('Plot Height (inches)', min_value=3.0, max_value=8.0, value=5.0)

        fig, ax = plt.subplots(figsize=(12, 4))

        x, y1, y2 = generate_data()

        ax.plot(x, y1, label='Verbraucherlastprofil', color='blue')
        ax.plot(x, y2, label='PV-Erzeugungsprofil', color='red')

        ax.set_xlabel('Zeit')
        ax.set_ylabel('Leistung [kW]')
        fig.suptitle('Darstellung der Eingangsdaten')

        ax.legend()

        st.pyplot(fig)



        st.write("### Simulationsergebnisse")
        data = {"Beschreibung":
                ["Jahreshöchstlast",
                 "Jahresenergieverbrauch",
                 "Batteriespeicherkapazität",
                 "Eigenverbrauchsanteil ohne BSS",
                 "Eigenverbrauchsanteil mit BSS",
                 "Jährliche PV-Erzeugung",
                 "Gesamte Netzeinspeisung",
                 "Bezug dus PVA",
                 "Bezug aus BSS",
                 "Bezug aus Netz"
                 ],
                 "Werk":[
                    "kW",
                    "kWh/a",
                    "kWh",
                    "%",
                    "%",
                    "kWh/a",
                    "kWh",
                    "kWh",
                    "kWh",
                    "kWh",
                 ]
            }
        data_frame = pd.DataFrame(data, columns=("Beschreibung","Wert"))
        st.table(data_frame)


with result_tab:
    st.write("## Hello from results!")

# st.success("BSS-Optimierungstool startet")