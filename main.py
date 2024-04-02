import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pyomo.environ import *
from pyomo.environ import SolverFactory
import datetime
import os



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

def get_date_inputs(label1="Date one", label2="Date two", initialDateOne= datetime.date(2018,1,1), initialDateTwo = datetime.date(2018,1,2), keyOne="k1", keyTwo ="k2"):

  col1, col2 = st.columns(2)

  with col1:
      date1 = st.date_input(label1, value=initialDateOne, key=keyOne)

  with col2:
      date2 = st.date_input(label2,value=initialDateTwo, key=keyTwo)

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

def check_files(file1, file2):
    df_file1 = df_file2 = None
    if file1 is not None:
        try:
            df_file1 = pd.read_excel(file1)
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

        # Check if DataFrame has required columns (Zeit, Leistung)
        if file1 and ('Zeit' not in df_file1.columns or 'Last kW' not in df_file1.columns ):
            st.error("The uploaded file must contain columns named 'Zeit' and 'Leistung'.")
        

    if file2 is not None:
        try:
            df_file2 = pd.read_excel(file2)
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Check if DataFrame has required columns (Zeit, Leistung)
    if file2 and ('Zeit' not in df_file2.columns or 'Leistung' not in df_file2.columns):
        st.error("The uploaded file must contain columns named 'Zeit' and 'Leistung'.")
    
    return df_file1,df_file2

def filter_data(uploaded_file, df_file, from_date, to_date):

    filter_data = None

    if(uploaded_file):
        try:
            df_file['Zeit'] = pd.to_datetime(df_file['Zeit'], format='%m/%d/%Y %I:%M:%S %p')
        except Exception as e:
            st.error(f"Error parsing 'Zeit' column: {e}")

        # Filter DataFrame based on selected dates
        filter_data = df_file[df_file['Zeit'].dt.date >= from_date]
        filter_data = filter_data[df_file['Zeit'].dt.date <= to_date]
    
    return filter_data


def obj_rule(model):
    # Berechnung des abgezinsten Zahlungsstroms
    Zahlungsstrom = sum(
        (model.k_PV_Verguetung * model.V_P_PVinsNetz[t] * model.dt - 
         model.k_Netzbezug * model.V_P_Netzbezug[t] * model.dt) / ((1+model.z)**j) 
        for j in model.J for t in model.T
    )
    
    # Berechnung der Investitionskosten des Batteriespeichers
    Investitionskosten_BSS = model.V_K_BSS * model.C_BSS + model.C_OM + model.C_Ersatz
    
    # Gesamte Zielfunktion
    return - Investitionskosten_BSS + Zahlungsstrom

def Beschränkung_PV_Last(model, t):
    if model.V_P_PV[t] >= model.V_P_Last[t]:
        return model.V_P_PV_Last[t] == model.V_P_Last[t] 
    else:
        return model.V_P_PV_Last[t] == model.V_P_PV[t] 
    
def Beschränkung_PVinsNetz(model, t):
    if model.V_P_PV[t] - model.V_P_Last[t] >= 0 and True :
        return model.V_P_PVinsNetz[t] == model.V_P_PV[t] - model.V_P_Last[t] - model.V_P_PV_BSS_lad[t] 
    
    else:
        return model.V_P_PVinsNetz[t] == 0

def Last_Bilanz(model, t):

        return model.V_P_Last[t] == model.V_P_PV_Last[t] + model.V_P_Netzbezug[t] + model.V_P_BSS_Last_ent[t]

def BSS_Energieinhalt(model, t):
    V_E_BSS_t_Anfangswert = model.V_E_BSS_t0 if t == min(model.T) else model.V_E_BSS_t[t - 1]
    return model.V_E_BSS_t[t]  == V_E_BSS_t_Anfangswert + (model.BSS_Wirkungsgrad_lad * model.V_P_PV_BSS_lad[t])* model.dt - (model.V_P_BSS_Last_ent[t] / model.BSS_Wirkungsgrad_ent) * model.dt

def Entladene_Leistung_ver(model, t):
    return model.V_P_Last[t] - model.V_P_PV[t] <= (model.V_E_BSS_t[t] - model.V_K_BSS * model.SOC_min)/model.dt

def Ladeleistung_ver(model, t):
    return model.V_P_PV[t] - model.V_P_Last[t] <= (model.V_K_BSS * model.SOC_max - model.V_E_BSS_t[t])/model.dt

def SOCmin(model, t):
    return model.V_K_BSS * model.SOC_min <= model.V_E_BSS_t[t]

def SOCmax(model, t):       
    return model.V_E_BSS_t[t] <= model.V_K_BSS * model.SOC_max

