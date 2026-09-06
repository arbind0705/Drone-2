# PX4 + ROS 2 + Gazebo Drone Demo — Current Working Setup

A practical handoff for reproducing the current working prototype:

- PX4 SITL + Gazebo Harmonic/Gazebo Sim
- Custom `x500_sensor_demo` model
- Five LiDAR sensors
- ROS 2 Humble
- LiDAR preprocessing + obstacle avoidance
- Offboard autonomous survey mission
- Gazebo RGB camera bridged into ROS 2
- OpenCV red-target detection with drone X/Y/Z reporting
- YOLO11n installed and independently tested on CPU

This document describes the **current known-good configuration**, not a theoretical redesign.

---

## 1. Current architecture

```text
                         PX4 SITL
                            │
                            │ Vehicle Odometry / Commands
                            ▼
                    ROS 2 Offboard Controller
                            │
                            │ Position Setpoints
                            ▼
                          PX4
                            │
                            ▼
                         Gazebo
                    ┌───────┴────────┐
                    │                │
                  LiDAR           Camera
                    │                │
                    ▼                ▼
              Gazebo Topics    Gazebo Image Topic
                    │                │
                    ▼                ▼
             ros_gz_bridge     ros_gz_bridge
                    │                │
                    ▼                ▼
          /drone/obstacle_*  /drone/camera/image_raw
                    │                │
                    ▼                ▼
             lidar_node      red_target_detector
                    │                │
                    └───────┬────────┘
                            ▼
                      Mission Demo
```

### What each part currently does

**PX4**
- Runs the simulated multicopter.
- Receives offboard position setpoints.
- Performs the actual flight control.

**Gazebo**
- Simulates the world, drone, LiDARs, camera, and obstacle/target models.

**`lidar_node.py`**
- Subscribes to five LaserScan topics.
- Processes each scan using a ±45° sector for horizontal LiDARs.
- Publishes `[front, right, rear, left, down]` to `/drone/obstacle_distances` at 10 Hz.

**`position_offboard_control.py`**
- Takes off to approximately 10 m.
- Flies the five survey waypoints.
- Uses the processed LiDAR distances for obstacle detection/bypass.
- Rejoins the route.
- Returns home and lands.

**Camera**
- Gazebo camera resolution: 640×480.
- ROS encoding: `rgb8`.
- Step: 1920 bytes.
- Raw ROS topic: `/drone/camera/image_raw`.

**`red_target_detector.py`**
- Converts the ROS image directly using NumPy; it intentionally does **not** use `cv_bridge`.
- Detects the red target using HSV color segmentation.
- Reads PX4 vehicle odometry.
- Reports target pixel location and the drone's X/Y/Z position.

**YOLO11n**
- Installed in `~/yolo_env`.
- CPU-only PyTorch is used because the CUDA-enabled PyTorch build caused hangs and the exposed NVIDIA driver was incompatible with that build.
- YOLO11n was independently tested successfully on `bus.jpg` and detected a bus and several people.
- The current reliable flight demo uses the deterministic red-target detector rather than making flight behavior depend on YOLO.

---

# 2. Required directories

## PX4

```bash
~/PX4-Autopilot
```

## ROS 2 perception workspace

```bash
~/ros2_ws
```

Package:

```bash
~/ros2_ws/src/drone_perception
```

## PX4 offboard workspace

```bash
~/px4_ros2_ws
```

Package:

```bash
~/px4_ros2_ws/src/ROS2-PX4_Drone_Teleoperation_Using_Joystick/px4_offboard
```

---

# 3. Important current PX4 parameters

The following were manually set successfully in the PX4 shell:

```text
MPC_XY_VEL_MAX = 3.0
MPC_ACC_HOR    = 1.5
```

Check them in PX4 with:

```text
param show MPC_XY_VEL_MAX
param show MPC_ACC_HOR
```

Expected:

```text
MPC_XY_VEL_MAX : 3.0000
MPC_ACC_HOR    : 1.5000
```

