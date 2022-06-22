"""
open_street_map_visualizer.py - Given the open street map objects that we want to visualize, draw the appropriate
artifacts on our canvas.
"""


import cv2
import numpy

from coordinate_transforms import *


CLASS_NAMES = ["wood", "water", "vineyard", "residential", "scrub", "unknown", "farmland", "parking", "construction",
               "park", "retail", "industrial", "commercial", "road", "water", "building", "grass", "bridge",
               "air_conditioning", "bridge", "service", "secondary", "footway", "tertiary", "steps", "cycleway",
               "primary", "fence", "unclassified", "retaining_wall", "wall", "path", "pedestrian", "primary_link",
               "secondary_link", "tertiary_link"]

CLASS_TO_COLOR = {"wood": 1,
                  "water": 2,
                  "vineyard": 3,
                  "residential": 4,
                  "scrub": 5,
                  "unknown": 6,
                  "farmland": 7,
                  "parking": 8,
                  "construction": 9,
                  "park": 10,
                  "grass": 11,
                  "bridge": 12,
                  "fence": 13,
                  "wall": 14,
                  "footway": 15,
                  "path": 16,
                  "cycleway": 17,
                  "pedestrian": 18,
                  "retaining_wall": 19,
                  "building": 20,
                  "road": 255}


class OpenStreetMapVisualizer(object):
    def __init__(self, response_data, logger, classes_to_be_drawn):
        self.nodes = response_data["nodes"]
        self.roads = response_data["roads"]
        self.regions = response_data["regions"]
        self.waterways = response_data["waterways"]
        self.buildings = response_data["buildings"]

        self.logger = logger
        self.classes_to_be_drawn = classes_to_be_drawn


    def draw_on_canvas(self, canvas, top_left_lat, top_left_lon, original_top, original_left, original_bottom, original_right):
        self._draw_regions(canvas, top_left_lat, top_left_lon)

        self._draw_waterways(canvas, top_left_lat, top_left_lon)

        self._draw_roads(canvas, top_left_lat, top_left_lon)

        self._draw_buildings(canvas, top_left_lat, top_left_lon)

        cropped_canvas = self._crop_canvas(canvas, top_left_lat, top_left_lon, original_top, original_left, original_bottom, original_right)

        return cropped_canvas


    def _draw_regions(self, canvas, top_left_lat, top_left_lon):

        regions = [self.regions[region_id] for region_id in self.regions.keys()]
        regions = sorted(regions, key=lambda x: x.get_area(self.nodes), reverse=True)

        # for region_id in self.regions.keys():
        for region in regions:
            # region = self.regions[region_id]

            coords = []
            for node in region.nodes:
                node = self.nodes[node]
                lat = float(node.lat)
                lon = float(node.lon)

                dx = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, top_left_lat, lon)
                if lon < top_left_lon:
                    dx *= -1

                dy = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, lat, top_left_lon)
                if lat > top_left_lat:
                    dy *= -1

                dx = int(dx)
                dy = int(dy)

                coords.append([dx, dy])

            coords = numpy.array(coords)

            if region.type in CLASS_TO_COLOR.keys():
                color = CLASS_TO_COLOR[region.type]

                if not self.classes_to_be_drawn or region.type in self.classes_to_be_drawn:
                    cv2.fillPoly(canvas, numpy.array([coords]), color)

            else:
                self.logger.debug("We found a '" + str(region.type) + "' region, but we will not draw it.")
                # Known region classes that we ignore: retail, industrial, commercial
                # We do not draw these, since they would interfere with other class declarations


    def _draw_roads(self, canvas, top_left_lat, top_left_lon):

        if self.classes_to_be_drawn and "road" not in self.classes_to_be_drawn:
            return

        road_i = 0
        for road_id in self.roads.keys():
            road = self.roads[road_id]

            if self.classes_to_be_drawn and road.type not in self.classes_to_be_drawn:
                continue

            prev_coord = None
            for node in road.nodes:
                node = self.nodes[node]
                lat = float(node.lat)
                lon = float(node.lon)

                dx = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, top_left_lat, lon)
                if lon < top_left_lon:
                    dx *= -1

                dy = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, lat, top_left_lon)
                if lat > top_left_lat:
                    dy *= -1

                dx = int(dx)
                dy = int(dy)

                color = CLASS_TO_COLOR["road"]
                if road.type in CLASS_TO_COLOR.keys():
                    color = CLASS_TO_COLOR[road.type]
                else:
                    self.logger.debug("We use the default color for the following road type: " + str(road.type))

                if dy < canvas.shape[0] and lon > top_left_lon and dx < canvas.shape[1] and lat < top_left_lat:
                    if prev_coord:
                        cv2.line(canvas, (dx, dy), (prev_coord[0], prev_coord[1]), color, 3)

                prev_coord = (dx, dy)

            road_i += 1


    def _draw_waterways(self, canvas, top_left_lat, top_left_lon):

        if self.classes_to_be_drawn and "water" not in self.classes_to_be_drawn:
            return

        for waterway in self.waterways.keys():
            waterway = self.waterways[waterway]

            coords = []
            for node in waterway.nodes:
                node = self.nodes[node]
                lat = float(node.lat)
                lon = float(node.lon)

                dx = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, top_left_lat, lon)
                if lon < top_left_lon:
                    dx *= -1

                dy = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, lat, top_left_lon)
                if lat > top_left_lat:
                    dy *= -1

                dx = int(dx)
                dy = int(dy)

                coords.append([dx, dy])

            coords = numpy.array(coords)
            color = CLASS_TO_COLOR["water"]
            cv2.polylines(canvas, numpy.array([coords]), False, color, 5)


    def _draw_buildings(self, canvas, top_left_lat, top_left_lon):

        if self.classes_to_be_drawn and "building" not in self.classes_to_be_drawn:
            return

        for building in self.buildings.keys():
            building = self.buildings[building]

            coords = []
            for node in building.nodes:
                node = self.nodes[node]
                lat = float(node.lat)
                lon = float(node.lon)

                dx = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, top_left_lat, lon)
                if lon < top_left_lon:
                    dx *= -1

                dy = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, lat, top_left_lon)
                if lat > top_left_lat:
                    dy *= -1

                dx = int(dx)
                dy = int(dy)

                coords.append([dx, dy])

            coords = numpy.array(coords)

            cv2.fillPoly(canvas, numpy.array([coords]), CLASS_TO_COLOR["building"])


    def _crop_canvas(self, canvas, top_left_lat, top_left_lon, original_top, original_left, original_bottom, original_right):
        rel_left = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, top_left_lat, original_left)
        rel_right = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, top_left_lat, original_right)
        rel_top = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, original_top, top_left_lon)
        rel_bottom = 10 * distance_between_two_gps_points(top_left_lat, top_left_lon, original_bottom, top_left_lon)

        rel_left = int(rel_left)
        rel_right = int(rel_right)
        rel_top = int(rel_top)
        rel_bottom = int(rel_bottom)

        # rel_top and rel_bottom are both too large for the canvas size
        self.logger.debug("The size of our canvas: " + str(canvas.shape))
        cropped_image = canvas[rel_top:rel_bottom, rel_left:rel_right, :]

        return cropped_image
