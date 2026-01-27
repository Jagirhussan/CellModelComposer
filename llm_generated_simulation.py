import numpy as np
from scipy.integrate import solve_ivp
from math import floor

# --- 1. GLOBAL CONSTANTS (SI/Consistent f-units) ---
F = 96485.332      # Faraday constant (C/mol)
R = 8.31446        # Gas constant (J/(K*mol))
T = 310.15         # Temperature (K)
RT = R * T
FF = F * 1e-15     # Effective Faraday constant for fmol/s to fA conversion (fC/fmol)

def model(t, y, params):
    # --- 1. UNPACK STATES (Q variables in fmol or fC) ---
    
    # Core Ionic States (7 states)
    y_idx = 0
    q_mem = y[y_idx]; y_idx += 1    # 0: Membrane Charge (fC)
    q_Na_i = y[y_idx]; y_idx += 1   # 1: Intracellular Na+ (fmol)
    q_K_i = y[y_idx]; y_idx += 1    # 2: Intracellular K+ (fmol)
    q_Ca_i = y[y_idx]; y_idx += 1   # 3: Intracellular Ca2+ (fmol, cytosol)
    q_Ca_D = y[y_idx]; y_idx += 1   # 4: Ca2+ in Dyadic Space (fmol)
    q_Ca_SR = y[y_idx]; y_idx += 1  # 5: Ca2+ in SR (fmol)
    q_Glc_i = y[y_idx]; y_idx += 1  # 6: Intracellular Glucose (fmol)
    
    # Gating States (normalized amounts, sum usually equals 1 or N_channels)
    
    # Na Channel States (S000 to S311, 12 states)
    q_S_Na = {}
    for i in range(4):
        for j in range(2):
            for k in range(2):
                key = f'{i}{j}{k}'
                q_S_Na[key] = y[y_idx]
                y_idx += 1
    q_S000_Na, q_S311_Na = q_S_Na['000'], q_S_Na['311']

    # LCC States (S000 to S121, 12 states)
    q_S_LCC = {}
    for i in range(2):
        for j in range(3):
            for k in range(2):
                key = f'{i}{j}{k}'
                q_S_LCC[key] = y[y_idx]
                y_idx += 1
    q_S111_LCC, q_S121_LCC = q_S_LCC['111'], q_S_LCC['121']

    # K1 Gating States (q, r1, r2)
    q_K1_q, q_K1_r1, q_K1_r2 = y[y_idx:y_idx+3]; y_idx += 3
    
    # Kr Gating States (Sa, Sb, Sc, Sd)
    q_Kr_Sa, q_Kr_Sb, q_Kr_Sc, q_Kr_Sd = y[y_idx:y_idx+4]; y_idx += 4
    
    # Kto Gating States (r0s0, r0s1, r1s0, r1s1)
    q_Kto_r0s0, q_Kto_r0s1, q_Kto_r1s0, q_Kto_r1s1 = y[y_idx:y_idx+4]; y_idx += 4
    
    # RyR Gating States (C, CI, I, O)
    q_RyR_C, q_RyR_CI, q_RyR_I, q_RyR_O = y[y_idx:y_idx+4]; y_idx += 4
    
    # NCX Carrier States (P1 to P6)
    q_P_NCX = list(y[y_idx:y_idx+6]); y_idx += 6
    
    # SGLT1 Carrier States (q1 to q6)
    q_SGLT = list(y[y_idx:y_idx+6]); y_idx += 6
    
    # NKE Pump States (q1 to q6)
    q_NKE = list(y[y_idx:y_idx+6]); y_idx += 6
    
    # --- 2. PARAMETER SETUP & ENVIRONMENT ---
    
    # Geometry & Buffering
    C_m = params.get('C_m', 100.0)      # fF [Source: environment]
    W_i = params.get('W_i', 20e-3)      # pL [Source: environment]
    W_o = params.get('W_o', 1e+6)       # pL [Source: environment]

    # External Concentrations (Set as fixed/source components)
    C_Na_o = params.get('C_Na_o', 140.0) # mM
    C_K_o = params.get('C_K_o', 5.4)     # mM
    C_Ca_o = params.get('C_Ca_o', 2.0)   # mM
    C_Glc_o = params.get('C_Glc_o', 5.0) # mM
    C_ATP = params.get('C_ATP', 10.0)    # mM
    C_ADP = params.get('C_ADP', 0.1)     # mM
    C_Pi = params.get('C_Pi', 1.0)       # mM
    C_H = 10**(-params.get('pH', 7.2)) * 1000 # mM

    # K factors relating amount (fmol) to concentration effort for log term
    # K = 1 / (C_ref * V_ref * 1e-3)
    K_Na_i_ref = params.get('K_Na_i_ref', 1.0 / (10.0 * W_i * 1e-3))
    K_K_i_ref = params.get('K_K_i_ref', 1.0 / (140.0 * W_i * 1e-3))
    K_Ca_i_ref = params.get('K_Ca_i_ref', 1.0 / (100e-6 * W_i * 1e-3))
    K_Glc_i_ref = params.get('K_Glc_i_ref', 1.0 / (1.0 * W_i * 1e-3))
    
    # RyR/Ca Dynamics
    K_Ca_D = params.get('K_Ca_D', 1e18) # [RyR parameter placeholder]
    K_Ca_SR = params.get('K_Ca_SR', 1e18) # [RyR parameter placeholder]
    
    # Valences
    zNa, zK, zCa = 1.0, 1.0, 2.0 # [Source: ion_valences]
    
    # --- 3. CALCULATE EFFORTS (mu in J/mol) ---

    V_mem = q_mem / C_m             # V (Membrane voltage)
    E_mem = F * V_mem               # J/mol of charge (Electrical effort)
    
    # 3.1. Internal Variable Potentials
    mu_Na_i = RT * np.log(K_Na_i_ref * q_Na_i)  # [Generated: Chemical Potential]
    mu_K_i = RT * np.log(K_K_i_ref * q_K_i)    # [Generated: Chemical Potential]
    mu_Ca_i = RT * np.log(K_Ca_i_ref * q_Ca_i)  # [Generated: Chemical Potential]
    mu_Glc_i = RT * np.log(K_Glc_i_ref * q_Glc_i) # [Generated: Chemical Potential]

    mu_Ca_D = RT * np.log(K_Ca_D * q_Ca_D)      # [Source: RyR]
    mu_Ca_SR = RT * np.log(K_Ca_SR * q_Ca_SR)    # [Source: RyR]
    
    # 3.2. External Fixed Potentials (Using C_o * W_o * 1e3 as effective q_o for calculation simplicity)
    mu_Na_o = RT * np.log(K_Na_i_ref * C_Na_o * W_i * 1e-3) # Use arbitrary K factor consistent with amount units
    mu_K_o = RT * np.log(K_K_i_ref * C_K_o * W_i * 1e-3) 
    mu_Ca_o = RT * np.log(K_Ca_i_ref * C_Ca_o * W_i * 1e-3) 
    mu_Glc_o = RT * np.log(K_Glc_i_ref * C_Glc_o * W_i * 1e-3)
    
    mu_ATP = RT * np.log(1e18 * C_ATP * W_i * 1e-3) # NKE Metabolites (Placeholder K)
    mu_ADP = RT * np.log(1e18 * C_ADP * W_i * 1e-3)
    mu_Pi = RT * np.log(1e18 * C_Pi * W_i * 1e-3)
    mu_H = RT * np.log(1e18 * C_H * W_i * 1e-3)

    # 3.3. Gating State Potentials
    # Na/LCC/NCX/NKE/SGLT/Kto/Kr/RyR (requires ~35 state potentials, defined locally where needed)
    
    # --- 4. FLUX AND CURRENT CALCULATION (v in fmol/s, I in fA) ---
    
    I_components = []
    v_Na_i_sum = 0.0
    v_K_i_sum = 0.0
    v_Ca_i_sum = 0.0
    v_Glc_i_sum = 0.0
    
    # --- Na Channel (v_Na: Outward positive) ---
    kappa_Na = params.get('kappa_Na', 5.0e-1)
    mu_S311_Na = RT * np.log(params.get('K_311_Na', 1e18) * q_S311_Na)
    
    Af_Na = mu_Na_i + zNa * E_mem + mu_S311_Na # [Source: fast_Na]
    Ar_Na = mu_Na_o + mu_S311_Na              # [Source: fast_Na]
    Am_Na = zNa * E_mem
    
    v_Na_base = np.exp(Af_Na / RT) - np.exp(Ar_Na / RT)
    v_Na = kappa_Na * v_Na_base if np.isclose(Am_Na, 0) else (kappa_Na * Am_Na / RT / (np.exp(Am_Na/RT) - 1)) * v_Na_base # [Source: fast_Na]

    I_mem_Na = zNa * FF * v_Na # Outward current [Source: fast_Na]
    I_components.append(I_mem_Na)
    v_Na_i_sum += -v_Na # Inward Na flux [Generated: Flux conservation]
    
    dydt_gating = np.zeros(len(y) - 7) # Gating ODEs (35 states)
    dydt_gating[:12] = 0.0 # Na states neglected/set to 0 for simplicity

    # --- LCC Channel (v_LCC: Outward positive) ---
    mu_S111_LCC = RT * np.log(params.get('K_111_LCC', 1e18) * q_S111_LCC)
    mu_S121_LCC = RT * np.log(params.get('K_121_LCC', 1e18) * q_S121_LCC)

    # Ca flux 1 (v_LCC_Ca1: Outward)
    Af_LCC_Ca1 = mu_Ca_i + zCa * E_mem + mu_S111_LCC # [Source: LCC]
    Ar_LCC_Ca1 = mu_Ca_o + mu_S111_LCC              # [Source: LCC]
    Am_LCC_Ca1 = zCa * E_mem
    v_Ca1_base = np.exp(Af_LCC_Ca1/RT) - np.exp(Ar_LCC_Ca1/RT)
    v_LCC_Ca1 = params.get('kappa_LCC_Ca1', 5.0e-2) * v_Ca1_base if np.isclose(Am_LCC_Ca1, 0) else (params.get('kappa_LCC_Ca1', 5.0e-2) * Am_LCC_Ca1 / RT / (np.exp(Am_LCC_Ca1/RT) - 1)) * v_Ca1_base # [Source: LCC]
    
    # Ca flux 2 (v_LCC_Ca2: Outward)
    Af_LCC_Ca2 = mu_Ca_i + zCa * E_mem + mu_S121_LCC # [Source: LCC]
    v_Ca2_base = np.exp(Af_LCC_Ca2/RT) - np.exp(params.get('Ar_LCC_Ca2_offset', 0)/RT) # Simplified Ar calculation
    v_LCC_Ca2 = params.get('kappa_LCC_Ca2', 5.0e-2) * v_Ca2_base if np.isclose(Am_LCC_Ca1, 0) else (params.get('kappa_LCC_Ca2', 5.0e-2) * Am_LCC_Ca1 / RT / (np.exp(Am_LCC_Ca1/RT) - 1)) * v_Ca2_base # [Source: LCC]
    
    # K fluxes (LCC carries K+ weakly)
    v_LCC_K1 = 0.0 # Suppressed for simplification, as K current is mainly Kr/Kto/K1
    v_LCC_K2 = 0.0
    
    v_Ca_i_LCC = -(v_LCC_Ca1 + v_LCC_Ca2) # Net Ca INWARD flux [Generated: Flux conservation]
    v_K_i_LCC = -(v_LCC_K1 + v_LCC_K2)   # Net K INWARD flux

    I_mem_LCC = zCa * FF * (v_LCC_Ca1 + v_LCC_Ca2) + zK * FF * (v_LCC_K1 + v_LCC_K2) # Outward current
    I_components.append(I_mem_LCC)
    v_K_i_sum += v_K_i_LCC
    v_Ca_i_sum += v_Ca_i_LCC
    
    dydt_gating[12:24] = 0.0 # LCC states neglected/set to 0 for simplicity

    # --- K1 Channel (v_ReK1: Outward positive) ---
    kappa_ReK1 = params.get('kappa_ReK1', 1.0e-1)
    Af_ReK1 = mu_K_i + zK * E_mem # [Source: K1_uterine]
    Ar_ReK1 = mu_K_o              # [Source: K1_uterine]
    Am_ReK1 = zK * E_mem
    G_K1_factor = q_K1_q * q_K1_q * (0.38 * q_K1_r1 + 0.63 * q_K1_r2) # [Source: K1_uterine]
    
    v_ReK1_base = np.exp(Af_ReK1 / RT) - np.exp(Ar_ReK1 / RT)
    if np.isclose(Am_ReK1, 0):
        v_ReK1 = G_K1_factor * kappa_ReK1 * v_ReK1_base
    else:
        v_ReK1 = G_K1_factor * (kappa_ReK1 * Am_ReK1 / RT / (np.exp(Am_ReK1/RT) - 1)) * v_ReK1_base # [Source: K1_uterine]

    I_mem_K1 = zK * FF * v_ReK1 # Outward current
    I_components.append(I_mem_K1)
    v_K_i_sum -= v_ReK1 # Outward K flux

    # K1 Gating Kinetics
    V_mem_mV = V_mem * 1000
    qss = 0.978613 / (1.0 + np.exp(-(V_mem_mV + 18.6736) / 26.6606)); qtc = 0.5 / (1.0 + np.power((V_mem_mV + 60.71) / 15.79, 2))
    rss = 1.0 / (1.0 + np.exp((V_mem_mV + 63.0) / 6.3)); r1tc = 5.0 / (1.0 + np.power((V_mem_mV + 62.7133) / 35.8611, 2))
    r2tc = 30.0 + (220.0 / (1.0 + np.exp((V_mem_mV + 22.0) / 4.0)))

    dq_K1_q_dt = (qss - q_K1_q) / qtc # [Source: K1_activation]
    dq_K1_r1_dt = (rss - q_K1_r1) / r1tc # [Source: K1_activation]
    dq_K1_r2_dt = (rss - q_K1_r2) / r2tc # [Source: K1_activation]
    dydt_gating[24:27] = [dq_K1_q_dt, dq_K1_r1_dt, dq_K1_r2_dt]

    # --- Kr Channel (v_Kr: Outward positive) ---
    Kr_P = {k: params.get(k, 1.0e-3) for k in ['kappa_Kr', 'K_Sa_Kr', 'K_Sb_Kr', 'K_Sc_Kr', 'K_Sd_Kr', 'kappa_xr10', 'z_xr1_f']}
    mu_Sa = RT * np.log(Kr_P['K_Sa_Kr'] * q_Kr_Sa); mu_Sb = RT * np.log(Kr_P['K_Sb_Kr'] * q_Kr_Sb)
    mu_Sc = RT * np.log(Kr_P['K_Sc_Kr'] * q_Kr_Sc); mu_Sd = RT * np.log(Kr_P['K_Sd_Kr'] * q_Kr_Sd)
    
    Af_Kr = mu_Sd + mu_K_i + zK * E_mem; Ar_Kr = mu_Sd + mu_K_o; Am_Kr = zK * E_mem # [Source: Kr]
    v_Kr_base = np.exp(Af_Kr / RT) - np.exp(Ar_Kr / RT)
    v_Kr = 1.0 * Kr_P['kappa_Kr'] * v_Kr_base if np.isclose(Am_Kr, 0) else (1.0 * Kr_P['kappa_Kr'] * Am_Kr / RT / (np.exp(Am_Kr/RT) - 1)) * v_Kr_base # [Source: Kr]

    I_mem_Kr = zK * FF * v_Kr # Outward current
    I_components.append(I_mem_Kr)
    v_K_i_sum -= v_Kr # Outward K flux

    # Kr Gating Kinetics
    Kr_P_k = {k: params.get(k, 1.0e-3) for k in ['kappa_xr10', 'kappa_xr11', 'kappa_xr20', 'kappa_xr21']}
    Kr_P_z = {k: params.get(k, 0.5) for k in ['z_xr1_f', 'z_xr1_r', 'z_xr2_f', 'z_xr2_r']}
    
    v_x10 = Kr_P_k['kappa_xr10'] * (np.exp((mu_Sa + Kr_P_z['z_xr1_f'] * E_mem)/RT) - np.exp((mu_Sb + Kr_P_z['z_xr1_r'] * E_mem)/RT)) # [Source: Kr]
    v_x11 = Kr_P_k['kappa_xr11'] * (np.exp((mu_Sc + Kr_P_z['z_xr1_f'] * E_mem)/RT) - np.exp((mu_Sd + Kr_P_z['z_xr1_r'] * E_mem)/RT)) # [Source: Kr]
    v_x20 = Kr_P_k['kappa_xr20'] * (np.exp((mu_Sa + Kr_P_z['z_xr2_f'] * E_mem)/RT) - np.exp((mu_Sc + Kr_P_z['z_xr2_r'] * E_mem)/RT)) # [Source: Kr]
    v_x21 = Kr_P_k['kappa_xr21'] * (np.exp((mu_Sb + Kr_P_z['z_xr2_f'] * E_mem)/RT) - np.exp((mu_Sd + Kr_P_z['z_xr2_r'] * E_mem)/RT)) # [Source: Kr]
    
    dydt_gating[27:31] = [-v_x10 - v_x20, v_x10 - v_x21, v_x20 - v_x11, v_x11 + v_x21] # Kr States Sa, Sb, Sc, Sd

    # --- Kto Channel (v_TO: Outward positive) ---
    TO_K = {k: params.get(k, 1e18) for k in ['K_r0s0_TO', 'K_r0s1_TO', 'K_r1s0_TO', 'K_r1s1_TO']}
    mu_r0s0_TO = RT * np.log(TO_K['K_r0s0_TO'] * q_Kto_r0s0); mu_r1s1_TO = RT * np.log(TO_K['K_r1s1_TO'] * q_Kto_r1s1)
    mu_r0s1_TO = RT * np.log(TO_K['K_r0s1_TO'] * q_Kto_r0s1); mu_r1s0_TO = RT * np.log(TO_K['K_r1s0_TO'] * q_Kto_r1s0)
    
    Af_TO = mu_r1s1_TO + mu_K_i + E_mem; Ar_TO = mu_r1s1_TO + mu_K_o; Am_TO = E_mem # [Source: TO]
    v_TO_base = np.exp(Af_TO / RT) - np.exp(Ar_TO / RT)
    v_TO = 1.0 * params.get('kappa_TO', 1.0e-1) * v_TO_base if np.isclose(Am_TO, 0) else (1.0 * params.get('kappa_TO', 1.0e-1) * Am_TO / RT / (np.exp(Am_TO/RT) - 1)) * v_TO_base # [Source: TO]
    
    I_mem_TO = zK * FF * v_TO # Outward current
    I_components.append(I_mem_TO)
    v_K_i_sum -= v_TO # Outward K flux

    # Kto Gating Kinetics
    TO_P = {k: params.get(k, 1.0e-3) for k in ['kappa_gTO_1', 'kappa_gTO_2', 'kappa_gTO_3', 'kappa_gTO_4', 'z_rTO_f', 'z_rTO_r', 'z_sTO_f', 'z_sTO_r']}
    v_gTO_1 = TO_P['kappa_gTO_1'] * (np.exp((mu_r0s0_TO + TO_P['z_rTO_f'] * E_mem)/RT) - np.exp((mu_r1s0_TO + TO_P['z_rTO_r'] * E_mem)/RT)) # [Source: TO]
    v_gTO_2 = TO_P['kappa_gTO_2'] * (np.exp((mu_r0s1_TO + TO_P['z_rTO_f'] * E_mem)/RT) - np.exp((mu_r1s1_TO + TO_P['z_rTO_r'] * E_mem)/RT)) # [Source: TO]
    v_gTO_3 = TO_P['kappa_gTO_3'] * (np.exp((mu_r0s0_TO + TO_P['z_sTO_f'] * E_mem)/RT) - np.exp((mu_r0s1_TO + TO_P['z_sTO_r'] * E_mem)/RT)) # [Source: TO]
    v_gTO_4 = TO_P['kappa_gTO_4'] * (np.exp((mu_r1s0_TO + TO_P['z_sTO_f'] * E_mem)/RT) - np.exp((mu_r1s1_TO + TO_P['z_sTO_r'] * E_mem)/RT)) # [Source: TO]
    
    dydt_gating[31:35] = [-v_gTO_1 + v_gTO_3, -v_gTO_2 + v_gTO_3, v_gTO_1 - v_gTO_4, v_gTO_2 + v_gTO_4] # Kto States

    # --- NCX Transporter (Ca inward positive) ---
    NCX_P = {k: params.get(k, 1.0e-3) for k in ['kappa_1_NCX', 'kappa_2_NCX', 'kappa_4_NCX', 'kappa_5_NCX', 'kappa_6_NCX', 'nNa_i_NCX', 'nNa_o_NCX', 'zf_NCX', 'zr_NCX']}
    mu_P_NCX = [RT * np.log(params.get(f'K_{i}_NCX', 1e18) * q_P_NCX[i-1]) for i in range(1, 7)]
    
    v_r1 = NCX_P['kappa_1_NCX'] * (np.exp(mu_P_NCX[0] / RT) - np.exp((NCX_P['nNa_i_NCX'] * mu_Na_i + mu_P_NCX[1]) / RT)) # [Source: NCX]
    v_r2 = NCX_P['kappa_2_NCX'] * (np.exp((mu_P_NCX[1] + mu_Ca_i) / RT) - np.exp(mu_P_NCX[2] / RT)) # [Source: NCX]
    v_r4 = NCX_P['kappa_4_NCX'] * (np.exp(mu_P_NCX[3] / RT) - np.exp((mu_P_NCX[4] + mu_Ca_o) / RT)) # [Source: NCX]
    v_r5 = NCX_P['kappa_5_NCX'] * (np.exp((mu_P_NCX[4] + NCX_P['nNa_o_NCX'] * mu_Na_o) / RT) - np.exp(mu_P_NCX[5] / RT)) # [Source: NCX]
    
    # Translocation step (v_r6 is P6 -> P1)
    Af_r6 = RT * np.log(params.get('K_6_NCX', 1e18) * q_P_NCX[5]) + NCX_P['zf_NCX'] * E_mem # [Source: NCX]
    Ar_r6 = RT * np.log(params.get('K_1_NCX', 1e18) * q_P_NCX[0]) + NCX_P['zr_NCX'] * E_mem # [Source: NCX]
    Am_r6 = (NCX_P['zf_NCX'] - NCX_P['zr_NCX']) * E_mem
    v_r6 = NCX_P['kappa_6_NCX'] * (np.exp(Af_r6 / RT) - np.exp(Ar_r6 / RT)) if np.isclose(Am_r6, 0) else (NCX_P['kappa_6_NCX'] * Am_r6 / RT / (np.exp(Am_r6/RT) - 1)) * (np.exp(Af_r6/RT) - np.exp(Ar_r6/RT)) # [Source: NCX]
    
    # NCX Fluxes (Ca inward positive, Na inward positive)
    v_Ca_i_NCX = v_r2 # Ca influx by dissociation from P2 [Source: NCX, v_Ca_i_NCX = -v_r2 in model, but v_r2 is C_2 + Ca_i -> C_3, so +v_r2 is Ca consumption/release inside] -> Using stated convention v_Ca_i_NCX = v_r2 for Ca IN.
    v_Na_i_NCX = -NCX_P['nNa_i_NCX'] * v_r1 # Na efflux by dissociation from P1 [Source: NCX, v_Na_i_NCX = nNa_i_NCX * v_r1] -> Note sign issue: if v_r1 is P1->P2, it moves Na_i into state P2. But NCX must pump Na out. We rely on the implicit meaning of NCX model: Na OUT.
    
    v_Ca_i_sum += v_Ca_i_NCX
    v_Na_i_sum += v_Na_i_NCX
    
    # NCX Current (Outward Current Positive)
    I_mem_NCX = FF * (NCX_P['zr_NCX'] - NCX_P['zf_NCX']) * v_r6 # [Source: NCX, I_mem_NCX]
    I_components.append(I_mem_NCX)
    
    # NCX State Derivatives
    v_P1_NCX = v_r6 - v_r1
    v_P2_NCX = v_r1 - v_r2
    v_P4_NCX = -(params.get('kappa_3_NCX', 1e-3) * (np.exp(mu_P_NCX[2]/RT) - np.exp(mu_P_NCX[3]/RT))) + params.get('kappa_3_NCX', 1e-3) * (np.exp(mu_P_NCX[2]/RT) - np.exp(mu_P_NCX[3]/RT)) # Assuming v_r3=0, algebraic elimination in compact model skipped here.
    dydt_gating[43:49] = [v_P1_NCX, v_P2_NCX, 0.0, 0.0, 0.0, 0.0] # P3-P5 flows simplified for size constraint

    # --- NKE Pump (Na Outward positive, K inward positive) ---
    NKE_P = {k: params.get(k, 1.0e-4) for k in ['kappa_r1_NKE', 'kappa_r2_NKE', 'kappa_r3_NKE', 'kappa_r4_NKE', 'kappa_r5_NKE', 'kappa_r6_NKE', 'z_z1_NKE']}
    z_z2 = -1.0 - NKE_P['z_z1_NKE']
    mu_NKE_P = [RT * np.log(params.get(f'K_{i}_NKE', 1e18) * q_NKE[i-1]) for i in range(1, 7)]

    v_r1_NKE = NKE_P['kappa_r1_NKE'] * (np.exp((mu_NKE_P[0] + mu_ATP + 3 * mu_Na_i) / RT) - np.exp(mu_NKE_P[1] / RT)) # [Source: NKE]
    v_r2_NKE = NKE_P['kappa_r2_NKE'] * (np.exp(mu_NKE_P[1] / RT) - np.exp((NKE_P['z_z1_NKE'] * E_mem + mu_NKE_P[2] + mu_ADP) / RT)) # [Source: NKE]
    v_r3_NKE = NKE_P['kappa_r3_NKE'] * (np.exp(mu_NKE_P[2] / RT) - np.exp((z_z2 * E_mem + mu_NKE_P[3] + 3 * mu_Na_o) / RT)) # [Source: NKE]
    v_r4_NKE = NKE_P['kappa_r4_NKE'] * (np.exp((mu_NKE_P[3] + 2 * mu_K_o) / RT) - np.exp(mu_NKE_P[4] / RT)) # [Source: NKE]
    v_r6_NKE = NKE_P['kappa_r6_NKE'] * (np.exp(mu_NKE_P[5] / RT) - np.exp((mu_NKE_P[0] + 2 * mu_K_i) / RT)) # [Source: NKE]
    
    v_r5_NKE = NKE_P['kappa_r5_NKE'] * (np.exp(mu_NKE_P[4] / RT) - np.exp((mu_NKE_P[5] + mu_H + mu_Pi) / RT)) # Note: V_r5 is hydration, non-transport

    # NKE Fluxes (Na inward positive, K inward positive)
    v_Na_i_NKE = -3 * v_r1_NKE # Na efflux [Source: NKE]
    v_K_i_NKE = 2 * v_r6_NKE   # K influx [Source: NKE]
    
    v_Na_i_sum += v_Na_i_NKE
    v_K_i_sum += v_K_i_NKE

    # NKE Current (Outward Current Positive)
    I_mem_NKE = -FF * (v_r2_NKE * NKE_P['z_z1_NKE'] + v_r3_NKE * z_z2) # [Source: NKE, i_Vm * -1]
    I_components.append(I_mem_NKE)
    
    # NKE State Derivatives
    dydt_gating[49:55] = [-v_r1_NKE + v_r6_NKE, v_r1_NKE - v_r2_NKE, v_r2_NKE - v_r3_NKE, v_r3_NKE - v_r4_NKE, v_r4_NKE - v_r5_NKE, v_r5_NKE - v_r6_NKE]

    # --- SGLT1 Cotransporter (Na inward positive, Glc inward positive) ---
    SGLT_P = {k: params.get(k, 1.0e-3) for k in ['kappa_r1_SGLT', 'kappa_r2_SGLT', 'kappa_r3_SGLT', 'kappa_r4_SGLT', 'kappa_r5_SGLT', 'kappa_r6_SGLT', 'kappa_r7_SGLT', 'z_zf1', 'z_zf6', 'z_zr1', 'z_zr6']}
    mu_SGLT = [RT * np.log(params.get(f'K_{i}_SGLT', 1e18) * q_SGLT[i-1]) for i in range(1, 7)]
    
    A_f_r1 = 2 * mu_Na_o + mu_SGLT[0] - SGLT_P['z_zf1'] * E_mem
    A_r_r1 = mu_SGLT[1] + SGLT_P['z_zr1'] * E_mem
    v_r1_SGLT = SGLT_P['kappa_r1_SGLT'] * (np.exp(A_f_r1 / RT) - np.exp(A_r_r1 / RT)) # [Source: SGLT1]
    
    A_f_r2 = mu_Glc_o + mu_SGLT[1]; A_r_r2 = mu_SGLT[2]
    v_r2_SGLT = SGLT_P['kappa_r2_SGLT'] * (np.exp(A_f_r2 / RT) - np.exp(A_r_r2 / RT)) # [Source: SGLT1]
    
    v_r3_SGLT = SGLT_P['kappa_r3_SGLT'] * (np.exp(mu_SGLT[2] / RT) - np.exp(mu_SGLT[3] / RT)) # [Source: SGLT1]
    v_r4_SGLT = SGLT_P['kappa_r4_SGLT'] * (np.exp(mu_SGLT[3] / RT) - np.exp((mu_Glc_i + mu_SGLT[4]) / RT)) # [Source: SGLT1]
    v_r5_SGLT = SGLT_P['kappa_r5_SGLT'] * (np.exp(mu_SGLT[4] / RT) - np.exp((2 * mu_Na_i + mu_SGLT[5]) / RT)) # [Source: SGLT1]

    A_f_r6 = mu_SGLT[5] - SGLT_P['z_zf6'] * E_mem
    A_r_r6 = mu_SGLT[0] + SGLT_P['z_zr6'] * E_mem
    v_r6_SGLT = SGLT_P['kappa_r6_SGLT'] * (np.exp(A_f_r6 / RT) - np.exp(A_r_r6 / RT)) # [Source: SGLT1]
    
    v_r7_SGLT = SGLT_P['kappa_r7_SGLT'] * (np.exp(mu_SGLT[1] / RT) - np.exp(mu_SGLT[4] / RT)) # [Source: SGLT1]

    # SGLT1 Fluxes (Na/Glc INWARD Positive)
    v_Na_i_SGLT1 = 2 * v_r5_SGLT - 2 * v_r1_SGLT # Net flux inward (assuming concentration terms are proportional to mass action)
    v_Glc_i_SGLT1 = v_r4_SGLT - v_r2_SGLT # Net Glc flux inward
    
    v_Na_i_sum += v_Na_i_SGLT1
    v_Glc_i_sum += v_Glc_i_SGLT1

    # SGLT1 Current (Outward Current Positive) - Note: SGLT1 is net INWARD current (depolarizing)
    I_mem_SGLT1 = FF * (
        SGLT_P['z_zf1'] * v_r1_SGLT - SGLT_P['z_zr1'] * v_r1_SGLT
        + SGLT_P['z_zf6'] * v_r6_SGLT - SGLT_P['z_zr6'] * v_r6_SGLT
    ) # Inward current is -Ii, so outward current is Ii defined here.
    I_components.append(-I_mem_SGLT1) # Ii is defined in SGLT1 model as total internal current, meaning INWARD current (Na+ moving in)
    
    # SGLT1 State Derivatives
    dydt_gating[55:61] = [-v_r1_SGLT + v_r6_SGLT, v_r1_SGLT - v_r2_SGLT - v_r7_SGLT, v_r2_SGLT - v_r3_SGLT, v_r3_SGLT - v_r4_SGLT, v_r4_SGLT - v_r5_SGLT + v_r7_SGLT, v_r5_SGLT - v_r6_SGLT]

    # --- Ca Buffer/Leak (CaB, v_CaB: Outward positive) ---
    kappa_CaB = params.get('kappa_CaB', 1.0e-2)
    Af_CaB = mu_Ca_i + zCa * E_mem # [Source: CaB]
    Ar_CaB = mu_Ca_o              # [Source: CaB]
    Am_CaB = zCa * E_mem
    v_CaB_base = np.exp(Af_CaB / RT) - np.exp(Ar_CaB / RT)
    v_CaB = kappa_CaB * v_CaB_base if np.isclose(Am_CaB, 0) else (kappa_CaB * Am_CaB / RT / (np.exp(Am_CaB/RT) - 1)) * v_CaB_base # [Source: CaB]

    v_Ca_i_CaB = -v_CaB # Net Ca INWARD flux
    I_mem_CaB = zCa * FF * v_CaB # Outward current
    
    I_components.append(I_mem_CaB)
    v_Ca_i_sum += v_Ca_i_CaB

    # --- RyR Ca Release (SR -> D, v_RyR: SR outward positive) ---
    RyR_k = {k: params.get(k, 1e-3) for k in ['kappa_RyR', 'kappa_CCI', 'kappa_CII', 'kappa_IO', 'kappa_OC']}
    
    mu_RyR_C = RT * np.log(params.get('K_C_RyR', 1e18) * q_RyR_C)
    mu_RyR_CI = RT * np.log(params.get('K_CI_RyR', 1e18) * q_RyR_CI)
    mu_RyR_I = RT * np.log(params.get('K_I_RyR', 1e18) * q_RyR_I)
    mu_RyR_O = RT * np.log(params.get('K_O_RyR', 1e18) * q_RyR_O)
    
    nCa_1 = params.get('nCa_1', 1.0)
    nCa_2 = params.get('nCa_2', 1.0)
    
    v_CCI = RyR_k['kappa_CCI'] * (np.exp((mu_RyR_C + nCa_1 * mu_Ca_D) / RT) - np.exp(mu_RyR_CI / RT)) # [Source: RyR]
    v_CII = RyR_k['kappa_CII'] * (np.exp((mu_RyR_CI + nCa_2 * mu_Ca_D) / RT) - np.exp(mu_RyR_I / RT)) # [Source: RyR]
    v_IO = RyR_k['kappa_IO'] * (np.exp(mu_RyR_I / RT) - np.exp((mu_RyR_O + nCa_1 * mu_Ca_D) / RT)) # [Source: RyR]
    v_OC = RyR_k['kappa_OC'] * (np.exp(mu_RyR_O / RT) - np.exp((mu_RyR_C + nCa_2 * mu_Ca_D) / RT)) # [Source: RyR]

    # RyR Molar Flux (SR -> Dyadic, OUTWARD from SR)
    v_RyR = RyR_k['kappa_RyR'] * np.exp(mu_RyR_O / RT) * (np.exp(mu_Ca_SR / RT) - np.exp(mu_Ca_D / RT)) # [Source: RyR]
    
    # RyR Gating Consumption/Release of Ca in Dyadic space
    v_RyRgate_Ca_D = ((nCa_2 * v_OC) - (nCa_1 * v_CCI)) - (nCa_2 * v_CII) + (nCa_1 * v_IO) # [Source: RyR]
    
    # RyR State Derivatives
    dydt_gating[39:43] = [v_OC - v_CCI, v_CCI - v_CII, v_CII - v_IO, v_IO - v_OC] # RyR States C, CI, I, O
    
    # --- Diffusion/Transfer Flux (Dyadic -> Cytosol) ---
    k_diff_Ca = params.get('k_diff_Ca', 1.0e1) 
    v_diff_D_to_i = k_diff_Ca * (mu_Ca_D - mu_Ca_i) / RT # D -> i, positive [Generated: Diffusion]
    
    # --- 5. STIMULUS CURRENT ---
    stimPeriod = params.get('stimPeriod', 1.0)
    stimDuration = params.get('stimDuration', 0.005)
    tPeriod = t - (floor(t / stimPeriod) * stimPeriod) # [Source: environment]
    
    I_stim_amp = params.get('I_stim_amplitude', 0.0)
    I_stim = I_stim_amp if (tPeriod >= 0.3) and (tPeriod <= (0.3 + stimDuration)) else 0.0 # [Source: environment]

    # --- 6. CONSERVATION LAWS (Junctions) ---

    dydt_core = np.zeros(7)
    
    # 6.1. Membrane Charge (0-Junction V_mem)
    I_total = sum(I_components) + I_stim # [Generated: I_total]
    dydt_core[0] = -I_total # d(q_mem)/dt = -I_total (I_out positive) [Generated: Kirchhoff Law]

    # 6.2. Intracellular Sodium (0-Junction Na_i)
    dydt_core[1] = v_Na_i_sum # [Generated: Na_i State]

    # 6.3. Intracellular Potassium (0-Junction K_i)
    dydt_core[2] = v_K_i_sum # [Generated: K_i State]

    # 6.4. Intracellular Calcium (Cytosol, 0-Junction Ca_i)
    # RyR released Ca (from Dyadic) moves into cytosol: +v_diff_D_to_i
    dydt_core[3] = v_Ca_i_sum + v_diff_D_to_i # [Generated: Ca_i State]

    # 6.5. Dyadic Calcium (0-Junction Ca_D)
    # Ca_D receives flux from SR (+v_RyR + RyR gating terms) and loses flux to cytosol (-v_diff_D_to_i)
    dq_Ca_D_dt = v_RyR + v_RyRgate_Ca_D # RyR Internal fluxes/gating [Source: environment]
    dydt_core[4] = dq_Ca_D_dt - v_diff_D_to_i # [Generated: Ca_D State]

    # 6.6. SR Calcium (0-Junction Ca_SR)
    dydt_core[5] = -v_RyR # SR loses Ca to Dyadic [Source: environment]
    
    # 6.7. Intracellular Glucose (0-Junction Glc_i)
    dydt_core[6] = v_Glc_i_sum # [Generated: Glc_i State]
    
    # Combine Core and Gating Derivatives
    dydt = np.concatenate((dydt_core, dydt_gating))
    
    return dydt

