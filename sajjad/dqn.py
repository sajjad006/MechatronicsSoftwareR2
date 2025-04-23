import gym
from gym import spaces
import numpy as np
import asyncio
import threading
from drone_simulator.client import DroneClient
from stable_baselines3 import PPO
import time

class DroneSimEnv(gym.Env):
    def __init__(self):
        super(DroneSimEnv, self).__init__()

        # Speed (0-5), Altitude (-100 to +100), Movement (0=fwd, 1=rev)
        self.action_space = spaces.MultiDiscrete([6, 201, 2])  # Altitude -100 to 100 scaled to 0–200

        # Observation: [speed, altitude, battery, sensor_status]
        self.observation_space = spaces.Box(
            low=np.array([0, -500, 0, 0]),
            high=np.array([5, 1000, 100, 2]),
            dtype=np.float32
        )

        self.client = DroneClient()
        self.websocket = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.client.connect())

    def reset(self):
        # Restart the server/client connection if needed or reinitialize state
        # For simplicity, simulate reset by reconnecting if crashed
        self.client.telemetry = None
        self.client.metrics = None
        self.client.command_count = 0
        self.client.start_time = time.time()
        return self._get_obs()

    def _get_obs(self):
        # Parse the telemetry string
        if not self.client.telemetry:
            return np.array([0, 0, 100, 2], dtype=np.float32)

        try:
            # Example telemetry format: "pos-x-pos-y-altitude-battery-status"
            parts = self.client.telemetry.split("-")
            altitude = int(parts[3])
            battery = float(parts[4].replace('%',''))
            status = parts[-1].strip().upper()
            sensor_status = {"RED": 0, "YELLOW": 1, "GREEN": 2}.get(status, 2)

            return np.array([self.client.speed, altitude, battery, sensor_status], dtype=np.float32)
        except Exception as e:
            print(f"Telemetry parse error: {e}")
            return np.array([0, 0, 100, 2], dtype=np.float32)

    def step(self, action):
        speed_idx, alt_idx, movement_idx = action
        speed = speed_idx
        altitude = alt_idx - 100  # Convert 0–200 to -100 to +100
        movement = "fwd" if movement_idx == 0 else "rev"

        data = self.loop.run_until_complete(
            self.client.send_command(self.client.websocket, speed, altitude, movement)
        )

        done = False
        reward = 0

        if data is None:
            done = True
            reward = -100
        else:
            metrics = self.client.metrics
            reward = 1 + int(metrics.get("total_distance", 0)) / 100

        obs = self._get_obs()
        return obs, reward, done, {}

env = DroneSimEnv()
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=100_000)
model.save("drone_autopilot_rl")