def Netzbezugsgrenze(model, t):
    return model.V_P_Netzbezug[t] <= model.V_P_Netzbezug_Grenze

def createModel(V_P_Last, V_P_PV):    

    model = ConcreteModel()
    #sets
    model.T = Set(initialize=range(len(V_P_Last)))  #Betrachtungszeitraum 
    model.J = Set(initialize=range(20))  #Lebensdauer des Batteriespeichers



    #___________________________________________________________________________________________________________________________________________
    # Entscheidungsvariablen
    # Variablen deklarieren und dem Modell hinzufügen
    model.V_P_Netzbezug = Var(model.T, within=NonNegativeReals) # Leistungsbezug aus dem öffentlichen Netz [kW]
    model.V_P_PVinsNetz = Var(model.T, within=NonNegativeReals) # Eingespeiste PV-Leistung ins öffentliche Netz [kW]
    model.V_P_PV_Last = Var(model.T, initialize=0.0) # PV-Eigenverbrauch [kW] 
    model.V_K_BSS = Var(within=NonNegativeReals) #Kapazität des BSS [kWh]
    model.V_E_BSS_t = Var(model.T,initialize=0.0) #Energieinhalt des BSS [kWh]
    model.V_P_BSS_Last_ent = Var(model.T, initialize=0.0, within=NonNegativeReals) #Aus dem Speicher zur Lastdeckung entladene Leistung [kW]
    model.V_P_PV_BSS_lad = Var(model.T, initialize=0.0, within=NonNegativeReals) #In den Speicher aus der PV-Anlage eingespeicherte Leistung [kW]

    #___________________________________________________________________________________________________________________________________________
    # Parameter (Werte eingeben)
    model.C_BSS = Param(initialize=170)  #Energiespezifische Anschaffungskosten des BSS [€/kWh]
    model.C_OM = Param(initialize=50) #Betriebs- und Wartungskosten des BSS [€]
    model.C_Ersatz = Param(initialize=1000) #Ersatzkosten des BSS am Ende des Betrachtungszeitraums [€]
    model.k_PV_Verguetung = Param(initialize=0.062) #Einspeisevergütung [€/kWh] 
    model.k_Netzbezug = Param(initialize=0.025) #Leistungsnetzbezug [kW]
    model.NE_Hoechstlast = Param(initialize=50) #Leistungspreis [€/kW/a]
    model.z = Param(initialize=0.02) #Kalkulationszinssatz [%]
    model.P_Selbst_ent = Param(initialize = 0.0003) #Selbstentladeleistung [kW]
    model.SOC_min = Param(initialize=0.20) #minimaler Speicherzustand 
    model.SOC_max = Param(initialize=0.80) #maximaler Speicherzustand 
    model.BSS_Wirkungsgrad_lad = Param(initialize=0.90) #Ladewirkungsgrad 
    model.BSS_Wirkungsgrad_ent = Param(initialize=0.80) #Entladewirkungsgrad 
    model.dt = Param(initialize=0.25) #Zeitschritt 
    model.V_E_BSS_t0 = Param(initialize = 0)
    model.V_P_Netzbezug_Grenze = Param(initialize=70) #Netzbezugsgrenze [kW]
    model.V_P_PVinsNetz_Grenze = Param(initialize=500) #maximal zulässige Einspeisegrenze [kW]

    # Übergabe der Daten als Eingangsparameter an das Pyomo-Modell
    model.V_P_Last = Param(model.T, initialize={t: V_P_Last[t] for t in model.T})
    model.V_P_PV = Param(model.T, initialize={t: V_P_PV[t] for t in model.T})

    model.objective = Objective(rule=obj_rule, sense=maximize)

    model.Beschränkung_PV_Last = Constraint(model.T, rule=Beschränkung_PV_Last)

    model.Beschränkung_PVinsNetz = Constraint(model.T, rule=Beschränkung_PVinsNetz)

    model.Last_Bilanz = Constraint(model.T, rule=Last_Bilanz)

    model.Netzbezugsgrenze_Restriktion = Constraint(model.T, rule=Netzbezugsgrenze)
    
    model.BSS_Energieinhalt = Constraint(model.T, rule=BSS_Energieinhalt)

    model.Entladene_Leistung_ver = Constraint(model.T, rule=Entladene_Leistung_ver)

    model.Ladeleistung_ver = Constraint(model.T, rule=Ladeleistung_ver)


    model.bss_grenzen_min_constraint = Constraint(model.T, rule=SOCmin)
    model.bss_grenzen_max_constraint = Constraint(model.T, rule=SOCmax)

    return model

