# /// script
# requires-python = ">=3.10,<3.15"
#
# [tool.marimo-studio]
# default = "animation"
# runtimes = ["server"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium", app_title="Simulating an epidemic")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, np, plt


@app.cell(hide_code=True)
def introduction(mo):
    mo.md(r"""
    # Simulating an epidemic

    Two hundred people wander around a city. Each is susceptible, infectious,
    or recovered. An infectious person infects each susceptible neighbour
    within the infection radius at a fixed rate per day and recovers after
    five days. People who keep their distance push away from their ten
    nearest neighbours.

    The classic SIR model averages this into three differential equations.
    Simulating every person keeps what the averages hide: who infected whom,
    and how a local habit bends the curve of the whole city.

    Adapted from 3Blue1Brown's
    [*Simulating an epidemic*](https://www.youtube.com/watch?v=gxAaO2rsdIs)
    and its `SIRSimulation` in
    [3b1b/videos](https://github.com/3b1b/videos/blob/master/_2020/sir.py).
    """)
    return


@app.cell(hide_code=True)
def controls(mo):
    distancing = mo.ui.slider(
        0,
        0.75,
        step=0.25,
        value=0,
        label="Share keeping their distance",
        show_value=True,
    )
    mo.hstack([distancing], justify="start")
    return (distancing,)


@app.cell
def city():
    population = 200
    city_size = 7
    infection_radius = 0.5
    infection_rate = 0.2  # per day, per infectious neighbour
    infectious_days = 5
    days = 24
    # A static export keeps the samples of every distancing level, so the city
    # records positions twice a day and the scene draws curves between them.
    samples_per_day = 2
    return (
        city_size,
        days,
        infection_radius,
        infection_rate,
        infectious_days,
        population,
        samples_per_day,
    )


@app.cell
def model(
    city_size,
    days,
    infection_radius,
    infection_rate,
    infectious_days,
    np,
    population,
    samples_per_day,
):
    def simulate(distancing, seed=1, steps_per_day=20):
        """Run the city for ``days`` and return every person's path and status.

        Each day, every person drifts toward a new gravity well one unit away in
        a random direction, bounces off the city walls, and caps their speed, as
        in 3Blue1Brown's model.
        """
        rng = np.random.default_rng(seed)
        half, dt = city_size / 2, 1 / steps_per_day
        position = rng.uniform(-half + 0.3, half - 0.3, (population, 2))
        velocity = np.zeros_like(position)
        well = position.copy()
        keeps_distance = rng.random(population) < distancing
        infected = np.full(population, np.inf)
        source = np.full(population, -1)
        infected[np.argmin(np.linalg.norm(position, axis=1))] = 0
        paths, history = [], []

        for step in range(days * steps_per_day + 1):
            time = step * dt
            sick = (infected <= time) & (time < infected + infectious_days)
            if step % (steps_per_day // samples_per_day) == 0:
                paths.append(position.copy())
                recovered = infected + infectious_days <= time
                history.append(
                    [1 - np.mean(sick | recovered), sick.mean(), recovered.mean()]
                )

            if step % steps_per_day == 0:
                angle = rng.uniform(0, 2 * np.pi, population)
                well = position + np.column_stack([np.cos(angle), np.sin(angle)])
            to_well = well - position
            gap = np.maximum(np.linalg.norm(to_well, axis=1, keepdims=True), 0.05)
            force = 0.2 * to_well / gap**3

            offset = position[None, :, :] - position[:, None, :]
            distance = np.linalg.norm(offset, axis=2) + np.diag(
                np.full(population, np.inf)
            )
            if keeps_distance.any():
                rows = np.flatnonzero(keeps_distance)
                nearest = np.argpartition(distance[rows], 10, axis=1)[:, :10]
                near = offset[rows[:, None], nearest]
                near_gap = np.maximum(distance[rows[:, None], nearest], 0.05)[..., None]
                force[rows] -= 2 * (near / near_gap**3).sum(axis=1)

            force += np.maximum(1 / np.maximum(position + half, 1e-3) - 1, 0)
            force -= np.maximum(1 / np.maximum(half - position, 1e-3) - 1, 0)
            velocity += force * dt
            speed = np.linalg.norm(velocity, axis=1, keepdims=True)
            velocity *= np.minimum(1, 0.5 / np.maximum(speed, 1e-9))
            position = np.clip(position + velocity * dt, -half, half)

            contact = (
                (distance < infection_radius)
                & sick[None, :]
                & ~np.isfinite(infected)[:, None]
            )
            caught = contact & (rng.random(contact.shape) < infection_rate * dt)
            new = np.flatnonzero(caught.any(axis=1))
            source[new] = caught[new].argmax(axis=1)
            infected[new] = time

        return np.array(paths), infected, source, np.array(history)

    return (simulate,)


@app.cell
def simulation(days, distancing, infectious_days, np, population, simulate):
    positions, infected, source, history = simulate(distancing.value)
    caught = np.isfinite(infected)
    cases = np.bincount(source[source >= 0], minlength=population)
    # Each person's path as x0, y0, x1, y1, and so on.
    paths = positions.round(2).transpose(1, 0, 2).reshape(population, -1).tolist()

    def day(time):
        return round(float(time), 2) if np.isfinite(time) else None

    people = [
        {
            "infected": day(infected[k]),
            "recovered": day(infected[k] + infectious_days),
            "source": int(source[k]) if source[k] >= 0 else None,
        }
        for k in range(population)
    ]
    peak = int(history[:, 1].argmax())
    first_cases = np.argsort(infected)[:15]
    summary = {
        "peak": float(history[peak, 1]),
        "peak_day": peak * days / (len(history) - 1),
        "infected": float(caught.mean()),
        "reproduction": float(cases[first_cases[caught[first_cases]]].mean()),
    }
    history = history.round(4).tolist()
    return history, paths, people, summary


@app.cell(hide_code=True)
def outbreak(mo, summary):
    mo.md(f"""
    At its peak on day **{summary["peak_day"]:.1f}**, **{summary["peak"]:.0%}**
    of the city is infectious at once. **{summary["infected"]:.0%}** catch it in
    total, and each of the first cases infects **{summary["reproduction"]:.1f}**
    others on average.
    """)
    return


@app.cell(hide_code=True)
def flattening(days, distancing, mo, np, plt, simulate):
    levels = [0, 0.25, 0.5, 0.75]
    flattening_figure, axes = plt.subplots(figsize=(7, 3.4))
    for level in levels:
        _, _, _, curve = simulate(level)
        current = np.isclose(level, distancing.value)
        axes.plot(
            np.linspace(0, days, len(curve)),
            curve[:, 1],
            color="#d3453d" if current else "#9aa5b1",
            linewidth=2.4 if current else 1.4,
            label=f"{level:.0%} keep their distance",
        )
    axes.set(xlabel="Day", ylabel="Share infectious", xlim=(0, days), ylim=(0, None))
    axes.yaxis.set_major_formatter(lambda share, _: f"{share:.0%}")
    axes.legend(frameon=False)
    axes.spines[["top", "right"]].set_visible(False)
    flattening_figure.tight_layout()
    mo.vstack(
        [
            flattening_figure,
            mo.md(
                "Each line runs the same city with a different share of people "
                "keeping their distance. The highlighted run is the one above."
            ),
        ]
    )
    return (flattening_figure,)


if __name__ == "__main__":
    app.run()
