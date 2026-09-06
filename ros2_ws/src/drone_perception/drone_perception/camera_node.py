import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraNode(Node):

    def __init__(self):
        super().__init__('camera_node')

        self.subscription = self.create_subscription(
            Image,
            '/world/default/model/x500_mono_cam_0/link/camera_link/sensor/camera/image',
            self.camera_callback,
            10
        )

        self.publisher = self.create_publisher(
            Image,
            '/drone/camera/processed',
            10
        )

        self.bridge = CvBridge()
        self.frame_count = 0

        self.get_logger().info('Camera perception node started.')
        self.get_logger().info('Waiting for camera frames...')

    def camera_callback(self, msg):

        self.frame_count += 1

        # ROS Image -> OpenCV
        frame = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding='bgr8'
        )

        # Convert to grayscale
        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        # Convert back to ROS Image
        processed_msg = self.bridge.cv2_to_imgmsg(
            gray,
            encoding='mono8'
        )

        processed_msg.header = msg.header

        self.publisher.publish(processed_msg)

        if self.frame_count % 10 == 0:
            height, width = gray.shape

            self.get_logger().info(
                f'Processed frame #{self.frame_count} '
                f'({width}x{height})'
            )


def main(args=None):

    rclpy.init(args=args)

    node = CameraNode()

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
