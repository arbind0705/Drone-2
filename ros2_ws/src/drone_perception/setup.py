from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'drone_perception'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='arbind',
    maintainer_email='arbind@todo.todo',
    description='Drone perception and sensor processing',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
		'camera_node = drone_perception.camera_node:main',
		'lidar_node = drone_perception.lidar_node:main',
		'scan_processor_node = drone_perception.scan_processor_node:main',
	],
    },
)
