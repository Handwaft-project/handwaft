class Smoother:
    """
    Smooths out jittery values over time using an exponential moving average.
    Call .update() every frame with the new raw value; it returns a smoothed value.
    """

    def __init__(self, smoothing_factor=0.3):
        # smoothing_factor: how much weight the NEW value gets each frame.
        # Lower = smoother but slower to react. Higher = snappier but jitterier.
        self.smoothing_factor = smoothing_factor
        self.smoothed_values = {}  # stores the last smoothed value per key

    def update(self, key, new_value):
        if key not in self.smoothed_values:
            # First time seeing this key — just use the raw value to start
            self.smoothed_values[key] = new_value
        else:
            old_value = self.smoothed_values[key]
            self.smoothed_values[key] = (
                self.smoothing_factor * new_value +
                (1 - self.smoothing_factor) * old_value
            )
        return self.smoothed_values[key]

    def update_dict(self, params_dict):
        """
        Convenience method: takes a dict like {'curl': 0.5, 'tilt': 0.1, ...}
        and returns a new dict with every value smoothed.
        """
        return {
            key: self.update(key, value)
            for key, value in params_dict.items()
        }