These settings made the survey flight more controlled than the previous faster configuration.

The offboard controller's yaw was also changed from:

```python
msg.yaw = 0.0
```

to:

```python
msg.yaw = 1.57079
```

So the current controller intentionally commands approximately 90° yaw.

---

# 4. Current survey route

The controller currently uses five survey waypoints:

```python
self.waypoints = [
    (5.0, 0.0, self.survey_altitude),
    (20.0, 0.0, self.survey_altitude),
    (20.0, 15.0, self.survey_altitude),
    (5.0, 15.0, self.survey_altitude),
    (0.0, 0.0, self.survey_altitude),
]
```

The configured survey altitude is:

```text
10.0 m
```

PX4 uses NED-style local coordinates in the odometry/setpoint path, so the flight output appears around:

```text
Z = -10 m
```

The route is:

```text
HOME (0,0)
   |
   | takeoff
   v
(5,0) ---------> (20,0)
                   |
                   |
                   v
                 (20,15)
                   |
                   |
                   v
                 (5,15)
                   |
                   |
                   v
                HOME (0,0)
                   |
                   v
                 LAND
```

---

# 5. Current Gazebo obstacle

File:

```text
~/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf
```

Current test obstacle:

```xml
<model name="test_obstacle">
  <static>true</static>
  <pose>12 0 10 0 0 0</pose>
  <link name="obstacle_link">
    <collision name="collision">
      <geometry>
        <box>
          <size>2 2 20</size>
        </box>
      </geometry>
    </collision>
    <visual name="visual">
      <geometry>
        <box>
          <size>2 2 20</size>
        </box>
      </geometry>
    </visual>
  </link>
</model>
```

This obstacle was successfully used to test LiDAR avoidance.

One successful flight produced:

```text
OBSTACLE DETECTED! Front=2.86m Right=2.10m Left=100.00m
Choosing LEFT bypass
...
Obstacle clear -> REJOIN SURVEY PATH
...
Rejoined survey path at WP5
```

That is the known proof that obstacle detection + bypass + route rejoin works.

---

# 6. Current red visual target

The same world file contains:

```xml
<model name="red_detection_target">
  <static>true</static>
  <pose>20 7.5 5 0 0 0</pose>
```

The target is a red box-like visual target currently used by the deterministic computer-vision detector.

Current target center:

```text
X = 20
Y = 7.5
Z = 5
```

It was successfully visible in the live camera and was detected during autonomous flight.

Important: this is currently a **red target/visual object**, not a pretrained YOLO class such as `person` or `car`.

---

# 7. ROS 2 environment

For normal ROS 2 terminals:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

For the PX4 offboard controller terminal:

```bash
source /opt/ros/humble/setup.bash
source ~/px4_ros2_ws/install/setup.bash
```

Do not use the YOLO virtual environment for PX4 builds.

---

# 8. Terminal layout

The clean working setup uses separate terminals.

```text
Terminal 1   MicroXRCEAgent
Terminal 2   PX4 + Gazebo
Terminal 3   LiDAR bridge
Terminal 4   Camera bridge
Terminal 5   LiDAR perception node
Terminal 6   Offboard survey controller
Terminal 7   Red target detector
```

YOLO environment is only needed when running YOLO-specific code/tests.

This is intentional. Keeping the processes separate made debugging much easier and prevents the camera/YOLO stack from destabilizing the known-good flight stack.

---

# 9. Start everything from a clean WSL session

If Gazebo or PX4 becomes stuck, clean the processes before restarting.

From **Windows PowerShell**:

```powershell
wsl --shutdown
```

Then:

```powershell
wsl
```

Do not run `wsl --shutdown` from inside WSL; it is a Windows command.

---

# 10. Terminal 1 — MicroXRCEAgent

Start:

```bash
MicroXRCEAgent udp4 -p 8888
```

Leave it running.

PX4 should later report something similar to:

