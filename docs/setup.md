# PX4 + ROS 2 + Gazebo Autonomous Survey Drone

## Overview

This project is an autonomous drone simulation built using:

- PX4 Autopilot
- Gazebo Sim
- ROS 2 Humble
- ROS-GZ Bridge
- Python
- OpenCV
- YOLO11n

The system uses a custom Gazebo x500 sensor model with five LiDAR sensors and an RGB camera.

## Project Architecture

```text
                    PX4
                     |
                 ROS 2 / DDS
                     |
          +----------+----------+
          |                     |
        LiDAR                 Camera
          |                     |
   Obstacle Detection       Image Stream
          |                     |
   Obstacle Avoidance       OpenCV / YOLO
          |                     |
          +----------+----------+
                     |
              Mission Controller
                     |
          Survey / Avoid / Rejoin
                     |
               Return / Land
