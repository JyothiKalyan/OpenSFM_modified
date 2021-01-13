import logging
import os
import subprocess

import PIL
from fpdf import FPDF
from opensfm import io


logger = logging.getLogger(__name__)


class Report:
    def __init__(self, data, stats = None):
        self.output_path = os.path.join(data.data_path, "stats")
        self.dataset_name = os.path.basename(data.data_path)

        self.mapi_light_light_green = [255, 255, 255]
        self.mapi_light_green = [0, 0, 0]
        self.mapi_light_grey = [218, 222, 228]
        self.mapi_dark_grey = [99, 115, 129]

        self.pdf = FPDF("P", "mm", "A4")
        self.pdf.add_page()

        self.title_size = 20
        self.h1 = 16
        self.h2 = 13
        self.h3 = 10
        self.text = 10
        self.small_text = 8
        self.margin = 10
        self.cell_height = 7
        self.total_size = 190

        if stats is not None:
            self.stats = stats
        else:
            self.stats = self._read_stats_file("stats.json")

    def save_report(self, filename):
        self.pdf.output(os.path.join(self.output_path, filename), "F")

    def _make_table(self, columns_names, rows, row_header=False):
        self.pdf.set_font("Helvetica", "", self.h3)
        self.pdf.set_line_width(0.3)

        columns_sizes = [int(self.total_size / len(rows[0]))] * len(rows[0])

        if columns_names:
            self.pdf.set_draw_color(*self.mapi_light_grey)
            self.pdf.set_fill_color(*self.mapi_light_grey)
            for col, size in zip(columns_names, columns_sizes):
                self.pdf.rect(
                    self.pdf.get_x(),
                    self.pdf.get_y(),
                    size,
                    self.cell_height,
                    style="FD",
                )
                self.pdf.set_text_color(*self.mapi_dark_grey)
                self.pdf.cell(size, self.cell_height, col, align="L")
            self.pdf.set_xy(self.margin, self.pdf.get_y() + self.cell_height)

        self.pdf.set_draw_color(*self.mapi_light_grey)
        self.pdf.set_fill_color(*self.mapi_light_light_green)

        for row in rows:
            for i, (col, size) in enumerate(zip(row, columns_sizes)):
                if i == 0 and row_header:
                    self.pdf.set_draw_color(*self.mapi_light_grey)
                    self.pdf.set_fill_color(*self.mapi_light_grey)
                self.pdf.rect(
                    self.pdf.get_x(),
                    self.pdf.get_y(),
                    size,
                    self.cell_height,
                    style="FD",
                )
                self.pdf.set_text_color(*self.mapi_dark_grey)
                if i == 0 and row_header:
                    self.pdf.set_draw_color(*self.mapi_light_grey)
                    self.pdf.set_fill_color(*self.mapi_light_light_green)
                self.pdf.cell(size, self.cell_height, col, align="L")
            self.pdf.set_xy(self.margin, self.pdf.get_y() + self.cell_height)

    def _read_stats_file(self, filename):
        file_path = os.path.join(self.output_path, filename)
        with io.open_rt(file_path) as fin:
            return io.json_load(fin)

    def _make_section(self, title):
        self.pdf.set_font("Helvetica", "B", self.h1)
        self.pdf.set_text_color(*self.mapi_dark_grey)
        self.pdf.cell(0, self.margin, title, align="L")
        self.pdf.set_xy(self.margin, self.pdf.get_y() + 1.5 * self.margin)

    def _make_subsection(self, title):
        self.pdf.set_xy(self.margin, self.pdf.get_y() - 0.5 * self.margin)
        self.pdf.set_font("Helvetica", "B", self.h2)
        self.pdf.set_text_color(*self.mapi_dark_grey)
        self.pdf.cell(0, self.margin, title, align="L")
        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin)

    def _make_centered_image(self, image_path, desired_height):
        width, height = PIL.Image.open(image_path).size
        resized_width = width * desired_height / height
        if resized_width > self.total_size:
            resized_width = self.total_size
            desired_height = height * resized_width / width

        self.pdf.image(
            image_path,
            self.pdf.get_x() + self.total_size / 2 - resized_width / 2,
            self.pdf.get_y(),
            h=desired_height,
        )
        self.pdf.set_xy(self.margin, self.pdf.get_y() + desired_height + self.margin)

    def make_title(self):
        # title
        self.pdf.set_font("Helvetica", "B", self.title_size)
        self.pdf.set_text_color(*self.mapi_light_green)
        self.pdf.cell(0, self.margin, "ODM Quality Report", align="C")
        self.pdf.set_xy(self.margin, self.title_size)

        # version number
        version_file = os.path.join(os.path.dirname(__file__), "../../../../VERSION")
        version = ""
        try:
            with open(version_file, 'r') as f:
               version = f.read().strip()
        except Exception as e:
            logger.warning("Invalid version file" + version_file + ": " + str(e))

        # indicate we don't know the version
        version = "unknown" if version == "" else version

        self.pdf.set_font("Helvetica", "", self.small_text)
        self.pdf.set_text_color(*self.mapi_dark_grey)
        self.pdf.cell(
            0, self.margin, f"Processed with ODM version {version}", align="R"
        )
        self.pdf.set_xy(self.margin, self.pdf.get_y() + 2 * self.margin)

    def make_dataset_summary(self):
        self._make_section("Dataset Summary")

        rows = [
            #["Dataset", self.dataset_name],
            ["Date", self.stats["processing_statistics"]["date"]],
            [
                "Area Covered",
                f"{self.stats['processing_statistics']['area']/1e6:.6f} km²",
            ],
            [
                "Processing Time",
                #f"{self.stats['processing_statistics']['steps_times']['Total Time']:.2f} seconds",
                self.stats['odm_processing_statistics']['total_time_human'],
            ],
        ]
        self._make_table(None, rows, True)
        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin)

    def _has_meaningful_gcp(self):
        return (
            self.stats["reconstruction_statistics"]["has_gcp"]
            and "average_error" in self.stats["gcp_errors"]
        )

    def make_processing_summary(self):
        self._make_section("Processing Summary")

        rec_shots, init_shots = (
            self.stats["reconstruction_statistics"]["reconstructed_shots_count"],
            self.stats["reconstruction_statistics"]["initial_shots_count"],
        )
        rec_points, init_points = (
            self.stats["reconstruction_statistics"]["reconstructed_points_count"],
            self.stats["reconstruction_statistics"]["initial_points_count"],
        )

        geo_string = []
        if self.stats["reconstruction_statistics"]["has_gps"]:
            geo_string.append("GPS")
        if self._has_meaningful_gcp():
            geo_string.append("GCP")

        rows = [
            [
                "Reconstructed Images",
                f"{rec_shots} over {init_shots} shots ({rec_shots/init_shots*100:.1f}%)",
            ],
            [
                "Reconstructed Points (Sparse)",
                f"{rec_points} over {init_points} points ({rec_points/init_points*100:.1f}%)",
            ],
            [
                "Reconstructed Components",
                f"{self.stats['reconstruction_statistics']['components']} component",
            ],
            [
                "Detected Features",
                f"{self.stats['features_statistics']['detected_features']['median']:,} features",
            ],
            [
                "Reconstructed Features",
                f"{self.stats['features_statistics']['reconstructed_features']['median']:,} features",
            ],
            ["Geographic Reference", " and ".join(geo_string)],
        ]

        # Dense (if available)
        if self.stats.get('point_cloud_statistics'):
            rows.insert(2, [
                "Reconstructed Points (Dense)",
                f"{self.stats['point_cloud_statistics']['summary']['num_points']:,} points"
            ])

        # GSD (if available)
        if self.stats['odm_processing_statistics'].get('average_gsd'):
            rows.insert(3, [
                "Average Ground Sampling Distance (GSD)",
                f"{self.stats['odm_processing_statistics']['average_gsd']:.1f} cm"
            ])

        row_gps_gcp = [" / ".join(geo_string) + " errors"]
        geo_errors = []
        if self.stats["reconstruction_statistics"]["has_gps"]:
            geo_errors.append(f"{self.stats['gps_errors']['average_error']:.2f}")
        if self._has_meaningful_gcp():
            geo_errors.append(f"{self.stats['gcp_errors']['average_error']:.2f}")
        row_gps_gcp.append(" / ".join(geo_errors) + " meters")
        rows.append(row_gps_gcp)

        self._make_table(None, rows, True)
        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin / 2)

        topview_height = 130
        topview_grids = [
            f for f in os.listdir(self.output_path) if f.startswith("topview")
        ]
        self._make_centered_image(
            os.path.join(self.output_path, topview_grids[0]), topview_height
        )

        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin)

    def make_processing_time_details(self):
        self._make_section("Processing Time Details")

        columns_names = list(self.stats["processing_statistics"]["steps_times"].keys())
        formatted_floats = []
        for v in self.stats["processing_statistics"]["steps_times"].values():
            formatted_floats.append(f"{v:.2f} sec.")
        rows = [formatted_floats]
        self._make_table(columns_names, rows)
        self.pdf.set_xy(self.margin, self.pdf.get_y() + 2 * self.margin)

    def make_gps_details(self):
        self._make_section("GPS/GCP Errors Details")

        # GPS
        for error_type in ["gps", "gcp"]:
            rows = []
            columns_names = [error_type.upper(), "Mean", "Sigma", "RMS Error"]
            if "average_error" not in self.stats[error_type + "_errors"]:
                continue
            for comp in ["x", "y", "z"]:
                row = [comp.upper() + " Error (meters)"]
                row.append(f"{self.stats[error_type + '_errors']['mean'][comp]:.3f}")
                row.append(f"{self.stats[error_type +'_errors']['std'][comp]:.3f}")
                row.append(f"{self.stats[error_type +'_errors']['error'][comp]:.3f}")
                rows.append(row)

            rows.append(
                [
                    "Total",
                    "",
                    "",
                    f"{self.stats[error_type +'_errors']['average_error']:.3f}",
                ]
            )
            self._make_table(columns_names, rows)
            self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin / 2)

        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin / 2)

    def make_features_details(self):
        self._make_section("Features Details")

        heatmap_height = 60
        heatmaps = [f for f in os.listdir(self.output_path) if f.startswith("heatmap")]
        self._make_centered_image(
            os.path.join(self.output_path, heatmaps[0]), heatmap_height
        )
        if len(heatmaps) > 1:
            logger.warning("Please implement multi-model display")

        columns_names = ["", "Min.", "Max.", "Mean", "Median"]
        rows = []
        for comp in ["detected_features", "reconstructed_features"]:
            row = [comp.replace("_", " ").replace("features", "").capitalize()]
            for t in columns_names[1:]:
                row.append(
                    f"{self.stats['features_statistics'][comp][t.replace('.', '').lower()]:.0f}"
                )
            rows.append(row)
        self._make_table(columns_names, rows)

        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin)

    def make_reconstruction_details(self):
        self._make_section("Reconstruction Details")

        rows = [
            [
                "Average reprojection Error",
                f"{self.stats['reconstruction_statistics']['reprojection_error']:.2f} pixels",
            ],
            [
                "Average Track Length",
                f"{self.stats['reconstruction_statistics']['average_track_length']:.2f} images",
            ],
            [
                "Average Track Length (> 2)",
                f"{self.stats['reconstruction_statistics']['average_track_length_over_two']:.2f} images",
            ],
        ]
        self._make_table(None, rows, True)
        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin)

    def make_camera_models_details(self):
        self._make_section("Camera Models Details")

        for camera, params in self.stats["camera_errors"].items():
            residual_grids = [
                f
                for f in os.listdir(self.output_path)
                if f.startswith("residuals_" + str(camera.replace("/", "_")))
            ]
            if not residual_grids:
                continue

            initial = params["initial_values"]
            optimized = params["optimized_values"]
            names = [""] + list(initial.keys())

            rows = []
            rows.append(["Initial"] + [f"{x:.4f}" for x in initial.values()])
            rows.append(["Optimized"] + [f"{x:.4f}" for x in optimized.values()])

            self._make_subsection(camera)
            self._make_table(names, rows)
            self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin / 2)

            residual_grid_height = 80
            self._make_centered_image(
                os.path.join(self.output_path, residual_grids[0]), residual_grid_height
            )

    def make_tracks_details(self):
        self._make_section("Tracks Details")
        matchgraph_height = 60
        matchgraph = [
            f for f in os.listdir(self.output_path) if f.startswith("matchgraph")
        ]
        self._make_centered_image(
            os.path.join(self.output_path, matchgraph[0]), matchgraph_height
        )

        histogram = self.stats["reconstruction_statistics"]["histogram_track_length"]
        start_length, end_length = 2, 10
        row_length = ["Length"]
        for length, _ in sorted(histogram.items(), key=lambda x: int(x[0])):
            if int(length) < start_length or int(length) > end_length:
                continue
            row_length.append(length)
        row_count = ["Count"]
        for length, count in sorted(histogram.items(), key=lambda x: int(x[0])):
            if int(length) < start_length or int(length) > end_length:
                continue
            row_count.append(f"{count}")

        self._make_table(None, [row_length, row_count], True)

        self.pdf.set_xy(self.margin, self.pdf.get_y() + self.margin)

    def add_page_break(self):
        self.pdf.add_page("P")

    def generate_report(self, odm_stats = None):
        self.make_title()
        self.make_dataset_summary()
        self.make_processing_summary()
        self.add_page_break()

        self.make_features_details()
        self.make_reconstruction_details()
        self.make_tracks_details()
        self.add_page_break()

        self.make_camera_models_details()
        self.make_gps_details()
        # self.make_processing_time_details()