```text
uxrce_dds_client synchronized with time offset ...
```

---

# 11. Terminal 2 — PX4 + Gazebo

Run:

```bash
cd ~/PX4-Autopilot

export MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA"

PX4_SYS_AUTOSTART=22000 \
PX4_SIM_MODEL=x500_sensor_demo \
./build/px4_sitl_default/bin/px4
```

Wait for:

```text
Gazebo world is ready
Spawning Gazebo model
Startup script returned successfully
pxh>
```

The world should contain:

```text
ground_plane
test_obstacle
red_detection_target
x500_sensor_demo_0
```

Check:

```bash
gz model --list
```

---

# 12. Verify Gazebo sensors before starting ROS nodes

Run:

```bash
gz topic -l | grep -E "lidar|camera"
```

Expected important topics:

```text
/world/default/model/x500_sensor_demo_0/link/lidar_front_link/sensor/lidar_front/scan
/world/default/model/x500_sensor_demo_0/link/lidar_right_link/sensor/lidar_right/scan
/world/default/model/x500_sensor_demo_0/link/lidar_rear_link/sensor/lidar_rear/scan
/world/default/model/x500_sensor_demo_0/link/lidar_left_link/sensor/lidar_left/scan
/world/default/model/x500_sensor_demo_0/link/lidar_down_link/sensor/lidar_down/scan
/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image
/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/camera_info
```

Check camera publisher:

```bash
gz topic -i -t /world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image
```

Expected type:

```text
gz.msgs.Image
```

Check front LiDAR publisher:

```bash
gz topic -i -t /world/default/model/x500_sensor_demo_0/link/lidar_front_link/sensor/lidar_front/scan
```

Expected type:

```text
gz.msgs.LaserScan
```

Do **not** use `gz topic -e` on the image topic; it dumps huge image messages and can make the terminal look frozen.

---

# 13. LiDAR bridge

Package:

```text
~/ros2_ws/src/drone_perception
```

Launch file:

```text
~/ros2_ws/src/drone_perception/launch/lidar_bridges.launch.py
```

Build when needed:

```bash
cd ~/ros2_ws
colcon build --symlink-install --packages-select drone_perception
```

Source:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

Start the five LiDAR bridges:

```bash
ros2 launch drone_perception lidar_bridges.launch.py
```

The launch file successfully created five Gazebo-to-ROS bridges for:

```text
front
right
rear
left
down
```

---

# 14. Verify LiDAR ROS topics

Run:

```bash
ros2 topic list | grep /drone/lidar
```

Expected:

```text
/drone/lidar_front
/drone/lidar_left
/drone/lidar_rear
/drone/lidar_right
/drone/lidar_down
```

Check front rate:

```bash
ros2 topic hz /drone/lidar_front
```

Known-good rate:

```text
~20 Hz
```

Check downward rate:

```bash
ros2 topic hz /drone/lidar_down
```

Known-good rate:

```text
~20 Hz
```

---

# 15. LiDAR processing node

Current file:

```text
~/ros2_ws/src/drone_perception/drone_perception/lidar_node.py
```

Build:

```bash
cd ~/ros2_ws
colcon build --symlink-install --packages-select drone_perception
```

Source:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

Start:

```bash
ros2 run drone_perception lidar_node
```

Expected startup:

```text
Five-LiDAR perception node started.
Horizontal LiDAR detection sector: +/-45 degrees.
```

Expected log format:

```text
FRONT: ... m | RIGHT: ... m | REAR: ... m | LEFT: ... m | DOWN: ... m
```

The node publishes:

```text
/drone/obstacle_distances
```

with five values in this order:

```text
[front, right, rear, left, down]
```

At 10 Hz.

Check it:

```bash
ros2 topic hz /drone/obstacle_distances
```

Known-good rate:

```text
10 Hz
```

Inspect data:

```bash
ros2 topic echo /drone/obstacle_distances --once
```

---

# 16. Current LiDAR preprocessing behavior

