#!/usr/bin/env python3

import cv2
import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from px4_msgs.msg import VehicleOdometry


class RedTargetDetector(Node):

    def __init__(self):
        super().__init__('red_target_detector')

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

        self.detected = False
        self.last_detected = False
        self.frame_count = 0

        self.camera_sub = self.create_subscription(
            Image,
            '/drone/camera/image_raw',
            self.camera_callback,
            qos_profile_sensor_data
        )

        self.odom_sub = self.create_subscription(
            VehicleOdometry,
            '/fmu/out/vehicle_odometry',
            self.odom_callback,
            qos_profile_sensor_data
        )

        self.get_logger().info(
            'Red target detector started.'
        )

    def odom_callback(self, msg):
        self.x = float(msg.position[0])
        self.y = float(msg.position[1])
        self.z = float(msg.position[2])

    def camera_callback(self, msg):

        try:

            if msg.encoding != 'rgb8':
                self.get_logger().error(
                    f'Unsupported encoding: {msg.encoding}'
                )
                return

            # ROS Image -> NumPy
            frame_rgb = np.frombuffer(
                msg.data,
                dtype=np.uint8
            ).reshape(
                (msg.height, msg.width, 3)
            )

            # RGB -> BGR for OpenCV
            frame = cv2.cvtColor(
                frame_rgb,
                cv2.COLOR_RGB2BGR
            )

            self.frame_count += 1

            # -------------------------------------------------
            # RED COLOR SEGMENTATION
            # -------------------------------------------------

            hsv = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2HSV
            )

            # Red wraps around the HSV hue boundary,
            # so use two ranges.
            lower_red_1 = np.array(
                [0, 100, 80],
                dtype=np.uint8
            )

            upper_red_1 = np.array(
                [10, 255, 255],
                dtype=np.uint8
            )

            lower_red_2 = np.array(
                [170, 100, 80],
                dtype=np.uint8
            )

            upper_red_2 = np.array(
                [180, 255, 255],
                dtype=np.uint8
            )

            mask1 = cv2.inRange(
                hsv,
                lower_red_1,
                upper_red_1
            )

            mask2 = cv2.inRange(
                hsv,
                lower_red_2,
                upper_red_2
            )

            mask = cv2.bitwise_or(
                mask1,
                mask2
            )

            # Remove tiny noise.
            kernel = np.ones(
                (5, 5),
                np.uint8
            )

            mask = cv2.morphologyEx(
                mask,
                cv2.MORPH_OPEN,
                kernel
            )

            mask = cv2.morphologyEx(
                mask,
                cv2.MORPH_CLOSE,
                kernel
            )

            # -------------------------------------------------
            # FIND RED TARGET
            # -------------------------------------------------

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            best_contour = None
            best_area = 0.0

            for contour in contours:

                area = cv2.contourArea(contour)

                if area < 200:
                    continue

                x, y, w, h = cv2.boundingRect(
                    contour
                )

                # Target should be reasonably tall.
                aspect_ratio = h / max(w, 1)

                if aspect_ratio < 1.2:
                    continue

                if area > best_area:

                    best_area = area
                    best_contour = contour

            self.detected = best_contour is not None

            # -------------------------------------------------
            # DRAW DETECTION
            # -------------------------------------------------

            if best_contour is not None:

                x, y, w, h = cv2.boundingRect(
                    best_contour
                )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    3
                )

                center_x = x + w // 2
                center_y = y + h // 2

                cv2.circle(
                    frame,
                    (center_x, center_y),
                    6,
                    (0, 255, 255),
                    -1
                )

                cv2.putText(
                    frame,
                    'RED TARGET',
                    (x, max(25, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                # -------------------------------------------------
                # LOG ONLY ON NEW DETECTION
                # -------------------------------------------------

                if not self.last_detected:

                    self.get_logger().info(
                        '===================================='
                    )

                    self.get_logger().info(
                        'RED TARGET DETECTED'
                    )

                    self.get_logger().info(
                        f'Pixel center : '
                        f'({center_x}, {center_y})'
                    )

                    self.get_logger().info(
                        f'Drone X      : '
                        f'{self.x:.2f} m'
                    )

                    self.get_logger().info(
                        f'Drone Y      : '
                        f'{self.y:.2f} m'
                    )

                    self.get_logger().info(
                        f'Drone Z      : '
                        f'{self.z:.2f} m'
                    )

                    self.get_logger().info(
                        f'Target area  : '
                        f'{best_area:.0f} px'
                    )

                    self.get_logger().info(
                        '===================================='
                    )

                # Display position.
                cv2.putText(
                    frame,
                    (
                        f'Drone XYZ: '
                        f'{self.x:.2f}, '
                        f'{self.y:.2f}, '
                        f'{self.z:.2f}'
                    ),
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )

            else:

                cv2.putText(
                    frame,
                    'Target: NOT DETECTED',
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2
                )

            cv2.putText(
                frame,
                f'Frame: {self.frame_count}',
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.imshow(
                'Drone Red Target Detection',
                frame
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                rclpy.shutdown()

            self.last_detected = self.detected

        except Exception as error:

            self.get_logger().error(
                f'Processing error: {error}'
            )


def main():

    rclpy.init()

    node = RedTargetDetector()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        cv2.destroyAllWindows()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
