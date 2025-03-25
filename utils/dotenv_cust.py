ENV_FILE = ".env"


def loads(envstr):
    env = {}
    for line in envstr:
        if "=" in line and not line.strip().startswith("#"):
            key, val = line.strip().split("=", 1)
            env[key] = val
    return env

def dumps(env):
    return "\n".join(["f{key}={val}" for key, val in env.items()])

def read(env_file=None):
    if not env_file:
        env_file = ENV_FILE
    with open(env_file) as envstr:
        return loads(envstr)

def write(env, env_file=None):
    if not env_file:
        env_file = ENV_FILE
    with open(env_file, "w") as f:
        for key, val in env.items():
            f.write(f"{key}={val}\n")

