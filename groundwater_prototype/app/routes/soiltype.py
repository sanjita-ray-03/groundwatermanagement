import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats
import pyodbc

# --------------------------
# 1. Load district boundaries
# --------------------------
districts_path = "groundwater_prototype/app/data/gadm40_IND_2.shp"
districts = gpd.read_file(districts_path)
print("✅ Districts loaded:", len(districts))

# --------------------------
# 2. Soil raster (MU_GLOBAL codes)
# --------------------------
soil_raster = "groundwater_prototype/app/data/HWSD2.bil"

# --------------------------
# 3. Zonal stats → dominant MU_GLOBAL per district
# --------------------------
stats = zonal_stats(
    districts,
    soil_raster,
    stats="majority",
    categorical=False,
    geojson_out=False,
    nodata=-9999
)

districts["MU_GLOBAL"] = [s["majority"] if s else None for s in stats]

# --------------------------
# 4. Connect to HWSD2.mdb
# --------------------------
mdb_path = "groundwater_prototype/app/data/HWSD2.mdb"
conn_str = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    rf"DBQ={mdb_path};"
)
conn = pyodbc.connect(conn_str)

# --------------------------
# 5. Load ALL soil layers (with depths)
# --------------------------
sql = """
SELECT l.HWSD2_SMU_ID AS MU_GLOBAL,
       l.TOPDEP, l.BOTDEP,
       l.SAND, l.CLAY, l.SILT
FROM HWSD2_LAYERS l
"""
layers = pd.read_sql(sql, conn)
conn.close()

print("✅ Soil layers loaded:", layers.shape)

# --------------------------
# 6. Compute weighted averages by MU_GLOBAL
# --------------------------
def weighted_avg(group):
    group = group.dropna(subset=["TOPDEP", "BOTDEP", "SAND", "CLAY", "SILT"])
    if group.empty:
        return pd.Series({"SAND_TOP": None, "CLAY_TOP": None, "SILT_TOP": None})
    group["thickness"] = group["BOTDEP"] - group["TOPDEP"]
    total_thickness = group["thickness"].sum()
    return pd.Series({
        "SAND_TOP": (group["SAND"] * group["thickness"]).sum() / total_thickness,
        "CLAY_TOP": (group["CLAY"] * group["thickness"]).sum() / total_thickness,
        "SILT_TOP": (group["SILT"] * group["thickness"]).sum() / total_thickness,
    })

soil_attr = layers.groupby("MU_GLOBAL").apply(weighted_avg).reset_index()

print("✅ Weighted soil attributes computed:", soil_attr.shape)

# --------------------------
# 7. Merge with districts
# --------------------------
result = districts.merge(soil_attr, on="MU_GLOBAL", how="left")

# --------------------------
# 8. Save output
# --------------------------
output_csv = "groundwater_prototype/app/data/district_soil_types_weighted.csv"
result[["NAME_1", "NAME_2", "MU_GLOBAL", "SAND_TOP", "CLAY_TOP", "SILT_TOP"]].to_csv(output_csv, index=False)

print(f"✅ District-wise weighted soil types saved to: {output_csv}")
