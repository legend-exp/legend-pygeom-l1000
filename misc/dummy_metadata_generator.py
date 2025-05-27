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
    argparser.add_argument(
        "-d",
        "--dets_from_metadata",
        type=str,
        help="Use detector from metadata as template. Should be in dict form, e.g., {'hpge': 'V000000A', ...}",
        default="",
    )
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


def calculate_and_place_pmts(channelmap: dict, pmts_meta: dict, pmts_pos: dict) -> None:
    # Floor PMTs are pretty trivial to place
    rawid = pmts_meta["daq"]["rawid"]
    for row in pmts_pos["floor"].values():
        row_index = row["id"]
        pmts_in_row = row["n"]
        radius = row["r"]

        for i in range(pmts_in_row):
            name = f"PMT0{row_index}{i+1:02d}"
            x = radius * np.cos(np.radians(360 / pmts_in_row * i))
            y = radius * np.sin(np.radians(360 / pmts_in_row * i))
            z = 0.0

            channelmap[name] = copy.deepcopy(pmts_meta)
            channelmap[name]["daq"]["rawid"] = rawid
            rawid += 1
            channelmap[name]["name"] = name
            channelmap[name]["location"] = {"name": "floor", "x": x, "y": y, "z": z}
            channelmap[name]["location"]["direction"] = {"nx": 0, "ny": 0, "nz": 1}

    # The wall PMTs require some polygon math
    faces = pmts_pos["tyvek"]["faces"]
    # Geant4 uses r as inscribe radius, but we need the circumradius
    radius = pmts_pos["tyvek"]["r"] / np.cos(np.pi / faces)

    # Compute vertices of the polygon
    vertices = [
        (radius * np.cos(2 * np.pi * i / faces), radius * np.sin(2 * np.pi * i / faces)) for i in range(faces)
    ]
    for row in pmts_pos["wall"].values():
        row_index = row["id"]
        pmts_in_row = row["n"]
        z = row["z"]

        # Distribute detectors evenly across faces
        detectors_per_face = pmts_in_row // faces  # How many detectors per face (integer division)
        extra_detectors = pmts_in_row % faces  # Remaining detectors to distribute
        pmt_id = 0

        # Now some crazy algorithm to distribute the extra detectors homogeneously
        # Invented by Lorenz Gebler
        m = extra_detectors  # short variable names to make the code more readable
        n = faces
        # Try splitting the polygon faces in repetitive cells
        scl = n // m  # shortest cell length
        sc = [0] * scl  # shortest cell
        sc[0] = 1  # Set the first element to 1
        extra_detectors_per_face = sc * m
        # In case we cannot split the polygon in equal cells
        if n % m != 0:
            k = n - len(extra_detectors_per_face)
            sclk = m // k
            sck = sc * sclk + [0]
            extra_detectors_per_face = sck * k + sc * (m - k)
        # We need to truncate the list as somehow it creates too big cells
        extra_detectors_per_face = extra_detectors_per_face[:n]

        for i in range(faces):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % faces]  # Wrap around

            # Compute face normal for PMT orientation
            edge_x = x2 - x1
            edge_y = y2 - y1
            normal_x = edge_y
            normal_y = -edge_x

            # Normalize the normal vector
            norm_length = np.sqrt(normal_x**2 + normal_y**2)
            normal_x /= norm_length
            normal_y /= norm_length
            normal_z = 0

            # Compute the number of detectors on this face, permutate the extras by the row index
            num_detectors_this_face = detectors_per_face + extra_detectors_per_face[(i + row_index) % faces]

            for j in range(num_detectors_this_face):
                name = f"PMT{row_index+10}{pmt_id+1:02d}"
                pmt_id += 1
                # Interpolate position along the face
                t = (j + 1) / (num_detectors_this_face + 1)  # Normalized position (avoid exact endpoints)
                x = x1 * (1 - t) + x2 * t
                y = y1 * (1 - t) + y2 * t

                channelmap[name] = copy.deepcopy(pmts_meta)
                channelmap[name]["daq"]["rawid"] = rawid
                rawid += 1
                channelmap[name]["name"] = name
                channelmap[name]["location"] = {"name": "wall", "x": x, "y": y, "z": z}
                channelmap[name]["location"]["direction"] = {"nx": normal_x, "ny": normal_y, "nz": normal_z}

        # Check that all PMTs are placed. We do not totally trust the distribution algorithm
        if pmt_id != pmts_in_row:
            msg = (
                "Not all PMTs were placed. Check the distribution algorithm. PMTs placed: "
                + str(pmt_id)
                + " PMTs to place: "
                + str(pmts_in_row)
            )
            raise ValueError(msg)


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

    special_output["watertank_instrumentation"] = {
        "tyvek": {
            "r": config["pmts"]["tyvek"]["r"],
            "faces": config["pmts"]["tyvek"]["faces"],
        },
    }

    special_output["detail"] = config["detail"]

    with Path(output_path).open("w") as f:
        yaml.dump(special_output, f)


def generate_channelmap(
    output_path: str,
    hpge_data: dict,
    hpge_names: list,
    hpge_rawid: list,
    string_idx: list,
    spms_data: dict,
    pmts_meta: dict,
    pmts_pos: dict,
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

    calculate_and_place_pmts(channelmap, pmts_meta, pmts_pos)

    with Path(output_path).open("w") as f:
        json.dump(channelmap, f, cls=NpEncoder, indent=4)


def main():
    args = parse_arguments()
    config = load_config(args.input)
    if args.dets_from_metadata != "":
        json_acceptable_string = args.dets_from_metadata.replace("'", '"')
        det_names_from_metadata = json.loads(json_acceptable_string)

    string_idx = np.arange(
        len(ARRAY_CONFIG["center"]["x_in_mm"]) * len(ARRAY_CONFIG["angle_in_deg"])
    ).reshape(len(ARRAY_CONFIG["center"]["x_in_mm"]), len(ARRAY_CONFIG["angle_in_deg"]))

    hpge_data, spms_data, pmts_meta = None, None, None

    if legendmeta.LegendMetadata() and args.dets_from_metadata:
        timestamp = "20230125T212014Z"
        chm = legendmeta.LegendMetadata().channelmap(on=timestamp)
        if "hpge" in det_names_from_metadata:
            hpge_data = chm[det_names_from_metadata["hpge"]]
        if "spms" in det_names_from_metadata:
            spms_data = chm[det_names_from_metadata["spms"]]
        if "pmts" in det_names_from_metadata:
            pmts_meta = chm[det_names_from_metadata["pmts"]]

    if not hpge_data:
        hpge_data = config["template_dets"]["hpge"]
    if not spms_data:
        spms_data = config["template_dets"]["spms"]
    if not pmts_meta:
        pmts_meta = config["template_dets"]["pmts"]

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

    pmts_pos = config["pmts_pos"]

    generate_special_metadata(args.output_special_metadata, config, string_idx, hpge_names)
    generate_channelmap(
        args.output_channelmap, hpge_data, hpge_names, hpge_rawid, string_idx, spms_data, pmts_meta, pmts_pos
    )


if __name__ == "__main__":
    main()
