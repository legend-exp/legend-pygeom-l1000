from __future__ import annotations

import copy
import json
from pathlib import Path

import legendmeta
import numpy as np
import yaml

# This script is used to generate the special_metadata.yaml and channelmap.yaml files for the LEGEND-1000 geometry.


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
    #    "center": {
    #        "x_in_mm": [0, 550, 110, -440, -550, -110, 440],
    #        "y_in_mm": [0, 190.5, 571.6, 381.1, -190.5, -571.6, -381.1],
    #    },
    #    "radius_in_mm": 220,
    "center": {
        "x_in_mm": [0.0, 533.7, 106.7, -427.0, -533.7, -106.7, 427.0],
        "y_in_mm": [0.0, 184.9, 554.7, 369.8, -184.9, -554.7, -369.8],
    },
    "radius_in_mm": 213.5,
    "angle_in_deg": [0, 60, 120, 180, 240, 300],
}

N_FIBER_MODULES_PER_STRING = 9


def load_config(input_path):
    """Load configuration from a JSON file."""
    with Path(input_path).open() as f:
        return json.load(f)


def calculate_and_place_pmts(channelmap: dict, pmts_meta: dict, pmts_pos: dict) -> None:
    # Floor PMTs are pretty trivial to place
    rawid = 6000
    for row in pmts_pos["floor"].values():
        row_index = row["id"]
        pmts_in_row = row["n"]
        radius = row["r"]

        for i in range(pmts_in_row):
            name = f"PMT0{row_index}{i + 1:02d}"
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
                name = f"PMT{row_index + 10}{pmt_id + 1:02d}"
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


def generate_special_metadata(config: dict, string_idx: list, hpge_names: list, pmts_pos: dict) -> dict:
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
        f"S{string + 1:02d}{n + 1:02d}": {
            "name": f"S{string + 1:02d}{n + 1:02d}",
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
        for n in range(N_FIBER_MODULES_PER_STRING)
    }

    special_output["calibration"] = {}

    special_output["watertank_instrumentation"] = {
        "tyvek": {
            "r": pmts_pos["tyvek"]["r"],
            "faces": pmts_pos["tyvek"]["faces"],
        },
    }

    special_output["detail"] = config["detail"]

    return special_output


def generate_channelmap(
    hpge_data: dict,
    hpge_names: list,
    hpge_rawid: list,
    string_idx: list,
    spms_data: dict,
    pmts_meta: dict,
    pmts_pos: dict,
) -> dict:
    """Generate channelmap.json file."""

    channelmap = {}
    for name, rawid in zip(hpge_names, hpge_rawid, strict=False):
        channelmap[name] = copy.deepcopy(hpge_data)
        channelmap[name]["name"] = name
        channelmap[name]["daq"]["rawid"] = rawid
        channelmap[name]["location"]["string"] = rawid // 100
        channelmap[name]["location"]["position"] = rawid % 100

    rawid = 5000
    for string in string_idx.flatten():
        for n in range(N_FIBER_MODULES_PER_STRING):
            name = f"S{string + 1:02d}{n + 1:02d}T"
            channelmap[name] = copy.deepcopy(spms_data)
            channelmap[name]["name"] = name
            channelmap[name]["location"]["fiber"] = name[:-1]
            channelmap[name]["location"]["position"] = "top"
            channelmap[name]["location"]["barrel"] = string + 1
            channelmap[name]["daq"]["rawid"] = rawid
            rawid += 1

        for n in range(N_FIBER_MODULES_PER_STRING):
            name = f"S{string + 1:02d}{n + 1:02d}B"
            channelmap[name] = copy.deepcopy(spms_data)
            channelmap[name]["name"] = name
            channelmap[name]["location"]["fiber"] = name[:-1]
            channelmap[name]["location"]["position"] = "bottom"
            channelmap[name]["location"]["barrel"] = string + 1
            channelmap[name]["daq"]["rawid"] = rawid
            rawid += 1

    calculate_and_place_pmts(channelmap, pmts_meta, pmts_pos)

    return channelmap


def _convert_numpy_types(obj):
    """Convert numpy types to native Python types recursively."""
    if isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def generate_dummy_metadata(
    input_config: str = "",
    dets_from_metadata: str = "",
) -> tuple[dict, dict]:
    """Generate dummy metadata objects without writing files.

    Returns:
        tuple: (channelmap_dict, special_metadata_dict)
    """
    # Default to configs directory if paths are not provided
    script_dir = Path(__file__).parent
    configs_dir = script_dir / "configs"

    if not input_config:
        input_config = str(configs_dir / "config.json")

    try:
        config = load_config(input_config)
    except FileNotFoundError as e:
        msg = f"Config file not found: {input_config}"
        raise FileNotFoundError(msg) from e
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in config file {input_config}: {e}"
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Error loading config file {input_config}: {e}"
        raise RuntimeError(msg) from e

    if dets_from_metadata != "":
        json_acceptable_string = dets_from_metadata.replace("'", '"')
        det_names_from_metadata = json.loads(json_acceptable_string)

    string_idx = np.arange(
        len(ARRAY_CONFIG["center"]["x_in_mm"]) * len(ARRAY_CONFIG["angle_in_deg"])
    ).reshape(len(ARRAY_CONFIG["center"]["x_in_mm"]), len(ARRAY_CONFIG["angle_in_deg"]))

    hpge_data, spms_data, pmts_meta = None, None, None

    if dets_from_metadata and legendmeta.LegendMetadata():
        timestamp = "20230125T212014Z"
        chm = legendmeta.LegendMetadata().channelmap(on=timestamp)
        if "hpge" in det_names_from_metadata:
            hpge_detector_name = det_names_from_metadata["hpge"]
            hpge_data = chm[hpge_detector_name]

    if not hpge_data:
        hpge_data = config["dummy_dets"]["hpge"]

    spms_data = config["dummy_dets"]["spms"]
    pmts_meta = config["dummy_dets"]["pmts"]

    hpge_names = np.sort(
        np.concatenate(
            [
                [f"V{i + 1:02d}{j + 1:02d}" for j in range(config["string"]["units"]["n"])]
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

    special_metadata = generate_special_metadata(config, string_idx, hpge_names, pmts_pos)
    channelmap = generate_channelmap(
        hpge_data, hpge_names, hpge_rawid, string_idx, spms_data, pmts_meta, pmts_pos
    )

    # Convert numpy types to native Python types to match file serialization behavior
    channelmap = _convert_numpy_types(channelmap)
    special_metadata = _convert_numpy_types(special_metadata)

    return channelmap, special_metadata


def setup_dummy_metadata(
    input_config: str = "",
    output_special_metadata: str = "",
    output_channelmap: str = "",
    dets_from_metadata: str = "",
) -> None:
    """Generate and write dummy metadata files to disk."""
    # Default to configs directory if paths are not provided
    script_dir = Path(__file__).parent
    configs_dir = script_dir / "configs"

    if not output_special_metadata:
        output_special_metadata = str(configs_dir / "special_metadata.yaml")
    if not output_channelmap:
        output_channelmap = str(configs_dir / "channelmap.json")

    # Generate the metadata objects
    channelmap, special_metadata = generate_dummy_metadata(input_config, dets_from_metadata)

    # Write to files
    with Path(output_special_metadata).open("w") as f:
        yaml.dump(special_metadata, f)

    with Path(output_channelmap).open("w") as f:
        json.dump(channelmap, f, cls=NpEncoder, indent=4)
