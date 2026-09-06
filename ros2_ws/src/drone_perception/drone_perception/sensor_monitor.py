import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, LaserScan


class SensorMonitor(Node):

    def __init__(self):
        super().__init__('sensor_monitor')

        self.camera_count = 0
        self.lidar_count = 0

        self.camera_sub = self.create_subscription(
            Image,
            '/world/default/model/x500_mono_cam_0/link/camera_link/sensor/camera/image',
            self.camera_callback,
            10
        )

        self.lidar_sub = self.create_subscription(
            LaserScan,
            '/x500_mono_cam_0/lidar/scan',
            self.lidar_callback,
            10
        )

        self.timer = self.create_timer(5.0, self.print_status)

        self.get_logger().info('Sensor Monitor started.')

    def camera_callback(self, msg):
        self.camera_count += 1

    def lidar_callback(self, msg):
        self.lidar_count += 1

    def print_status(self):
        self.get_logger().info(
            f'Camera frames: {self.camera_count} | '
            f'LiDAR scans: {self.lidar_count}'
        )

        self.camera_count = 0
        self.lidar_count = 0


def main(args=None):
    rclpy.init(args=args)

    node = SensorMonitor()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
