# run_app.py
"""
Wrapper script to always launch the Streamlit app on a free port.
Usage:
    python run_app.py
"""
import os
import subprocess
from utils.port_utils import find_free_port


def main():
    # Determine a free port (default fallback 8501)
    port = find_free_port(int(os.environ.get("PORT", 8501)))
    # Address to bind (default 0.0.0.0)
    address = os.environ.get("ADDRESS", "0.0.0.0")

    # Prepare environment for Streamlit
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_ADDRESS"] = address

    # Launch Streamlit with the computed port and address
    subprocess.run(["streamlit", "run", "app.py"], env=env)


if __name__ == "__main__":
    main()
