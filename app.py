"""Tender Desk's Gradio interface and assignment-compatible /run endpoint."""

import os
import time
from html import escape
from pathlib import Path

import gradio as gr

import env
import logbook
import monitor
import pipeline

env.load_env()
logbook.start()

TITLE = "Tender Desk"
LABELS = {"bid": "Shortlist for bid", "no_bid": "Do not bid", "review": "Needs review"}
CSS = Path(__file__).with_name("tender.css").read_text(encoding="utf-8")
HEADER = """
<div class="td-brand">
    <span class="td-mark" aria-hidden="true"></span>
    <span>Tender Desk</span>
</div>
<header class="td-hero">
    <div class="td-hero-copy">
        <p class="td-scope">Spanish public works</p>
        <h1>Should we bid?</h1>
        <p>Review a construction tender, estimate the competition, and decide whether to prepare a bid.</p>
    </div>
    <div class="td-blueprint" aria-hidden="true"><div class="td-plan"></div></div>
</header>
"""
EMPTY_RESULT = "Paste a tender and select **Analyse tender** to see your recommendation."


def serve(raw_input: str, fit: str = pipeline.DEFAULT_FIT) -> dict:
    started = time.perf_counter()
    result = pipeline.run(raw_input, fit)
    return logbook.log_request(result | {"latency_s": round(time.perf_counter() - started, 3)})


def on_run(raw_input, fit):
    if not (raw_input or "").strip():
        raise gr.Error("Paste a construction tender or load the TED example.")
    record = serve(raw_input, fit)
    outputs = record["outputs"]
    facts = outputs["component_a"]
    result = outputs["component_b"]
    decision = result["decision"]
    guidance = f"### {LABELS[decision]}\n{result['reason']}\n"
    estimate = result["estimated_offers"]
    if estimate is not None:
        radius = result["typical_error"]
        guidance += (
            f"\n- **{estimate}** Estimated offers\n"
            f"- **{max(1, estimate - radius)}–{estimate + radius}** Historical error range"
        )
    budget = facts.get("budget_eur")
    duration = facts.get("duration_months")
    award_basis = {"price_quality": "Multiple criteria", "price": "Lowest price"}.get(facts.get("award_basis"), "Unknown")
    summary = "#### Notice details\nNo notice fields available."
    if facts:
        summary = (
            "#### Notice details\n"
            f"- Budget excl. VAT **{'€' + format(budget, ',.2f') if budget is not None else 'Unknown'}**\n"
            f"- Duration **{format(duration, 'g') + ' months' if duration is not None else 'Unknown'}**\n"
            f"- Construction code (CPV) **{facts.get('cpv') or 'Unknown'}**\n"
            f"- Award criteria **{award_basis}**"
        )
    return guidance, summary, outputs, record["id"]


def feedback(request_id, value):
    if not request_id:
        gr.Warning("Analyse a tender first.")
        return
    logbook.log_feedback(request_id, value)
    gr.Info("Thanks for the feedback.")


def refresh_monitor():
    logs = logbook.load()
    reference = monitor.load_reference()
    if reference is None:
        message = "The team’s reference set is pending. Review rate, latency and cost are recorded below."
    elif len(logs) < monitor.MIN_WINDOW:
        message = f"Drift alerts start after {monitor.MIN_WINDOW} requests."
    else:
        alerts = monitor.alerts(logs, reference)
        message = "\n".join(f"- {message}" for message in alerts) if alerts else "No alerts in the current window."
    drift = None
    if reference is not None and len(logs) >= monitor.MIN_WINDOW:
        drift = monitor.drift(reference, monitor.live_features(logs))
    labels = {
        "requests": "Requests", "sent to review": "Sent to review",
        "rated 👍/👎": "Rated requests", "share 👎 (of rated)": "Negative feedback",
        "median latency (s)": "Median latency (s)",
        "mean cost per request (€)": "Cost per request (€)", "total cost (€)": "Total cost (€)",
    }
    metrics = "".join(
        f"<div><dt>{escape(labels[row.metric])}</dt><dd>{escape(str(row.value))}</dd></div>"
        for row in monitor.summary(logs).itertuples()
    )
    summary = f'<section aria-label="Request summary"><h3>Request summary</h3><dl class="td-metrics">{metrics}</dl></section>'
    return message, summary, monitor.quality(logs), gr.update(value=drift, visible=drift is not None)


