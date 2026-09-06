# Autonomous Survey Drone — PX4 + ROS 2 + Gazebo

> **Build it. Break it. Improve it. Make it yours.**

A practical autonomous-drone simulation built with **PX4 SITL, Gazebo Sim, ROS 2 Humble, a custom x500 sensor model, five LiDAR sensors, an RGB camera, obstacle avoidance, and visual target detection**.

This repository is intended as a starting point for experimentation. The current system is a **working simulation prototype**, not a production-ready or flight-certified autonomy stack.

---

## What You Get

The current known-good build demonstrates:

- Autonomous PX4 Offboard takeoff and flight
- A predefined five-waypoint survey mission
- Five simulated LiDAR sensors
- LiDAR preprocessing and obstacle detection
- Obstacle bypass and survey-path rejoin
- Autonomous return-to-home and landing
- Gazebo RGB camera streamed into ROS 2
- OpenCV-based red visual-target detection
- Drone X/Y/Z reporting at detection time
- YOLO11n installed and independently tested on CPU
- A custom `x500_sensor_demo` Gazebo model

### Current mission concept

```text
                 TAKEOFF
                    |
                    v
             Survey Waypoints
                    |
          +---------+---------+
          |                   |
        LiDAR               Camera
          |                   |
    Obstacle Detection     Target Detection
          |                   |
    Avoid / Rejoin         Record Position
          |                   |
          +---------+---------+
                    |
                    v
               RETURN HOME
                    |
                    v
                  LAND
```

---

## Why This Repository Exists

The goal is not to provide one "perfect" drone.

The goal is to provide a **working baseline that you can understand, modify, and extend**.

You can replace the:

- drone model
- sensors
- camera
- target system
- waypoint planner
- obstacle-avoidance logic
- object detector
- mapping system
- onboard computer
- communication architecture

and turn the project into your own robotics platform.

> **Don't just run the drone. Build your version of it.**
>
> Try a different sensor. Change the planner. Add mapping. Make the detector smarter. Make it fail in a new way and teach it not to.
>
> **Robotics gets interesting when you stop being afraid to change things. Have fun building.**

---

## Current Status

### Functional prototype — COMPLETE

| Capability | Status |
|---|---:|
| PX4 SITL + Gazebo | ✅ |
| Custom x500 sensor model | ✅ |
| Five-LiDAR simulation | ✅ |
| ROS 2 LiDAR bridge | ✅ |
| LiDAR preprocessing | ✅ |
| Autonomous 5-waypoint survey | ✅ |
| Obstacle detection | ✅ |
| Obstacle bypass | ✅ |
| Survey-path rejoin | ✅ |
| Return-to-home | ✅ |
| Automatic landing/disarm | ✅ |
| Gazebo RGB camera | ✅ |
| ROS 2 camera bridge | ✅ |
| Live visual target detection | ✅ |
| Detection during autonomous flight | ✅ |
| Drone X/Y/Z reporting | ✅ |
| YOLO11n installation | ✅ |
| YOLO11n standalone inference | ✅ |

---

## Architecture

```text
                         PX4 SITL
                            |
                  Vehicle Odometry /
                     Flight Commands
                            |
                            v
                 ROS 2 Offboard Controller
                            |
                     Position Setpoints
                            |
                            v
                          PX4
                            |
                            v
                          Gazebo
                     +------+------+
                     |             |
                   LiDAR         Camera
                     |             |
                     v             v
              Gazebo Topics   Gazebo Image
                     |             |
                     v             v
                ros_gz_bridge  ros_gz_bridge
                     |             |
                     v             v
               lidar_node    image_raw
                     |             |
                     v             v
           obstacle distances   OpenCV / YOLO
                     |             |
                     +------+------+
                            |
                            v
                       Mission Demo
```

### Component responsibilities

**PX4**
- Simulates the multicopter flight controller.
- Receives Offboard position setpoints.
- Handles flight control, arming, flight mode, and landing.

**Gazebo**
- Simulates the world, drone, LiDARs, camera, obstacle, and visual target.

**LiDAR perception**
- Reads five `LaserScan` streams.
- Uses a ±45° central sector for horizontal LiDARs.
- Publishes processed `[front, right, rear, left, down]` distances.

