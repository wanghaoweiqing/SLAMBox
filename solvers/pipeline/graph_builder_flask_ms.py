"""
Building and execution of a node graph(multi-stream broadcasting).

Main classes that describe the connection between the 
server and the graph editor and the construction and 
execution of a node graph. Software platform for accessing
video stream from camera or from video file, functions and methods
for processing and analyzing a optical stream.

Static type version.
"""
import sys
from typing import List, Dict, Any, Tuple
from flask import Flask, Response, request, jsonify, render_template
import numpy as np
import cv2
from solvers import RootNode, pipeline

# Define data types for the node graph script and for the node itself.
NodeType = Dict[Any, Any]
ScriptType = List[NodeType]
ActionScriptType = Dict[str, Any]
RoiType = Tuple[Any, Any, Any, Any]  # type for region of interest


class GraphBuilderFlaskMS(pipeline.GraphBuilderTemplate):
    """Building and execution of a node graph"""

    def __init__(
        self, script: ActionScriptType, root_node: str = "WebStreaming"
    ) -> None:
        # Initializing the template class
        super().__init__(script, root_node)

    def execution_controller(self, input_script: ActionScriptType) -> None:
        """Controller for building a graph of nodes and control parameter updates"""
        match input_script["command"]:
            case "action":
                self.script = input_script["script"]
                self.graph = pipeline.build_rooted_graph(
                    self.script, "WebStreaming", self.buffer
                )
            case "update":
                if pipeline.scripts_comparison(input_script["script"], self.script):
                    self.graph_update(self.graph, input_script["script"])
            case "stop":
                sys.exit(0)


class GraphStreaming:
    """Launching and updating streaming graph"""

    def __init__(self, script: ScriptType) -> None:
        self.script = script
        self.app = Flask(__name__)
        self.update = False

        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/video_feed")
        def video_feed():
            return Response(
                self.generate_frames(GraphBuilderFlaskMS(self.script)),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

        @self.app.route("/json", methods=["POST"])
        def receive_json():
            self.script = request.get_json()
            self.update = True
            return f"Video server received script"

        @self.app.route("/selected_area", methods=["POST"])
        def selected_area():
            data = request.get_json()
            start_x = int(data["start_x"])
            start_y = int(data["start_y"])
            end_x = int(data["end_x"])
            end_y = int(data["end_y"])
            print(f"-> get roi: {data}")
            return jsonify({"message": "data received"})

    def generate_frames(self, graph_builder):
        while True:
            frame = graph_builder.graph.show_frame()
            if self.update:
                graph_builder.execution_controller(self.script)
                self.update = False
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    def run(self) -> None:
        """The main loop, processing the node execution script tree"""
        # self.app.run(host='192.168.88.253', debug=True)
        self.app.run(debug=True)

    def __del__(self) -> None:
        """Closing video capture and window"""
        print("GraphBuilder close")
