import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# --- 1. MODEL DEFINITION AND PARAMETERS ---

# Universal Constants (from SGLT1_kinetic model)
R = 8.314        # J/(K mol)
T = 293.0        # K (20 C)
F = 96485.0      # C/mol

# Cell Geometry and Capacitance (Approximate Cardiac Cell Values)
Cm = 100e-12     # Farads (pF) - Total membrane capacitance
V_cell = 20e-15  # Liters (pL) - Intracellular volume (20,000 um^3)

# Conversion Factors
k_fmol_to_mol = 1e-15
k_fA_to_A = 1e-15
k_mM_to_M = 1e-3
k_M_to_mM = 1e3

# Fixed External Concentrations (mM)
Nao = 140.0      # External Sodium (mM)
Glco = 5.0       # External Glucose (mM)

# SGLT1 Kinetic Parameters (from SGLT1_kinetic model)
alpha = 0.3
delta = 0.7

# SGLT1 Rate Constants (base values, per_s, per_s_mM, or per_s_mM2)
k_12_0 = 0.08
k_23_0 = 100.0
k_34 = 50.0
k_45 = 800.0
k_56 = 10.0
k_61_0 = 3.0
k_25 = 0.3
k_21_0 = 500.0
k_32 = 20.0
k_43 = 50.0
k_54_0 = 1.0971e4
k_65_0 = 5e-5
k_16_0 = 35.0
k_52 = 0.823

# Total Transporter Concentration (C_T)
# Based on sum of initial states provided in source (~100 fmol)
C_T = 100.0 # fmol

# Leak Channel Parameters (Simple Sodium Leak)
G_Na_Leak = 1.0e-9 # S (1 nS conductance)

def model_dydt(t, y):
    """
    The function defining the derivatives of the coupled system.
    y = [Vm, Nai, Glci, CNa2_o, SCNa2_o, SCNa2_i, CNa2_i, Ci]
    
    Units:
    Vm: V
    Nai, Glci: mM
    SGLT States (C_x): fmol
    """
    
    # --- 2. EXTRACT STATE VARIABLES ---
    
    Vm = y[0]
    Nai = y[1]
    Glci = y[2]
    CNa2_o = y[3]
    SCNa2_o = y[4]
    SCNa2_i = y[5]
    CNa2_i = y[6]
    Ci = y[7]
    
    # Initialize derivative vector
    dydt = np.zeros_like(y)
    
    # --- 3. SGLT1 KINETIC CALCULATIONS ---
    
    # 3.1. Calculate Vm dependence factor (mu)
    mu = (F * Vm) / (R * T)
    
    # 3.2. Calculate Voltage/Concentration dependent rates (k_ij)
    
    # Rates depending on Vm (alpha, delta)
    k_16 = k_16_0 * np.exp(delta * mu)
    k_61 = k_61_0 * np.exp(-delta * mu)
    k_12 = k_12_0 * Nao**2 * np.exp(-alpha * mu)
    k_21 = k_21_0 * np.exp(alpha * mu)
    
    # Rates depending on concentration
    k_65 = k_65_0 * Nai**2
    k_23 = k_23_0 * Glco
    k_54 = k_54_0 * Glci
    
    # Rates independent of Vm or [Conc]
    # k_34, k_45, k_56, k_25, k_32, k_43, k_52 are fixed parameters defined globally
    
    # 3.3. Calculate algebraic state C_o (State 1)
    C_o = C_T - (CNa2_i + CNa2_o + SCNa2_o + SCNa2_i + Ci)
    
    # Ensure C_o remains non-negative due to numerical stiffness
    C_o = np.maximum(0, C_o)

    # 3.4. Calculate SGLT Currents and Fluxes
    
    # SGLT Current (Ii, in fA)
    # Ii = 2 * F * [(alpha * (k12*Co - k21*CNa2o)) - (delta * (k16*Co - k61*Ci))]
    I_SGLT1_fA = (2 * F) * (
        (alpha * ((k_12 * C_o) - (k_21 * CNa2_o))) - 
        (delta * ((k_16 * C_o) - (k_61 * Ci)))
    )
    
    # Glc Flux (J_Glc, inward, in fmol/s)
    # Transport step is 3->4
    J_Glc_SGLT1_fmol_s = (k_34 * SCNa2_o) - (k_43 * SCNa2_i)
    
    # Na Flux (J_Na, inward, in fmol/s) - 2 Na+ per Glc
    J_Na_SGLT1_fmol_s = 2.0 * J_Glc_SGLT1_fmol_s
    
    # --- 4. LEAK CHANNEL CALCULATIONS ---
    
    # 4.1. Nernst Potential for Na+ (E_Na)
    if Nai <= 0: # Avoid log(0)
         E_Na = R * T / F * np.log(Nao / 1e-6)
    else:
         E_Na = R * T / F * np.log(Nao / Nai) # [Nao] and [Nai] are in mM, ratio is fine
    
    # 4.2. Leak Current (I_Na, Leak, in A)
    I_Na_Leak = G_Na_Leak * (Vm - E_Na)
    
    # --- 5. DERIVATIVES OF STATE VARIABLES ---
    
    # 5.1. Vm Derivative (dydt[0])
    
    I_SGLT1_A = I_SGLT1_fA * k_fA_to_A
    I_Total = I_SGLT1_A + I_Na_Leak
    
    dVm_dt = -I_Total / Cm
    dydt[0] = dVm_dt
    
    # 5.2. Concentration Derivatives
    
    # Conversion of fmol/s flux to mol/s
    J_Na_SGLT1_mol_s = J_Na_SGLT1_fmol_s * k_fmol_to_mol
    J_Glc_SGLT1_mol_s = J_Glc_SGLT1_fmol_s * k_fmol_to_mol
    
    # Leak Flux (mol/s). Inward current (I_Na_Leak < 0) results in positive inward flux
    J_Na_Leak_mol_s = -I_Na_Leak / F
    
    # d[Na]i/dt (dydt[1])
    # d[C]/dt = (1/V_cell) * J_total * k_M_to_mM (to get mM/s)
    dNa_dt = k_M_to_mM / V_cell * (J_Na_SGLT1_mol_s + J_Na_Leak_mol_s)
    dydt[1] = dNa_dt

    # d[Glc]i/dt (dydt[2])
    dGlc_dt = k_M_to_mM / V_cell * J_Glc_SGLT1_mol_s
    dydt[2] = dGlc_dt
    
    # 5.3. SGLT Kinetic State Derivatives (dydt[3] to dydt[7]) (fmol/s)
    
    # dCNa2_o/dt (dydt[3], State 2)
    dydt[3] = (
        ((k_12 * C_o) + (k_52 * CNa2_i) + (k_32 * SCNa2_o)) - 
        ((k_21 + k_25 + k_23) * CNa2_o)
    )
    
    # dSCNa2_o/dt (dydt[4], State 3)
    dydt[4] = (
        ((k_23 * CNa2_o) + (k_43 * SCNa2_i)) - 
        ((k_32 + k_34) * SCNa2_o)
    )
    
    # dSCNa2_i/dt (dydt[5], State 4)
    dydt[5] = (
        ((k_34 * SCNa2_o) + (k_54 * CNa2_i)) - 
        ((k_43 + k_45) * SCNa2_i)
    )
    
    # dCNa2_i/dt (dydt[6], State 5)
    dydt[6] = (
        ((k_25 * CNa2_o) + (k_45 * SCNa2_i) + (k_65 * Ci)) - 
        ((k_52 + k_54 + k_56) * CNa2_i)
    )
    
    # dCi/dt (dydt[7], State 6)
    dydt[7] = (
        ((k_16 * C_o) + (k_56 * CNa2_i)) - 
        ((k_61 + k_65) * Ci)
    )
    
    return dydt