def solve(df_V_P_Last,df_V_P_PV):
    print("Hello from solve")

    V_P_Last = df_V_P_Last["Last kW"].tolist()
    
    V_P_PV = df_V_P_PV["Leistung"].tolist()
    model = createModel(V_P_Last,V_P_PV)
    
    
    # Das Problem lösen
    solver = SolverFactory('gurobi', solver_io="python")  # Gurobi-Optimierer verwenden
    solver.solve(model)

    # Ergebnisse der Variablen für jeden Zeitpunkt drucken
    print("Zeitpunkt\tV_P_Netzbezug\tV_P_PVinsNetz\tV_E_BSS\tV_E_BSS_t\tV_P_BSS_lad_PV\tV_P_BSS_ent_Last")
    results = []    

    for t in model.T:

        # Berechnung der ungedeckten Last
        ungedeckte_last = value(model.V_P_Last[t]) - value(model.V_P_PV[t])
        if ungedeckte_last < 0:
            ungedeckte_last = 0

        #Berechnung der überschüssigen Leistung
        überschüssige_Leistung = value(model.V_P_PV[t]) - value(model.V_P_Last[t])
        if überschüssige_Leistung < 0:
            überschüssige_Leistung = 0 
    
        #Leistungsbezug aus PVA 
        Bezug_PVA = {} 
        Bezug_PVA[t] = min(model.V_P_Last[t],model.V_P_PV[t])

        #Leistungsbezug aus PVA und Batteriespeicher
        Bezug_PVA_Speicher = {} 
        Bezug_PVA_Speicher[t] = Bezug_PVA[t] + value(model.V_P_BSS_Last_ent[t])

        values = [
            df_V_P_Last["Zeit"][t],
            t,
            V_P_Last[t],
            V_P_PV[t],
            ungedeckte_last,
            überschüssige_Leistung, 
            value(model.V_P_PV_Last[t]),
            value(model.V_P_Netzbezug[t]),
            value(model.V_P_PVinsNetz[t]),
            value(model.V_E_BSS_t[t]),
            value(model.V_P_PV_BSS_lad[t]),
            value(model.V_P_BSS_Last_ent[t]),
        ]

        print("\t".join(str(value) for value in values))
        results.append(values)

    # Erstellen eines Pandas DataFrame
    df_results = pd.DataFrame(results, columns=["Zeit","Zeitpunkt", "Last[kW]","PV[kW]","Last_ungedeckt[kW]","überschüssige_Leistung [kW]","PVA-Last[kW]","Netzbezug[kW]","PVinsNetz[kW]", "E_BSS_t[kWh]","P_BSS_lad_PV[kW]","BSS_ent_Last[kW]"])

    # Speichern des DataFrames in einer Excel-Datei
    output_file = "Simulationsergebnisse.xlsx"
    output_path = os.path.join("./", output_file) 
    df_results.to_excel(output_path, index=False)

    print("Ergebnisse wurden erfolgreich in die Datei", output_path, "gespeichert.")


    # Löse das Optimierungsproblem
    solver = SolverFactory('gurobi')  # Wähle den Gurobi-Solver
    results = solver.solve(model)  # löse das Modell

    # Erhalte den optimalen Wert der Variablen V_K_BSS
    optimal_V_E_BSS = model.V_K_BSS.value

    # Überprüfe, ob die Lösung gültig ist
    if results.solver.termination_condition == TerminationCondition.optimal:
        # Ersetze die Variablen und Parameter des Modells mit den optimalen Werten
        model.solutions.load_from(results)
        
        # Berechne den Wert der Zielfunktion für die optimale Lösung
        obj_value = - (optimal_V_E_BSS * model.C_BSS + model.C_OM + model.C_Ersatz) + sum((model.k_PV_Verguetung * model.V_P_PVinsNetz[t].value * model.dt - model.k_Netzbezug * model.V_P_Netzbezug[t].value * model.dt) / ((1 + model.z) ** j) for j in model.J for t in model.T)

        print("Wert des Kapitalwerts (NPV) für die optimale Lösung:", obj_value)
    else:
        print("Das Optimierungsproblem wurde nicht optimal gelöst.")


    #Simulationsergebnisse
    #Jahreshöchstlast
    P_Last_max = df_V_P_Last['Last kW'].max()
    print("Jahreshöchstlast", P_Last_max, "kW")

    #Jahresenergieverbrauch
    E_Verbrauch = sum(V_P_Last[t]for t in model.T) * model.dt
    print("Jahresenergieverbrauch",E_Verbrauch, "kWh")

    #Jährliche PV-Erzeugung
    E_PV = sum(V_P_PV[t] for t in model.T) * model.dt 
    print("Jährliche PV-Erzeugung",E_PV, "kWh")


    #Eigenverbrauchsanteil ohne BSS 
    EV_PV = (sum(value(model.V_P_PV_Last[t]) for t in model.T) / E_PV) * 100
    print("Eigenverbrauchsanteil ohne BSS ",EV_PV, "%")

    #Batteriespeicherkapazität
    print("Batteriespeicherkapazität",model.V_K_BSS.value, "kWh")

    # Eigenverbrauchsanteil mit BSS
    EV_PVundBSS = ((sum(value(model.V_P_PV_Last[t]) for t in model.T) + sum(value(model.V_P_BSS_Last_ent[t]) for t in model.T)) / E_PV) * 100
    print("Eigenverbrauchsanteil mit BSS ", EV_PVundBSS, "%")

    #Gesamte Netzeinspeisung
    PVinsNetz = sum(value(model.V_P_PVinsNetz[t]) for t in model.T) * model.dt
    print("Gesamte Netzeinspeisung",PVinsNetz, "kWh")


    return model,df_results