Horizontal LiDARs use only a central sector of:

```text
-45° to +45°
```

The old version used the minimum range across the whole 360° scan. That caused unrelated side/rear structures to affect the reported distance.

The current implementation intentionally restricts horizontal detection to the forward sector of each sensor.

Valid values must satisfy:

```text
finite(distance)
range_min <= distance <= range_max
```

No valid reading is represented internally as infinity and published as 100.0 m.

---

# 17. Verify processed obstacle data

Run:

```bash
ros2 topic echo /drone/obstacle_distances
```

A typical safe-area reading is something like:


```text
data:
- 10.6
- 10.9
- 11.2
- 10.9
- 0.17
```

The final value is the downward LiDAR distance.

---

# 18. Camera bridge

The current working camera bridge is separate from the five-LiDAR bridge launch.

Use a new terminal:

```bash
source /opt/ros/humble/setup.bash
```

Start:

```bash
ros2 run ros_gz_bridge parameter_bridge \
'/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
--ros-args \
-r /world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image:=/drone/camera/image_raw
```

Leave this terminal running.

---

# 19. Verify camera ROS topic

Source:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

Check:

```bash
ros2 topic info /drone/camera/image_raw
```

Known-good result:

```text
Type: sensor_msgs/msg/Image
Publisher count: 1
```

Check rate:

```bash
ros2 topic hz /drone/camera/image_raw
```

The current camera stream has been observed around roughly 5–10 Hz, depending on system load. The raw Gazebo camera itself is configured at 20 Hz, but the bridged/WSL stream can be slower.

Check encoding:

```bash
ros2 topic echo /drone/camera/image_raw --once --field encoding
```

Expected:

```text
rgb8
```

Check dimensions:

```bash
ros2 topic echo /drone/camera/image_raw --once --field height
ros2 topic echo /drone/camera/image_raw --once --field width
```

Expected:

```text
480
640
```

Check step:

```bash
ros2 topic echo /drone/camera/image_raw --once --field step
```

Expected:

```text
1920
```

---

# 20. Why the current red detector does not use cv_bridge

The normal ROS environment has:

```text
NumPy 1.26.4
```

because the installed ROS 2 Humble `cv_bridge` was compiled against NumPy 1.x.

The YOLO virtual environment has its own Python packages and uses NumPy 2.x.

Therefore the current red detector directly converts the ROS image buffer with NumPy instead of importing `cv_bridge`.

For the known camera encoding:

```text
rgb8
```

conversion is:

```python
frame_rgb = np.frombuffer(msg.data, dtype=np.uint8)
frame_rgb = frame_rgb.reshape((msg.height, msg.width, 3))
frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
```

This is intentional.

---

# 21. Camera viewer (optional)

A basic camera viewer can be run from the normal ROS Python environment with `cv_bridge` working against NumPy 1.26.4.

If a viewer file already exists:

```bash
python3 /tmp/camera_viewer.py
```

The camera window should show the Gazebo scene.

The red target was successfully visible in this live viewer before flight testing.

---

# 22. Red target detector — current reliable object-detection demo

File:

```text
~/red_target_detector.py
```

The detector:

1. subscribes to `/drone/camera/image_raw`
2. reads `/fmu/out/vehicle_odometry`
3. converts `rgb8` to an OpenCV frame
4. detects red pixels in HSV space
5. removes small noise
6. selects a sufficiently large/tall red contour
7. draws a bounding box
8. prints the target pixel center
9. prints the current drone X/Y/Z

Run it from the YOLO environment:

```bash
source ~/yolo_env/bin/activate
python ~/red_target_detector.py
```

Expected startup:

```text
[red_target_detector]: Red target detector started.
```

When the target is visible:

```text
RED TARGET DETECTED
Pixel center : (...)
Drone X      : ... m
Drone Y      : ... m
Drone Z      : ... m
Target area  : ... px
```

A successful autonomous-flight run produced detections such as:

```text
RED TARGET DETECTED
Pixel center : (636, 397)
Drone X      : 14.13 m
Drone Y      : 15.21 m
Drone Z      : -9.99 m

RED TARGET DETECTED
Pixel center : (485, 417)
Drone X      : 9.86 m
Drone Y      : 15.17 m
Drone Z      : -10.00 m

RED TARGET DETECTED
Pixel center : (138, 425)
Drone X      : 4.05 m
Drone Y      : 13.16 m
Drone Z      : -10.00 m
```

This proves camera detection and PX4 position reporting occurred while the drone was flying.

---

# 23. YOLO environment

Virtual environment:

```text
~/yolo_env
```

Activate:

```bash
source ~/yolo_env/bin/activate
```

Current important packages:

```text
ultralytics       8.4.142
torch             2.14.0+cpu
torchvision       0.29.0+cpu
numpy             2.2.6
opencv-python     5.0.0.93
```

The CPU-only PyTorch build is intentional.

The previous CUDA-enabled build was:

```text
torch 2.14.0+cu130
```

and it caused very slow/hanging initialization in the current WSL/NVIDIA driver configuration.

Current CPU PyTorch test:

```text
Torch imported!
Version: 2.14.0+cpu
CUDA: False
Import time: ~1 sec
Tensor test: successful
```

---

# 24. Verify YOLO installation

Activate:

```bash
source ~/yolo_env/bin/activate
```

Test import:

```bash
python -c "from ultralytics import YOLO; print('YOLO OK')"
```

Load model:

```bash
python - <<'PY'
from ultralytics import YOLO
model = YOLO("yolo11n.pt")
print("YOLO model loaded successfully")
PY
```

A standalone inference test succeeded:

```text
DETECTED: bus confidence=0.94
DETECTED: person confidence=0.89
DETECTED: person confidence=0.88
DETECTED: person confidence=0.86
DETECTED: person confidence=0.62
TEST COMPLETE
```

This verifies the YOLO installation itself.

---

# 25. Important YOLO limitation in the current demo

A plain Gazebo cube/wall is not automatically a YOLO `cube` class.

Therefore:

```text
YOLO11n + generic Gazebo cube = not guaranteed to detect it
```

For the current demo, use:

```text
OpenCV red-target detection
```

for the controlled target.

YOLO11n can later be used for general classes such as person/car/etc. without changing the PX4 flight controller.

---

# 26. Start the complete demonstration

Recommended sequence.

### Terminal 1

```bash
MicroXRCEAgent udp4 -p 8888
```

### Terminal 2

```bash
cd ~/PX4-Autopilot
export MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA"

PX4_SYS_AUTOSTART=22000 \
PX4_SIM_MODEL=x500_sensor_demo \
./build/px4_sitl_default/bin/px4
```

Wait for `pxh>` and Gazebo.

### Terminal 3 — LiDAR bridges

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch drone_perception lidar_bridges.launch.py
```

### Terminal 4 — Camera bridge

```bash
source /opt/ros/humble/setup.bash

ros2 run ros_gz_bridge parameter_bridge \
'/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
--ros-args \
-r /world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image:=/drone/camera/image_raw
```

### Terminal 5 — LiDAR perception

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run drone_perception lidar_node
```

### Terminal 6 — red target detector

```bash
source ~/yolo_env/bin/activate
python ~/red_target_detector.py
```

### Terminal 7 — autonomous flight

```bash
source /opt/ros/humble/setup.bash
source ~/px4_ros2_ws/install/setup.bash
ros2 run px4_offboard position_offboard_control.py
```

---

# 27. Expected flight behavior

The controller should print states similar to:

```text
State=TAKEOFF
Takeoff complete -> SURVEY
Going to WP1: (5.0, 0.0, -10.0)
WP1 reached
Going to WP2: (20.0, 0.0, -10.0)
WP2 reached
Going to WP3: (20.0, 15.0, -10.0)
WP3 reached
Going to WP4: (5.0, 15.0, -10.0)
WP4 reached
Going to WP5: (0.0, 0.0, -10.0)
WP5 reached
Survey complete -> RETURN HOME / LAND
Landing complete -> DISARM
```