**Offboard mission controller**
- Takes the drone to approximately 10 m.
- Flies the survey waypoints.
- Uses processed LiDAR distances for obstacle detection/bypass.
- Rejoins the route and lands at home.

**Camera**
- Provides a 640×480 RGB stream.
- Is bridged to `/drone/camera/image_raw`.

**Red target detector**
- Uses HSV color segmentation.
- Does not depend on `cv_bridge`.
- Reads PX4 odometry and reports the drone position when a target is seen.

**YOLO11n**
- Runs separately inside `~/yolo_env`.
- CPU-only PyTorch is currently used.
- It has been independently tested on a standard image.
- The current flight demo does not make flight behavior depend on YOLO.

---

## Repository Layout

```text
autonomous_survey_drone/
│
├── README.md
├── .gitignore
│
├── docs/
│   └── setup.md
│
├── px4_custom/
│   └── model/
│       └── model.sdf
│
├── worlds/
│   └── default.sdf
│
├── ros2_ws/
│   └── src/
│       └── drone_perception/
│
├── px4_ros2_ws/
│   └── src/
│       └── ROS2-PX4_Drone_Teleoperation_Using_Joystick/
│
└── vision/
    ├── red_target_detector.py
    └── yolo_camera_detector.py
```

---

# Quick Start

The detailed current working setup follows below. Use **separate terminals** for the major processes.

## Terminal 1 — MicroXRCEAgent

```bash
MicroXRCEAgent udp4 -p 8888
```

Leave it running.

---

## Terminal 2 — PX4 + Gazebo

```bash
cd ~/PX4-Autopilot

export MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA"

PX4_SYS_AUTOSTART=22000 PX4_SIM_MODEL=x500_sensor_demo ./build/px4_sitl_default/bin/px4
```

Wait for the world to load and for PX4 to reach `pxh>`.

Verify:

```bash
gz model --list
```

Expected:

```text
ground_plane
test_obstacle
red_detection_target
x500_sensor_demo_0
```

---

## Terminal 3 — LiDAR bridge

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch drone_perception lidar_bridges.launch.py
```

---

## Terminal 4 — Camera bridge

```bash
source /opt/ros/humble/setup.bash

ros2 run ros_gz_bridge parameter_bridge '/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' --ros-args -r /world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image:=/drone/camera/image_raw
```

---

## Terminal 5 — LiDAR perception

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 run drone_perception lidar_node
```

---

## Terminal 6 — Visual target detector

```bash
source ~/yolo_env/bin/activate

python ~/red_target_detector.py
```

Or use the repository copy:

```bash
source ~/yolo_env/bin/activate

python vision/red_target_detector.py
```

---

## Terminal 7 — Autonomous mission

```bash
source /opt/ros/humble/setup.bash
source ~/px4_ros2_ws/install/setup.bash

ros2 run px4_offboard position_offboard_control.py
```

---

# Current Survey Route

The controller currently uses:

```text
HOME
(0,0)
   |
   v
WP1 (5,0)
   |
   v
WP2 (20,0)
   |
   v
WP3 (20,15)
   |
   v
WP4 (5,15)
   |
   v
WP5 (0,0)
   |
   v
RETURN / LAND
```

Configured survey altitude:

```text
10.0 m
```

PX4 local odometry/setpoints use NED-style Z coordinates, so the flight output appears around:

```text
Z = -10 m
```

---

# LiDAR System

Five simulated LiDAR sensors are used:

```text
/drone/lidar_front
/drone/lidar_right
/drone/lidar_rear
/drone/lidar_left
/drone/lidar_down
```

Message type:

```text
sensor_msgs/msg/LaserScan
```

The demonstrated simulated sensor rate is approximately 20 Hz.

Processed topic:

```text
/drone/obstacle_distances
```

Type:

```text
std_msgs/msg/Float32MultiArray
```

Order:

```text
[front, right, rear, left, down]
```

The processing node runs at approximately 10 Hz.

### Verify LiDAR

```bash
ros2 topic list | grep /drone/lidar
```

```bash
ros2 topic hz /drone/lidar_front
```

```bash
ros2 topic echo /drone/obstacle_distances --once
```

---

# Obstacle Avoidance

