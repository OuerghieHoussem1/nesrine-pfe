from pyomo.environ import *
from pyomo.environ import SolverFactory
import pandas as pd
import os

# Das lineare Programmierungsproblem erstellen
model = ConcreteModel()


#Lesen von Leistungsbedarf- und PV-Leistungsdaten aus Excel-Dateien 
df_V_P_Last = pd.read_excel('./Last.xlsx')
df_V_P_PV = pd.read_excel('./PV.xlsx')

# Konvertieren der Daten in Listen oder Arrays
V_P_Last = df_V_P_Last['Last kW'].tolist()
V_P_PV = df_V_P_PV['Leistung'].tolist()


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

#___________________________________________________________________________________________________________________________________________
# Zielfunktion und Optimierung
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

# Die Zielfunktion maximieren
model.objective = Objective(rule=obj_rule, sense=maximize)

#___________________________________________________________________________________________________________________________________________
# Beschränkungen und Restriktionen definieren

def Beschränkung_PV_Last(model, t):
    if model.V_P_PV[t] >= model.V_P_Last[t]:
        return model.V_P_PV_Last[t] == model.V_P_Last[t] 
    else:
        return model.V_P_PV_Last[t] == model.V_P_PV[t] 

model.Beschränkung_PV_Last = Constraint(model.T, rule=Beschränkung_PV_Last)

def Beschränkung_PVinsNetz(model, t):
    if model.V_P_PV[t] - model.V_P_Last[t] >= 0:
        return model.V_P_PVinsNetz[t] == model.V_P_PV[t] - model.V_P_Last[t] - model.V_P_PV_BSS_lad[t] 
    
    else:
        return model.V_P_PVinsNetz[t] == 0

model.Beschränkung_PVinsNetz = Constraint(model.T, rule=Beschränkung_PVinsNetz)


def Last_Bilanz(model, t):

        return model.V_P_Last[t] == model.V_P_PV_Last[t] + model.V_P_Netzbezug[t] + model.V_P_BSS_Last_ent[t]

model.Last_Bilanz = Constraint(model.T, rule=Last_Bilanz)



# Die Netzbezugsgrenze limitiert die maximale Netzbezugsleistung
def Netzbezugsgrenze(model, t):
    return model.V_P_Netzbezug[t] <= model.V_P_Netzbezug_Grenze

model.Netzbezugsgrenze_Restriktion = Constraint(model.T, rule=Netzbezugsgrenze)




# Bestimmung des Energieinhalts des Batteriespeichers
def BSS_Energieinhalt(model, t):
    V_E_BSS_t_Anfangswert = model.V_E_BSS_t0 if t == min(model.T) else model.V_E_BSS_t[t - 1]
    return model.V_E_BSS_t[t]  == V_E_BSS_t_Anfangswert + (model.BSS_Wirkungsgrad_lad * model.V_P_PV_BSS_lad[t])* model.dt - (model.V_P_BSS_Last_ent[t] / model.BSS_Wirkungsgrad_ent) * model.dt

model.BSS_Energieinhalt = Constraint(model.T, rule=BSS_Energieinhalt)


# Verfügbare entladene Leistung zur Lastdeckung 
def Entladene_Leistung_ver(model, t):
    return model.V_P_Last[t] - model.V_P_PV[t] <= (model.V_E_BSS_t[t] - model.V_K_BSS * model.SOC_min)/model.dt

model.Entladene_Leistung_ver = Constraint(model.T, rule=Entladene_Leistung_ver)

# Verfügbare  Ladeleistung des BSS
def Ladeleistung_ver(model, t):
    return model.V_P_PV[t] - model.V_P_Last[t] <= (model.V_K_BSS * model.SOC_max - model.V_E_BSS_t[t])/model.dt

model.Ladeleistung_ver = Constraint(model.T, rule=Ladeleistung_ver)

# Beschränkungen für die oberen und unteren Grenzen des SOC
def SOCmin(model, t):
    return model.V_K_BSS * model.SOC_min <= model.V_E_BSS_t[t]

def SOCmax(model, t):       
    return model.V_E_BSS_t[t] <= model.V_K_BSS * model.SOC_max

model.bss_grenzen_min_constraint = Constraint(model.T, rule=SOCmin)
model.bss_grenzen_max_constraint = Constraint(model.T, rule=SOCmax)


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
        value(model.V_P_BSS_Last_ent[t]
        
),
        
    ]
    print("\t".join(str(value) for value in values))
    results.append(values)

# Erstellen eines Pandas DataFrame
df_results = pd.DataFrame(results, columns=["Zeitpunkt", "Last[kW]","PV[kW]","Last_ungedeckt[kW]","überschüssige_Leistung [kW]","PVA-Last[kW]","Netzbezug[kW]","PVinsNetz[kW]", "E_BSS_t[kWh]","P_BSS_lad_PV[kW]","BSS_ent_Last[kW]"])

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

