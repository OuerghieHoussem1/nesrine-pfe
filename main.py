import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

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

with data_tab:
    col1, col2 = st.container().columns(2)
    is_batteriespeichers = True
    with col1:
        uploaded_file1, uploaded_file2 = get_file_inputs("Upload File 1","Upload File 2")
        from_date,to_date = get_date_inputs("Von","Bis")
        chosen_option = get_radio_checkboxes(["Batteriespeichers","PV-anlage"])
        is_batteriespeichers = True if chosen_option == "Batteriespeichers" else False
        maximale_lack_leistung,maximale_entlade_leistung = get_number_inputs("Maximale lack leistung","maximale entlade leistung", are_disabled=not is_batteriespeichers)
        SOC_min,SOC_max = get_number_inputs("SOCmin","SOCmax", are_disabled=not is_batteriespeichers)
        lade_wirduns_grad,entlade_wirdruns_grad=get_number_inputs("ladewirdungsgrad","entladewirdungsgrad", are_disabled=not is_batteriespeichers)
    with col2:
        st.write("## Hello from data col 2!")


with result_tab:
    st.write("## Hello from results!")

# st.success("Nesrine's app started")