with gr.Blocks(title=TITLE) as demo:
    gr.HTML(HEADER, elem_id="tender-header", js_on_load=None, padding=False)
    with gr.Tabs(elem_id="tender-tabs"):
        with gr.Tab("App"):
            request_id = gr.State("")
            with gr.Row(elem_id="tender-workspace"):
                with gr.Column(scale=6, min_width=0, elem_classes=["td-panel", "td-form"]):
                    with gr.Row(elem_classes="td-panel-heading"):
                        gr.Markdown("## Tender notice", elem_classes="td-section-title")
                        sample = gr.Button("Load TED example", size="sm", scale=0, min_width=0,
                                           elem_id="tender-example")
                    raw_input = gr.Textbox(
                        label="Tender notice text", show_label=False,
                        placeholder="Paste the tender notice here in Spanish or English…",
                        lines=7, max_lines=16, elem_id="tender-input",
                    )
                    gr.Markdown("Remove contact names, emails, and phone numbers before pasting.",
                                elem_classes="td-help")
                    fit = gr.Radio(
                        pipeline.FIT_OPTIONS, value=pipeline.DEFAULT_FIT,
                        label="Can your company meet the tender requirements?", elem_id="tender-fit",
                    )
                    run_button = gr.Button("Analyse tender", variant="primary", elem_id="tender-analyse")
                with gr.Column(scale=5, min_width=0, elem_classes=["td-panel", "td-result"]):
                    gr.Markdown("## Bid guidance", elem_classes="td-section-title")
                    guidance = gr.Markdown(EMPTY_RESULT, elem_id="tender-guidance")
                    with gr.Column(elem_id="tender-expanded"):
                        summary = gr.Markdown(elem_id="tender-facts")
                        with gr.Accordion("Technical details", open=False):
                            details = gr.JSON(show_label=False)
                        with gr.Row(elem_classes="td-feedback"):
                            up = gr.Button("Useful", size="sm")
                            down = gr.Button("Needs improvement", size="sm")
            sample.click(lambda: (pipeline.DATA / "example.txt").read_text(encoding="utf-8"),
                         None, raw_input, api_name=False)
            run_button.click(
                on_run, [raw_input, fit], [guidance, summary, details, request_id],
                api_name="run", scroll_to_output=True,
            )
            up.click(lambda rid: feedback(rid, 1), request_id, None, api_name=False)
            down.click(lambda rid: feedback(rid, -1), request_id, None, api_name=False)

        with gr.Tab("Monitoring"):
            with gr.Column(elem_classes="td-panel"):
                with gr.Row(elem_id="tender-monitor-heading"):
                    gr.Markdown("## App monitoring", elem_classes="td-section-title")
                    refresh = gr.Button("Refresh metrics", scale=0, min_width=0, elem_id="tender-refresh")
                alert = gr.Markdown(elem_id="tender-monitor-alert")
                summary_cards = gr.HTML(js_on_load=None, elem_id="tender-monitor-summary")
                quality_plot = gr.LinePlot(
                    x="time", y="value", color="signal", label="Review and feedback over time",
                    y_axis_format=".0%", y_lim=[0, 1], x_title="Time", y_title="Share of requests",
                    height=310,
                )
                drift_table = gr.Dataframe(label="Changes from the reference set", interactive=False, visible=False)
                outputs = [alert, summary_cards, quality_plot, drift_table]
                refresh.click(refresh_monitor, None, outputs, api_name=False)
                demo.load(refresh_monitor, None, outputs, api_name=False)


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Base(
            primary_hue="teal", neutral_hue="slate",
            font=[gr.themes.GoogleFont("DM Sans"), "system-ui", "sans-serif"],
        ),
        css=CSS, footer_links=[],
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("PORT", "7860")), show_error=False,
    )
