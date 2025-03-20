#!/usr/bin/env python3

import terraform
import dotenv


def tfvar2dotenv(var_name, env_file=None, terraform_target_dir=None):
    tf_val = str(terraform.output(terraform_target_dir, var_name))
    tf_val = f"\"{tf_val}\""
    env = dotenv.read(env_file)
    current_val = env.get(var_name.upper())
    if current_val == tf_val:
        return
    env[var_name.upper()] = tf_val
    dotenv.write(env, env_file)
    return var_name.upper()

def main(var_name):
    return tfvar2dotenv(var_name)


if __name__ == "__main__":
    import sys
    var_name = main(sys.argv[1])
    if var_name: sys.exit(0)
    sys.exit(1)

