from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    bridge_arguments = [

        # =====================================================
        # LiDAR
        # =====================================================

        '/world/default/model/x500_sensor_demo_0/link/lidar_front_link/sensor/lidar_front/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',

        '/world/default/model/x500_sensor_demo_0/link/lidar_right_link/sensor/lidar_right/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',

        '/world/default/model/x500_sensor_demo_0/link/lidar_rear_link/sensor/lidar_rear/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',

        '/world/default/model/x500_sensor_demo_0/link/lidar_left_link/sensor/lidar_left/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',

        '/world/default/model/x500_sensor_demo_0/link/lidar_down_link/sensor/lidar_down/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',

        # =====================================================
        # Camera image
        # =====================================================

        '/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',

        # =====================================================
        # Camera information
        # =====================================================

        '/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',

        # =====================================================
        # ROS remappings
        # =====================================================

        '--ros-args',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/lidar_front_link/sensor/lidar_front/scan:=/drone/lidar_front',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/lidar_right_link/sensor/lidar_right/scan:=/drone/lidar_right',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/lidar_rear_link/sensor/lidar_rear/scan:=/drone/lidar_rear',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/lidar_left_link/sensor/lidar_left/scan:=/drone/lidar_left',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/lidar_down_link/sensor/lidar_down/scan:=/drone/lidar_down',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/image:=/drone/camera/image_raw',

        '-r',
        '/world/default/model/x500_sensor_demo_0/link/camera_link/sensor/camera/camera_info:=/drone/camera/camera_info',
    ]

    return LaunchDescription([
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=bridge_arguments,
            output='screen',
        )
    ])
