telemetry = "X-5-Y-70-BAT-97.8711990153748-GYR-[0.22222222222222224, 0.0, 0.0]-WIND-35.67899767600586-DUST-32.57303873773703-SENS-GREEN"

telemetry = telemetry.split('-')
telemetry_dict = {}
for i in range(0, len(telemetry), 2):
    key = telemetry[i]
    value = telemetry[i + 1]
    if key == "GYR":
        value = list(map(float, value.strip('[]').split(',')))
    elif key in ["X", "Y", "BAT", "WIND", "DUST"]:
        value = float(value)
    telemetry_dict[key] = value
telemetry_dict["SENS"] = telemetry[-1]
print(telemetry_dict)
print(telemetry_dict.get("X", 0))