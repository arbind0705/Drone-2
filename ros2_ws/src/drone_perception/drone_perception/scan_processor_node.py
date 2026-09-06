import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanProcessorNode(Node):

    def __init__(self):
        super().__init__('scan_processor_node')

        self.subscription = self.create_subscription(
            LaserScan,
            '/world/default/model/x500_mono_cam_0/link/lidar_sensor_link/sensor/lidar/scan',
            self.scan_callback,
            10
        )

        self.publisher = self.create_publisher(
            LaserScan,
            '/drone/lidar_scan',
            10
        )

        self.frame_count = 0

        self.get_logger().info('360° LiDAR scan processor started.')
        self.get_logger().info('Waiting for LiDAR scans...')

    def scan_callback(self, msg):

        self.frame_count += 1

        # Create a copy of the incoming scan
        processed_scan = LaserScan()

        processed_scan.header = msg.header

        processed_scan.angle_min = msg.angle_min
        processed_scan.angle_max = msg.angle_max
        processed_scan.angle_increment = msg.angle_increment

        processed_scan.time_increment = msg.time_increment
        processed_scan.scan_time = msg.scan_time

        processed_scan.range_min = msg.range_min
        processed_scan.range_max = msg.range_max

        processed_ranges = []

        for distance in msg.ranges:

            # Replace invalid measurements with maximum range.
            if not math.isfinite(distance):
                processed_ranges.append(msg.range_max)

            # Protect against measurements outside sensor limits.
            elif distance < msg.range_min:
                processed_ranges.append(msg.range_max)

            elif distance > msg.range_max:
                processed_ranges.append(msg.range_max)

            else:
                processed_ranges.append(distance)

        processed_scan.ranges = processed_ranges

        # Preserve intensities if available
        processed_scan.intensities = list(msg.intensities)

        self.publisher.publish(processed_scan)

        # Print status once every second
        if self.frame_count % 20 == 0:

            valid_distances = [
                d for d in processed_ranges
                if math.isfinite(d)
            ]

            if valid_distances:
                closest = min(valid_distances)

                self.get_logger().info(
                    f'Scan #{self.frame_count} | '
                    f'Points: {len(processed_ranges)} | '
                    f'Closest obstacle: {closest:.2f} m'
                )


def main(args=None):

    rclpy.init(args=args)

    node = ScanProcessorNode()

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
