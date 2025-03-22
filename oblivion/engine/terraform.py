import subprocess
import json

TARGET_DIR = "terraform"


def output(target_dir=None, var_name=None):
    if not target_dir:
        target_dir = TARGET_DIR
    try:
        command = ["terraform", f"-chdir={target_dir}", "output", "-json"],
        if var_name:
            cmd.append(var_name)
        result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
        )
        outputs = json.loads(result.stdout)
        return outputs
    except subprocess.CalledProcessError as e:
        print(f"Error calling terraform: {e}")

