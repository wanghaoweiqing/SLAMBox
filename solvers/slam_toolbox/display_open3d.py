"""
Show 3D map and camera path
"""
import copy
from multiprocessing import Process, Queue
import numpy as np
from scipy.spatial.transform import Rotation as scipyR  # type: ignore
import open3d as o3d  # type: ignore


class DisplayOpen3D:
    def __init__(self, width=1280, height=720, scale=0.05, point_size=2.0):
        self.amount = 100
        self.width = width
        self.height = height
        self.scale = scale
        self.point_size = point_size
        self.state = None
        self.queue = Queue()
        self.vp = Process(
            name="DisplayOpen3D", target=self.viewer_thread, args=(self.queue,)
        )
        self.vp.daemon = True
        self.vp.start()

    def viewer_thread(self, q):
        self.viewer_init(self.width, self.height)
        while True:
            self.viewer_refresh(q)

    def viewer_init(self, w, h):
        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window(
            window_name="Open3D Map", width=w, height=h, left=100, top=200
        )

        self.ctr = self.vis.get_view_control()
        self.ctr.change_field_of_view(step=0.45)
        self.ctr.set_constant_z_far(1000.0)
        self.ctr.set_constant_z_near(0.01)

        self.widget3d = self.vis.get_render_option()
        self.widget3d.show_coordinate_frame = True
        self.widget3d.background_color = np.asarray([0, 0, 0])
        self.widget3d.point_size = self.point_size

        self.pcl = o3d.geometry.PointCloud()
        self.pcl.points = o3d.utility.Vector3dVector(np.random.randn(self.amount, 3))
        self.pcl.paint_uniform_color((0.5, 0.1, 0.1))

        self.axis = o3d.geometry.TriangleMesh.create_coordinate_frame()
        # self.axis = o3d.geometry.TriangleMesh.create_box(0.2, 0.2, 0.2)
        # self.axis.compute_vertex_normals()
        # self.axis.paint_uniform_color((1.0, 0.0, 0.0))

        self.vis.add_geometry(self.pcl)
        self.vis.add_geometry(self.axis)

    def viewer_refresh(self, q):
        while not q.empty():
            self.state = q.get()

        if self.state is not None:
            if self.state[0].shape[0] >= 1:
                # draw keypoints
                rotation_matrix = scipyR.from_euler("zyx", [0, 0, 180], degrees=True)
                self.pcl.points = o3d.utility.Vector3dVector(
                    rotation_matrix.apply(self.state[0])
                )
                self.pcl.colors = o3d.utility.Vector3dVector(self.state[1])
                self.widget3d.point_size = self.state[2]

                # This part is not working correctly yet
                # self.axis.translate(self.state[3], relative=False)

        self.vis.update_geometry(self.pcl)
        # self.vis.update_geometry(self.axis)
        self.vis.poll_events()
        self.vis.update_renderer()

    def send_to_visualization(self, mapp, psize):
        """Sending data to the visualization process
        0.003 - coefficient for converting 0:255 to 0:1
        Combine two arrays: an array of points and camera trajectory points,
        color of camera points is red"""
        if self.queue is None:
            return
        pts = [p.pt * self.scale for p in mapp.points]
        colors = [p.color * 0.003 for p in mapp.points]
        cam_pts = [
            np.linalg.inv(cam_frame.pose)[:, [-1]][:3].ravel() * self.scale
            for cam_frame in mapp.frames
        ]

        cam_colors = [(1.0, 0.0, 0.0)] * len(cam_pts)
        self.queue.put((np.array(pts + cam_pts), np.array(colors + cam_colors), psize))

        # This part is not working correctly yet
        # pose = mapp.frames[-1].pose[:,[-1]][:3].ravel() * self.scale
        # self.queue.put((np.array(pts + cam_pts), np.array(colors + cam_colors), psize, np.array(pose)))

    def __del__(self):
        self.vis.destroy_window()
