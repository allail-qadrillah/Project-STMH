"""Order-independent PCG64 streams identified by (role ID, one-based window)."""

import copy

import numpy as np


def make_stream(config, role, window=0):
    project = config["project"]
    key = (project["stream_ids"][role], window)
    sequence = np.random.SeedSequence(project["master_seed"], spawn_key=key)
    rng = np.random.Generator(np.random.PCG64(sequence))
    record = {"role": role, "window": window, "master_seed": project["master_seed"],
              "bit_generator": project["rng"], "spawn_key": list(key),
              "pool_size": sequence.pool_size, "initial_state": copy.deepcopy(rng.bit_generator.state)}
    return rng, record
