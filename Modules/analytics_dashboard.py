from __future__ import annotations

import html
import json
import math
from collections import Counter
from datetime import datetime

import pandas as pd
import streamlit as st

from Modules.body_input import get_patients, get_observations
from Modules.guardian_observations import get_guardian_observations
from Modules.session_storage import get_monitoring_sessions
from Modules.session_report import build_session_summary


METRIC_LABELS = {
    "eye_aspect_ratio": "Eye Aspect Ratio",
    "blink_rate": "Blink Rate",
    "eye_closure_duration": "Eye Closure Duration (sec)",
    "mouth_aspect_ratio": "Mouth Aspect Ratio",
    "mouth_open_duration": "Mouth Opening Duration (sec)",
    "mouth_open_frequency": "Mouth Opening Events",
    "nose_to_eye_ratio": "Nose-to-Eye Ratio",
    "nose_to_mouth_ratio": "Nose-to-Mouth Ratio",
    "head_roll_degrees": "Head Roll (degrees)",
    "facial_geometry_change": "Facial Geometry Change",
    "torso_inclination": "Torso Inclination (degrees)",
    "hand_to_torso_distance": "Hand-to-Torso Distance",
    "tracking_quality": "Tracking Quality",
}


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        if math.isfinite(result):
            return result
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def _text(value, fallback="Not recorded"):
    if value is None:
        return fallback
    result = str(value).strip()
    return result if result else fallback


