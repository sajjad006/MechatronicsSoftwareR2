"""Test client for drone simulator WebSocket server."""
# filepath: /Users/trishit_debsharma/Documents/Code/Mechatronic/software_round2/drone_simulator/client.py
import asyncio
import json
import sys
import websockets
import time
from typing import Dict, Any, Optional
from drone_simulator.logging_config import get_logger
from simulator import DroneSimulator
import argparse

logger = get_logger("client")

class DroneClient:
    """WebSocket client for testing the drone simulator."""
    
    def __init__(self, uri: str = "ws://localhost:8765", simulator=None) -> None:
        """Initialize the client."""
        self.uri = uri
        self.connection_id = None
        self.telemetry = None
        self.metrics = None
        self.start_time = time.time()
        self.command_count = 0
        self.simulator = simulator if simulator else None
        logger.info(f"Drone client initialized with server URI: {uri}")
    
    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        logger.info(f"Attempting to connect to {self.uri}")
        print(f"Attempting to connect to {self.uri}...")
        print("Make sure the server is running (python run_server.py)")
        
        try:
            # Configure ping_interval and ping_timeout properly
            logger.debug("Establishing WebSocket connection")
            async with websockets.connect(
                self.uri, 
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10,   # Wait 10 seconds for pong response
                close_timeout=5    # Wait 5 seconds for close to complete
            ) as websocket:
                # Receive welcome message
                response = await websocket.recv()
                data = json.loads(response)
                self.connection_id = data.get("connection_id")
                logger.info(f"Connected successfully with ID: {self.connection_id}")
                logger.info(f"Server message: {data['message']}")
                
                print(f"Connected with ID: {self.connection_id}")
                print(f"Server says: {data['message']}")
                
                # Interactive control of the drone
                # await self.interactive_control(websocket)
                await self.interactive_simulation_control(websocket)

                
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connection closed abnormally: {e}")
            print("\nThe connection was closed unexpectedly. Possible reasons:")
            print("- Server crashed or restarted")
            print("- Network issues causing ping timeout")
            print("- Server closed the connection due to inactivity")
            
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Connection closed normally by the server")
            
        except ConnectionRefusedError:
            logger.error(f"Connection refused. Is the server running at {self.uri}?")
            print("\nTroubleshooting steps:")
            print("1. Make sure the server is running: python run_server.py")
            print("2. Check if the server is listening on the correct address")
            print("3. Check if there are any firewalls blocking the connection")
            print("4. Try 'ws://127.0.0.1:8765' instead of 'ws://localhost:8765'")
            
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            print(f"\nConnection error: {e}")
        
        finally:
            # Log session summary
            session_duration = time.time() - self.start_time
            logger.info(f"Session summary - "
                      f"Duration: {session_duration:.1f}s, "
                      f"Commands sent: {self.command_count}, "
                      f"Connection ID: {self.connection_id}")
    
    async def send_command(self, websocket, speed: int, altitude: int, movement: str) -> Optional[Dict[str, Any]]:
        """Send a command to the drone server and return the response."""
        try:
            data = {
                "speed": speed,
                "altitude": altitude,
                "movement": movement
            }
            self.command_count += 1
            logger.info(f"Sending command #{self.command_count}: {data}")
            
            await websocket.send(json.dumps(data))
            
            response = await websocket.recv()
            response_data = json.loads(response)
            
            # Check if the drone has crashed
            if response_data.get("status") == "crashed":
                crash_message = response_data.get('message', 'Unknown crash')
                logger.warning(f"Drone crashed: {crash_message}")
                
                print(f"\n*** DRONE CRASHED: {crash_message} ***")
                print("Connection will be terminated.")
                
                # Update metrics one last time
                if "metrics" in response_data:
                    self.metrics = response_data["metrics"]
                    logger.info(f"Final metrics: {self.metrics}")
                
                # Show final telemetry
                if "final_telemetry" in response_data:
                    self.telemetry = response_data["final_telemetry"]
                    logger.info(f"Final telemetry: {self.telemetry}")
                    self.display_status()
                
                print("\nFinal Flight Statistics:")
                print(f"Total distance traveled: {self.metrics.get('total_distance', 0)}")
                print(f"Successful flight iterations: {self.metrics.get('iterations', 0)}")
                print("\nConnection terminated due to crash")
                
                # Return None to indicate a crash occurred
                return None
            
            logger.debug(f"Received response: {response_data}")
            return response_data
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"Connection closed while sending command: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Error sending command: {e}", exc_info=True)
            return None

    async def interactive_simulation_control(self, websocket) -> None:
        """Interactively control the drone through the console."""
        logger.info("Starting custom control")

        try:
            prev_sensor = "GREEN"
            while True:
                # sensor status, battery, 
                if self.telemetry:
                    sensor_status=self.telemetry.split('-')[-1]
                    current_altitude=int(self.telemetry.split('-')[3])
                    iteration = int(self.metrics['iterations'])
                else:
                    iteration=0
                    current_altitude=0
                    sensor_status="GREEN"
                # battery=self.telemetry['battery']
                # altitude = max(current_altitude+1, 50)

                if iteration==0:
                    altitude = 70
                else:
                    altitude = (-1)**(iteration+1)

                if (sensor_status == "YELLOW" or sensor_status == "RED") and prev_sensor != sensor_status:
                    altitude=-(current_altitude-2)
                
                prev_sensor = sensor_status
               
                try:
                    speed = 1
                    movement = 'fwd'
                    
                    # Send command
                    data = await self.send_command(websocket, speed, altitude, movement)
                    if data:
                        self.update_state(data)

                        if self.simulator:
                            self.simulator.update(data)

                        self.display_status()
                    elif data is None:  # Crash occurred
                        break
                        
                except ValueError as e:
                    print(f"Invalid input format: {e}")
                    print("Use format: speed,altitude,movement (e.g., '2,0,fwd')")
                    logger.warning(f"Invalid input format: {e}")
                
        except KeyboardInterrupt:
            logger.info("User interrupted the client with Ctrl+C")
            print("\nExiting...")
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection to server was closed")
            print("\nConnection to server was closed")

    async def interactive_control(self, websocket) -> None:
        """Interactively control the drone through the console."""
        logger.info("Starting custom control")

        try:
            prev_sensor = "GREEN"
            while True:
                # sensor status, battery, 
                if self.telemetry:
                    sensor_status=self.telemetry.split('-')[-1]
                    current_altitude=int(self.telemetry.split('-')[3])
                    iteration = int(self.metrics['iterations'])
                else:
                    iteration=0
                    current_altitude=0
                    sensor_status="GREEN"
                # battery=self.telemetry['battery']
                # altitude = max(current_altitude+1, 50)

                if iteration==0:
                    altitude = 50
                else:
                    altitude = (-1)**(iteration+1)

                if (sensor_status == "YELLOW" or sensor_status == "RED") and prev_sensor != sensor_status:
                    altitude=-(current_altitude-2)
                
                prev_sensor = sensor_status
               
                try:
                    speed = 1
                    # altitude = 50
                    movement = 'fwd'
                    
                    # Send command
                    data = await self.send_command(websocket, speed, altitude, movement)
                    if data:
                        self.update_state(data)
                        # simulator.update(data)
                        self.display_status()
                    elif data is None:  # Crash occurred
                        break
                        
                except ValueError as e:
                    print(f"Invalid input format: {e}")
                    print("Use format: speed,altitude,movement (e.g., '2,0,fwd')")
                    logger.warning(f"Invalid input format: {e}")
                
        except KeyboardInterrupt:
            logger.info("User interrupted the client with Ctrl+C")
            print("\nExiting...")
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection to server was closed")
            print("\nConnection to server was closed")
     
    def update_state(self, data: Dict[str, Any]) -> None:
        """Update client state with server response."""
        if data["status"] == "success":
            self.telemetry = data["telemetry"]
            self.metrics = data["metrics"]
            logger.debug(f"Updated state with telemetry: {self.telemetry}")
            logger.debug(f"Updated state with metrics: {self.metrics}")
        else:
            logger.warning(f"Error response: {data['message']}")
            print(f"\nError: {data['message']}")
            if "metrics" in data:
                self.metrics = data["metrics"]
    
    def display_status(self) -> None:
        """Display current telemetry and metrics."""
        if not self.telemetry:
            print("No telemetry data available yet")
            return
            
        print("\n----- Telemetry -----")
        # print(f"Position: ({self.telemetry['x_position']}, {self.telemetry['y_position']})")
        # print(f"Battery: {self.telemetry['battery']:.1f}%")
        # print(f"Wind Speed: {self.telemetry['wind_speed']}%")
        # print(f"Dust Level: {self.telemetry['dust_level']}%")
        # print(f"Sensor Status: {self.telemetry['sensor_status']}")
        # print(f"Gyroscope: {self.telemetry['gyroscope']}")
        print(self.telemetry)
        
        print("\n----- Metrics -----")
        print(f"Successful Iterations: {self.metrics['iterations']}")
        print(f"Total Distance: {self.metrics['total_distance']}")
        
        # logger.info(f"Status displayed - Position: ({self.telemetry['x_position']}, {self.telemetry['y_position']}), "
        #            f"Battery: {self.telemetry['battery']:.1f}%, "
        #            f"Iterations: {self.metrics['iterations']}, "
        #            f"Distance: {self.metrics['total_distance']}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Drone Client")
    parser.add_argument('--uri', type=str, default="ws://localhost:8765", help="WebSocket server URI")
    parser.add_argument('--simulator', action='store_true', help="Run the simulator")
    args = parser.parse_args()

    async def main_async():
        simulator = None
        if args.simulator:
            simulator = DroneSimulator()
            # Start simulator as a background task
            asyncio.create_task(simulator.run())
            print("Simulator started")

        logger.info(f"Starting Drone Client with server URI: {args.uri}")
        client = DroneClient(args.uri, simulator=simulator)
        await client.connect()

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
        print("\nClient stopped by user")

if __name__ == "__main__":
    main()