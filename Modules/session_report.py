from datetime import datetime
from html import escape


def _safe_number(value):
    """Return a valid numeric value, or None."""
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        try:
            number = float(value)
            if number == number and abs(number) != float("inf"):
                return number
        except (TypeError, ValueError, OverflowError):
            pass

    return None


def _format_number(value, digits=3):
    """Format a numeric value for display."""
    number = _safe_number(value)

    if number is None:
        return "N/A"

    return f"{number:.{digits}f}"


def build_session_summary(session):
    """
    Build numerical summary information from a completed session.

    Expected session structure:
    {
        "session_id": "...",
        "started_at": "...",
        "stopped_at": "...",
        "duration_seconds": 0,
        "sample_count": 0,
        "samples": [
            {
                "timestamp": "...",
                "elapsed_seconds": 0,
                "metrics": {...}
            }
        ],
        "events": [
            {
                "timestamp": "...",
                "elapsed_seconds": 0,
                "event": "..."
            }
        ]
    }
    """

    samples = session.get("samples", [])
    events = session.get("events", [])

    # Metrics to include in the numerical report.
    metric_labels = {
        "eye_aspect_ratio": "Eye Aspect Ratio",
        "blink_rate": "Blink Rate",
        "eye_closure_duration": "Eye Closure Duration",
        "mouth_aspect_ratio": "Mouth Aspect Ratio",
        "mouth_open_duration": "Mouth Opening Duration",
        "mouth_open_frequency": "Mouth Opening Events",
        "nose_to_eye_ratio": "Nose-to-Eye Ratio",
        "nose_to_mouth_ratio": "Nose-to-Mouth Ratio",
        "head_roll_degrees": "Head Roll",
        "facial_geometry_change": "Facial Geometry Change",
        "torso_inclination": "Torso Inclination",
        "hand_to_torso_distance": "Hand-to-Torso Distance",
        "tracking_quality": "Tracking Quality",
    }

    measurements = []

    for metric_key, metric_label in metric_labels.items():

        values = []

        for sample in samples:

            metrics = sample.get("metrics", {})

            if not isinstance(metrics, dict):
                continue

            number = _safe_number(metrics.get(metric_key))

            if number is not None:
                values.append(number)

        if values:

            measurements.append({
                "key": metric_key,
                "measurement": metric_label,
                "valid_samples": len(values),
                "average": sum(values) / len(values),
                "minimum": min(values),
                "maximum": max(values)
            })

    # Session blink count is recorded as a cumulative value.
    blink_values = []

    for sample in samples:

        metrics = sample.get("metrics", {})

        if isinstance(metrics, dict):

            blink_count = _safe_number(
                metrics.get("session_blink_count")
            )

            if blink_count is not None:
                blink_values.append(blink_count)

    session_blink_count = (
        int(max(blink_values))
        if blink_values
        else None
    )

    return {
        "sample_count": len(samples),
        "event_count": len(events),
        "measurements": measurements,
        "session_blink_count": session_blink_count
    }


