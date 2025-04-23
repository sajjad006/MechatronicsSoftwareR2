import asyncio
import pygame
import random
import platform
from math import sin, cos, radians

# Initialize Pygame
pygame.init()

class Drone:
    def __init__(self, x, y):
        self.x = x  # X coordinate
        self.altitude = y  # Altitude (inverted for Pygame Y-axis)
        self.speed = 5  # Pixels per frame
        self.gyro_x = 0  # Roll
        self.gyro_y = 0  # Pitch
        self.gyro_z = 0  # Yaw
        self.angle = 0  # Orientation in degrees

class Environment:
    def __init__(self):
        self.wind_speed = random.uniform(-2, 2)  # Random wind speed
        self.dust_speed = random.uniform(0, 1)  # Dust effect on movement

class DroneSimulator:
    def __init__(self, width=800, height=600, fps=60):
        # Screen dimensions and setup
        self.WIDTH = width
        self.HEIGHT = height
        self.FPS = fps
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Drone Simulation")

        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.GRAY = (100, 100, 100)

        # Font for displaying parameters
        self.font = pygame.font.SysFont('arial', 20)

        # Initialize drone and environment
        self.drone = None
        self.env = None
        self.clock = pygame.time.Clock()

        # Load drone image
        self.drone_image = self.create_drone_image()

    def create_drone_image(self):
        try:
            image = pygame.image.load("sajjad/drone_image.png").convert_alpha()
            image = pygame.transform.scale(image, (80, 80))
        except pygame.error:
            # Fallback if image loading fails
            image = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(image, self.BLUE, (40, 40), 40)
        return image

    def setup(self):
        self.drone = Drone(0, 0)
        self.env = Environment()

    def update(self, data):
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
        
        telemetry = data['telemetry']

        # parse this string and update it to drone object of self class 'X-5-Y-70-BAT-97.8711990153748-GYR-[0.22222222222222224, 0.0, 0.0]-WIND-35.67899767600586-DUST-32.57303873773703-SENS-GREEN'\
        # Example: telemetry = "X-5-Y-70-BAT-97.8711990153748-GYR-[0.22222222222222224, 0.0, 0.0]-WIND-35.67899767600586-DUST-32.57303873773703-SENS-GREEN"
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
        telemetry_dict["SENS"] = telemetry[-1]  # Sensor status
        
        # Simulate drone movement
        self.drone.speed = 5
        self.drone.x = telemetry_dict.get("X", self.drone.x)
        self.drone.altitude = telemetry_dict.get("Y", self.drone.altitude)
        self.drone.gyro_x = telemetry_dict.get("GYR", [0, 0, 0])[0]
        self.drone.gyro_y = telemetry_dict.get("GYR", [0, 0, 0])[1]
        self.drone.gyro_z = telemetry_dict.get("GYR", [0, 0, 0])[2]

        # Boundary checks
        self.drone.x = max(0, min(self.drone.x, self.WIDTH))
        self.drone.altitude = max(50, min(self.drone.altitude, self.HEIGHT - 50))
        self.drone.angle += self.drone.gyro_z * 0.1
        self.drone.gyro_z *= 0.9
        self.drone.gyro_x *= 0.9
        self.drone.gyro_y *= 0.9

        # Draw skybox gradient (sky -> horizon -> ground)
        for y in range(self.HEIGHT):
            blend = y / self.HEIGHT
            r = int(30 * (1 - blend) + 10 * blend)
            g = int(120 * (1 - blend) + 80 * blend)
            b = int(200 * (1 - blend) + 20 * blend)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.WIDTH, y))

        # Draw drone
        rotated_drone = pygame.transform.rotate(self.drone_image, self.drone.angle)
        drone_rect = rotated_drone.get_rect(center=(self.drone.x, self.drone.altitude))
        self.screen.blit(rotated_drone, drone_rect)

        # Draw dust particles
        for _ in range(10):
            dust_x = random.randint(0, self.WIDTH)
            dust_y = random.randint(0, self.HEIGHT)
            pygame.draw.circle(self.screen, self.WHITE, (dust_x, dust_y), 1)

        # HUD Box
        hud_rect = pygame.Rect(10, 10, 250, 220)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), hud_rect)
        pygame.draw.rect(self.screen, self.BLUE, hud_rect, 2)

        # Battery simulation and visual bar
        battery_level = max(0, 100 - pygame.time.get_ticks() / 1000)
        pygame.draw.rect(self.screen, self.GRAY, (20, 190, 200, 20))  # background
        pygame.draw.rect(self.screen, self.RED, (20, 190, 2 * battery_level, 20))  # level
        battery_text = self.font.render(f"Battery: {battery_level:.1f}%", True, self.WHITE)
        self.screen.blit(battery_text, (20, 165))

        # Telemetry text
        params = [
            f"X: {self.drone.x:.1f}",
            f"Altitude: {self.HEIGHT - self.drone.altitude:.1f}",
            f"Speed: {self.drone.speed:.1f}",
            f"Gyro X (Roll): {self.drone.gyro_x:.1f}",
            f"Gyro Y (Pitch): {self.drone.gyro_y:.1f}",
            f"Gyro Z (Yaw): {self.drone.gyro_z:.1f}",
            f"Wind: {self.env.wind_speed:.1f}",
            f"Dust: {self.env.dust_speed:.1f}",
        ]
        for i, text in enumerate(params):
            label = self.font.render(text, True, self.WHITE)
            self.screen.blit(label, (20, 20 + i * 20))

        pygame.display.flip()
        self.clock.tick(self.FPS)
        return True

    async def run(self):
        self.setup()
        running = True
        while running:
            running = self.update({"telemetry": "X-0-Y-0-BAT-100-GYR-[0.0, 0.0, 0.0]-WIND-0.0-DUST-0.0-SENS-GREEN"})
            await asyncio.sleep(1.0 / self.FPS)

if platform.system() == "Emscripten":
    simulator = DroneSimulator()
    asyncio.ensure_future(simulator.run())
else:
    if __name__ == "__main__":
        simulator = DroneSimulator()
        asyncio.run(simulator.run())