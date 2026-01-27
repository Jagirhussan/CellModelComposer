import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# --- Numerical Safeguards ---
def safe_exp(x):
    return np.exp(np.clip(x, -700, 700))

def safe_log(x):
    return np.log(np.maximum(x, 1e-50))

def safe_power(base, exp):
    return np.power(np.maximum(base, 1e-50), exp)

def safe_sqrt(x):
    return np.sqrt(np.maximum(x, 1e-50))

def model(t, y, params):
    # 1. Scaffold States (0 to 4)
    V_mem = y[0]
    Na_i = y[1]
    Na_o = y[2]
    Glc_i = y[3]
    Glc_o = y[4]
    # 2. Unpack Internal States
    sglt1_transporter_params_kinetic_V_E = y[5] # [Internal State] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_SGLT1_kinetic_CNa2_o = y[6] # [Internal State] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_SCNa2_o = y[7] # [Internal State] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_SCNa2_i = y[8] # [Internal State] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_CNa2_i = y[9] # [Internal State] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_C_i = y[10] # [Internal State] Source: sglt1_transporter_SGLT1_kinetic
    # 3. Unpack Parameters & Constants
    sglt1_transporter_params_kinetic_R = params.get('sglt1_transporter_params_kinetic_R', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_T = params.get('sglt1_transporter_params_kinetic_T', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_F = params.get('sglt1_transporter_params_kinetic_F', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_C_o_0 = params.get('sglt1_transporter_params_kinetic_C_o_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_C_i_0 = params.get('sglt1_transporter_params_kinetic_C_i_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_CNa2_o_0 = params.get('sglt1_transporter_params_kinetic_CNa2_o_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_CNa2_i_0 = params.get('sglt1_transporter_params_kinetic_CNa2_i_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_SCNa2_o_0 = params.get('sglt1_transporter_params_kinetic_SCNa2_o_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_SCNa2_i_0 = params.get('sglt1_transporter_params_kinetic_SCNa2_i_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_alpha = params.get('sglt1_transporter_params_kinetic_alpha', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_delta = params.get('sglt1_transporter_params_kinetic_delta', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_12_0 = params.get('sglt1_transporter_params_kinetic_k_12_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_23_0 = params.get('sglt1_transporter_params_kinetic_k_23_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_34 = params.get('sglt1_transporter_params_kinetic_k_34', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_45 = params.get('sglt1_transporter_params_kinetic_k_45', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_56 = params.get('sglt1_transporter_params_kinetic_k_56', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_61_0 = params.get('sglt1_transporter_params_kinetic_k_61_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_25 = params.get('sglt1_transporter_params_kinetic_k_25', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_21_0 = params.get('sglt1_transporter_params_kinetic_k_21_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_32 = params.get('sglt1_transporter_params_kinetic_k_32', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_43 = params.get('sglt1_transporter_params_kinetic_k_43', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_54_0 = params.get('sglt1_transporter_params_kinetic_k_54_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_65_0 = params.get('sglt1_transporter_params_kinetic_k_65_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_16_0 = params.get('sglt1_transporter_params_kinetic_k_16_0', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_k_52 = params.get('sglt1_transporter_params_kinetic_k_52', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_test_volt = params.get('sglt1_transporter_params_kinetic_test_volt', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_params_kinetic_dt = params.get('sglt1_transporter_params_kinetic_dt', 0.0) # [Parameter] Source: sglt1_transporter_params_kinetic
    sglt1_transporter_SGLT1_kinetic_C_i = params.get('sglt1_transporter_SGLT1_kinetic_C_i', 0.0) # [Parameter] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_CNa2_o = params.get('sglt1_transporter_SGLT1_kinetic_CNa2_o', 0.0) # [Parameter] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_CNa2_i = params.get('sglt1_transporter_SGLT1_kinetic_CNa2_i', 0.0) # [Parameter] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_SCNa2_o = params.get('sglt1_transporter_SGLT1_kinetic_SCNa2_o', 0.0) # [Parameter] Source: sglt1_transporter_SGLT1_kinetic
    sglt1_transporter_SGLT1_kinetic_SCNa2_i = params.get('sglt1_transporter_SGLT1_kinetic_SCNa2_i', 0.0) # [Parameter] Source: sglt1_transporter_SGLT1_kinetic
    C_m_default = 1.534e-4 # [Default] Membrane Capacitance (e.g. ~153 pF/cm^2 scaled)
    # 4. Algebraic Equations (Sorted)
    sglt1_transporter_params_kinetic_V0_Vm = V_mem # [Source: sglt1_transporter_params_kinetic]
    sglt1_transporter_params_kinetic_rate_VE = 0 if t < 1204.75 else (sglt1_transporter_params_kinetic_test_volt + 0.05) / sglt1_transporter_params_kinetic_dt if t >= 1204.75 and t < 1204.75 + sglt1_transporter_params_kinetic_dt else 0 if t >= 1204.75 + sglt1_transporter_params_kinetic_dt and t < 2984.75 else -(sglt1_transporter_params_kinetic_test_volt + 0.05) / sglt1_transporter_params_kinetic_dt if t >= 2984.75 and t < 2984.75 + sglt1_transporter_params_kinetic_dt else 0 # [Source: sglt1_transporter_params_kinetic]
    sglt1_transporter_SGLT1_kinetic_C_T = sglt1_transporter_params_kinetic_C_o_0 + sglt1_transporter_params_kinetic_C_i_0 + sglt1_transporter_params_kinetic_CNa2_o_0 + sglt1_transporter_params_kinetic_CNa2_i_0 + sglt1_transporter_params_kinetic_SCNa2_o_0 + sglt1_transporter_params_kinetic_SCNa2_i_0 # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_C_o = sglt1_transporter_SGLT1_kinetic_C_T - (sglt1_transporter_SGLT1_kinetic_CNa2_i + sglt1_transporter_SGLT1_kinetic_CNa2_o + sglt1_transporter_SGLT1_kinetic_SCNa2_o + sglt1_transporter_SGLT1_kinetic_SCNa2_i + sglt1_transporter_SGLT1_kinetic_C_i) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_mu = sglt1_transporter_params_kinetic_F * sglt1_transporter_params_kinetic_V0_Vm / (sglt1_transporter_params_kinetic_R * sglt1_transporter_params_kinetic_T) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_16 = sglt1_transporter_params_kinetic_k_16_0 * safe_exp(sglt1_transporter_params_kinetic_delta * sglt1_transporter_SGLT1_kinetic_mu) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_61 = sglt1_transporter_params_kinetic_k_61_0 * safe_exp(-sglt1_transporter_params_kinetic_delta * sglt1_transporter_SGLT1_kinetic_mu) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_12 = sglt1_transporter_params_kinetic_k_12_0 * safe_power(Na_o, 2) * safe_exp(-sglt1_transporter_params_kinetic_alpha * sglt1_transporter_SGLT1_kinetic_mu) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_21 = sglt1_transporter_params_kinetic_k_21_0 * safe_exp(sglt1_transporter_params_kinetic_alpha * sglt1_transporter_SGLT1_kinetic_mu) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_65 = sglt1_transporter_params_kinetic_k_65_0 * safe_power(Na_i, 2) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_23 = sglt1_transporter_params_kinetic_k_23_0 * Glc_o # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_k_54 = sglt1_transporter_params_kinetic_k_54_0 * Glc_i # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_I_ss = 2 * sglt1_transporter_params_kinetic_F * (sglt1_transporter_SGLT1_kinetic_k_16 * sglt1_transporter_SGLT1_kinetic_C_o - sglt1_transporter_SGLT1_kinetic_k_61 * sglt1_transporter_SGLT1_kinetic_C_i) # [Source: sglt1_transporter_SGLT1_kinetic]
    sglt1_transporter_SGLT1_kinetic_Ii = 2 * sglt1_transporter_params_kinetic_F * (sglt1_transporter_params_kinetic_alpha * (sglt1_transporter_SGLT1_kinetic_k_12 * sglt1_transporter_SGLT1_kinetic_C_o - sglt1_transporter_SGLT1_kinetic_k_21 * sglt1_transporter_SGLT1_kinetic_CNa2_o) - sglt1_transporter_params_kinetic_delta * (sglt1_transporter_SGLT1_kinetic_k_16 * sglt1_transporter_SGLT1_kinetic_C_o - sglt1_transporter_SGLT1_kinetic_k_61 * sglt1_transporter_SGLT1_kinetic_C_i)) # [Source: sglt1_transporter_SGLT1_kinetic]
    # 5. Internal State Derivatives
    d_sglt1_transporter_params_kinetic_V_E_dt = sglt1_transporter_params_kinetic_rate_VE # [Source: sglt1_transporter_params_kinetic]
    d_sglt1_transporter_SGLT1_kinetic_CNa2_o_dt = sglt1_transporter_SGLT1_kinetic_k_12 * sglt1_transporter_SGLT1_kinetic_C_o + sglt1_transporter_params_kinetic_k_52 * sglt1_transporter_SGLT1_kinetic_CNa2_i + sglt1_transporter_params_kinetic_k_32 * sglt1_transporter_SGLT1_kinetic_SCNa2_o - (sglt1_transporter_SGLT1_kinetic_k_21 + sglt1_transporter_params_kinetic_k_25 + sglt1_transporter_SGLT1_kinetic_k_23) * sglt1_transporter_SGLT1_kinetic_CNa2_o # [Source: sglt1_transporter_SGLT1_kinetic]
    d_sglt1_transporter_SGLT1_kinetic_SCNa2_o_dt = sglt1_transporter_SGLT1_kinetic_k_23 * sglt1_transporter_SGLT1_kinetic_CNa2_o + sglt1_transporter_params_kinetic_k_43 * sglt1_transporter_SGLT1_kinetic_SCNa2_i - (sglt1_transporter_params_kinetic_k_32 + sglt1_transporter_params_kinetic_k_34) * sglt1_transporter_SGLT1_kinetic_SCNa2_o # [Source: sglt1_transporter_SGLT1_kinetic]
    d_sglt1_transporter_SGLT1_kinetic_SCNa2_i_dt = sglt1_transporter_params_kinetic_k_34 * sglt1_transporter_SGLT1_kinetic_SCNa2_o + sglt1_transporter_SGLT1_kinetic_k_54 * sglt1_transporter_SGLT1_kinetic_CNa2_i - (sglt1_transporter_params_kinetic_k_43 + sglt1_transporter_params_kinetic_k_45) * sglt1_transporter_SGLT1_kinetic_SCNa2_i # [Source: sglt1_transporter_SGLT1_kinetic]
    d_sglt1_transporter_SGLT1_kinetic_CNa2_i_dt = sglt1_transporter_params_kinetic_k_25 * sglt1_transporter_SGLT1_kinetic_CNa2_o + sglt1_transporter_params_kinetic_k_45 * sglt1_transporter_SGLT1_kinetic_SCNa2_i + sglt1_transporter_SGLT1_kinetic_k_65 * sglt1_transporter_SGLT1_kinetic_C_i - (sglt1_transporter_params_kinetic_k_52 + sglt1_transporter_SGLT1_kinetic_k_54 + sglt1_transporter_params_kinetic_k_56) * sglt1_transporter_SGLT1_kinetic_CNa2_i # [Source: sglt1_transporter_SGLT1_kinetic]
    d_sglt1_transporter_SGLT1_kinetic_C_i_dt = sglt1_transporter_SGLT1_kinetic_k_16 * sglt1_transporter_SGLT1_kinetic_C_o + sglt1_transporter_params_kinetic_k_56 * sglt1_transporter_SGLT1_kinetic_CNa2_i - (sglt1_transporter_SGLT1_kinetic_k_61 + sglt1_transporter_SGLT1_kinetic_k_65) * sglt1_transporter_SGLT1_kinetic_C_i # [Source: sglt1_transporter_SGLT1_kinetic]
    # 6. Scaffold Derivatives (Conservation Laws)
    d_V_mem_dt = -1 * (sglt1_transporter_SGLT1_kinetic_I_ss) / C_m_default # [Generated: Kirchhoff Law (I/C)]
    d_Na_i_dt = 1 * (((sglt1_transporter_SGLT1_kinetic_I_ss)) / sglt1_transporter_params_kinetic_F) # [Generated: Conservation Mirror]
    d_Na_o_dt = -1 * ((sglt1_transporter_SGLT1_kinetic_I_ss) / sglt1_transporter_params_kinetic_F) # [Generated: Conservation]
    d_Glc_i_dt = 1 * (((sglt1_transporter_SGLT1_kinetic_I_ss)) / (2 * sglt1_transporter_params_kinetic_F)) # [Generated: Conservation Mirror]
    d_Glc_o_dt = -1 * ((sglt1_transporter_SGLT1_kinetic_I_ss) / (2 * sglt1_transporter_params_kinetic_F)) # [Generated: Conservation]
    # 7. Return Vector
    return [d_V_mem_dt, d_Na_i_dt, d_Na_o_dt, d_Glc_i_dt, d_Glc_o_dt, d_sglt1_transporter_params_kinetic_V_E_dt, d_sglt1_transporter_SGLT1_kinetic_CNa2_o_dt, d_sglt1_transporter_SGLT1_kinetic_SCNa2_o_dt, d_sglt1_transporter_SGLT1_kinetic_SCNa2_i_dt, d_sglt1_transporter_SGLT1_kinetic_CNa2_i_dt, d_sglt1_transporter_SGLT1_kinetic_C_i_dt]

if __name__ == "__main__":
    # Total States: 5 Scaffold + 6 Internal
    y0 = [0.0] * 11
    params = {
    "sglt1_transporter_params_kinetic_R": 8.31,
    "sglt1_transporter_params_kinetic_T": 293.0,
    "sglt1_transporter_params_kinetic_F": 96485.0,
    "sglt1_transporter_params_kinetic_C_o_0": 13.7727015449461,
    "sglt1_transporter_params_kinetic_C_i_0": 11.4302815603453,
    "sglt1_transporter_params_kinetic_CNa2_o_0": 72.295598813025,
    "sglt1_transporter_params_kinetic_CNa2_i_0": 1.73527350102727,
    "sglt1_transporter_params_kinetic_SCNa2_o_0": 0.16701061319503,
    "sglt1_transporter_params_kinetic_SCNa2_i_0": 0.233806833618937,
    "sglt1_transporter_params_kinetic_alpha": 0.3,
    "sglt1_transporter_params_kinetic_delta": 0.7,
    "sglt1_transporter_params_kinetic_k_12_0": 0.08,
    "sglt1_transporter_params_kinetic_k_23_0": 100.0,
    "sglt1_transporter_params_kinetic_k_34": 50.0,
    "sglt1_transporter_params_kinetic_k_45": 800.0,
    "sglt1_transporter_params_kinetic_k_56": 10.0,
    "sglt1_transporter_params_kinetic_k_61_0": 3.0,
    "sglt1_transporter_params_kinetic_k_25": 0.3,
    "sglt1_transporter_params_kinetic_k_21_0": 500.0,
    "sglt1_transporter_params_kinetic_k_32": 20.0,
    "sglt1_transporter_params_kinetic_k_43": 50.0,
    "sglt1_transporter_params_kinetic_k_54_0": 10971.0,
    "sglt1_transporter_params_kinetic_k_65_0": 5e-05,
    "sglt1_transporter_params_kinetic_k_16_0": 35.0,
    "sglt1_transporter_params_kinetic_k_52": 0.823,
    "sglt1_transporter_params_kinetic_test_volt": 0.0,
    "sglt1_transporter_params_kinetic_dt": 0.001,
    "sglt1_transporter_SGLT1_kinetic_C_i": 0.0,
    "sglt1_transporter_SGLT1_kinetic_CNa2_o": 0.0,
    "sglt1_transporter_SGLT1_kinetic_CNa2_i": 0.0,
    "sglt1_transporter_SGLT1_kinetic_SCNa2_o": 0.0,
    "sglt1_transporter_SGLT1_kinetic_SCNa2_i": 0.0
}
    t_span = (0, 100)
# try:
    sol = solve_ivp(model, t_span, y0, args=(params,), method='BDF')
    print('Simulation Successful!')
    print('Solution shape:', sol.y.shape)
# except Exception as e:
    # print(f'Simulation Failed: {e}')