The current world contains a large test obstacle:

```text
Position:
X = 12
Y = 0
Z = 10

Size:
2 × 2 × 20 m
```

The demonstrated controller can:

```text
SURVEY
   |
   v
Obstacle detected
   |
   v
Choose bypass
   |
   v
AVOID
   |
   v
Obstacle clear
   |
   v
REJOIN
   |
   v
Continue survey
```

A successful run produced:

```text
OBSTACLE DETECTED! Front=2.86m Right=2.10m Left=100.00m
Choosing LEFT bypass
Obstacle clear -> REJOIN SURVEY PATH
```

This is the current proof that LiDAR-based detection, bypass, and route rejoining work together.

---

# Camera

Gazebo camera:

```text
640 × 480
encoding: rgb8
step: 1920
```

ROS topic:

```text
/drone/camera/image_raw
```

Verify:

```bash
ros2 topic info /drone/camera/image_raw
```

```bash
ros2 topic hz /drone/camera/image_raw
```

```bash
ros2 topic echo /drone/camera/image_raw --once --field encoding
```

```bash
ros2 topic echo /drone/camera/image_raw --once --field width
ros2 topic echo /drone/camera/image_raw --once --field height
```

Expected:

```text
rgb8
640
480
```

---

# Visual Target Detection

The current controlled target is:

```text
red_detection_target
```

Current world position:

```text
X = 20
Y = 7.5
Z = 5
```

The current detector uses:

```text
RGB image
   ↓
HSV conversion
   ↓
Red segmentation
   ↓
Contour filtering
   ↓
Bounding box
   ↓
Target event
   ↓
Current drone X/Y/Z
```

Example:

```text
RED TARGET DETECTED
Pixel center : (636, 397)
Drone X      : 14.13 m
Drone Y      : 15.21 m
Drone Z      : -9.99 m
Target area  : 506 px
```

The important distinction is:

> The current detector reports the **drone's position when the target is seen**. It does not yet calculate the target's exact world coordinate.

---

# YOLO11n

The YOLO environment is separate:

```text
~/yolo_env
```

Activate:

```bash
source ~/yolo_env/bin/activate
```

The tested setup uses:

```text
Ultralytics 8.4.142
PyTorch 2.14.0+cpu
TorchVision 0.29.0+cpu
```

YOLO11n was independently tested successfully on `bus.jpg` and detected a bus and several people.

### Why CPU?

The previous CUDA-enabled PyTorch environment caused very slow/hanging initialization in the current WSL/NVIDIA-driver configuration.

The current CPU build is reliable.

> **Do not treat CPU-only YOLO as the final hardware architecture.** It is simply the stable development configuration for this prototype.

---

# Important Limitations

## 1. Predefined mission

The drone currently follows a fixed set of waypoints.

It does **not** yet:

- autonomously explore an unknown environment;
- generate its own survey path;
- perform full SLAM;
- maintain an unexplored-area map;
- select next-best viewpoints dynamically.

## 2. Target position is not yet estimated

The current detector reports:

```text
drone position + target pixel position
```

It does not yet solve:

```text
camera pixel
+
camera pose
+
camera calibration
+
ground geometry
=
target world coordinate
```

That is an important future upgrade.

## 3. Red target detection is controlled

The OpenCV detector is specifically designed for a red visual target.

It is not a generic object-recognition system.

## 4. YOLO is not currently part of flight-critical logic

YOLO11n works independently, but the reliable mission demonstration uses the deterministic red-target detector.

This keeps visual experimentation separate from the flight controller.

## 5. Simulation only

The sensors, dynamics, camera, and communication are simulated.

A real drone introduces:

- sensor noise;
- calibration errors;
- latency;
- vibration;
- motion blur;
- lighting variation;
- wireless communication issues;
- hardware timing constraints;
- power limitations.

## 6. Not flight-certified

This repository should **not** be treated as a production-ready autonomous flight stack or directly deployed to a real aircraft.

Real deployment requires extensive hardware-in-the-loop and flight testing, independent safety systems, manual override, sensor validation, geofencing, failsafes, and aircraft-specific configuration.

---

# Future Direction

The current project is intentionally designed to grow.

## Multiple Colored Ground Targets

Replace the single visual target with several cubes:

