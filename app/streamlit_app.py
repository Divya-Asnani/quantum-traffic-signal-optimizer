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

from src.comparison import compare_solutions
from data.sample_scenario import (
    TRAFFIC_DEMAND,
    DEFAULT_TIMING,
    CLASSICAL_TIMING,
    QUANTUM_TIMING
)
# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Quantum Traffic Signal Optimizer",
    page_icon="🚦",
    layout="wide"
)


# --------------------------------------------------
# Title
# --------------------------------------------------

st.title("🚦 Quantum Traffic Signal Optimizer")

st.markdown(
    """
    **AI-Powered Traffic Prediction + Classical Optimization + QAOA**

    This dashboard compares default, classical, and quantum-optimized
    traffic signal timings using the same traffic evaluation model.
    """
)


# --------------------------------------------------
# Temporary Traffic Data
# --------------------------------------------------

# traffic = TRAFFIC_DEMAND


# --------------------------------------------------
# Temporary Signal Timings
# --------------------------------------------------

# default_timing = {
#     "North": 30,
#     "South": 30,
#     "East": 30,
#     "West": 30
# }

# classical_timing = {
#     "North": 40,
#     "South": 35,
#     "East": 25,
#     "West": 20
# }

# quantum_timing = {
#     "North": 45,
#     "South": 35,
#     "East": 25,
#     "West": 15
# }

# --------------------------------------------------
# Interactive Traffic Conditions
# --------------------------------------------------

st.header("🚗 Traffic Conditions")

st.sidebar.header("Traffic Input")

north_traffic = st.sidebar.number_input(
    "North Traffic",
    min_value=0,
    max_value=200,
    value=TRAFFIC_DEMAND["North"]
)

south_traffic = st.sidebar.number_input(
    "South Traffic",
    min_value=0,
    max_value=200,
    value=TRAFFIC_DEMAND["South"]
)

east_traffic = st.sidebar.number_input(
    "East Traffic",
    min_value=0,
    max_value=200,
    value=TRAFFIC_DEMAND["East"]
)

west_traffic = st.sidebar.number_input(
    "West Traffic",
    min_value=0,
    max_value=200,
    value=TRAFFIC_DEMAND["West"]
)


traffic = {
    "North": north_traffic,
    "South": south_traffic,
    "East": east_traffic,
    "West": west_traffic
}


default_timing = DEFAULT_TIMING
classical_timing = CLASSICAL_TIMING
quantum_timing = QUANTUM_TIMING

# --------------------------------------------------
# Run comparison
# --------------------------------------------------

comparison = compare_solutions(
    traffic,
    default_timing,
    classical_timing,
    quantum_timing
)
# --------------------------------------------------
# Solution Selection
# --------------------------------------------------

st.header("🚦 Select Signal Configuration")

selected_solution = st.selectbox(
    "Choose a configuration to visualize:",
    ["Default", "Classical", "QAOA"]
)

selected_key = selected_solution.lower()

if selected_key == "qaoa":
    st.info("QAOA results will be connected after the quantum optimization module is integrated.")
    selected_result = comparison["classical"]
else:
    selected_result = comparison[selected_key]

# --------------------------------------------------
# Intersection Visualization
# --------------------------------------------------

def create_intersection_plot(traffic, timing):
    """
    Create a simple four-way intersection visualization.
    """

    approaches = ["North", "South", "East", "West"]

    x_positions = {
        "North": 0,
        "South": 0,
        "East": 1,
        "West": -1
    }

    y_positions = {
        "North": 1,
        "South": -1,
        "East": 0,
        "West": 0
    }

    fig = px.scatter(
        x=[x_positions[a] for a in approaches],
        y=[y_positions[a] for a in approaches],
        text=[
            f"{a}<br>"
            f"Traffic: {traffic[a]}<br>"
            f"Green: {timing[a]}s"
            for a in approaches
        ]
    )

    # Intersection roads
    fig.add_shape(
        type="rect",
        x0=-0.25,
        x1=0.25,
        y0=-1.2,
        y1=1.2
    )

    fig.add_shape(
        type="rect",
        x0=-1.2,
        x1=1.2,
        y0=-0.25,
        y1=0.25
    )

    fig.update_traces(
        marker_size=30,
        textposition="middle center"
    )

    fig.update_layout(
        title="Four-Way Intersection",
        xaxis=dict(
            visible=False,
            range=[-1.5, 1.5]
        ),
        yaxis=dict(
            visible=False,
            range=[-1.5, 1.5]
        ),
        showlegend=False,
        height=500
    )

    return fig  
def create_intersection_plot(traffic, timing):

    approaches = ["North", "South", "East", "West"]

    x_positions = {
        "North": 0,
        "South": 0,
        "East": 1,
        "West": -1
    }

    y_positions = {
        "North": 1,
        "South": -1,
        "East": 0,
        "West": 0
    }

    fig = px.scatter(
        x=[x_positions[a] for a in approaches],
        y=[y_positions[a] for a in approaches],
        text=[
            f"{a}<br>"
            f"Traffic: {traffic[a]}<br>"
            f"Green: {timing[a]}s"
            for a in approaches
        ]
    )

    fig.add_shape(
        type="rect",
        x0=-0.25,
        x1=0.25,
        y0=-1.2,
        y1=1.2
    )

    fig.add_shape(
        type="rect",
        x0=-1.2,
        x1=1.2,
        y0=-0.25,
        y1=0.25
    )

    fig.update_traces(
        marker_size=30,
        textposition="middle center"
    )

    fig.update_layout(
        title="Four-Way Intersection",
        xaxis=dict(
            visible=False,
            range=[-1.5, 1.5]
        ),
        yaxis=dict(
            visible=False,
            range=[-1.5, 1.5]
        ),
        showlegend=False,
        height=500
    )

    return fig

