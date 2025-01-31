from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import legendmeta
import numpy as np
import yaml


# This script is used to generate the special_metadata.yaml and channelmap.yaml files for the LEGEND-1000 geometry.
def parse_arguments():
    """Parse command line arguments."""
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-i", "--input", type=str, required=True)
    argparser.add_argument("-s", "--output_special_metadata", type=str, default="special_metadata.yaml")
    argparser.add_argument("-c", "--output_channelmap", type=str, default="channelmap.json")
    return argparser.parse_args()


# Helper class taken from https://stackoverflow.com/questions/50916422/python-typeerror-object-of-type-int64-is-not-json-serializable
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# Constants
ARRAY_CONFIG = {
    "center": {
        "x_in_mm": [0, 550, 110, -440, -550, -110, 440],
        "y_in_mm": [0, 190.5, 571.6, 381.1, -190.5, -571.6, -381.1],
    },
    "radius_in_mm": 220,
    "angle_in_deg": [0, 60, 120, 180, 240, 300],
}

N_FIBERS_PER_STRING = 3


def load_config(input_path):
    """Load configuration from a JSON file."""
    with Path(input_path).open() as f:
        return json.load(f)


def generate_special_metadata(output_path: str, config: dict, string_idx: list, hpge_names: list) -> None:
    """Generate special_metadata.yaml file."""

    special_output = {}

    special_output["hpge_string"] = {
        f"{string_idx[i][j] + 1}": {
            "center": {
                "x_in_mm": ARRAY_CONFIG["center"]["x_in_mm"][i],
                "y_in_mm": ARRAY_CONFIG["center"]["y_in_mm"][i],
            },
            "angle_in_deg": ARRAY_CONFIG["angle_in_deg"][j],
            "radius_in_mm": ARRAY_CONFIG["radius_in_mm"],
            "rod_radius_in_mm": config["string"]["copper_rods"]["r_offset_from_center"],
        }
        for i, j in np.ndindex(string_idx.shape)
    }

    special_output["hpges"] = {
        f"{name}": {"rodlength_in_mm": config["string"]["units"]["l"], "baseplate": "xlarge"}
        for name in hpge_names
    }

    special_output["fibers"] = {
        f"S{string+1:02d}{n+1:02d}": {
            "name": f"S{string+1:02d}{n+1:02d}",
            "type": "single_string",
            "geometry": {"tpb": {"thickness_in_nm": 1093}},
            "location": {
                "x": float(
                    ARRAY_CONFIG["center"]["x_in_mm"][string // len(ARRAY_CONFIG["angle_in_deg"])]
                    + ARRAY_CONFIG["radius_in_mm"]
                    * np.cos(
                        np.radians(ARRAY_CONFIG["angle_in_deg"][string % len(ARRAY_CONFIG["angle_in_deg"])])
                    )
                ),
                "y": float(
                    ARRAY_CONFIG["center"]["y_in_mm"][string // len(ARRAY_CONFIG["angle_in_deg"])]
                    + ARRAY_CONFIG["radius_in_mm"]
                    * np.sin(
                        np.radians(ARRAY_CONFIG["angle_in_deg"][string % len(ARRAY_CONFIG["angle_in_deg"])])
                    )
                ),
                "module_num": n,
            },
        }
        for string in string_idx.flatten()
        for n in range(N_FIBERS_PER_STRING)
    }

    special_output["calibration"] = {}

    with Path(output_path).open("w") as f:
        yaml.dump(special_output, f)


def generate_channelmap(
    output_path: str, hpge_data: dict, hpge_names: list, hpge_rawid: list, string_idx: list, spms_data: dict
) -> None:
    """Generate channelmap.json file."""

    channelmap = {}
    for name, rawid in zip(hpge_names, hpge_rawid):
        channelmap[name] = copy.deepcopy(hpge_data)
        channelmap[name]["name"] = name
        channelmap[name]["daq"]["rawid"] = rawid
        channelmap[name]["location"]["string"] = rawid // 100
        channelmap[name]["location"]["position"] = rawid % 100

    for string in string_idx.flatten():
        for n in range(N_FIBERS_PER_STRING):
            name = f"S{string+1:02d}{n+1:02d}T"
            channelmap[name] = copy.deepcopy(spms_data)
            channelmap[name]["name"] = name
            channelmap[name]["location"]["fiber"] = name[:-1]
            channelmap[name]["location"]["position"] = "top"
            channelmap[name]["location"]["barrel"] = string + 1

        for n in range(N_FIBERS_PER_STRING):
            name = f"S{string+1:02d}{n+1:02d}B"
            channelmap[name] = copy.deepcopy(spms_data)
            channelmap[name]["name"] = name
            channelmap[name]["location"]["fiber"] = name[:-1]
            channelmap[name]["location"]["position"] = "bottom"
            channelmap[name]["location"]["barrel"] = string + 1

    with Path(output_path).open("w") as f:
        json.dump(channelmap, f, cls=NpEncoder, indent=4)


def main():
    args = parse_arguments()
    config = load_config(args.input)

    string_idx = np.arange(
        len(ARRAY_CONFIG["center"]["x_in_mm"]) * len(ARRAY_CONFIG["angle_in_deg"])
    ).reshape(len(ARRAY_CONFIG["center"]["x_in_mm"]), len(ARRAY_CONFIG["angle_in_deg"]))

    chm = legendmeta.LegendMetadata().channelmap()
    hpge_data = chm[config["dummy_dets"]["hpge"]]
    hpge_names = np.sort(
        np.concatenate(
            [
                [f"V{i+1:02d}{j+1:02d}" for j in range(config["string"]["units"]["n"])]
                for i in range(string_idx.size)
            ]
        )
    )
    hpge_rawid = np.sort(
        np.concatenate(
            [
                [(i + 1) * 100 + j + 1 for j in range(config["string"]["units"]["n"])]
                for i in range(string_idx.size)
            ]
        )
    )

    spms_data = chm[config["dummy_dets"]["spms"]]

    generate_special_metadata(args.output_special_metadata, config, string_idx, hpge_names)
    generate_channelmap(args.output_channelmap, hpge_data, hpge_names, hpge_rawid, string_idx, spms_data)


if __name__ == "__main__":
    main()
