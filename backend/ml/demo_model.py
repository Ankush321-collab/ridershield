class DemoRiskModel:
    def predict(self, frame):
        predictions = []
        for _, row in frame.iterrows():
            score = (
                float(row["zone_flood_risk"]) * 0.003
                + float(row["zone_traffic_risk"]) * 0.0025
                + float(row["zone_store_risk"]) * 0.0015
                + float(row["forecast_rainfall"]) * 0.008
                + float(row["forecast_aqi"]) / 1000
                + (0.08 if int(row["hour"]) >= 18 else 0.0)
                + (0.05 if bool(row["is_monsoon"]) else 0.0)
                - min(float(row["rider_tenure_days"]) / 3650, 0.05)
            )
            predictions.append(max(0.05, min(0.95, score)))
        return predictions
