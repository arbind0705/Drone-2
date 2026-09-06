#!/usr/bin/env python3

import numpy as np
import cv2
import rclpy

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image

from ultralytics import YOLO


class YOLOCameraDetector(Node):

    def __init__(self):
        super().__init__('yolo_camera_detector')

        # ---------------------------------------------------------
        # YOLO model
        # ---------------------------------------------------------

        self.get_logger().info(
            'Loading YOLO11n model...'
        )

        self.model = YOLO('yolo11n.pt')

        # Start with a moderate confidence threshold.
        self.confidence = 0.40

        self.get_logger().info(
            'YOLO11n loaded successfully.'
        )

        # ---------------------------------------------------------
        # Camera subscription
        # ---------------------------------------------------------

        self.subscription = self.create_subscription(
            Image,
            '/drone/camera/image_raw',
            self.image_callback,
            qos_profile_sensor_data
        )

        self.frame_count = 0
        self.detection_count = 0

        self.get_logger().info(
            'Waiting for camera frames...'
        )

    # =============================================================
    # CAMERA CALLBACK
    # =============================================================

    def image_callback(self, msg):

        try:

            # -----------------------------------------------------
            # Validate image
            # -----------------------------------------------------

            if msg.encoding != 'rgb8':

                self.get_logger().error(
                    f'Unsupported encoding: {msg.encoding}'
                )

                return

            expected_size = (
                msg.height *
                msg.width *
                3
            )

            if len(msg.data) < expected_size:

                self.get_logger().error(
                    'Camera image data is smaller than expected.'
                )

                return

            # -----------------------------------------------------
            # ROS Image -> NumPy
            # -----------------------------------------------------

            image = np.frombuffer(
                msg.data,
                dtype=np.uint8
            )

            image = image.reshape(
                (msg.height, msg.width, 3)
            )

            # Camera publishes RGB.
            # OpenCV display expects BGR.
            frame = cv2.cvtColor(
                image,
                cv2.COLOR_RGB2BGR
            )

            self.frame_count += 1

            # -----------------------------------------------------
            # YOLO inference
            # -----------------------------------------------------

            results = self.model.predict(
                source=frame,
                conf=self.confidence,
                verbose=False,
                device='cpu'
            )

            result = results[0]

            annotated = frame.copy()

            self.detection_count = 0

            # -----------------------------------------------------
            # Process detections
            # -----------------------------------------------------

            if result.boxes is not None:

                for box in result.boxes:

                    self.detection_count += 1

                    # Bounding box
                    x1, y1, x2, y2 = (
                        box.xyxy[0]
                        .cpu()
                        .numpy()
                        .astype(int)
                    )

                    # Confidence
                    confidence = float(
                        box.conf[0].cpu().item()
                    )

                    # Class
                    class_id = int(
                        box.cls[0].cpu().item()
                    )

                    class_name = self.model.names[
                        class_id
                    ]

                    # -------------------------------------------------
                    # Draw bounding box
                    # -------------------------------------------------

                    cv2.rectangle(
                        annotated,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    label = (
                        f'{class_name} '
                        f'{confidence * 100:.1f}%'
                    )

                    cv2.putText(
                        annotated,
                        label,
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    # -------------------------------------------------
                    # Log detection
                    # -------------------------------------------------

                    self.get_logger().info(
                        f'DETECTED: '
                        f'{class_name} '
                        f'confidence={confidence:.2f} '
                        f'box=({x1},{y1})-({x2},{y2})'
                    )

            # -----------------------------------------------------
            # Status overlay
            # -----------------------------------------------------

            cv2.putText(
                annotated,
                f'YOLO11n | Frame: {self.frame_count}',
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                annotated,
                f'Detections: {self.detection_count}',
                (10, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            # -----------------------------------------------------
            # Display
            # -----------------------------------------------------

            cv2.imshow(
                'Drone YOLO Detection',
                annotated
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):

                self.get_logger().info(
                    'Q pressed. Shutting down.'
                )

                rclpy.shutdown()

        except Exception as error:

            self.get_logger().error(
                f'Camera processing error: {error}'
            )


# ================================================================
# MAIN
# ================================================================

def main():

    rclpy.init()

    node = YOLOCameraDetector()

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
