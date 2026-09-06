# Autonomous Survey Drone

PX4 + ROS 2 + Gazebo autonomous drone simulation with a custom sensor-equipped x500 model.

## Features

- Custom Gazebo x500 sensor model
- 5-LiDAR perception system
- RGB camera
- ROS 2 integration
- Autonomous survey waypoint mission
- LiDAR obstacle detection
- Obstacle avoidance and path rejoin
- Automatic return and landing
- Visual red-target detection
- PX4 position reporting during detection
- YOLO11n integration

## Architecture

```text
                     PX4
                      |
                 ROS 2 / DDS
                      |
          +-----------+-----------+
          |                       |
        LiDAR                   Camera
          |                       |
  Obstacle Detection       Visual Detection
          |                       |
  Obstacle Avoidance       OpenCV / YOLO
          |                       |
          +-----------+-----------+
                      |
               Mission Controller
                      |
             Survey / Avoid / Land

