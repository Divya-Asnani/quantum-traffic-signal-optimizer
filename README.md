# Quantum Traffic Signal Optimizer

An AI-assisted traffic signal optimization system that combines traffic-flow prediction with quantum optimization to improve green-time allocation at a signalized intersection.

## Overview

Traffic congestion at intersections is influenced by changing vehicle demand across different approaches. Fixed signal timings may therefore result in inefficient allocation of green time.

This project uses a machine learning model to predict traffic demand and a Quantum Approximate Optimization Algorithm (QAOA) to determine an optimized signal-timing configuration based on the predicted demand.

A classical optimization approach is also applied to the same problem to provide a comparative evaluation.

## Objectives

* Predict traffic volume for the approaches of a signalized intersection.
* Optimize green-time allocation based on predicted traffic demand.
* Apply QAOA to the signal-timing optimization problem.
* Compare the quantum and classical optimization results.
* Visualize the resulting traffic and signal-timing improvements.

## Methodology

### Traffic Prediction

Historical traffic data is processed and used to train a supervised machine learning model for predicting traffic volume.

Model performance will be evaluated using appropriate regression metrics such as MAE, RMSE, and R².

### Signal Optimization

The predicted traffic demand is used to formulate a constrained signal-timing optimization problem.

The optimization considers factors including traffic demand, signal-cycle duration, and feasible green-time limits.

### Quantum Optimization

The signal-timing problem is formulated as a small optimization instance and solved using QAOA through quantum simulation.

The resulting quantum solution is compared with a classical solution under the same traffic conditions and constraints.

## Technology Stack

* Python
* Pandas
* NumPy
* Scikit-learn
* Qiskit
* Qiskit Aer
* Streamlit
* Plotly
* Matplotlib

## Evaluation

The system evaluates both traffic prediction and signal optimization performance.

The quantum and classical approaches will be compared using factors such as:

* Signal-timing allocation
* Objective value
* Estimated waiting time
* Estimated congestion
* Computational performance

The comparison is performed on the same optimization problem to provide a consistent evaluation of both approaches.

## Scope

The project focuses on a single signalized intersection and a small optimization instance suitable for quantum simulation.

This is a proof-of-concept demonstrating the application of AI and quantum optimization to adaptive traffic-signal control.
