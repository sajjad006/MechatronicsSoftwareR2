# Drone Simulator

## Work Done By Me

 - `client.py`
	 Updated the `interactive_control()` function to dynamically send commands to the drone server y analyzing the telemetry data being received after every iteration.

	Achieved a maximum distance of 135m in about 135 iterations. 

- `simulator.py`
	Created a virtual drone simulator using `pygame` module and the same is populated from the drone client using real time telemetry data. 

- `dqn.py`
	Tried to implement a Reinforcement Learning model using `stable_baselines`
