"""
OSM_over_aws.py - A class that defines how SatelliteImageFetcher will interact with the Sentinel2 dataset hosted on
                           an AWS S3 bucket. Uses SentinelHub. (https://github.com/sentinel-hub/sentinelhub-py)
"""

import logging
import math
import datetime
import cv2
import numpy
import requests
import time
import geojson
from geojson import Feature, Point, FeatureCollection, Polygon

# TODO - remove the "trunk." from this import statement
from logger_factory import create_logger
from open_street_map_xml_parser1 import OpenStreetMapXmlParser
from open_street_map_visualizer import OpenStreetMapVisualizer, CLASS_NAMES

# The location where the examples below will save the testing output. You should modify this for your system.
IMAGE_OUTPUT_DIRECTORY = "C:\\Works\\NGA\\outputs\\"

DATETIME_STRING_FORMAT = "%Y-%m-%d"
EARTH_RADIUS_METERS = 6378137  ## 6371000 from wiki


class OpenStreetMap(object):
    def __init__(self, config=None):
        log_level = config.get("log_level", logging.INFO)
        self.logger = create_logger(log_level, self.__class__.__name__)
        self.xml_parser = OpenStreetMapXmlParser(self.logger)

        self.classes_to_be_drawn = config.get("allowed_classes", None)
        if self.classes_to_be_drawn:
            self._validate_classes_to_be_drawn()


    def _validate_classes_to_be_drawn(self):
        for class_name in self.classes_to_be_drawn:
            if class_name not in CLASS_NAMES:
                exception_string = "The class name '" + str(class_name) + "' is not a valid drawable class. The valid " \
                                + "class names are: \n" + ", ".join(CLASS_NAMES) + " ."
                raise Exception(exception_string)


    def meter_offset_gps(self, orig_lat, orig_lon, dx, dy):
        """ Calculates a new GPS coordinate given an original GPS coordinate and an offset in meters.
            This assumes a spherical representation of the Earth, and may be inaccurate over extremely large distances.
            Returns a tuple of (new latitude , new longitude). """
        d_lat_radians = dy / EARTH_RADIUS_METERS
        d_lon_radians = dx / (EARTH_RADIUS_METERS * math.cos(math.pi * orig_lat / 180))

        new_lat = orig_lat + d_lat_radians * 180/math.pi
        new_lon = orig_lon + d_lon_radians * 180/math.pi

        return new_lat, new_lon


    def _inflate_area_of_interest(self, original_top, original_left, original_bottom, original_right):
        avg_lat = (original_top + original_bottom) / 2
        dlat = original_top - original_bottom

        avg_lon = (original_left + original_right) / 2
        dlon = original_right - original_left

        dlat *= 1.5
        dlon *= 1.5

        new_top = avg_lat + dlat
        new_bot = avg_lat - dlat
        new_left = avg_lon - dlon
        new_right = avg_lon + dlon

        return (new_top, new_left), (new_bot, new_right)


    def fetch_image(self, lat, lon, temporal_samples, tile_size_meters, resize=None, zoom_level=10):

        self.logger.info("Starting our fetch process for " + str(lat) + ", " + str(lon))

        lat0, lon0 = self.meter_offset_gps(lat, lon, -0.5*tile_size_meters, -0.5*tile_size_meters)
        lat1, lon1 = self.meter_offset_gps(lat, lon, 0.5*tile_size_meters, 0.5*tile_size_meters)

        top_left = (lat1, lon0)
        bottom_right = (lat0, lon1)

        return self.fetch_image_from_bounding_box(top_left, bottom_right, temporal_samples, resize=resize, zoom_level=zoom_level)


    def fetch_image_from_bounding_box(self, top_left, bottom_right, temporal_samples, resize=None, zoom_level=-1):
        """ Returns a list of 3-channel ndarrays representing the satellite image defined by the given bounding box.
            Each image in the list is taken from a different point in time, evenly spaced throughout the year.
            Temporal_samples defines the number of images taken.
            To resize the image to a given size, provide a tuple of pixel dimensions to the resize parameter."""

        start_time = time.time() * 1000

        if zoom_level != -1:
            self.logger.warning("The zoom_level has been specified, but is not applicable for the OpenStreetMap dataset")

        # Inflate AOI slightly, to capture all involved entities
        new_top_left, new_bottom_right = self._inflate_area_of_interest(top_left[0], top_left[1], bottom_right[0], bottom_right[1])

        sample_url = "http://openstreetmap.org/api/0.6/map?bbox={left},{bottom},{right},{top}"
        filled_url = sample_url.format(left=new_top_left[1], bottom=new_bottom_right[0], right=new_bottom_right[1], top=new_top_left[0])
        self.logger.debug("Requesting the following link: " + str(filled_url))
        xml_response = requests.get(filled_url).content

        xml_parser = OpenStreetMapXmlParser(self.logger)
        xml_parser.parse_xml(xml_response)
        extracted_data = xml_parser.get_extracted_data()
        #print(extracted_data)
        #print(xml_parser)g
        canvas, (max_lat, max_lon) = xml_parser.create_image_canvas(xml_response, top_left, bottom_right)

        visualizer = OpenStreetMapVisualizer(extracted_data, self.logger, self.classes_to_be_drawn)
        output_canvas = visualizer.draw_on_canvas(canvas, max_lat, max_lon, top_left[0], top_left[1], bottom_right[0], bottom_right[1])

        images = []
        for _ in range(temporal_samples):
            # Resize image and put in the image list as appropriate
            if resize:
                output_canvas = cv2.resize(output_canvas, resize, interpolation=cv2.INTER_NEAREST)
            images.append(output_canvas)

        self.logger.info("The OpenStreetMap image was generated in " + str(time.time()*1000 - start_time) + " ms")

        return numpy.array(images), extracted_data, xml_response,xml_parser, new_top_left, new_bottom_right


