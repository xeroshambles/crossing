# Simulations of adaptive intersection manager and combined crossing strategies for an intersections network

This codebase is accompanying papers

  1. "An Adaptive Approach for the Coordination of Autonomous Vehicles at Intersections", by Nicholas Glorio, Stefano Mariani, Giacomo Cabri, and Franco Zambonelli, and published in [WETICE 2021](https://www.wetice2021.org) proceedings.
  2. "Combining Coordination Strategies for Autonomous Vehicles in Intersection Networks", by Marco Gambelli, Stefano Mariani, Giacomo Cabri, and Franco Zambonelli, and published in [IDC 2021](http://www.idc2021.unirc.it/program.html) proceedings.

Credit for the codebase go to Nicholas Glorio and Marco Gambelli.

## Overview

Each folder contains a standalone python project:

  - those **without** the `multi_` prefix are used in the 1st paper
  - those **with** the `multi_` prefix are used in the 2nd paper

## Instructions

| :warning: WARNING          |
|:---------------------------|
| Section in progress        |

Requirements to run the experiments:

  - have SUMO 1.8+ installed
  - have python 3+ installed
  - have traci python package installed

Each folder is a separate simulation tha can be launched through its own `main.py` python script.

To run simulations in batch [...TBD]