If the LiDAR obstacle is encountered, the controller can enter:

```text
AVOID
```

then:

```text
REJOIN
```

and continue the route.

---

# 28. Expected vision behavior during flight

The red detector operates independently of the flight controller.

When the red target enters the camera view:

```text
RED TARGET DETECTED
Pixel center : (...)
Drone X      : ...
Drone Y      : ...
Drone Z      : ...
```

The drone does not automatically change course because of the red target.

Current architecture is deliberately:

```text
LiDAR -> obstacle avoidance / flight safety
Camera -> target detection / reporting
PX4 -> autonomous movement
```

This separation makes the prototype easier to demonstrate and debug.

---

# 29. Useful verification commands

## PX4 process

```bash
pgrep -af px4
```

## Gazebo process

```bash
pgrep -af 'gz sim'
```

## Bridges

```bash
pgrep -af parameter_bridge
```

## ROS nodes

```bash
ros2 node list
```

## Topics

```bash
ros2 topic list | grep -E 'lidar|camera|obstacle'
```

## LiDAR topic info

```bash
ros2 topic info /drone/lidar_front
ros2 topic info /drone/lidar_down
```

## Obstacle data

```bash
ros2 topic info /drone/obstacle_distances
ros2 topic echo /drone/obstacle_distances --once
```

## Camera data

```bash
ros2 topic info /drone/camera/image_raw
ros2 topic echo /drone/camera/image_raw --once --field encoding
ros2 topic echo /drone/camera/image_raw --once --field width
ros2 topic echo /drone/camera/image_raw --once --field height
```

## PX4 odometry

Because PX4 publishes VehicleOdometry with a QoS profile that can be incompatible with default reliable subscribers, sensor-data/BEST_EFFORT QoS should be used for custom ROS subscribers.

Check:

```bash
ros2 topic info -v /fmu/out/vehicle_odometry
```

Known working position source:

```text
/fmu/out/vehicle_odometry
```

---

# 30. Common problems and fixes

## Problem: launch file not found

If:

```text
file 'lidar_bridges.launch.py' was not found
```

check:

```bash
ls ~/ros2_ws/src/drone_perception/launch/
```

It should contain:

```text
lidar_bridges.launch.py
sensors.launch.py
```

Then rebuild cleanly:

