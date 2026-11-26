"""Constraint-dominant fitness, without extra objectives or tie breakers."""


def calculate_fitness(metrics, config, mode):
    if mode not in ("static", "dynamic"):
        raise ValueError("Fitness mode must be static or dynamic")
    if metrics["status"] == "INFEASIBLE":
        return 1 / (1 + metrics["normalized_cpu_violation"])
    if metrics["status"] != "FEASIBLE":
        raise ValueError("Unknown placement status")
    cost = metrics["active_pm_count"] / config["infrastructure"]["available_pm_count"]
    if mode == "dynamic":
        if metrics["normalized_migration_cost"] is None:
            raise ValueError("Dynamic fitness requires a reference placement")
        fit = config["fitness"]
        cost = fit["server_weight"] * cost + fit["migration_weight"] * metrics["normalized_migration_cost"]
    return 1 + 1 / (1 + cost)