def build_printable_html(session):
    """
    Generate a complete printable HTML session report.

    The report includes:
    - Session information
    - Numerical measurement summary
    - Event timeline
    - Every recorded numerical sample

    No webcam video is included or saved.
    """

    summary = build_session_summary(session)

    session_id = escape(
        str(session.get("session_id", "Unavailable"))
    )

    started_at = escape(
        str(session.get("started_at", "Unavailable"))
    )

    stopped_at = escape(
        str(session.get("stopped_at", "Unavailable"))
    )

    duration = _safe_number(
        session.get("duration_seconds")
    )

    duration_text = (
        f"{duration:.1f} seconds"
        if duration is not None
        else "Unavailable"
    )

    samples = session.get("samples", [])
    events = session.get("events", [])

    # -----------------------------------------
    # MEASUREMENT SUMMARY TABLE
    # -----------------------------------------

    measurement_rows = ""

    for item in summary["measurements"]:

        measurement_rows += f"""
        <tr>
            <td>{escape(str(item["measurement"]))}</td>
            <td>{item["valid_samples"]}</td>
            <td>{_format_number(item["average"])}</td>
            <td>{_format_number(item["minimum"])}</td>
            <td>{_format_number(item["maximum"])}</td>
        </tr>
        """

    if not measurement_rows:

        measurement_rows = """
        <tr>
            <td colspan="5">No valid numerical measurements recorded.</td>
        </tr>
        """

    # -----------------------------------------
    # EVENT TIMELINE TABLE
    # -----------------------------------------

    event_rows = ""

    for event in events:

        timestamp = escape(
            str(event.get("timestamp", "Unavailable"))
        )

        elapsed = _safe_number(
            event.get("elapsed_seconds")
        )

        elapsed_text = (
            f"{elapsed:.1f}"
            if elapsed is not None
            else "N/A"
        )

        event_name = escape(
            str(event.get("event", "Unspecified event"))
        )

        event_rows += f"""
        <tr>
            <td>{timestamp}</td>
            <td>{elapsed_text}</td>
            <td>{event_name}</td>
        </tr>
        """

    if not event_rows:

        event_rows = """
        <tr>
            <td colspan="3">No events recorded during this session.</td>
        </tr>
        """

    # -----------------------------------------
    # RECORDED SAMPLE TABLE
    # -----------------------------------------

    sample_rows = ""

    sample_columns = [
        ("eye_aspect_ratio", "EAR"),
        ("blink_rate", "Blink Rate"),
        ("session_blink_count", "Session Blinks"),
        ("mouth_aspect_ratio", "Mouth Ratio"),
        ("eye_closure_duration", "Eye Closure (sec)"),
        ("mouth_open_duration", "Mouth Open (sec)"),
        ("mouth_open_frequency", "Mouth Events"),
        ("nose_to_eye_ratio", "Nose/Eye"),
        ("nose_to_mouth_ratio", "Nose/Mouth"),
        ("head_roll_degrees", "Head Roll"),
        ("torso_inclination", "Torso Inclination"),
        ("hand_to_torso_distance", "Hand/Torso Distance"),
        ("tracking_quality", "Tracking Quality"),
    ]

    sample_headers = "".join(
        f"<th>{escape(label)}</th>"
        for _, label in sample_columns
    )

    for index, sample in enumerate(samples, start=1):

        timestamp = escape(
            str(sample.get("timestamp", "Unavailable"))
        )

        elapsed = _safe_number(
            sample.get("elapsed_seconds")
        )

        elapsed_text = (
            f"{elapsed:.1f}"
            if elapsed is not None
            else "N/A"
        )

        metrics = sample.get("metrics", {})

        if not isinstance(metrics, dict):
            metrics = {}

        cells = ""

        for metric_key, _ in sample_columns:

            value = metrics.get(metric_key)

            if metric_key in (
                "session_blink_count",
                "mouth_open_frequency"
            ):
                number = _safe_number(value)

                formatted = (
                    str(int(number))
                    if number is not None
                    else "N/A"
                )
            else:
                formatted = _format_number(value)

            cells += f"<td>{escape(formatted)}</td>"

        sample_rows += f"""
        <tr>
            <td>{index}</td>
            <td>{timestamp}</td>
            <td>{elapsed_text}</td>
            {cells}
        </tr>
        """

    if not sample_rows:

        sample_rows = f"""
        <tr>
            <td colspan="{len(sample_columns) + 3}">
                No numerical samples recorded.
            </td>
        </tr>
        """

    # -----------------------------------------
    # COMPLETE HTML REPORT
    # -----------------------------------------

    html = f"""
    <!DOCTYPE html>
    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>PainLens AI - Session Report</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                color: #1e293b;
                background: #f8fafc;
                margin: 0;
                padding: 25px;
            }}

            .report {{
                max-width: 1200px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
            }}

            h1 {{
                color: #2563eb;
                margin-bottom: 5px;
            }}

            .subtitle {{
                color: #64748b;
                margin-top: 0;
            }}

            h2 {{
                color: #1e40af;
                margin-top: 35px;
                border-bottom: 2px solid #dbeafe;
                padding-bottom: 8px;
            }}

            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 12px;
                margin-top: 20px;
            }}

            .summary-card {{
                background: #eff6ff;
                padding: 16px;
                border-radius: 8px;
                border: 1px solid #dbeafe;
            }}

            .summary-card .label {{
                color: #64748b;
                font-size: 13px;
            }}

            .summary-card .value {{
                font-size: 21px;
                font-weight: bold;
                margin-top: 8px;
                overflow-wrap: anywhere;
            }}

            .session-info {{
                line-height: 1.8;
                margin-top: 20px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 13px;
            }}

            th {{
                background: #1e40af;
                color: white;
                text-align: left;
            }}

            th, td {{
                border: 1px solid #cbd5e1;
                padding: 9px;
            }}

            tr:nth-child(even) {{
                background: #f1f5f9;
            }}

            .table-container {{
                width: 100%;
                overflow-x: auto;
            }}

            .disclaimer {{
                background: #fff7ed;
                border: 1px solid #fed7aa;
                color: #9a3412;
                padding: 15px;
                border-radius: 8px;
                margin-top: 30px;
                line-height: 1.5;
            }}

            .print-button {{
                background: #2563eb;
                color: white;
                border: none;
                padding: 12px 22px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 15px;
                margin-bottom: 20px;
            }}

            .footer {{
                margin-top: 30px;
                color: #64748b;
                font-size: 12px;
                text-align: center;
            }}

            @media (max-width: 700px) {{
                body {{
                    padding: 8px;
                }}

                .report {{
                    padding: 15px;
                }}

                .summary-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}

            @media print {{

                body {{
                    background: white;
                    padding: 0;
                }}

                .report {{
                    max-width: none;
                    padding: 0;
                    border-radius: 0;
                }}

                .print-button {{
                    display: none;
                }}

                h2 {{
                    break-after: avoid;
                }}

                tr {{
                    break-inside: avoid;
                }}

                .table-container {{
                    overflow: visible;
                }}

            }}

        </style>

    </head>

    <body>

        <div class="report">

            <button class="print-button"
                    onclick="window.print()">
                Print / Save as PDF
            </button>

            <h1>PainLens AI</h1>

            <p class="subtitle">
                Numerical Observation Session Report
            </p>

            <hr>

            <h2>Session Information</h2>

            <div class="session-info">

                <strong>Session ID:</strong>
                {session_id}
                <br>

                <strong>Session Started:</strong>
                {started_at}
                <br>

                <strong>Session Stopped:</strong>
                {stopped_at}
                <br>

                <strong>Duration:</strong>
                {duration_text}

            </div>

            <div class="summary-grid">

                <div class="summary-card">
                    <div class="label">Recorded Samples</div>
                    <div class="value">
                        {summary["sample_count"]}
                    </div>
                </div>

                <div class="summary-card">
                    <div class="label">Detected Events</div>
                    <div class="value">
                        {summary["event_count"]}
                    </div>
                </div>

                <div class="summary-card">
                    <div class="label">Session Blinks</div>
                    <div class="value">
                        {
                            summary["session_blink_count"]
                            if summary["session_blink_count"] is not None
                            else "N/A"
                        }
                    </div>
                </div>

                <div class="summary-card">
                    <div class="label">Session Duration</div>
                    <div class="value">
                        {duration_text}
                    </div>
                </div>

            </div>

            <h2>Measurement Summary</h2>

            <div class="table-container">

                <table>

                    <thead>
                        <tr>
                            <th>Measurement</th>
                            <th>Valid Samples</th>
                            <th>Average</th>
                            <th>Minimum</th>
                            <th>Maximum</th>
                        </tr>
                    </thead>

                    <tbody>
                        {measurement_rows}
                    </tbody>

                </table>

            </div>

            <h2>Event Timeline</h2>

            <div class="table-container">

                <table>

                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Elapsed Seconds</th>
                            <th>Observed Event</th>
                        </tr>
                    </thead>

                    <tbody>
                        {event_rows}
                    </tbody>

                </table>

            </div>

            <h2>Complete Numerical Observation Log</h2>

            <p>
                Each row represents one recorded numerical sample.
                Missing measurements are displayed as N/A.
            </p>

            <div class="table-container">

                <table>

                    <thead>
                        <tr>
                            <th>Sample</th>
                            <th>Timestamp</th>
                            <th>Elapsed Seconds</th>
                            {sample_headers}
                        </tr>
                    </thead>

                    <tbody>
                        {sample_rows}
                    </tbody>

                </table>

            </div>

            <div class="disclaimer">

                <strong>Important Medical Disclaimer</strong>

                <p>
                    PainLens AI is an experimental behavioural
                    observation prototype. The measurements in
                    this report are observational indicators only.
                    They do not confirm, measure definitively, or
                    diagnose pain. This report must not replace
                    professional medical assessment.
                </p>

                <p>
                    This report contains numerical observations,
                    timestamps and detected events only. Webcam
                    video is not stored in this report.
                </p>

            </div>

            <div class="footer">

                Generated by PainLens AI

            </div>

        </div>

    </body>

    </html>
    """

    return html