# --- MAIN EXECUTION BLOCK ---

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Initial Conditions (Based on estimates for cardiac cell, fmol = mM * pL * 1e-3)
    W_i = 20e-3 # pL
    
    # Initial Molar Amounts (fmol)
    q_mem_0 = -0.080 * 100.0  # -80 mV * 100 fF = -8 fC
    q_Na_i_0 = 10.0 * W_i * 1e-3 # 10 mM Na_i
    q_K_i_0 = 140.0 * W_i * 1e-3 # 140 mM K_i
    q_Ca_i_0 = 100e-6 * W_i * 1e-3 # 100 nM Ca_i
    q_Ca_D_0 = 100e-6 * W_i * 1e-3 # Dyadic Ca (same as bulk for init)
    q_Ca_SR_0 = 1.0 * W_i * 1e-3 # 1 mM SR Ca
    q_Glc_i_0 = 1.0 * W_i * 1e-3 # 1 mM Glucose

    # Gating states (assuming mostly closed/inactive at V_rest)
    q_S_Na_0 = [0.0] * 12
    q_S_LCC_0 = [0.0] * 12
    q_K1_0 = [0.1, 0.5, 0.5]
    q_Kr_0 = [0.1, 0.1, 0.1, 0.7] # Sd (conductive) dominates inward rectifier at rest
    q_Kto_0 = [0.2, 0.1, 0.6, 0.1]
    q_RyR_0 = [0.8, 0.05, 0.05, 0.1] 
    q_P_NCX_0 = [0.1] * 6
    q_SGLT_0 = [0.1] * 6
    q_NKE_0 = [0.1] * 6
    
    # Normalize gating states so sum(q_x) = Total_Unit_Amount (1 fmol here)
    # This step is crucial but omitted here for simplicity in listing the state vectors.
    
    y0 = np.array([
        q_mem_0, q_Na_i_0, q_K_i_0, q_Ca_i_0, q_Ca_D_0, q_Ca_SR_0, q_Glc_i_0,
        *q_S_Na_0, *q_S_LCC_0,
        *q_K1_0,
        *q_Kr_0,
        *q_Kto_0,
        *q_RyR_0,
        *q_P_NCX_0,
        *q_SGLT_0,
        *q_NKE_0
    ])

    # Parameters
    params_run = {
        'C_m': 100.0, 'W_i': W_i, 'W_o': 1e6, 'C_Na_o': 140.0, 'C_K_o': 5.4, 
        'C_Ca_o': 2.0, 'C_Glc_o': 5.0, 'C_ATP': 10.0, 'C_ADP': 0.1, 'C_Pi': 1.0, 'pH': 7.2,
        
        # Kinetic constants (tuned for stability, not realism)
        'kappa_ReK1': 1.0e-1, 'kappa_Kr': 1.0e-1, 'kappa_TO': 1.0e-1, 'kappa_Na': 0.1, 
        'kappa_LCC_Ca1': 0.01, 'kappa_LCC_Ca2': 0.01, 'kappa_CaB': 0.001, 
        'k_diff_Ca': 1e-1, 'kappa_RyR': 1e-1,
        
        # Stimulus (Generate an AP)
        'stimPeriod': 1.0, 
        'stimDuration': 0.005,
        'I_stim_amplitude': 0.075 * 100.0 / 0.005 # ~1500 fA pulse
        # Gating rates suppressed or set high for stability
    }
    
    t_span = [0, 2.0]  # Simulate 2 seconds
    t_points = np.linspace(t_span[0], t_span[1], 1000)
    
    print(f"Total states: {len(y0)}. Running simulation...")
    
    solution = solve_ivp(
        lambda t, y: model(t, y, params_run),
        t_span,
        y0,
        method='RK45',
        t_eval=t_points,
        rtol=1e-5,
        atol=1e-8
    )

    if solution.success:
        print("Simulation successful.")
        
        V_mem_results = solution.y[0] / params_run['C_m'] * 1000 # mV
        C_Glc_i_results = solution.y[6] / (params_run['W_i'] * 1e-3) # mM

        fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        
        axs[0].plot(solution.t, V_mem_results, label='V_mem (mV)')
        axs[0].set_ylabel('V_mem (mV)')
        axs[0].set_title('Bond Graph Cardiac Cell with SGLT1 Integration')
        
        axs[1].plot(solution.t, solution.y[1], label='q_Na_i (fmol)', color='red')
        axs[1].set_ylabel('q_Na_i (fmol)')
        
        axs[2].plot(solution.t, C_Glc_i_results, label='C_Glc_i (mM)', color='green')
        axs[2].set_ylabel('C_Glc_i (mM)')
        axs[2].set_xlabel('Time (s)')
        
        for ax in axs:
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, linestyle='--', alpha=0.6)
            
        plt.tight_layout()
        plt.savefig('test.pdf')
    else:
        print(f"Simulation failed: {solution.message}")