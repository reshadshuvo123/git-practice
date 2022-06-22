"""data_models.py - contains class definitions for the data structures contained in the OpenStreetMap XML response."""


class Node(object):
    def __init__(self, id, lat, lon,features):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.features=features


class Road(object):
    def __init__(self, nodes, name, type, foot=False):
        self.nodes = nodes
        self.name = name
        self.type = type
        self.foot = foot


class Region(object):
    def __init__(self, nodes, type):
        self.nodes = nodes
        self.type = type

    def get_area(self, node_dictionary):
        total = 0

        prev_node = self.nodes[-1]
        for node in self.nodes:
            node_obj = node_dictionary[node]
            prev_node_obj = node_dictionary[prev_node]

            node_lat = float(node_obj.lat)
            node_lon = float(node_obj.lon)
            prev_node_lat = float(prev_node_obj.lat)
            prev_node_lon = float(prev_node_obj.lon)

            difference = node_lon * prev_node_lat - prev_node_lon * node_lat
            total += difference

            prev_node = node

        return abs(total / 2)


class Building(object):
    def __init__(self, nodes, name):
        self.nodes = nodes
        self.name = name


class Railways(object):
    def __init__(self, nodes, name):
        self.nodes = nodes
        self.name = name
        self.type = type