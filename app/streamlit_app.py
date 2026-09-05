import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# Add project root to Python path
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_backend import (
    run_pipeline,
    prepare_pipeline,
    submit_ibm_pipeline,
    retrieve_ibm_pipeline,
)
from src.ibm_quantum_optimizer import (
    get_qaoa_job_status,
    submit_qaoa_job_ibm,
)

@st.cache_data(show_spinner=False, ttl=3600)
def cached_pipeline(demand_tuple):
    demand = dict(demand_tuple)
    return run_pipeline(custom_demand=demand)

@st.cache_data(show_spinner=False)
def cached_intersection_html(traffic_demand_tuple, signal_timing_tuple, mode):
    """Cache intersection HTML rendering to avoid regenerating complex JS"""
    traffic_demand = dict(traffic_demand_tuple)
    signal_timing = dict(signal_timing_tuple) if signal_timing_tuple else None
    return render_intersection(traffic_demand=traffic_demand, signal_timing=signal_timing, mode=mode)

# --------------------------------------------------
# Page configuration & Styling
# --------------------------------------------------

st.set_page_config(
    page_title="Quantum Traffic Signal Optimizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Typography and Base Styling */
    html, body, .stApp {
        font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Enforce light theme across the app to prevent dark mode white-on-white text */
    .stApp {
        background-color: #FFFFFF !important;
        color: #334155 !important;
    }
    
    /* Ensure all text elements default to readable dark colors */
    .stApp p, 
    .stApp span, 
    .stApp label, 
    .stApp div[data-baseweb="radio"], 
    .stApp .stMarkdown,
    .stApp .stText {
        color: #334155 !important;
    }

    /* Sidebar specific text enforcement */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] .stMarkdown {
        color: #0F172A !important;
    }

    /* Explicit override for Radio labels (resolves invisible labels) */
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        color: #0F172A !important;
    }

    /* Selectboxes & Number Inputs */
    div[data-testid="stSelectbox"] label p,
    div[data-testid="stNumberInput"] label p {
        color: #0F172A !important;
    }
    
    /* Info Callouts (st.info) */
    div[data-testid="stAlert"] {
        background-color: #E0F2FE !important;
    }
    div[data-testid="stAlert"] p, 
    div[data-testid="stAlert"] span {
        color: #0C4A6E !important;
    }

    /* Spinner Text Fix */
    div[data-testid="stSpinner"] > div {
        background: transparent !important;
    }
    div[data-testid="stSpinner"] p, 
    div[data-testid="stSpinner"] span {
        color: #0F172A !important;
        background: transparent !important;
    }
    
    /* Primary Button styles (must protect from global text overrides) */
    div.stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
    }
    div.stButton > button[kind="primary"] p,
    div.stButton > button[kind="primary"] span {
        color: #FFFFFF !important;
    }
    
    /* Clean Dashboard Header */
    .dash-header {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: flex-end;
        padding-top: 1rem;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid #E2E8F0;
        background-color: #FFFFFF;
    }
    
    .dash-title-container {
        flex: 1 1 auto;
        margin-right: 1rem;
    }
    
    .dash-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    
    .dash-subtitle {
        font-size: 1.1rem;
        font-weight: 400;
        color: #64748B;
    }
    
    .status-indicator {
        font-size: 0.9rem;
        font-weight: 600;
        padding: 0.3rem 0.8rem;
        border-radius: 4px;
        background-color: #F8FAFC;
        color: #334155;
        border: 1px solid #E2E8F0;
        display: inline-block; 
        margin-top: 1rem;
        white-space: nowrap;
    }
    
    .status-ready { background-color: #ECFDF5; color: #065F46; border-color: #A7F3D0; }
    
    /* Section Typography */
    .section-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #0F172A;
        margin-top: 2.5rem;
        margin-bottom: 1.2rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #E2E8F0;
    }
    
    .sub-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.8rem;
    }

    /* Structured Data Cards */
    .data-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        height: 100%;
    }
    
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
    }
    
    /* Initial State Container */
    .empty-state {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 2rem;
        text-align: left;
        margin-top: 1rem;
        margin-bottom: 2rem;
    }
    
    .empty-state h3 {
        color: #0F172A;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .empty-state-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }
    
    .step-box {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
    }
    
    .step-num { font-weight: 700; color: #2563EB; font-size: 0.9rem; margin-bottom: 0.3rem;}
    .step-desc { font-size: 0.85rem; color: #475569; line-height: 1.4; }
    
    /* Technical Metadata */
    .meta-key {
        font-weight: 600;
        color: #475569;
    }
    .meta-val {
        font-family: 'SFMono-Regular', Consolas, monospace;
        color: #0F172A;
    }

    /* Responsive Media Queries */
    @media (max-width: 768px) {
        .dash-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .status-indicator {
            margin-top: 1rem;
        }
        .data-card {
            margin-bottom: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# IBM QUANTUM ASYNC SESSION STATE
# ============================================================

if "ibm_job_id" not in st.session_state:
    st.session_state.ibm_job_id = None

if "ibm_job_status" not in st.session_state:
    st.session_state.ibm_job_status = None

if "ibm_prepared_results" not in st.session_state:
    st.session_state.ibm_prepared_results = None

if "optimization_results" not in st.session_state:
    st.session_state.optimization_results = None

# --------------------------------------------------
# Cache Invalidation Helpers
# --------------------------------------------------
def invalidate_results():
    st.session_state.optimization_results = None

# --------------------------------------------------
# Left Control Panel (Sidebar)
# --------------------------------------------------

with st.sidebar:
    st.markdown("### Operational Configuration")
    st.markdown("Select traffic demand inputs for the signal network.")
    traffic_source = st.radio(
        "Traffic Source",
        ["AI Prediction", "Simulation", "Custom"],
        on_change=invalidate_results
    )
    
    custom_demand = None
    
    if traffic_source == "Simulation":
        PRESETS = {
            "Morning Rush": {"North": 120.0, "South": 80.0, "East": 30.0, "West": 25.0},
            "Evening Rush": {"North": 30.0, "South": 40.0, "East": 110.0, "West": 150.0},
            "North-South Heavy": {"North": 95.0, "South": 105.0, "East": 15.0, "West": 20.0},
            "East-West Heavy": {"North": 10.0, "South": 15.0, "East": 85.0, "West": 90.0},
            "Balanced Traffic": {"North": 50.0, "South": 50.0, "East": 50.0, "West": 50.0},
            "Low Traffic": {"North": 10.0, "South": 8.0, "East": 12.0, "West": 5.0}
        }
        
        scenario_name = st.selectbox(
            "Select Scenario",
            list(PRESETS.keys()),
            on_change=invalidate_results
        )
        custom_demand = PRESETS[scenario_name]
        
    elif traffic_source == "Custom":
        st.markdown("**Directional Demand (Vehicles)**")
        col1, col2 = st.columns(2)
        with col1:
            n_val = st.number_input("North", min_value=0.0, value=50.0, step=5.0, on_change=invalidate_results)
            e_val = st.number_input("East", min_value=0.0, value=50.0, step=5.0, on_change=invalidate_results)
        with col2:
            s_val = st.number_input("South", min_value=0.0, value=50.0, step=5.0, on_change=invalidate_results)
            w_val = st.number_input("West", min_value=0.0, value=50.0, step=5.0, on_change=invalidate_results)
        
        custom_demand = {"North": n_val, "East": e_val, "South": s_val, "West": w_val}
        
    else:
        st.info("Live Random Forest ML predictions on the historical dataset will be executed.")

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    # ============================================================
# RUN OPTIMIZATION
# ============================================================

if st.button("Run Optimization", type="primary", use_container_width=True):
    try:
        # ========================================================
        # STEP 1: GET USER TRAFFIC DEMAND
        # ========================================================

        if custom_demand is None:
            st.error(
                "Please select a traffic scenario or enter custom traffic demand."
            )
            st.stop()

        traffic_demand = {
            "North": float(custom_demand["North"]),
            "East": float(custom_demand["East"]),
            "South": float(custom_demand["South"]),
            "West": float(custom_demand["West"])
        }

        total_demand = sum(traffic_demand.values())

        if total_demand <= 0:
            st.error("Traffic demand must contain at least one vehicle.")
            st.stop()

        # ========================================================
        # STEP 2: PREPARE BACKEND
        # ========================================================

        with st.spinner("Calculating classical optimization..."):

            prepared_results = prepare_pipeline(
                custom_demand=traffic_demand
            )

        # ========================================================
        # STEP 3: SUBMIT QAOA TO IBM QUANTUM
        # ========================================================

        with st.spinner("Submitting QAOA to IBM Quantum..."):

            job_id, ibm_metadata = submit_qaoa_job_ibm(
                prepared_results["traffic_demand"],
                shots=512,
                reps=1
            )

        # ========================================================
        # STEP 4: SAVE CURRENT OPTIMIZATION
        # ========================================================

        prepared_results["ibm_job_id"] = job_id
        prepared_results["qaoa_metadata"] = ibm_metadata
        prepared_results["qaoa_status"] = "QUEUED"

        st.session_state.user_traffic_demand = traffic_demand

        st.session_state.ibm_prepared_results = prepared_results

        st.session_state.ibm_job_id = job_id
        st.session_state.ibm_job_status = "QUEUED"

        # Remove previous completed results
        st.session_state.optimization_results = None

        # ========================================================
        # STEP 5: DISPLAY INPUT SENT TO BACKEND
        # ========================================================

        st.success(
            "Traffic optimization prepared successfully."
        )

        st.info(
            f"""
**Traffic Demand Sent to Backend**

North: {traffic_demand["North"]:.0f} vehicles  
East: {traffic_demand["East"]:.0f} vehicles  
South: {traffic_demand["South"]:.0f} vehicles  
West: {traffic_demand["West"]:.0f} vehicles  

**Total Demand:** {total_demand:.0f} vehicles
"""
        )

        st.success(
            f"QAOA submitted successfully to IBM Quantum. "
            f"Job ID: `{job_id}`"
        )

        st.info(
            "The QAOA calculation is running asynchronously. "
            "Classical optimization has already been calculated."
        )

    except Exception as e:
        st.error(
            f"Optimization failed: {str(e)}"
        )


# ============================================================
# IBM QUANTUM JOB STATUS
# ============================================================

if st.session_state.get("ibm_job_id"):

    st.markdown("### IBM Quantum Hardware")

    job_id = st.session_state.ibm_job_id

    st.write(f"**Job ID:** `{job_id}`")

    if st.button(
        "Check IBM Quantum Job Status",
        use_container_width=True
    ):

        try:

            current_status = get_qaoa_job_status(job_id)

            st.session_state.ibm_job_status = current_status

            # ====================================================
            # JOB COMPLETED
            # ====================================================

            if current_status == "DONE":

                prepared_results = (
                    st.session_state.ibm_prepared_results
                )

                with st.spinner(
                    "Retrieving QAOA result..."
                ):

                    final_results = retrieve_ibm_pipeline(
                        job_id=job_id,
                        traffic_demand=(
                            prepared_results["traffic_demand"]
                        ),
                        prepared_results=prepared_results
                    )

                # Save final comparison results
                st.session_state.optimization_results = (
                    final_results
                )

                st.success(
                    "IBM Quantum optimization completed successfully."
                )

                st.rerun()

            # ====================================================
            # JOB STILL RUNNING
            # ====================================================

            elif current_status in [
                "QUEUED",
                "RUNNING",
                "INITIALIZING",
                "VALIDATING"
            ]:

                st.info(
                    f"IBM Quantum job status: **{current_status}**"
                )

            # ====================================================
            # JOB FAILED
            # ====================================================

            elif current_status in [
                "CANCELLED",
                "ERROR",
                "FAILED"
            ]:

                st.error(
                    f"IBM Quantum job finished with status: "
                    f"**{current_status}**"
                )

            # ====================================================
            # OTHER STATUS
            # ====================================================

            else:

                st.warning(
                    f"IBM Quantum job status: "
                    f"**{current_status}**"
                )

        except Exception as e:

            st.error(
                f"Unable to retrieve IBM Quantum status: {str(e)}"
            )

    # ============================================================
    # CURRENT STATUS
    # ============================================================

    current_status = st.session_state.get(
        "ibm_job_status"
    )

    if current_status:

        st.caption(
            f"Current IBM Quantum status: {current_status}"
        )
#------------------------------------
# Main Content Area - Header
# --------------------------------------------------

status_text = "OPTIMIZED" if st.session_state.get("optimization_results") else "READY"
status_class = "status-ready" if status_text == "OPTIMIZED" else ""

st.markdown(f"""
<div class="dash-header">
    <div class="dash-title-container">
        <div class="dash-title">Quantum Traffic Optimizer</div>
        <div class="dash-subtitle">AI-powered traffic prediction and quantum signal optimization</div>
    </div>
    <div class="status-indicator {status_class}">SYSTEM STATUS: {status_text}</div>
</div>
""", unsafe_allow_html=True)


import json

# --------------------------------------------------
# Intersection Visualization Architecture
# --------------------------------------------------

def render_intersection(traffic_demand=None, signal_timing=None, mode="neutral"):
    """
    Renders a clean, data-driven CSS/HTML four-way intersection.
    """
    
    html_str = """
    <style>
        .intersection-outer {
            width: 100%;
            display: flex;
            justify-content: center;
            overflow: hidden;
            margin-bottom: 2rem;
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 1rem;
        }
        .intersection-scaler {
            transform-origin: top center;
            width: 600px;
            height: 600px;
        }
        @media (max-width: 800px) {
            .intersection-scaler { transform: scale(0.8); height: 480px; }
        }
        @media (max-width: 600px) {
            .intersection-scaler { transform: scale(0.6); height: 360px; }
        }
        @media (max-width: 400px) {
            .intersection-scaler { transform: scale(0.45); height: 270px; }
        }
        .intersection-wrapper {
            position: relative;
            width: 100%;
            max-width: 600px;
            height: 600px;
            margin: 0 auto;
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            overflow: hidden;
            font-family: 'Inter', sans-serif;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        /* Roads */
        .road-vertical {
            position: absolute;
            top: 0; bottom: 0;
            left: 220px; right: 220px;
            background-color: #334155;
        }
        .road-horizontal {
            position: absolute;
            left: 0; right: 0;
            top: 220px; bottom: 220px;
            background-color: #334155;
        }
        .center-box {
            position: absolute;
            left: 220px; top: 220px;
            width: 160px; height: 160px;
            background-color: #1E293B;
        }
        
        /* Lane Markings */
        .lane-divider-v {
            position: absolute;
            left: 298px; top: 0; bottom: 0;
            width: 4px;
            background-image: linear-gradient(to bottom, transparent 50%, #FBBF24 50%);
            background-size: 100% 40px;
        }
        .lane-divider-h {
            position: absolute;
            top: 298px; left: 0; right: 0;
            height: 4px;
            background-image: linear-gradient(to right, transparent 50%, #FBBF24 50%);
            background-size: 40px 100%;
        }
        
        /* Stop Lines */
        .stop-line-n { position: absolute; left: 220px; top: 214px; width: 78px; height: 6px; background: white; }
        .stop-line-s { position: absolute; left: 302px; top: 380px; width: 78px; height: 6px; background: white; }
        .stop-line-e { position: absolute; left: 380px; top: 220px; width: 6px; height: 78px; background: white; }
        .stop-line-w { position: absolute; left: 214px; top: 302px; width: 6px; height: 78px; background: white; }

        /* Labels */
        .dir-label {
            position: absolute;
            font-weight: 700;
            font-size: 0.9rem;
            color: #334155;
            background: rgba(255,255,255,0.95);
            padding: 6px 12px;
            border-radius: 4px;
            border: 1px solid #CBD5E1;
            z-index: 20;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .label-n { top: 20px; left: 120px; }
        .label-s { bottom: 20px; right: 120px; }
        .label-e { right: 20px; top: 120px; }
        .label-w { left: 20px; bottom: 120px; }
        .demand-sub { font-size: 0.75rem; font-weight: 400; color: #64748B; margin-top:2px; }

        /* Traffic Lights */
        .t-light-box {
            position: absolute;
            width: 24px; height: 24px;
            background-color: #1E293B;
            border-radius: 4px;
            border: 2px solid #475569;
            z-index: 10;
        }
        .t-light-indicator {
            width: 14px; height: 14px;
            background-color: #64748B; /* Neutral */
            border-radius: 50%;
            margin: 3px auto;
        }
        .t-light-n { left: 185px; top: 185px; }
        .t-light-s { left: 391px; top: 391px; }
        .t-light-e { left: 391px; top: 185px; }
        .t-light-w { left: 185px; top: 391px; }
        .light-green { background-color: #22C55E !important; box-shadow: 0 0 8px #22C55E; }
        .light-red { background-color: #EF4444 !important; }
        .light-yellow { background-color: #FBBF24 !important; box-shadow: 0 0 8px #FBBF24; }
        
        /* Vehicles */
        .vehicle {
            position: absolute;
            background-color: #38BDF8;
            border-radius: 3px;
            border: 2px solid #0284C7;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            z-index: 5;
            transition:
        top 3s linear,
        left 3s linear,
        opacity 0.5s linear;
        }
        .vehicle::after {
            /* Minimal window accent */
            content: '';
            position: absolute;
            background: #0284C7;
        }
        /* Vertical Cars */
        .veh-v { width: 24px; height: 36px; }
        .veh-v::after { left: 2px; right: 2px; height: 6px; }
        .veh-n { left: 246px; }
        .veh-n::after { bottom: 6px; } /* Front window facing down */
        .veh-s { left: 330px; }
        .veh-s::after { top: 6px; } /* Front window facing up */
        
        /* Horizontal Cars */
        .veh-h { width: 36px; height: 24px; }
        .veh-h::after { top: 2px; bottom: 2px; width: 6px; }
        .veh-w { top: 326px; }
        .veh-w::after { right: 6px; } /* Front window facing right */
        .veh-e { top: 246px; }
        .veh-e::after { left: 6px; } /* Front window facing left */
        
        .neutral-overlay {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255,255,255,0.95);
            padding: 20px 30px;
            border-radius: 8px;
            border: 1px solid #CBD5E1;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            z-index: 100;
        }
    </style>
    <div class="intersection-outer">
        <div class="intersection-scaler">
            <div class="intersection-wrapper">
                <!-- Roads -->
                <div class="road-vertical"></div>
                <div class="road-horizontal"></div>
                <div class="center-box"></div>
                
                <!-- Lane Markings -->
                <div class="lane-divider-v"></div>
                <div class="lane-divider-h"></div>
                <div class="stop-line-n"></div>
                <div class="stop-line-s"></div>
                <div class="stop-line-e"></div>
                <div class="stop-line-w"></div>
                
                <!-- Traffic Lights -->
                <div class="t-light-box t-light-n"><div class="t-light-indicator light-yellow"></div></div>
                <div class="t-light-box t-light-s"><div class="t-light-indicator light-yellow"></div></div>
                <div class="t-light-box t-light-e"><div class="t-light-indicator light-yellow"></div></div>
                <div class="t-light-box t-light-w"><div class="t-light-indicator light-yellow"></div></div>
    """
    
    if mode == "neutral":
        html_str += """
                <div class="vehicle veh-v veh-n" style="top:170px;"></div>
                <div class="vehicle veh-v veh-s" style="top:394px;"></div>
            """
    
    # Render Labels
    for d, d_cls in [("North", "label-n"), ("South", "label-s"), ("East", "label-e"), ("West", "label-w")]:
        demand_text = f"{traffic_demand[d]:.1f} veh/h" if (traffic_demand and mode == "populated") else "--- veh/h"
        html_str += f"""
        <div class="dir-label {d_cls}">
            {d}
            <div class="demand-sub">{demand_text}</div>
        </div>
        """

    # Overlay
    if mode == "neutral":
        html_str += """
        <div class="neutral-overlay">
            <h4 style="margin:0 0 10px 0; color:#1E293B; font-weight:600;">System Ready</h4>
            <p style="margin:0; color:#64748B; font-size:0.95rem;">Configure traffic conditions and<br>run optimization to analyze the intersection.</p>
        </div>
        """
        
    html_str += "</div></div></div>"
    
    if mode == "populated" and signal_timing:
        timing_json = json.dumps(signal_timing)
        html_str += f"""
        <div style="text-align:center; font-size:0.8rem; color:#94A3B8; margin-top:10px;">
            Visualization represents relative traffic flow under the selected signal allocation.
        </div>
        <script>
(function() {{

    const timing = {timing_json};
    const demand = {json.dumps(traffic_demand)};

    const directions = ["North", "East", "South", "West"];

    const wrapper = document.querySelector('.intersection-wrapper');

    if (!wrapper) {{
        console.log("Intersection wrapper not found");
        return;
    }}

    let running = true;
    let activeIndex = 0;
    let cycleCount = 0;

    const maxCycles = 6;

    /*
     * Convert QAOA timing into visual time.
     *
     * Example:
     * North = 10 sec -> 3 sec visual green
     * South = 20 sec -> 6 sec visual green
     */
    function getGreenDuration(dir) {{
        return Math.max(2500, (timing[dir] || 10) * 300);
    }}

    /*
     * Convert traffic demand into vehicle arrival frequency.
     */
    let maxDemand = Math.max(
        demand.North || 0,
        demand.East || 0,
        demand.South || 0,
        demand.West || 0,
        1
    );

    function sleep(ms) {{
        return new Promise(resolve => setTimeout(resolve, ms));
    }}

    /*
     * Create one vehicle.
     */
    function createVehicle(dir) {{

        const car = document.createElement("div");

        if (dir === "North" || dir === "South") {{
            car.className = "vehicle veh-v";
        }} else {{
            car.className = "vehicle veh-h";
        }}

        /*
         * Starting positions.
         */
        if (dir === "North") {{
            car.style.left = "246px";
            car.style.top = "-50px";
        }}

        else if (dir === "South") {{
            car.style.left = "330px";
            car.style.top = "520px";
        }}

        else if (dir === "West") {{
            car.style.left = "-50px";
            car.style.top = "326px";
        }}

        else if (dir === "East") {{
            car.style.left = "520px";
            car.style.top = "246px";
        }}

        wrapper.appendChild(car);

        return car;
    }}

    /*
     * Move vehicle through intersection.
     */
    function moveVehicle(car, dir) {{

        /*
         * Force browser to render starting position first.
         */
        car.getBoundingClientRect();

        /*
         * Smooth movement.
         */
        car.style.transition =
            "top 3s linear, left 3s linear, opacity 0.5s linear";

        if (dir === "North") {{
            car.style.top = "520px";
        }}

        else if (dir === "South") {{
            car.style.top = "-50px";
        }}

        else if (dir === "West") {{
            car.style.left = "520px";
        }}

        else if (dir === "East") {{
            car.style.left = "-50px";
        }}

        /*
         * Remove vehicle after crossing.
         */
        setTimeout(() => {{
            if (car.parentNode) {{
                car.style.opacity = "0";

                setTimeout(() => {{
                    if (car.parentNode) {{
                        car.parentNode.removeChild(car);
                    }}
                }}, 500);
            }}
        }}, 3000);
    }}

    /*
     * Set traffic lights.
     */
    function setLights(activeDir) {{

        directions.forEach(dir => {{

            const selector =
                ".t-light-" +
                dir.charAt(0).toLowerCase() +
                " .t-light-indicator";

            const light = document.querySelector(selector);

            if (!light) return;

            light.classList.remove(
                "light-green",
                "light-red",
                "light-yellow"
            );

            if (dir === activeDir) {{
                light.classList.add("light-green");
            }} else {{
                light.classList.add("light-red");
            }}
        }});
    }}

    /*
     * Generate vehicles based on traffic demand.
     */
    async function vehicleArrivalLoop() {{

        while (running) {{

            for (const dir of directions) {{

                const dirDemand = demand[dir] || 0;

                const probability =
                    (dirDemand / maxDemand) * 0.65;

                if (Math.random() < probability) {{

                    /*
                     * Only create vehicles for visualization.
                     */
                    const car = createVehicle(dir);

                    /*
                     * Small delay guarantees the browser
                     * paints the initial position.
                     */
                    await sleep(100);

                    moveVehicle(car, dir);
                }}
            }}

            await sleep(1400);
        }}
    }}

    /*
     * Traffic signal cycle.
     */
    async function signalCycle() {{

        while (running && cycleCount < maxCycles) {{

            const dir = directions[activeIndex];

            /*
             * Green light is controlled by
             * the actual QAOA timing.
             */
            const greenDuration =
                getGreenDuration(dir);

            console.log(
                "GREEN:",
                dir,
                "QAOA timing:",
                timing[dir],
                "seconds"
            );

            setLights(dir);

            /*
             * During green signal, vehicles
             * continue moving.
             */
            await sleep(greenDuration);

            /*
             * Yellow transition.
             */
            const lightSelector =
                ".t-light-" +
                dir.charAt(0).toLowerCase() +
                " .t-light-indicator";

            const activeLight =
                document.querySelector(lightSelector);

            if (activeLight) {{
                activeLight.classList.remove("light-green");
                activeLight.classList.add("light-yellow");
            }}

            await sleep(500);

            /*
             * Next direction.
             */
            activeIndex =
                (activeIndex + 1) % directions.length;

            if (activeIndex === 0) {{
                cycleCount++;

                console.log(
                    "Completed traffic cycle:",
                    cycleCount
                );
            }}
        }}

        running = false;

        /*
         * Reset lights.
         */
        directions.forEach(dir => {{

            const selector =
                ".t-light-" +
                dir.charAt(0).toLowerCase() +
                " .t-light-indicator";

            const light =
                document.querySelector(selector);

            if (light) {{
                light.classList.remove(
                    "light-green",
                    "light-red"
                );

                light.classList.add("light-yellow");
            }}
        }});
    }}

    /*
     * Initial vehicles.
     *
     * Higher traffic demand = more vehicles.
     */
    directions.forEach(dir => {{

        const rate =
            (demand[dir] || 0) / maxDemand;

        const count =
            Math.max(2, Math.floor(rate * 5));

        for (let i = 0; i < count; i++) {{

            const car = createVehicle(dir);

            /*
             * Stagger initial vehicles.
             */
            setTimeout(() => {{
                if (running) {{
                    moveVehicle(car, dir);
                }}
            }}, i * 800);
        }}
    }});

    /*
     * Start simulation.
     */
    vehicleArrivalLoop();
    signalCycle();

}})();
</script>
 """
        
    return html_str

# --------------------------------------------------
# Initial State (Before Optimization)
# --------------------------------------------------

if st.session_state.get("optimization_results") is None:
    st.markdown("""
    <div class="empty-state">
        <h3>Optimization Workflow</h3>
        <div class="empty-state-grid">
            <div class="step-box">
                <div class="step-num">1. Traffic Demand</div>
                <div class="step-desc">AI Prediction or manually defined scenario inputs.</div>
            </div>
            <div class="step-box">
                <div class="step-num">2. Demand Processing</div>
                <div class="step-desc">Normalizes and formats the input into a 4-way vector.</div>
            </div>
            <div class="step-box">
                <div class="step-num">3. Classical Optimization</div>
                <div class="step-desc">Exhaustively computes the absolute global 5s-grid optimum.</div>
            </div>
            <div class="step-box">
                <div class="step-num">4. QAOA Optimization</div>
                <div class="step-desc">Computes the quantum optimum within the restricted 8-qubit space.</div>
            </div>
            <div class="step-box">
                <div class="step-num">5. Performance Analysis</div>
                <div class="step-desc">Validates cycle constraints and computes final metrics.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.components.v1.html(render_intersection(mode="neutral"), height=720)
    st.stop()


# --------------------------------------------------
# Post-Optimization Analysis
# --------------------------------------------------

results = st.session_state.optimization_results
traffic = results["traffic_demand"]
default_timing = results["default_timing"]
classical_full_timing = results["classical_full_timing"]
classical_restricted_timing = results["classical_quantum_compatible_timing"]
qaoa_timing = results["qaoa_timing"]
comparison = results["comparison"]
qaoa_failed = results["qaoa_failed"]

# --- Section 1: Traffic Demand ---
st.markdown('<div class="section-title">1. Traffic Demand</div>', unsafe_allow_html=True)

d_cols = st.columns(4)
directions = ["North", "East", "South", "West"]
for i, d in enumerate(directions):
    with d_cols[i]:
        st.markdown(f"""
        <div class="data-card" style="margin-bottom: 2rem;">
            <div class="metric-label">{d} APPROACH</div>
            <div class="metric-value">{traffic[d]:.1f} <span style="font-size:1rem; font-weight:normal; color:#64748B;">veh</span></div>
        </div>
        """, unsafe_allow_html=True)

# --- Section 3: Optimization Results (Show FIRST for faster perceived load) ---
st.markdown('<div class="section-title">2. Optimization Results</div>', unsafe_allow_html=True)

o_cols = st.columns(4)
overview_metrics = [
    ("Default Baseline", default_timing, comparison["default"]["objective"]),
    ("Full Classical", classical_full_timing, comparison["classical_full"]["objective"]),
    ("Quantum-Compatible Classical", classical_restricted_timing, comparison["classical_restricted"]["objective"]),
    ("QAOA", qaoa_timing if not qaoa_failed else None, comparison["qaoa"]["objective"] if not qaoa_failed else None)
]

for i, (name, timing, obj) in enumerate(overview_metrics):
    with o_cols[i]:
        if timing is None:
            st.markdown(f"""
            <div class="data-card" style="border-top: 4px solid #EF4444; opacity: 0.7;">
                <div class="sub-title" style="font-size: 1rem;">{name}</div>
                <div style="color: #EF4444; font-weight: 600;">Execution Failed</div>
            </div>
            """, unsafe_allow_html=True)
            continue
            
        color = "#94A3B8" if i == 0 else ("#3B82F6" if i == 1 else ("#14B8A6" if i == 2 else "#8B5CF6"))
        st.markdown(f"""
        <div class="data-card" style="border-top: 4px solid {color};">
            <div class="sub-title" style="font-size: 1rem;">{name}</div>
            <div style="margin-bottom: 1rem;">
                <span class="metric-label">OBJECTIVE:</span>
                <span style="font-size: 1.2rem; font-weight: 700;">{obj:.1f}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9rem;">
                <div><span class="meta-key">N:</span> {timing['North']}s</div>
                <div><span class="meta-key">E:</span> {timing['East']}s</div>
                <div><span class="meta-key">S:</span> {timing['South']}s</div>
                <div><span class="meta-key">W:</span> {timing['West']}s</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
st.markdown('<div class="section-title">2. Intersection Visualization</div>', unsafe_allow_html=True)

with st.expander("📊 Show Animation", expanded=True):
    v_col1, v_col2 = st.columns([1, 1])
    with v_col1:
        view_state = st.radio(
            "Visualization State",
            ["Before (Baseline)", "After (Optimized)"],
            horizontal=True
        )
    with v_col2:
        if not qaoa_failed:
            sol_opts = ["QAOA", "Full Classical", "Quantum-Compatible Classical"]
        else:
            sol_opts = ["Full Classical", "Quantum-Compatible Classical"]
            
        selected_solution = st.selectbox("Optimized Solution", sol_opts)

    if view_state == "Before (Baseline)":
        active_timing = default_timing
    else:
        if selected_solution == "QAOA":
            active_timing = qaoa_timing
        elif selected_solution == "Full Classical":
            active_timing = classical_full_timing
        else:
            active_timing = classical_restricted_timing

    st.markdown("<br>", unsafe_allow_html=True)
    # Use cached rendering for faster display
    html_content = render_intersection(
    traffic_demand=traffic,
    signal_timing=active_timing,
    mode="populated"
)

import base64

html_b64 = base64.b64encode(
    html_content.encode("utf-8")
).decode("utf-8")

iframe_html = f"""
<iframe
    src="data:text/html;base64,{html_b64}"
    width="100%"
    height="720"
    style="border:none;"
></iframe>
"""

# --- Section 3: Optimization Results ---
st.markdown('<div class="section-title">3. Optimization Results</div>', unsafe_allow_html=True)

o_cols = st.columns(4)
overview_metrics = [
    ("Default Baseline", default_timing, comparison["default"]["objective"]),
    ("Full Classical", classical_full_timing, comparison["classical_full"]["objective"]),
    ("Quantum-Compatible Classical", classical_restricted_timing, comparison["classical_restricted"]["objective"]),
    ("QAOA", qaoa_timing if not qaoa_failed else None, comparison["qaoa"]["objective"] if not qaoa_failed else None)
]

for i, (name, timing, obj) in enumerate(overview_metrics):
    with o_cols[i]:
        if timing is None:
            st.markdown(f"""
            <div class="data-card" style="border-top: 4px solid #EF4444; opacity: 0.7;">
                <div class="sub-title" style="font-size: 1rem;">{name}</div>
                <div style="color: #EF4444; font-weight: 600;">Execution Failed</div>
            </div>
            """, unsafe_allow_html=True)
            continue
            
        color = "#94A3B8" if i == 0 else ("#3B82F6" if i == 1 else ("#14B8A6" if i == 2 else "#8B5CF6"))
        st.markdown(f"""
        <div class="data-card" style="border-top: 4px solid {color};">
            <div class="sub-title" style="font-size: 1rem;">{name}</div>
            <div style="margin-bottom: 1rem;">
                <span class="metric-label">OBJECTIVE:</span>
                <span style="font-size: 1.2rem; font-weight: 700;">{obj:.1f}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9rem;">
                <div><span class="meta-key">N:</span> {timing['North']}s</div>
                <div><span class="meta-key">E:</span> {timing['East']}s</div>
                <div><span class="meta-key">S:</span> {timing['South']}s</div>
                <div><span class="meta-key">W:</span> {timing['West']}s</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# --- Section 4: Performance Analysis ---
with st.expander("📈 Performance Analysis", expanded=False):
    st.markdown('<div class="section-title" style="margin-top: 0;">Metrics & Comparisons</div>', unsafe_allow_html=True)
    
    def format_delta(baseline, new_val):
        diff = new_val - baseline
        pct = (abs(diff) / baseline * 100) if baseline != 0 else 0
        color = "#059669" if diff < 0 else ("#DC2626" if diff > 0 else "#64748B")
        text = f"Improved by {pct:.1f}%" if diff < 0 else (f"Worsened by {pct:.1f}%" if diff > 0 else "0.0% change")
        return f'<span style="color: {color}; font-weight:600;">{text}</span>'

    st.markdown('<div class="sub-title">Full Classical vs Default Baseline</div>', unsafe_allow_html=True)
    p_cols = st.columns(3)
    c_res = comparison["classical_full"]
    d_res = comparison["default"]

    with p_cols[0]:
        st.markdown(f"""<div class="data-card"><div class="metric-label">Total Queue</div>
        <div class="metric-value">{c_res['total_queue']:.0f}</div>
        <div style="margin-top:0.5rem; font-size:0.9rem;">{format_delta(d_res['total_queue'], c_res['total_queue'])}</div></div>""", unsafe_allow_html=True)
        
    with p_cols[1]:
        st.markdown(f"""<div class="data-card"><div class="metric-label">Waiting Time</div>
        <div class="metric-value">{c_res['total_waiting_time']:.0f}</div>
        <div style="margin-top:0.5rem; font-size:0.9rem;">{format_delta(d_res['total_waiting_time'], c_res['total_waiting_time'])}</div></div>""", unsafe_allow_html=True)
        
    with p_cols[2]:
        st.markdown(f"""<div class="data-card"><div class="metric-label">Avg Congestion</div>
        <div class="metric-value">{c_res['average_congestion']:.2f}</div>
        <div style="margin-top:0.5rem; font-size:0.9rem;">{format_delta(d_res['average_congestion'], c_res['average_congestion'])}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    analysis_data = [
        {
            "Algorithm": "Full Classical",
            "Description": "Broader 5-second timing search space",
            "Objective": c_res["objective"]
        },
        {
            "Algorithm": "Quantum-Compatible Classical",
            "Description": "Classical optimum within the QAOA representable space",
            "Objective": comparison["classical_restricted"]["objective"]
        }
    ]

    if not qaoa_failed:
        analysis_data.append({
            "Algorithm": "QAOA",
            "Description": "Quantum optimization within the identical representable space",
            "Objective": comparison["qaoa"]["objective"]
        })

    analysis_df = pd.DataFrame(analysis_data)
    st.dataframe(
        analysis_df,
        column_config={
            "Objective": st.column_config.NumberColumn("Objective Value", format="%.2f")
        },
        hide_index=True,
        use_container_width=True
    )

# --- Section 5: Quantum Details ---
with st.expander("⚛️ Quantum Optimization Details", expanded=False):
    st.markdown('<div class="section-title" style="margin-top: 0;">QAOA Quantum Analysis</div>', unsafe_allow_html=True)
    
    if qaoa_failed:
        st.error(f"QAOA Execution Failed: {results['qaoa_metadata'].get('error', 'Unknown Error')}")
    else:
        meta = results["qaoa_metadata"]
        gap = comparison["qaoa_gap_vs_quantum_compatible"]
        
        if gap <= 1e-6:
            st.success("**Optimum Reached:** QAOA successfully located the true global optimum of the quantum-encodable space.")
        else:
            st.info(f"**Local Minimum:** QAOA found a local minimum with a {gap:.2f} objective gap compared to the theoretical quantum-encodable optimum.")

        m_cols = st.columns(4)
        with m_cols[0]:
            st.markdown(f"<div class='data-card'><div class='metric-label'>Qubits</div><div class='metric-value' style='font-size:1.4rem;'>{meta.get('num_qubits', 8)}</div></div>", unsafe_allow_html=True)
        with m_cols[1]:
            st.markdown(f"<div class='data-card'><div class='metric-label'>Depth (Reps)</div><div class='metric-value' style='font-size:1.4rem;'>{meta.get('qaoa_reps', 1)}</div></div>", unsafe_allow_html=True)
        with m_cols[2]:
            st.markdown(f"<div class='data-card'><div class='metric-label'>QUBO Energy</div><div class='metric-value' style='font-size:1.4rem;'>{meta.get('qaoa_energy', 0):.2f}</div></div>", unsafe_allow_html=True)
        with m_cols[3]:
            st.markdown(f"<div class='data-card'><div class='metric-label'>Penalty</div><div class='metric-value' style='font-size:1.4rem;'>{meta.get('penalty_contribution', 0):.2f}</div></div>", unsafe_allow_html=True)