# --- 6. SIMULATION SETUP AND EXECUTION ---

if __name__ == "__main__":
    
    # Initial Conditions (Based on physiological values and SGLT model defaults)
    
    # 0. Vm (Membrane potential, V)
    Vm_0 = -0.075 # -75 mV
    
    # 1. Nai (Intracellular Sodium, mM)
    Nai_0 = 10.0 
    
    # 2. Glci (Intracellular Glucose, mM)
    Glci_0 = 0.5 
    
    # SGLT Kinetic States (fmol) - Initial values provided in source material
    # C_o_0 is calculated algebraically from C_T
    CNa2_o_0 = 72.295598813025 
    SCNa2_o_0 = 0.16701061319503
    SCNa2_i_0 = 0.233806833618937
    CNa2_i_0 = 1.73527350102727
    Ci_0 = 11.4302815603453
    
    # C_o_0 = C_T - (sum of others)
    # The sum of initial states should equal C_T
    # C_T = 100 fmol
    
    y0 = [
        Vm_0, Nai_0, Glci_0, 
        CNa2_o_0, SCNa2_o_0, SCNa2_i_0, CNa2_i_0, Ci_0
    ]

    # Time span (seconds)
    t_span = (0, 50.0) 
    t_points = np.linspace(t_span[0], t_span[1], 500)

    print("Running simulation...")
    
    # Solve the ODE system
    solution = solve_ivp(
        model_dydt, 
        t_span, 
        y0, 
        t_eval=t_points, 
        method='BDF', # Use stiff solver appropriate for coupled kinetic systems
        rtol=1e-6, 
        atol=1e-8
    )

    if not solution.success:
        print(f"Simulation failed: {solution.message}")
    else:
        print("Simulation successful.")

    # --- 7. PLOTTING RESULTS ---

    V_m_mV = solution.y[0, :] * 1000
    Nai_mM = solution.y[1, :]
    Glci_mM = solution.y[2, :]
    
    SGLT_states = solution.y[3:, :]
    
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    
    # Plot Vm
    axes[0].plot(solution.t, V_m_mV, label='$V_m$')
    axes[0].set_ylabel('Membrane Potential (mV)')
    axes[0].set_title('Cardiac Cell Model with SGLT1 and Na Leak')
    
    # Plot Concentrations
    axes[1].plot(solution.t, Nai_mM, label='[Na]$_i$ (SGLT + Leak)')
    axes[1].plot(solution.t, Glci_mM, label='[Glc]$_i$ (SGLT)')
    axes[1].set_ylabel('Concentration (mM)')
    axes[1].legend()

    # Plot SGLT States
    axes[2].plot(solution.t, SGLT_states[0, :], label='CNa2_o (State 2)')
    axes[2].plot(solution.t, SGLT_states[1, :], label='SCNa2_o (State 3)')
    axes[2].plot(solution.t, SGLT_states[2, :], label='SCNa2_i (State 4)')
    axes[2].plot(solution.t, SGLT_states[3, :], label='CNa2_i (State 5)')
    axes[2].plot(solution.t, SGLT_states[4, :], label='Ci (State 6)')
    axes[2].set_ylabel('SGLT1 State Population (fmol)')
    axes[2].set_xlabel('Time (s)')
    axes[2].legend(loc='upper right', ncol=2, fontsize='small')

    plt.tight_layout()
    plt.savefig('test.pdf',dpi=300)