def get_new_instance(config):
    """ Returns a new instance of the Sentinel2OverAws object, given the configuration spec as a dictionary.
        An example config spec can be seen below. """
    return OpenStreetMap(config)



def geo_jason(new_top_left,new_bottom_right,data):
    new_top, new_left = new_top_left
    new_bot, new_right = new_bottom_right
    ROI = Polygon([[new_top, new_left, new_bot, new_right]])

    nodes = data["nodes"].keys()
    nodesall=[]
    for i in nodes:
        id = data['nodes'].get(i).id
        lat = data['nodes'].get(i).lat
        lon = data['nodes'].get(i).lon
        node_features= data['nodes'].get(i).features
        properties_nodes={'types': 'Nodes', 'id':id, 'lat': lat, 'lon': lon,'features': node_features}
        nodesall.append(properties_nodes)
    Node_features = Feature(geometry=ROI,properties={'buildings': nodesall})

    buildings=data['buildings'].keys()
    building=[]
    for i in buildings:
        id = i
        types='building'
        names = data['buildings'].get(i).name
        connected = data['buildings'].get(i).nodes
        properties_buildings={'types': types, 'id':id, 'names': names,'connection': connected}
        building.append(properties_buildings)
    Building_features = Feature(geometry=ROI,properties={'buildings': building})

    roads = data['roads'].keys()
    road = []
    for i in roads:
        id = i
        type = 'roads'
        types = data['roads'].get(i).type
        names = data['roads'].get(i).name
        connected = data['roads'].get(i).nodes   ### highway, smaller side road? what types of roads
        properties_roads = {'type': type,'types':types, 'id': id, 'names': names, 'connection': connected}
        road.append(properties_roads)

    road_features =  Feature(geometry=ROI,properties={'roads':road})

    regions = data['regions'].keys()
    region = []
    for i in regions:
        id = i
        type = 'regions'
        types= data['regions'].get(i).type
        connected = data['regions'].get(i).nodes
        properties = {'type':type,'types': types, 'id': id,'connection': connected}
        region.append(properties)
    region_features = Feature(geometry=ROI,properties={'regions': region})

    waterways = data['waterways'].keys()
    waterway = []
    for i in waterways:
        id = i
        type = 'waterways'
        types= data['waterways'].get(i).type
        connected = data['waterways'].get(i).nodes
        properties = {'type':type,'types': types, 'id': id, 'connection': connected}
        waterway.append(properties)

    waterway_features = Feature(geometry=ROI,properties={'waterways': waterway})

    railways = data['Railways'].keys()
    railway = []
    for i in railways:
        id = i
        type = 'railways'
        types = data['Railways'].get(i).type
        name = data['Railways'].get(i).name
        connected = data['waterways'].get(i).node
        properties = {'type': type, 'types': types, 'id': id,'name':name, 'connection': connected}
        railway.append(properties)

    railway_features = Feature(geometry=ROI, properties={'railways': railway})

    feature = Feature(geometry=ROI,properties={'roads':road,'regions':region,'waterways':waterway,'buildings':building,'railway':railway})

    return feature, Node_features, road_features, region_features, waterway_features, Building_features, railway_features







if __name__ == "__main__":
    """ A few examples of how to create and use the Sentinel2OverAws class to fetch Sentinel2 data. """
    config = {"log_level": logging.INFO}
    sentinel_fetcher = OpenStreetMap(config=config)

    # RTC
    original_left = -77.15438
    original_bottom = 39.08831
    original_right = -77.14963
    original_top = 39.09083

    # University View
    original_left = -76.93571
    original_top = 38.99345
    original_right = -76.93305
    original_bottom = 38.99099

    top_left = (original_top, original_left)
    bottom_right = (original_bottom, original_right)
    now = time.time() * 1000
    temporal_samples = 1
    output_image_cube,data,c,d,new_top_left, new_bottom_right= sentinel_fetcher.fetch_image_from_bounding_box(top_left, bottom_right, temporal_samples)
    #output_image_cube = sentinel_fetcher.fetch_image(39.08831, -77.15438, temporal_samples, 500)


    feature, Node_features,road_features, region_features, waterway_features, Building_features,railway_features = geo_jason(new_top_left, new_bottom_right, data)

    for i, img in enumerate(output_image_cube):
        cv2.imwrite(IMAGE_OUTPUT_DIRECTORY + datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S_" + str(i) + ".png"), img)
