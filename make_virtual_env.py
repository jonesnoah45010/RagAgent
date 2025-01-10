import os
import getpass
import sys

MyUserName = getpass.getuser()
Here = os.getcwd()

dirname = input("Directory name of environment: ")

env = os.path.join(Here, dirname)

default_version = f"{sys.version_info.major}.{sys.version_info.minor}"

in_version = input(f"Enter desired Python version or press Enter to use system default of {default_version}: ")

if in_version == "":
    version = default_version
elif "3." in in_version:
    version = in_version
else:
    version = default_version

# Create directory for the environment
os.makedirs(env, exist_ok=True)

# Initialize the virtual environment
os.system(f"python{version} -m venv {env}")

# Instructions for activating the virtual environment
if os.name == 'posix':  # macOS and Linux
    activate_cmd = f"source {env}/bin/activate"
else:  # Windows
    activate_cmd = f"{env}\\Scripts\\activate"

print("Run the command below to start the new virtual environment:")
print(activate_cmd)