st.header("🚦 Intersection")

st.subheader(
    f"{selected_solution} Signal Configuration"
)

intersection_fig = create_intersection_plot(
    traffic,
    selected_result["signal_timing"]
)

st.plotly_chart(
    intersection_fig,
    use_container_width=True
)

st.subheader(
    f"{selected_solution} Performance"
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Queue",
        f"{selected_result['total_queue']:.0f}"
    )

with col2:
    st.metric(
        "Waiting Time",
        f"{selected_result['total_waiting_time']:.0f}"
    )

with col3:
    st.metric(
        "Avg. Congestion",
        f"{selected_result['average_congestion']:.2f}"
    )

with col4:
    st.metric(
        "Objective",
        f"{selected_result['objective']:.2f}"
    )

# --------------------------------------------------
# Section 1: Traffic Conditions
# --------------------------------------------------

st.header("🚗 Traffic Conditions")

traffic_df = pd.DataFrame(
    {
        "Approach": traffic.keys(),
        "Vehicles": traffic.values()
    }
)

st.dataframe(
    traffic_df,
    use_container_width=True,
    hide_index=True
)

fig_traffic = px.bar(
    traffic_df,
    x="Approach",
    y="Vehicles",
    title="Traffic Demand by Approach"
)

st.plotly_chart(
    fig_traffic,
    use_container_width=True
)


# --------------------------------------------------
# Section 2: Signal Timing
# --------------------------------------------------

st.header("🚦 Signal Timing")

timing_df = pd.DataFrame(
    {
        "Approach": list(traffic.keys()),
        "Default": list(default_timing.values()),
        "Classical": list(classical_timing.values()),
        "QAOA": list(quantum_timing.values())
    }
)

st.dataframe(
    timing_df,
    use_container_width=True,
    hide_index=True
)

fig_timing = px.bar(
    timing_df,
    x="Approach",
    y=["Default", "Classical", "QAOA"],
    barmode="group",
    title="Green-Time Allocation"
)

st.plotly_chart(
    fig_timing,
    use_container_width=True
)


# --------------------------------------------------
# Section 3: Performance Metrics
# --------------------------------------------------

st.header("📊 Performance Comparison")


def create_performance_dataframe(comparison):
    rows = []

    for solution in ["default", "classical", "quantum"]:

        result = comparison[solution]

        rows.append(
            {
                "Solution": solution.capitalize(),
                "Total Queue": result["total_queue"],
                "Total Waiting Time": result["total_waiting_time"],
                "Average Congestion": result["average_congestion"],
                "Objective": result["objective"]
            }
        )

    return pd.DataFrame(rows)


performance_df = create_performance_dataframe(comparison)

st.dataframe(
    performance_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# Metric Cards
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

default_result = comparison["default"]
classical_result = comparison["classical"]
quantum_result = comparison["quantum"]

with col1:
    st.subheader("Default")
    st.metric(
        "Objective",
        f"{default_result['objective']:.2f}"
    )
    st.metric(
        "Waiting Time",
        f"{default_result['total_waiting_time']:.2f}"
    )

with col2:
    st.subheader("Classical")
    st.metric(
        "Objective",
        f"{classical_result['objective']:.2f}",
        delta=f"{classical_result['objective'] - default_result['objective']:.2f}"
    )
    st.metric(
        "Waiting Time",
        f"{classical_result['total_waiting_time']:.2f}"
    )

with col3:
    st.subheader("QAOA")
    st.metric(
        "Objective",
        f"{quantum_result['objective']:.2f}",
        delta=f"{quantum_result['objective'] - default_result['objective']:.2f}"
    )
    st.metric(
        "Waiting Time",
        f"{quantum_result['total_waiting_time']:.2f}"
    )


# --------------------------------------------------
# Section 4: Queue Comparison
# --------------------------------------------------

st.header("🚗 Queue Comparison")

queue_df = pd.DataFrame(
    {
        "Approach": list(traffic.keys()),
        "Default": [
            default_result["queue_length"][x]
            for x in traffic
        ],
        "Classical": [
            classical_result["queue_length"][x]
            for x in traffic
        ],
        "QAOA": [
            quantum_result["queue_length"][x]
            for x in traffic
        ]
    }
)

fig_queue = px.bar(
    queue_df,
    x="Approach",
    y=["Default", "Classical", "QAOA"],
    barmode="group",
    title="Queue Length Comparison"
)

st.plotly_chart(
    fig_queue,
    use_container_width=True
)


# --------------------------------------------------
# Section 5: Congestion Comparison
# --------------------------------------------------

st.header("🚧 Congestion Comparison")

congestion_df = pd.DataFrame(
    {
        "Approach": list(traffic.keys()),
        "Default": [
            default_result["congestion"][x]
            for x in traffic
        ],
        "Classical": [
            classical_result["congestion"][x]
            for x in traffic
        ],
        "QAOA": [
            quantum_result["congestion"][x]
            for x in traffic
        ]
    }
)

fig_congestion = px.bar(
    congestion_df,
    x="Approach",
    y=["Default", "Classical", "QAOA"],
    barmode="group",
    title="Congestion Score Comparison"
)

st.plotly_chart(
    fig_congestion,
    use_container_width=True
)


# --------------------------------------------------
# Final Summary
# --------------------------------------------------

st.header("🏁 Summary")

best_solution = min(
    comparison,
    key=lambda x: comparison[x]["objective"]
)

st.success(
    f"Best solution according to the current objective: "
    f"**{best_solution.upper()}**"
)

st.info(
    "Note: The current traffic and signal timings are temporary "
    "development values. They will be replaced by the actual AI, "
    "classical optimizer, and QAOA outputs during integration."
)