```bash
cd ~/ros2_ws
rm -rf build/drone_perception
rm -rf install/drone_perception
rm -rf log
colcon build --symlink-install --packages-select drone_perception
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

---

## Problem: Gazebo process survives after PX4 stops

Check:

```bash
pgrep -af 'gz sim'
```

Then kill the reported PID:

```bash
kill <PID>
```

If necessary:

```bash
kill -9 <PID>
```

Then verify again.

If Gazebo behaves strangely, the cleanest full reset is from Windows PowerShell:

```powershell
wsl --shutdown
```

followed by:

```powershell
wsl
```

---

## Problem: Gazebo `gz_frame_id` warnings

Warnings such as:

```text
XML Element[gz_frame_id], child of element[sensor], not defined in SDF.
```

have repeatedly appeared with this model.

They did not prevent the world from loading or the sensors from publishing.

Do not treat these warnings as the primary failure unless a sensor actually stops publishing.

---

## Problem: camera topic exists but no frames seem to arrive

Check:

```bash
gz topic -i -t /world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image
```

You need:

```text
gz.msgs.Image
```

Then check the bridge:

```bash
ros2 topic info /drone/camera/image_raw
```

You need:

```text
Publisher count: 1
```

Then:

```bash
ros2 topic hz /drone/camera/image_raw
```

Do not use `gz topic -e` on the image stream as a normal diagnostic; it can dump large image messages and make the terminal appear frozen.

---

## Problem: `cv_bridge` throws `_ARRAY_API not found`

Cause:

The system ROS `cv_bridge` was compiled against NumPy 1.x, but the Python environment had NumPy 2.x.

Known working normal ROS environment:

```text
NumPy 1.26.4
cv_bridge OK
```

Fix the normal environment with:

```bash
python3 -m pip install --user --force-reinstall "numpy==1.26.4"
```

Do not install the YOLO Python packages directly into the normal ROS environment again.

The current detector avoids `cv_bridge` anyway.

---

## Problem: YOLO/PyTorch hangs

The old problem was the CUDA build:

```text
torch 2.14.0+cu130
```

combined with the WSL/NVIDIA driver exposed to the environment.

The current working YOLO environment uses:

```text
torch 2.14.0+cpu
torchvision 0.29.0+cpu
```

Verify:

```bash
source ~/yolo_env/bin/activate
python -c "import torch; print(torch.__version__)"
```

Expected:

```text
2.14.0+cpu
```

Then:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Expected:

```text
False
```

This is intentional for the current demo.

---

## Problem: YOLO says 0 detections on the artificial obstacle

That is expected.

The tall rectangular test obstacle is not a guaranteed YOLO class.

Use the controlled red target and `red_target_detector.py` for the reproducible visual demo.

---

## Problem: odometry subscriber receives no messages

PX4 VehicleOdometry uses QoS that may not match the default reliable subscriber.

Use:

```python
from rclpy.qos import qos_profile_sensor_data
```

and:

```python
self.create_subscription(
    VehicleOdometry,
    '/fmu/out/vehicle_odometry',
    callback,
    qos_profile_sensor_data
)
```

---

# 31. Known-good result checklist

Before calling the demo ready, verify all of the following.

```text
[ ] MicroXRCEAgent running
[ ] PX4 starts normally
[ ] Gazebo world loads
[ ] x500_sensor_demo_0 exists
[ ] test_obstacle exists
[ ] red_detection_target exists
[ ] five LiDAR Gazebo topics exist
[ ] camera Gazebo topic exists
[ ] LiDAR bridge running
[ ] /drone/lidar_* topics exist
[ ] /drone/obstacle_distances publishes at ~10 Hz
[ ] camera bridge running
[ ] /drone/camera/image_raw has Publisher count 1
[ ] camera stream is receiving frames
[ ] red target visible in camera
[ ] red_target_detector starts
[ ] red target detection reports X/Y/Z
[ ] offboard controller starts
[ ] drone takes off
[ ] survey waypoints are reached
[ ] obstacle can trigger AVOID/REJOIN
[ ] drone returns home
[ ] drone lands/disarms
```

---

# 32. Current functional status

## Completed and demonstrated

```text
PX4 SITL + Gazebo                         ✅
Custom x500 sensor model                 ✅
Five-LiDAR simulation                    ✅
ROS 2 LiDAR bridging                     ✅
LiDAR preprocessing                      ✅
10 Hz obstacle-distance output           ✅
Autonomous 5-waypoint survey             ✅
Obstacle detection                       ✅
Obstacle bypass                          ✅
Survey-path rejoin                       ✅
Return-to-home                           ✅
Automatic landing/disarm                 ✅
Gazebo RGB camera                        ✅
ROS 2 camera bridge                      ✅
640×480 RGB image                        ✅
Live camera viewer                       ✅
Red target visual detection              ✅
Detection during autonomous flight       ✅
Drone X/Y/Z reporting with detection    ✅
YOLO11n installation                     ✅
YOLO11n standalone inference             ✅
CPU-only PyTorch                         ✅
```

## Optional future improvements

```text
Use realistic cube meshes instead of red box target
Multiple colored targets
Estimate exact target world coordinates from camera geometry
YOLO live object classes (person/car/etc.)
RGB + thermal camera fusion
GPU-accelerated YOLO after driver/toolchain cleanup
Dynamic exploration instead of predefined survey waypoints
Mapping / SLAM
Object tracking over multiple frames
Persistent target database
```

---

# 33. Recommended final demo

For the most reliable presentation, use the current architecture without adding risky dependencies:

```text
                 AUTONOMOUS DRONE SURVEY
                            │
              ┌─────────────┴─────────────┐
              │                           │
             PX4                        Camera
              │                           │
        Survey mission              Red target detector
              │                           │
          5 waypoints                 Target found
              │                           │
              ▼                           ▼
            LiDAR                 Drone X / Y / Z
              │                           │
        obstacle found                    │
              │                           │
          AVOID / REJOIN                 │
              │                           │
              └─────────────┬─────────────┘
                            ▼
                     Continue survey
                            │
                            ▼
                       Return + Land
