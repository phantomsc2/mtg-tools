"""Interactive notebook interface for the exact mana-base report."""
from collections import Counter
from fractions import Fraction

import ipywidgets as widgets
from IPython.display import Markdown, display

from mana_analysis import LANDS, ROOT, casting_modes, percentage, read_deck
from mana_basic_search import CAPACITIES, NAMES
from mana_report import Evaluation, suggestion_text


def interface():
    defaults = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
    defaults["Awaken the Honored Dead"] -= 1
    defaults["Bitter Triumph"] += 1
    cards = list(dict.fromkeys(mode.card for mode in casting_modes()))
    counts = {card: widgets.BoundedIntText(value=defaults[card], min=0, max=4,
                                           layout=widgets.Layout(width="75px")) for card in cards}
    weights = {card: widgets.FloatText(value=1, layout=widgets.Layout(width="95px")) for card in cards}
    penalty = widgets.FloatText(value=0.0032, description="Penalty λ", step=0.0001)
    land_label = widgets.HTML()
    stale = widgets.HTML()
    progress = widgets.IntProgress(value=0, min=0, max=100, description="Progress")
    status = widgets.HTML()
    run = widgets.Button(description="Run analysis", button_style="primary", icon="play")
    output = widgets.Output()

    def changed(change=None):
        land_label.value = f"<b>Inferred lands: {60 - sum(w.value for w in counts.values())}</b>"
        stale.value = "<span style='color:#a45b00'>Setup changed; run analysis to update results.</span>"

    for widget in (*counts.values(), *weights.values(), penalty):
        widget.observe(changed, names="value")
    changed()
    header = widgets.HBox([widgets.HTML("<b>Spell</b>", layout=widgets.Layout(width="240px")),
                           widgets.HTML("<b>Copies</b>", layout=widgets.Layout(width="75px")),
                           widgets.HTML("<b>Weight</b>")])
    rows = [widgets.HBox([widgets.Label(card, layout=widgets.Layout(width="240px")), counts[card], weights[card]])
            for card in cards]

    def on_run(button):
        run.disabled = True
        progress.value = 0
        output.clear_output(wait=True)
        try:
            deck = Counter({c: counts[c].value for c in cards if counts[c].value})
            lands = 60 - sum(deck.values())
            if not deck:
                raise ValueError("Select at least one spell.")
            if any(weights[c].value <= 0 for c in deck):
                raise ValueError("Weights for selected spells must be positive.")
            if penalty.value < 0:
                raise ValueError("The penalty must be nonnegative.")
            if not 1 <= lands <= sum(CAPACITIES):
                raise ValueError(f"No candidate land bases for {lands} lands in the bounded pool.")
            remaining = lands - 1
            deck["Swamp"] = 1
            for name, cap in zip(NAMES, CAPACITIES):
                add = min(remaining, cap - deck[name])
                deck[name] += add
                remaining -= add
            deck += Counter()  # discard zero-count entries
            def update(start, end):
                def callback(done, total, message):
                    progress.value = start + (end-start)*done//total
                    status.value = message
                return callback
            with output:
                print(f"Evaluating {lands} lands and {60-lands} spells in the bounded land pool...", flush=True)
                ev = Evaluation(deck, {c: Fraction(str(weights[c].value)) for c in counts if counts[c].value},
                                Fraction(str(penalty.value)), {}, update(0, 55))
                print(f"Evaluated {len(ev.bases):,} candidate land bases. Calculating crossings...", flush=True)
                suggestions = ev.sensitivities(progress=update(55, 80))
                print("Calculating casting coverage...", flush=True)
                curves = ev.curves(progress=update(80, 100))
                best = ev.describe(ev.winner)
                display(Markdown("## Optimal deck\n\n" + "\n".join(
                    f"- {n} {name}" for name, n in ev.full_deck(ev.winner).items() if n)))
                display(Markdown(f"**Weighted success:** {float(best['weighted_success']):.4%}  \n"
                                 f"**Penalty:** {float(best['penalty']):.4%}  \n"
                                 f"**Fitness:** {float(best['fitness']):.4%}  \n"
                                 f"**Loss:** {float(best['loss']):.4%}; {len(ev.ties)} tied bases."))
                table = ["## Per-card crossings", "",
                         "Changing a weight renormalizes all spell weights while the land penalty stays fixed. "
                         "A card?s castability can therefore stay the same or move in the opposite direction.",
                         "", "| Card | Value less | Value more |", "|---|---|---|"]
                table += [f"| {row['card']} | {suggestion_text(row['less'], 'less')} | "
                          f"{suggestion_text(row['more'], 'more')} |" for row in suggestions]
                display(Markdown("\n".join(table)))
                for side, title in (("play", "On the play"), ("draw", "On the draw")):
                    table = [f"## {title}", "", "| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |",
                             "|---|---|---:|---:|---:|---:|---:|---:|"]
                    table += [f"| {row['card']} | {row['cost']} | " +
                              " | ".join("—" if p is None else percentage(p) for p in row[side]) + " |"
                              for row in curves]
                    display(Markdown("\n".join(table)))
                print("Analysis complete.")
            status.value = "Complete"
            stale.value = "<span style='color:green'>Results match the current setup.</span>"
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            status.value = "Analysis failed"
            stale.value = "<span style='color:#a45b00'>No current result.</span>"
            with output:
                print(f"Cannot evaluate: {exc}")
        finally:
            run.disabled = False

    run.on_click(on_run)
    display(widgets.VBox([header, *rows, penalty, land_label, stale, run, progress, status, output]))