def _safe_json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
        return decoded if isinstance(decoded, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _session_metrics(session):
    samples = session.get("samples") or []
    rows = []
    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            continue
        metrics = sample.get("metrics") or {}
        if not isinstance(metrics, dict):
            continue
        elapsed = _number(sample.get("elapsed_seconds"))
        row = {
            "Sample": index,
            "Elapsed seconds": elapsed,
            "Timestamp": _text(sample.get("timestamp"), ""),
        }
        for key, label in METRIC_LABELS.items():
            row[label] = _number(metrics.get(key))
        rows.append(row)
    return pd.DataFrame(rows)


def _make_findings(patient, guardians, body_records, session, summary):
    findings = []

    findings.append(
        f"The selected patient has {len(guardians)} guardian questionnaire "
        f"submission(s) and {len(body_records)} patient-linked Body Map "
        f"record(s) available."
    )

    sample_count = summary.get("sample_count", 0)
    event_count = summary.get("event_count", 0)
    findings.append(
        f"The selected Live Monitoring session contains {sample_count} "
        f"recorded sample(s) and {event_count} event(s)."
    )

    if sample_count == 0:
        findings.append(
            "No numerical samples were available in this session, so "
            "measurement trends could not be calculated."
        )
    else:
        measurements = summary.get("measurements", [])
        if measurements:
            best = max(measurements, key=lambda item: item.get("valid_samples", 0))
            findings.append(
                f"The most frequently available measurement was "
                f"{best.get('measurement', 'a measurement')}, with "
                f"{best.get('valid_samples', 0)} valid value(s)."
            )
        else:
            findings.append(
                "Samples exist, but none of the supported numerical "
                "measurements contained valid numeric values."
            )

    reported_frequencies = [
        str(item.get("frequency")).strip()
        for item in guardians
        if item.get("frequency") and str(item.get("frequency")).strip()
    ]
    if reported_frequencies:
        common_frequency, count = Counter(reported_frequencies).most_common(1)[0]
        findings.append(
            f"The most common frequency response across guardian "
            f"submissions was '{common_frequency}' ({count} submission(s))."
        )
    else:
        findings.append(
            "No guardian frequency responses were recorded."
        )

    region_counts = Counter()
    for record in body_records:
        for region in _safe_json_list(record.get("selected_regions")):
            region_counts[str(region)] += 1

    if region_counts:
        region, count = region_counts.most_common(1)[0]
        findings.append(
            f"The most frequently recorded Body Map region was "
            f"'{region}' ({count} record(s))."
        )
    else:
        findings.append(
            "No selected body regions were available in the patient's "
            "linked Body Map records."
        )

    findings.append(
        "These are descriptions of recorded data only. They do not "
        "establish that a measurement or body region represents pain."
    )
    return findings


def _build_html_report(patient, guardians, body_records, session_record,
                       session, summary, findings):
    esc = lambda value: html.escape(_text(value))
    patient_rows = [
        ("Patient ID", patient.get("id")),
        ("Name", patient.get("name")),
        ("Age", patient.get("age")),
        ("Sex", patient.get("sex")),
        ("Blood group", patient.get("blood_group")),
        ("Special medical condition", patient.get("special_medical_condition")),
        ("Current medical condition", patient.get("current_medical_condition")),
    ]

    profile_html = "".join(
        f"<tr><th>{html.escape(str(label))}</th><td>{esc(value)}</td></tr>"
        for label, value in patient_rows
    )

    guardian_html = ""
    guardian_labels = [
        ("observed_behaviour", "Unusual behaviour noticed"),
        ("first_noticed", "When first noticed"),
        ("frequency", "Frequency"),
        ("duration", "Usual duration"),
        ("triggers", "Possible triggers"),
        ("different_from_usual", "Different from usual behaviour"),
    ]
    for record in guardians:
        guardian_html += (
            f"<h3>Guardian submission #{esc(record.get('id'))} — "
            f"{esc(record.get('created_at'))}</h3><table>"
        )
        for key, label in guardian_labels:
            guardian_html += (
                f"<tr><th>{html.escape(label)}</th>"
                f"<td>{esc(record.get(key))}</td></tr>"
            )
        changes = ", ".join(_safe_json_list(record.get("daily_changes")))
        guardian_html += (
            f"<tr><th>Changes in daily activities</th>"
            f"<td>{esc(changes or 'Not recorded')}</td></tr></table>"
        )
    if not guardian_html:
        guardian_html = "<p>No guardian submissions were recorded.</p>"

    body_html = ""
    for record in body_records:
        regions = ", ".join(_safe_json_list(record.get("selected_regions")))
        body_html += (
            "<tr>"
            f"<td>{esc(record.get('created_at'))}</td>"
            f"<td>{esc(regions)}</td>"
            f"<td>{esc(record.get('body_view'))}</td>"
            f"<td>{esc(record.get('input_source'))}</td>"
            f"<td>{esc(record.get('notes'))}</td>"
            "</tr>"
        )
    if not body_html:
        body_html = '<tr><td colspan="5">No linked Body Map records.</td></tr>'

    measurement_html = ""
    for item in summary.get("measurements", []):
        measurement_html += (
            f"<tr><td>{esc(item.get('measurement'))}</td>"
            f"<td>{item.get('valid_samples', 0)}</td>"
            f"<td>{item.get('average', 0):.4f}</td>"
            f"<td>{item.get('minimum', 0):.4f}</td>"
            f"<td>{item.get('maximum', 0):.4f}</td></tr>"
        )
    if not measurement_html:
        measurement_html = '<tr><td colspan="5">No valid measurements.</td></tr>'

    sample_html = ""
    for index, sample in enumerate(session.get("samples") or [], start=1):
        metrics = sample.get("metrics") or {}
        cells = [
            f"<td>{index}</td>",
            f"<td>{esc(sample.get('timestamp'))}</td>",
            f"<td>{esc(sample.get('elapsed_seconds'))}</td>",
        ]
        for key in METRIC_LABELS:
            value = _number(metrics.get(key))
            cells.append(f"<td>{value:.4f}</td>" if value is not None else "<td>N/A</td>")
        sample_html += "<tr>" + "".join(cells) + "</tr>"
    if not sample_html:
        sample_html = (
            f'<tr><td colspan="{3 + len(METRIC_LABELS)}">'
            "No recorded numerical samples.</td></tr>"
        )

    event_html = ""
    for event in session.get("events") or []:
        event_html += (
            f"<tr><td>{esc(event.get('timestamp'))}</td>"
            f"<td>{esc(event.get('elapsed_seconds'))}</td>"
            f"<td>{esc(event.get('event'))}</td></tr>"
        )
    if not event_html:
        event_html = '<tr><td colspan="3">No events recorded.</td></tr>'

    findings_html = "".join(f"<li>{html.escape(item)}</li>" for item in findings)
    started = session_record.get("started_at") or session.get("started_at")
    stopped = session_record.get("stopped_at") or session.get("stopped_at")
    session_id = session_record.get("session_id") or session.get("session_id")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PainLens AI - Combined Observation Report</title>
<style>
body{{font-family:Arial,sans-serif;color:#1e293b;margin:28px;line-height:1.5}}
main{{max-width:1100px;margin:auto}}h1{{color:#1d4ed8}}h2{{color:#1e40af;margin-top:30px}}
table{{border-collapse:collapse;width:100%;margin:12px 0 24px;font-size:13px}}
td,th{{border:1px solid #cbd5e1;padding:8px;text-align:left;vertical-align:top}}
th{{background:#eff6ff}}.note{{padding:14px;background:#fff7ed;border:1px solid #fed7aa}}
button{{padding:10px 16px;background:#2563eb;color:white;border:0;border-radius:5px}}
@media print{{button{{display:none}}body{{margin:12mm}}}}
</style></head><body><main>
<button onclick="window.print()">Print / Save as PDF</button>
<h1>PainLens AI</h1><p>Combined Behavioural Observation Report</p>
<p><b>Generated:</b> {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
<h2>1. Patient Profile</h2><table>{profile_html}</table>
<h2>2. Selected Live Monitoring Session</h2>
<p><b>Session ID:</b> {esc(session_id)}<br>
<b>Started:</b> {esc(started)}<br><b>Stopped:</b> {esc(stopped)}<br>
<b>Duration (seconds):</b> {esc(session_record.get('duration_seconds') or session.get('duration_seconds'))}<br>
<b>Recorded samples:</b> {summary.get('sample_count', 0)}<br>
<b>Detected events:</b> {summary.get('event_count', 0)}</p>
<h3>Measurement Summary</h3><table><tr><th>Measurement</th><th>Valid samples</th>
<th>Average</th><th>Minimum</th><th>Maximum</th></tr>{measurement_html}</table>
<h3>Event Timeline</h3><table><tr><th>Timestamp</th><th>Elapsed seconds</th><th>Event</th></tr>{event_html}</table>
<h3>Complete Numerical Sample Log</h3><table><tr><th>Sample</th><th>Timestamp</th><th>Elapsed seconds</th>
{''.join(f'<th>{html.escape(label)}</th>' for label in METRIC_LABELS.values())}</tr>{sample_html}</table>
<h2>3. Guardian Observations</h2>
<p>All saved questionnaire submissions for this patient are included.</p>{guardian_html}
<h2>4. Body Map History</h2>
<p>These are patient-linked records. They are not assumed to have occurred during the selected monitoring session.</p>
<table><tr><th>Date/time</th><th>Selected regions</th><th>View</th><th>Input source</th><th>Notes</th></tr>{body_html}</table>
<h2>5. Descriptive Analytics</h2><ul>{findings_html}</ul>
<div class="note"><b>Important limitations</b><p>
PainLens AI is an experimental behavioural observation and communication prototype.
Facial ratios, blink rate, mouth movement, posture, tracking quality, guardian reports
and body locations are not validated standalone measures of pain. Tracking quality
describes technical landmark visibility, not confidence that pain is present.
No pain probability or diagnosis is generated. Missing values are left missing, not
treated as zero. This report should be reviewed by a qualified healthcare professional
and must not replace medical assessment.</p></div>
<p>Generated by PainLens AI.</p></main></body></html>"""


def render_analytics_dashboard():
    st.title("📊 PainLens AI — Combined Analytics")
    st.write(
        "This report combines guardian-reported context, one selected "
        "Live Monitoring session, and patient-linked Body Map history."
    )
    st.caption(
        "Select one patient and one completed monitoring session. "
        "All guardian and Body Map records for that patient are included."
    )
    st.divider()

    patients = get_patients()
    if not patients:
        st.warning("Register a patient on the Dashboard before opening Analytics.")
        return

    patient_by_id = {int(p["id"]): p for p in patients}
    patient_ids = list(patient_by_id)
    active_id = st.session_state.get("selected_patient_id")
    default_index = patient_ids.index(int(active_id)) if active_id is not None and int(active_id) in patient_ids else 0

    selected_patient_id = st.selectbox(
        "Select patient",
        patient_ids,
        index=default_index,
        format_func=lambda pid: f"{patient_by_id[pid].get('name', 'Unnamed')} (ID: {pid})",
        key="analytics_patient_selector",
    )
    st.session_state.selected_patient_id = selected_patient_id
    patient = patient_by_id[selected_patient_id]

    guardians = get_guardian_observations(selected_patient_id)
    body_records = get_observations(selected_patient_id)
    sessions = get_monitoring_sessions(selected_patient_id)

    st.subheader("Patient profile")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Age", _text(patient.get("age")))
    c2.metric("Sex", _text(patient.get("sex")))
    c3.metric("Guardian submissions", len(guardians))
    c4.metric("Body Map records", len(body_records))
    with st.expander("Medical and profile information"):
        st.write("**Name:**", _text(patient.get("name")))
        st.write("**Blood group:**", _text(patient.get("blood_group")))
        st.write("**Special medical condition:**", _text(patient.get("special_medical_condition")))
        st.write("**Current medical condition:**", _text(patient.get("current_medical_condition")))

    st.divider()
    st.subheader("Select a completed Live Monitoring session")
    if not sessions:
        st.warning("No permanently saved Live Monitoring sessions exist for this patient yet.")
        st.info("Complete and stop a Live Monitoring session first. It must be saved successfully to the database.")
        return

    session_ids = list(range(len(sessions)))
    selected_index = st.selectbox(
        "Saved session",
        session_ids,
        format_func=lambda i: (
            f"{sessions[i].get('started_at') or 'Date unavailable'} "
            f"| Session: {sessions[i].get('session_id', 'Unknown')} "
            f"| Samples: {sessions[i].get('sample_count', 0)}"
        ),
        key="analytics_session_selector",
    )
    session_record = sessions[selected_index]
    session = session_record.get("session_data") or {}
    if not isinstance(session, dict):
        st.error("The selected session data is not in the expected format.")
        return

    summary = build_session_summary(session)
    findings = _make_findings(patient, guardians, body_records, session, summary)

    st.divider()
    st.header("Combined report")

    st.subheader("Live Monitoring overview")
    duration = _number(session_record.get("duration_seconds"))
    a, b, c, d = st.columns(4)
    a.metric("Session duration", f"{duration:.1f} sec" if duration is not None else "N/A")
    b.metric("Recorded samples", summary.get("sample_count", 0))
    c.metric("Detected events", summary.get("event_count", 0))
    d.metric(
        "Session blinks",
        summary.get("session_blink_count")
        if summary.get("session_blink_count") is not None else "N/A",
    )

    if summary.get("measurements"):
        st.subheader("Measurement statistics")
        st.dataframe(
            [{
                "Measurement": item["measurement"],
                "Valid samples": item["valid_samples"],
                "Average": round(item["average"], 4),
                "Minimum": round(item["minimum"], 4),
                "Maximum": round(item["maximum"], 4),
            } for item in summary["measurements"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No valid numerical measurements were available for this session.")

    sample_frame = _session_metrics(session)
    available_metrics = [
        label for label in METRIC_LABELS.values()
        if not sample_frame.empty and label in sample_frame.columns
        and sample_frame[label].notna().any()
    ]
    st.subheader("Measurement trends")
    if available_metrics:
        selected_metric = st.selectbox(
            "Choose a measurement to graph",
            available_metrics,
            key="analytics_metric_selector",
        )
        chart_frame = sample_frame[["Elapsed seconds", selected_metric]].dropna()
        if not chart_frame.empty:
            chart_frame = chart_frame.set_index("Elapsed seconds")
            st.line_chart(chart_frame, height=280)
            st.caption(
                "The graph displays recorded values over elapsed session time. "
                "It does not show a validated pain scale."
            )
        else:
            st.info("There are no valid values to graph for this measurement.")
    else:
        st.info("No supported numerical measurement series is available to graph.")

    events = session.get("events") or []
    if events:
        event_counts = Counter(
            str(event.get("event", "Unspecified event"))
            for event in events if isinstance(event, dict)
        )
        st.subheader("Recorded event counts")
        st.bar_chart(
            pd.DataFrame(
                {"Event count": dict(event_counts)}
            )
        )
        st.dataframe(
            [{
                "Timestamp": event.get("timestamp"),
                "Elapsed seconds": event.get("elapsed_seconds"),
                "Event": event.get("event"),
            } for event in events if isinstance(event, dict)],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No event entries were recorded in this session.")

    st.divider()
    st.subheader("Guardian observation analysis")
    if guardians:
        frequency_counts = Counter(
            str(item.get("frequency"))
            for item in guardians
            if item.get("frequency") and str(item.get("frequency")).strip()
        )
        if frequency_counts:
            st.write("**Reported frequency responses across submissions**")
            st.bar_chart(pd.DataFrame({"Submissions": dict(frequency_counts)}))
        for record in guardians:
            with st.expander(
                f"Submission #{record.get('id')} — {record.get('created_at') or 'Date unavailable'}"
            ):
                st.write("**Unusual behaviour:**", _text(record.get("observed_behaviour")))
                st.write("**First noticed:**", _text(record.get("first_noticed")))
                st.write("**Frequency:**", _text(record.get("frequency")))
                st.write("**Usual duration:**", _text(record.get("duration")))
                st.write("**Possible triggers:**", _text(record.get("triggers")))
                st.write("**Different from usual:**", _text(record.get("different_from_usual")))
                changes = _safe_json_list(record.get("daily_changes"))
                st.write("**Daily changes:**", ", ".join(changes) if changes else "Not recorded")
    else:
        st.info("No Guardian Observations have been submitted for this patient.")

    st.divider()
    st.subheader("Body Map history")
    if body_records:
        region_counts = Counter()
        body_rows = []
        for record in body_records:
            regions = _safe_json_list(record.get("selected_regions"))
            for region in regions:
                region_counts[str(region)] += 1
            body_rows.append({
                "Date/time": record.get("created_at"),
                "Selected regions": ", ".join(str(r) for r in regions) or "Not recorded",
                "Body view": record.get("body_view"),
                "Input source": record.get("input_source"),
                "Notes": record.get("notes"),
            })
        if region_counts:
            st.write("**Frequency of recorded body regions**")
            st.bar_chart(pd.DataFrame({"Record count": dict(region_counts)}))
        st.dataframe(body_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Body Map entries are patient-level records. The database does not "
            "link them to a particular Live Monitoring session."
        )
    else:
        st.info("No patient-linked Body Map observations were found.")

    st.divider()
    st.subheader("Descriptive findings")
    for finding in findings:
        st.markdown(f"- {finding}")

    st.subheader("Reliability and interpretation")
    st.markdown(
        """
        - **Tracking quality** describes how successfully landmarks were detected; it is not confidence that pain is present.
        - Facial and body measurements can be affected by camera angle, lighting, movement, individual differences and tracking errors.
        - No paediatric clinical reference ranges or validated pain thresholds are applied.
        - Missing measurements are excluded from calculations rather than treated as zero.
        - Guardian responses are subjective reports and Body Map entries record reported/observed locations.
        - The report does not calculate a pain score, pain probability or diagnosis.
        """
    )
    st.warning(
        "PainLens AI is an experimental observation and communication aid. "
        "It cannot determine whether a child is in pain. Please use clinical "
        "judgement and consult a qualified healthcare professional, especially "
        "if the child has new, severe or worsening symptoms."
    )

    st.divider()
    st.subheader("Download combined report")
    report_html = _build_html_report(
        patient, guardians, body_records, session_record,
        session, summary, findings
    )
    safe_name = "".join(
        char if char.isalnum() or char in ("-", "_") else "_"
        for char in str(patient.get("name", "patient"))
    )
    st.download_button(
        "⬇️ Download complete report (HTML)",
        data=report_html.encode("utf-8"),
        file_name=f"PainLens_Combined_Report_{safe_name}_Session_{session_record.get('id', 'record')}.html",
        mime="text/html",
        use_container_width=True,
    )
    st.caption(
        "Open the downloaded HTML report in a browser and select "
        "'Print / Save as PDF' to create a PDF copy."
    )
