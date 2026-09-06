#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleOdometry,
)

from std_msgs.msg import Float32MultiArray


class OffboardControl(Node):

    def __init__(self):
        super().__init__('survey_mission_controller')

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # PX4 publishers
        self.mode_pub = self.create_publisher(
            OffboardControlMode,
            '/fmu/in/offboard_control_mode',
            qos
        )

        self.setpoint_pub = self.create_publisher(
            TrajectorySetpoint,
            '/fmu/in/trajectory_setpoint',
            qos
        )

        self.command_pub = self.create_publisher(
            VehicleCommand,
            '/fmu/in/vehicle_command',
            qos
        )

        # PX4 odometry
        self.odom_sub = self.create_subscription(
            VehicleOdometry,
            '/fmu/out/vehicle_odometry',
            self.odom_callback,
            qos
        )

        # LiDAR: [front, right, rear, left, down]
        self.lidar_sub = self.create_subscription(
            Float32MultiArray,
            '/drone/obstacle_distances',
            self.lidar_callback,
            10
        )

        # Vehicle position
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

        self.position_received = False
        self.lidar_received = False

        # Flight altitude
        self.survey_altitude = -10.0

        # Initialize targets
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = self.survey_altitude

        # =========================================================
        # SURVEY ROUTE
        #
        # HOME -> WP1 -> WP2 -> WP3 -> WP4 -> HOME
        #
        #              WP4 -------- WP3
        #               |             |
        #               |             |
        #              WP1 -------- WP2
        #               |
        #              HOME
        #
        # =========================================================

        self.waypoints = [
            (5.0, 0.0, self.survey_altitude),     # WP1
            (20.0, 0.0, self.survey_altitude),    # WP2
            (20.0, 15.0, self.survey_altitude),   # WP3
            (5.0, 15.0, self.survey_altitude),    # WP4
            (0.0, 0.0, self.survey_altitude),    # WP5 / HOME
        ]

        self.current_waypoint = 0
        self.waypoint_tolerance = 0.6

        # =========================================================
        # OBSTACLE AVOIDANCE
        # =========================================================

        self.safe_distance = 4.5
        self.bypass_distance = 3.0
        self.clear_distance = 6.5

        self.bypass_direction = 0
        self.avoid_waypoint = None

        # =========================================================
        # SENSOR VALUES
        # =========================================================

        self.front = 100.0
        self.right = 100.0
        self.rear = 100.0
        self.left = 100.0
        self.down = 100.0

        # =========================================================
        # MISSION STATE
        # =========================================================

        self.state = 'TAKEOFF'
        self.counter = 0

        self.timer = self.create_timer(
            0.1,
            self.timer_callback
        )

        self.get_logger().info(
            'Survey mission controller started'
        )

        self.get_logger().info(
            f'{len(self.waypoints)} survey waypoints loaded'
        )

        self.get_logger().info(
            f'Survey altitude: {abs(self.survey_altitude):.1f} m'
        )

    # =============================================================
    # CALLBACKS
    # =============================================================

    def odom_callback(self, msg):
        self.x = msg.position[0]
        self.y = msg.position[1]
        self.z = msg.position[2]

        self.position_received = True

    def lidar_callback(self, msg):
        if len(msg.data) < 5:
            return

        self.front = float(msg.data[0])
        self.right = float(msg.data[1])
        self.rear = float(msg.data[2])
        self.left = float(msg.data[3])
        self.down = float(msg.data[4])

        self.lidar_received = True

    # =============================================================
    # OFFBOARD HEARTBEAT
    # =============================================================

    def publish_mode(self):
        msg = OffboardControlMode()

        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False

        msg.timestamp = self.now()

        self.mode_pub.publish(msg)

    # =============================================================
    # POSITION SETPOINT
    # =============================================================

    def publish_setpoint(self):
        msg = TrajectorySetpoint()

        msg.position = [
            float(self.target_x),
            float(self.target_y),
            float(self.target_z)
        ]

        msg.yaw = 1.57079
        msg.timestamp = self.now()

        self.setpoint_pub.publish(msg)

    # =============================================================
    # VEHICLE COMMAND
    # =============================================================

    def send_command(
        self,
        command,
        param1=0.0,
        param2=0.0
    ):
        msg = VehicleCommand()

        msg.command = command
        msg.param1 = param1
        msg.param2 = param2

        msg.target_system = 1
        msg.target_component = 1

        msg.source_system = 1
        msg.source_component = 1

        msg.from_external = True
        msg.timestamp = self.now()

        self.command_pub.publish(msg)

    # =============================================================
    # SET WAYPOINT
    # =============================================================

    def set_current_waypoint(self):
        if self.current_waypoint >= len(self.waypoints):
            return

        self.target_x = self.waypoints[
            self.current_waypoint
        ][0]

        self.target_y = self.waypoints[
            self.current_waypoint
        ][1]

        self.target_z = self.waypoints[
            self.current_waypoint
        ][2]

    # =============================================================
    # WAYPOINT DISTANCE
    # =============================================================

    def waypoint_distance(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dz = self.target_z - self.z

        return math.sqrt(
            dx * dx +
            dy * dy +
            dz * dz
        )

    def waypoint_reached(self):
        return (
            self.waypoint_distance()
            < self.waypoint_tolerance
        )

    # =============================================================
    # MISSION STATE MACHINE
    # =============================================================

    def update_mission(self):

        # =========================================================
        # TAKEOFF
        # =========================================================

        if self.state == 'TAKEOFF':

            self.target_x = 0.0
            self.target_y = 0.0
            self.target_z = self.survey_altitude

            if (
                self.position_received
                and abs(
                    self.z -
                    self.survey_altitude
                ) < 0.5
            ):
                self.state = 'SURVEY'
                self.current_waypoint = 0

                self.set_current_waypoint()

                self.get_logger().info(
                    'Takeoff complete -> SURVEY'
                )

                self.get_logger().info(
                    f'Going to WP1: '
                    f'({self.target_x:.1f}, '
                    f'{self.target_y:.1f}, '
                    f'{self.target_z:.1f})'
                )

            return

        # =========================================================
        # SURVEY
        # =========================================================

        if self.state == 'SURVEY':

            # Obstacle detection
            if (
                self.lidar_received
                and self.front < self.safe_distance
            ):

                self.get_logger().warn(
                    f'OBSTACLE DETECTED! '
                    f'Front={self.front:.2f}m '
                    f'Right={self.right:.2f}m '
                    f'Left={self.left:.2f}m'
                )

                self.avoid_waypoint = (
                    self.current_waypoint
                )

                # Select side with more free space
                if self.left > self.right:

                    self.bypass_direction = -1

                    self.get_logger().info(
                        'Choosing LEFT bypass'
                    )

                else:

                    self.bypass_direction = 1

                    self.get_logger().info(
                        'Choosing RIGHT bypass'
                    )

                self.state = 'AVOID'

                return

            # Normal waypoint navigation
            self.set_current_waypoint()

            if self.waypoint_reached():

                self.get_logger().info(
                    f'WP{self.current_waypoint + 1} reached'
                )

                self.current_waypoint += 1

                # All waypoints complete
                if (
                    self.current_waypoint
                    >= len(self.waypoints)
                ):

                    self.state = 'LAND'

                    self.target_x = 0.0
                    self.target_y = 0.0
                    self.target_z = 0.0

                    self.get_logger().info(
                        'Survey complete -> '
                        'RETURN HOME / LAND'
                    )

                else:

                    self.set_current_waypoint()

                    self.get_logger().info(
                        f'Going to WP'
                        f'{self.current_waypoint + 1}: '
                        f'({self.target_x:.1f}, '
                        f'{self.target_y:.1f}, '
                        f'{self.target_z:.1f})'
                    )

            return

        # =========================================================
        # OBSTACLE AVOIDANCE
        # =========================================================

        if self.state == 'AVOID':

            if self.avoid_waypoint is not None:

                original_x = self.waypoints[
                    self.avoid_waypoint
                ][0]

                original_y = self.waypoints[
                    self.avoid_waypoint
                ][1]

                original_z = self.waypoints[
                    self.avoid_waypoint
                ][2]

            else:

                original_x = self.target_x
                original_y = self.target_y
                original_z = self.target_z

            # Move sideways first
            self.target_x = self.x

            self.target_y = (
                self.y +
                self.bypass_direction *
                self.bypass_distance
            )

            self.target_z = original_z

            # Once clear, rejoin original path
            if self.front > self.clear_distance:

                self.state = 'REJOIN'

                self.target_x = original_x
                self.target_y = original_y
                self.target_z = original_z

                self.get_logger().info(
                    'Obstacle clear -> '
                    'REJOIN SURVEY PATH'
                )

            return

        # =========================================================
        # REJOIN
        # =========================================================

        if self.state == 'REJOIN':

            self.set_current_waypoint()

            if self.waypoint_reached():

                self.get_logger().info(
                    f'Rejoined survey path at '
                    f'WP{self.current_waypoint + 1}'
                )

                self.state = 'SURVEY'

            return

        # =========================================================
        # LAND
        # =========================================================

        if self.state == 'LAND':

            self.target_x = 0.0
            self.target_y = 0.0
            self.target_z = 0.0

            if (
                self.position_received
                and abs(self.z) < 0.3
            ):

                self.send_command(
                    VehicleCommand
                    .VEHICLE_CMD_COMPONENT_ARM_DISARM,
                    0.0
                )

                self.get_logger().info(
                    'Landing complete -> DISARM'
                )

                self.state = 'DONE'

            return

        # =========================================================
        # DONE
        # =========================================================

        if self.state == 'DONE':

            self.target_x = 0.0
            self.target_y = 0.0
            self.target_z = 0.0

            return

    # =============================================================
    # TIMER
    # =============================================================

    def timer_callback(self):

        self.publish_mode()

        if self.position_received:
            self.update_mission()

        self.publish_setpoint()

        # Enter Offboard and arm
        if self.counter == 10:

            self.send_command(
                VehicleCommand
                .VEHICLE_CMD_DO_SET_MODE,
                1.0,
                6.0
            )

            self.get_logger().info(
                'Switching to Offboard mode'
            )

            self.send_command(
                VehicleCommand
                .VEHICLE_CMD_COMPONENT_ARM_DISARM,
                1.0
            )

            self.get_logger().info(
                'Arm command sent'
            )

        self.counter += 1

        # Status every second
        if self.counter % 10 == 0:

            self.get_logger().info(
                f'State={self.state} '
                f'WP={self.current_waypoint + 1}/'
                f'{len(self.waypoints)} '
                f'Pos=('
                f'{self.x:.2f}, '
                f'{self.y:.2f}, '
                f'{self.z:.2f}) '
                f'Target=('
                f'{self.target_x:.2f}, '
                f'{self.target_y:.2f}, '
                f'{self.target_z:.2f}) '
                f'LiDAR F={self.front:.2f} '
                f'R={self.right:.2f} '
                f'L={self.left:.2f}'
            )

    # =============================================================
    # TIMESTAMP
    # =============================================================

    def now(self):
        return int(
            self.get_clock().now().nanoseconds / 1000
        )


# ================================================================
# MAIN
# ================================================================

def main(args=None):

    rclpy.init(args=args)

    node = OffboardControl()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
