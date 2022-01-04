# Necessary Imports
import json

# Handles creating a "config" object for main.py 
def parse_config(config):
    with open("schema.json", "r") as f:
        schema = json.load(f)
    parse_config_data_types(config, schema) # Parse everything into its data type specified in the schema
    return config

# Need special handling
special_keys = set(["Hatch Default ID", "Contour Default ID", "Segment Styles", "Velocity Profiles"])

def default_config():
    with open("schema.json", "r") as f:
        schema = json.load(f)
    config = {} 

    # Need specially handled
    config["Hatch Default ID"] = schema["Hatch Default ID"]
    config["Contour Default ID"] = schema["Contour Default ID"]
    config["Segment Styles"] = schema["Segment Styles"]
    config["Velocity Profiles"] = schema["Velocity Profiles"]

    # Can handle as a general case
    for category in schema: # Fill with default values according to the schema 
        if category in special_keys:
            continue
        for attribute in schema[category]: 
            config[attribute["name"]] = attribute["default"]

    # Convert to correct data types, as by default they are stringified
    parse_config_data_types(config, schema)       
    return config

def parse_config_data_types(config, schema):
    for category in schema:
        if category in special_keys:
            continue
        for attribute in schema[category]:
            config[attribute["name"]] = get_value_of_attribute(config[attribute["name"]], attribute["type"])

# Provided a string value and a data type for it, correctly parse it 
def get_value_of_attribute(value, data_type):
    if data_type == "int":
        return int(value)
    elif data_type == "float":
        return float(value)
    elif data_type == "bool":
        return True if value == "Yes" else False
    else:
        return value