"""Download matching 2023 cartographic boundaries and audit exact tract coverage."""

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import shapefile
from tract_data_audit import acquire, check_ids


def main():
    raw = Path("data/raw/tract-study-2026-10-24")
    out = Path("docs/evidence/tract-study")
    name = "cb_2023_04_tract_500k"
    path, receipt = acquire(raw, name + ".zip",
                            f"https://www2.census.gov/geo/tiger/GENZ2023/shp/{name}.zip")
    with zipfile.ZipFile(path) as archive:
        projection = archive.read(name + ".prj").decode()
        if 'GCS_North_American_1983' not in projection:
            raise ValueError("Unexpected boundary coordinate system")
        reader = shapefile.Reader(**{
            suffix: io.BytesIO(archive.read(f"{name}.{suffix}")) for suffix in ("shp", "shx", "dbf")
        })
        features = []
        for row in reader.iterShapeRecords():
            record = row.record.as_dict()
            geometry = row.shape.__geo_interface__
            if geometry["type"] not in {"Polygon", "MultiPolygon"}:
                raise ValueError("Expected tract polygons")
            features.append({"type": "Feature", "id": record["GEOID"],
                             "properties": {"tractfips": record["GEOID"],
                                            "name": record["NAMELSAD"]},
                             "geometry": geometry})
    boundaries = pd.DataFrame({"tractfips": [f["id"] for f in features]})
    check_ids(boundaries, "tractfips")
    data = pd.read_csv(out / "tract_join_audit.csv", dtype={"tractfips": str})
    coverage = data[["tractfips"]].merge(boundaries, how="outer", indicator=True,
                                        validate="one_to_one")
    coverage.to_csv(out / "boundary_join.csv", index=False)
    report = {"source": receipt, "projection": projection,
              "counts": coverage._merge.value_counts().to_dict(),
              "use": "Generalized 1:500,000 display boundaries; not distance or area analysis"}
    (out / "boundary_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # NAD83 longitude/latitude is retained for cartographic display at this coarse scale.
    # Do not use these coordinates for precision spatial measurements.
    (out / "tract_boundaries.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": sorted(features, key=lambda f: f["id"])},
        separators=(",", ":")), encoding="utf-8")
    print(json.dumps(report["counts"]))
    if not coverage._merge.eq("both").all():
        raise ValueError("Boundary mismatch requires review before modeling")


if __name__ == "__main__":
    main()
