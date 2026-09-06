import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32MultiArray


class LidarNode(Node):

    def __init__(self):
        super().__init__('lidar_node')

        # ---------------------------------------------------------
        # Processed distances
        #
        # [front, right, rear, left, down]
        # ---------------------------------------------------------

        self.distances = {
            'front': float('inf'),
            'right': float('inf'),
            'rear': float('inf'),
            'left': float('inf'),
            'down': float('inf'),
        }

        # ---------------------------------------------------------
        # Main 360-degree horizontal scanner
        # ---------------------------------------------------------

        self.front_sub = self.create_subscription(
            LaserScan,
            '/drone/lidar_front',
            self.front_scan_callback,
            10
        )

        # ---------------------------------------------------------
        # Downward LiDAR
        # ---------------------------------------------------------

        self.down_sub = self.create_subscription(
            LaserScan,
            '/drone/lidar_down',
            self.down_scan_callback,
            10
        )

        # ---------------------------------------------------------
        # Output
        # ---------------------------------------------------------

        self.publisher = self.create_publisher(
            Float32MultiArray,
            '/drone/obstacle_distances',
            10
        )

        # Publish processed data at 10 Hz.
        self.timer = self.create_timer(
            0.1,
            self.publish_distances
        )

        self.log_counter = 0

        self.get_logger().info(
            'LiDAR perception node started.'
        )

        self.get_logger().info(
            'Using front LiDAR as 360-degree obstacle scanner.'
        )

        self.get_logger().info(
            'Sectors: Front +/-45 deg, '
            'Right -135 to -45 deg, '
            'Rear +/-45 deg around 180 deg, '
            'Left +45 to +135 deg.'
        )

    # =============================================================
    # ANGLE NORMALIZATION
    # =============================================================

    def normalize_angle(self, angle_deg):

        while angle_deg > 180.0:
            angle_deg -= 360.0

        while angle_deg < -180.0:
            angle_deg += 360.0

        return angle_deg

    # =============================================================
    # VALID RANGE
    # =============================================================

    def valid_range(self, distance, msg):

        return (
            math.isfinite(distance)
            and distance > 0.0
            and msg.range_min <= distance <= msg.range_max
        )

    # =============================================================
    # FRONT 360-DEGREE SCAN
    # =============================================================

    def front_scan_callback(self, msg):

        front_values = []
        right_values = []
        rear_values = []
        left_values = []

        for i, distance in enumerate(msg.ranges):

            if not self.valid_range(distance, msg):
                continue

            angle_rad = (
                msg.angle_min +
                i * msg.angle_increment
            )

            angle_deg = self.normalize_angle(
                math.degrees(angle_rad)
            )

            # -----------------------------------------------------
            # FRONT
            # -45 deg to +45 deg
            # -----------------------------------------------------

            if -45.0 <= angle_deg <= 45.0:

                front_values.append(distance)

            # -----------------------------------------------------
            # RIGHT
            # -135 deg to -45 deg
            # -----------------------------------------------------

            elif -135.0 <= angle_deg < -45.0:

                right_values.append(distance)

            # -----------------------------------------------------
            # LEFT
            # +45 deg to +135 deg
            # -----------------------------------------------------

            elif 45.0 < angle_deg <= 135.0:

                left_values.append(distance)

            # -----------------------------------------------------
            # REAR
            # Around +/-180 deg
            # -----------------------------------------------------

            else:

                rear_values.append(distance)

        # ---------------------------------------------------------
        # Store sector minima
        # ---------------------------------------------------------

        self.distances['front'] = (
            min(front_values)
            if front_values
            else float('inf')
        )

        self.distances['right'] = (
            min(right_values)
            if right_values
            else float('inf')
        )

        self.distances['rear'] = (
            min(rear_values)
            if rear_values
            else float('inf')
        )

        self.distances['left'] = (
            min(left_values)
            if left_values
            else float('inf')
        )

    # =============================================================
    # DOWNWARD SCAN
    # =============================================================

    def down_scan_callback(self, msg):

        values = []

        for distance in msg.ranges:

            if self.valid_range(distance, msg):

                values.append(distance)

        if values:

            self.distances['down'] = min(values)

        else:

            self.distances['down'] = float('inf')

    # =============================================================
    # PUBLISH
    # =============================================================

    def publish_distances(self):

        front = self.distances['front']
        right = self.distances['right']
        rear = self.distances['rear']
        left = self.distances['left']
        down = self.distances['down']

        output = [
            front,
            right,
            rear,
            left,
            down
        ]

        # Replace infinity with 100 m.
        output = [
            100.0 if math.isinf(distance) else distance
            for distance in output
        ]

        msg = Float32MultiArray()

        msg.data = output

        self.publisher.publish(msg)

        # ---------------------------------------------------------
        # Status logging
        # ---------------------------------------------------------

        self.log_counter += 1

        if self.log_counter >= 10:

            self.log_counter = 0

            self.get_logger().info(
                f'FRONT: {front:.2f} m | '
                f'RIGHT: {right:.2f} m | '
                f'REAR: {rear:.2f} m | '
                f'LEFT: {left:.2f} m | '
                f'DOWN: {down:.2f} m'
            )


# ================================================================
# MAIN
# ================================================================

def main(args=None):

    rclpy.init(args=args)

    node = LidarNode()

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