```

The presentation story is:

> The drone autonomously surveys a predefined area, uses five LiDAR sensors for obstacle awareness and bypass, uses its onboard-style camera pipeline to identify a visual target, records the drone position at the time of detection, then continues the mission and returns home.

---

# 34. Do not change the working baseline unnecessarily

The following files are part of the current known-good baseline:

```text
~/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf
~/PX4-Autopilot/Tools/simulation/gz/models/x500_sensor_demo/model.sdf
~/ros2_ws/src/drone_perception/drone_perception/lidar_node.py
~/ros2_ws/src/drone_perception/launch/lidar_bridges.launch.py
~/px4_ros2_ws/src/ROS2-PX4_Drone_Teleoperation_Using_Joystick/px4_offboard/px4_offboard/position_offboard_control.py
~/red_target_detector.py
```

Before making major changes, make a backup:

```bash
mkdir -p ~/drone_demo_backup

cp ~/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf \
   ~/drone_demo_backup/default.sdf

cp ~/PX4-Autopilot/Tools/simulation/gz/models/x500_sensor_demo/model.sdf \
   ~/drone_demo_backup/model.sdf

cp ~/ros2_ws/src/drone_perception/drone_perception/lidar_node.py \
   ~/drone_demo_backup/lidar_node.py

cp ~/px4_ros2_ws/src/ROS2-PX4_Drone_Teleoperation_Using_Joystick/px4_offboard/px4_offboard/position_offboard_control.py \
   ~/drone_demo_backup/position_offboard_control.py

cp ~/red_target_detector.py \
   ~/drone_demo_backup/red_target_detector.py
```

---

# 35. One-command environment reminders

### ROS 2 perception shell

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

### PX4 offboard shell

```bash
source /opt/ros/humble/setup.bash
source ~/px4_ros2_ws/install/setup.bash
```

### YOLO shell

```bash
source ~/yolo_env/bin/activate
```

### Full PX4 launch

```bash
cd ~/PX4-Autopilot
export MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA"
PX4_SYS_AUTOSTART=22000 PX4_SIM_MODEL=x500_sensor_demo ./build/px4_sitl_default/bin/px4
```

### Five-LiDAR bridge

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch drone_perception lidar_bridges.launch.py
```

### LiDAR perception

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run drone_perception lidar_node
```

### Camera bridge

```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
'/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
--ros-args \
-r /world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image:=/drone/camera/image_raw
```

### Red target detector

```bash
source ~/yolo_env/bin/activate
python ~/red_target_detector.py
```

### Autonomous mission

```bash
source /opt/ros/humble/setup.bash
source ~/px4_ros2_ws/install/setup.bash
ros2 run px4_offboard position_offboard_control.py
```

---

# 36. Final note

The current prototype is already functionally demonstrated. The most important rule for reproducing it is:

**Start from a clean PX4/Gazebo runtime, verify sensors, then add ROS bridges/nodes one layer at a time.**

Do not mix the ROS NumPy/cv_bridge environment with the YOLO virtual environment unnecessarily, and do not replace the CPU-only PyTorch build with the old CUDA 13 build unless the WSL NVIDIA driver/toolchain is deliberately updated.