def print_data():
    print(st.session_state.model)


with data_tab:
    col1, col2 = st.container().columns(2)
    is_Batteriespeicher = True
    with col1:
        st.write("##### Daten importieren")
        uploaded_file1, uploaded_file2 = get_file_inputs("Lastprofildaten herunterladen (Last)","PV-Erzeugungsdaten herunterladen (PV)")
        
        df_Last_Kw, df_Leistung = check_files(uploaded_file1,uploaded_file2)
        
        st.write("##### Betrachtungszeitraum")
        from_date,to_date = get_date_inputs("Von","Bis", initialDateOne=datetime.date(2018,1,1), initialDateTwo=datetime.date(2018,1,2), keyOne="from_date", keyTwo="to_date")

        if from_date > to_date:
            st.error("Start date must be before end date.")
        

        filtered_df_Last_kW = filter_data(uploaded_file1,df_Last_Kw,from_date, to_date)
        filtered_df_Leistung = filter_data(uploaded_file2,df_Leistung,from_date, to_date)
        


        if(uploaded_file1 and uploaded_file2):
            test_button = st.button("Test")
            if(test_button):
                model,res_df = solve(df_Last_Kw,df_Leistung)
                st.session_state.res_df = res_df
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


        if(uploaded_file1):
            ax.plot(filtered_df_Last_kW["Zeit"],filtered_df_Last_kW["Last kW"],label='Last', color='blue')
        if(uploaded_file2):
            ax.plot(filtered_df_Leistung["Zeit"],filtered_df_Leistung["Leistung"],label='PV', color='red')

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
    if 'res_df'  in st.session_state:
        st.write("##### Betrachtungszeitraum")
        result_from_date,result_to_date = get_date_inputs("Von","Bis", initialDateOne=datetime.date(2018,1,1), initialDateTwo=datetime.date(2018,1,2), keyOne="result_from_date", keyTwo="result_to_date")
                
        col1, col2 = st.container().columns(2)

        res_df = st.session_state.res_df

        filtered_res_data = filter_data(uploaded_file1,res_df,result_from_date, result_to_date)

        with col1:

            fig, ax = plt.subplots(figsize=(15, 4))


            ax.plot(filtered_res_data["Zeit"],filtered_res_data["Last[kW]"],label='Last[kW]', color='red') 
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["PV[kW]"],label='PV[kW]', color='blue')
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["Netzbezug[kW]"],label='Netzbezug[kW]', color='green')
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["PVinsNetz[kW]"],label='PVinsNetz[kW]', color='yellow')
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["BSS_ent_Last[kW]"],label='BSS_ent_Last[kW]', color='black')
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["P_BSS_lad_PV[kW]"],label='P_BSS_lad_PV[kW]', color='brown')

            ax.set_xlabel('Zeit')
            ax.set_ylabel('Leistung [kW]')
            fig.suptitle('Darstellung der Eingangsdaten')

            ax.legend()

            st.pyplot(fig)
        with col2:

            fig, ax = plt.subplots(figsize=(15, 4))

            ax.plot(filtered_res_data["Zeit"],filtered_res_data["E_BSS_t[kWh]"],label='E_BSS_t[kWh]', color='red') 
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["BSS_ent_Last[kW]"],label='BSS_ent_Last[kW]', color='magenta')
            ax.plot(filtered_res_data["Zeit"],filtered_res_data["P_BSS_lad_PV[kW]"],label='P_BSS_lad_PV[kW]', color='orange')

            ax.set_xlabel('Zeit')
            ax.set_ylabel('Leistung [kW]')
            fig.suptitle('Darstellung der Eingangsdaten')

            ax.legend()

            st.pyplot(fig)
    else:
        st.write("##### Please run the simulation to see results")