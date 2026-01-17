import json

def load_menu(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    return data
