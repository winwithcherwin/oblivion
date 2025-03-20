import subprocess
import json

TARGET_DIR = "terraform"


def output(target_dir=None, var_name=None):
    if not target_dir:
        target_dir = TARGET_DIR
    try:
        result = subprocess.run(
                ["terraform", f"-chdir={target_dir}", "output", "-json"],
                check=True,
                capture_output=True,
                text=True,
        )
        outputs = json.loads(result.stdout)
        if not var_name:
            return outputs
        return outputs[var_name]["value"]
    except subprocess.CalledProcessError as e:
        print(f"Error calling terraform: {e}")
    except KeyError:
        print(f"Variable '{var_name}' not found in output")