```text
RED
BLUE
GREEN
YELLOW
```

The drone can search for them throughout its survey area and build a target list.

## Target World-Coordinate Estimation

Upgrade the vision pipeline to estimate:

```text
Target X
Target Y
Target Z
```

using calibrated camera geometry and drone pose.

The intended output:

```text
TARGET DETECTED

Color: RED

Estimated World Position:
X = 12.4 m
Y = 4.2 m
Z = 0.5 m
```

## General YOLO Detection

Move from a controlled color target to general object detection:

```text
person
car
backpack
bottle
chair
...
```

## RGB + Thermal

A future hardware architecture can use:

```text
        RGB Camera
             |
             |
        +----+----+
        |         |
        | ARM SBC |
        |         |
        | ROS 2   |
        | OpenCV  |
        | YOLO    |
        | Fusion  |
        +----+----+
             |
        Thermal Camera
             |
             v
            PX4
```

The exact Orange Pi-class board, camera interfaces, thermal sensor, and power architecture should be selected and validated against the real hardware.

## Dynamic Exploration

Future navigation can evolve from:

```text
Fixed Waypoints
```

to:

```text
Unknown Environment
        ↓
Mapping
        ↓
Obstacle Map
        ↓
Exploration Planner
        ↓
Next Best Viewpoint
        ↓
Navigation
```

## Onboard Compute

The current heavy perception work is performed on the development machine.

A future version can move perception onto an onboard ARM SBC.

---

# Development Philosophy

This project is intentionally a **baseline**, not a locked product.

```text
Build
  ↓
Test
  ↓
Break
  ↓
Measure
  ↓
Fix
  ↓
Improve
  ↓
Build again
```

You do not have to preserve the current architecture.

Try:

```text
different LiDAR arrangement
different camera
thermal sensing
different flight controller
different world
different planner
different detector
SLAM
mapping
path planning
target tracking
multi-drone coordination
```

Make the project behave the way **you** think an autonomous robot should behave.

> **Take it apart. Rebuild it. Improve it. Make it yours.**
>
> There is no single "correct" drone here. The fun is in seeing how far you can push the baseline.

---

# Contributing / Experimenting

Create your own branch:

```bash
git checkout -b feature/my-drone-change
```

Make changes:

```bash
git add .
git commit -m "Add my drone change"
```

Push:

```bash
git push -u origin feature/my-drone-change
```

Keep experimental changes separate from the known-good baseline whenever possible.

---

# Useful Diagnostics

## Gazebo models

```bash
gz model --list
```

## Gazebo sensors

```bash
gz topic -l | grep -E "lidar|camera"
```

## PX4

```bash
pgrep -af px4
```

## Gazebo process

```bash
pgrep -af 'gz sim'
```

## ROS nodes

```bash
ros2 node list
```

## Relevant ROS topics

```bash
ros2 topic list | grep -E 'lidar|camera|obstacle'
```

## PX4 odometry

```bash
ros2 topic echo /fmu/out/vehicle_odometry --once
```

---

# Clean WSL Reset

If PX4 or Gazebo becomes stuck:

From Windows PowerShell:

```powershell
wsl --shutdown
```

Then:

```powershell
wsl
```

Do not run `wsl --shutdown` from inside WSL.

For a partial cleanup inside WSL:

```bash
pkill -f '/build/px4_sitl_default/bin/px4'
pkill -f 'gz sim'
pkill -f parameter_bridge
pkill -f live_yolo_detector
pkill -f red_target_detector
```

Then verify with `pgrep`.

---

# License / Third-Party Code

Before public release, add a project license of your choice.

When using or redistributing upstream PX4, ROS 2, Gazebo assets, datasets, model files, or third-party code, keep their original license and attribution requirements.

---

# Final Status

The current repository is a **working autonomous-drone simulation baseline**.

It already demonstrates the important integration loop:

```text
PX4
 ↓
Gazebo
 ↓
LiDAR + Camera
 ↓
ROS 2
 ↓
Perception
 ↓
Obstacle Avoidance + Target Detection
 ↓
Autonomous Mission
 ↓
Return + Land
```

The next version is up to you.

**Take the baseline, change it, break it, rebuild it, and have fun.**
