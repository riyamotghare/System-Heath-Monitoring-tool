"""app.py - Streamlit user interface for the IT Support & System Health Monitoring Tool."""

import plotly.graph_objects as go
import streamlit as st

import database as db
import monitor

st.set_page_config(page_title="IT Support & System Health", page_icon="🖥️", layout="wide")

# Create the database/table on startup (safe to run every time).
db.init_db()

st.title("🖥️ IT Support & System Health Monitoring Tool")
st.caption("Monitor this machine, run basic network checks, and manage support tickets.")

# ---------------------------------------------------------------------------
# Sidebar: configurable thresholds
# ---------------------------------------------------------------------------
st.sidebar.header("Alert Thresholds (%)")
thresholds = {
    "cpu": st.sidebar.slider("CPU", 1, 100, 85),
    "ram": st.sidebar.slider("RAM", 1, 100, 85),
    "disk": st.sidebar.slider("Disk", 1, 100, 90),
}
st.sidebar.info("Lower a threshold (e.g. to 5%) to see a warning appear.")

tab_health, tab_network, tab_tickets, tab_about = st.tabs(
    ["System Health", "Network Diagnostics", "Support Tickets", "About the Project"]
)

# ---------------------------------------------------------------------------
# Tab 1: System Health
# ---------------------------------------------------------------------------
with tab_health:
    st.subheader("System Health")
    st.button("🔄 Refresh metrics")  # any click reruns the script and re-reads psutil

    try:
        info = monitor.get_system_info()
        metrics = monitor.get_metrics()
    except Exception as exc:  # psutil can fail on restricted systems
        st.error(f"Could not read system metrics: {exc}")
    else:
        # Warnings first so they are impossible to miss
        warnings = monitor.check_thresholds(metrics, thresholds)
        if warnings:
            for message in warnings:
                st.warning(f"⚠️ {message}")
        else:
            st.success("All monitored resources are within their thresholds.")

        # Metric cards + progress bars
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("CPU Utilization", f"{metrics['cpu_percent']:.1f}%")
            st.progress(min(int(metrics["cpu_percent"]), 100) / 100)
        with c2:
            st.metric("RAM Utilization", f"{metrics['ram_percent']:.1f}%")
            st.progress(min(int(metrics["ram_percent"]), 100) / 100)
            st.caption(f"Total: {metrics['ram_total']} | Available: {metrics['ram_available']}")
        with c3:
            st.metric("Disk Utilization", f"{metrics['disk_percent']:.1f}%")
            st.progress(min(int(metrics["disk_percent"]), 100) / 100)
            st.caption(
                f"Drive {metrics['disk_path']} | Total: {metrics['disk_total']} "
                f"| Free: {metrics['disk_free']}"
            )

        # Usage vs threshold chart
        fig = go.Figure()
        fig.add_bar(
            x=["CPU", "RAM", "Disk"],
            y=[metrics["cpu_percent"], metrics["ram_percent"], metrics["disk_percent"]],
            name="Current usage",
        )
        fig.add_scatter(
            x=["CPU", "RAM", "Disk"],
            y=[thresholds["cpu"], thresholds["ram"], thresholds["disk"]],
            mode="markers",
            marker=dict(symbol="line-ew", size=40, line=dict(width=3, color="red")),
            name="Threshold",
        )
        fig.update_layout(
            yaxis=dict(range=[0, 100], title="Percent"),
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig)

        # System details
        st.markdown("#### System Details")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Hostname", info["hostname"])
        d2.metric("Operating System", info["os"])
        d3.metric(
            "CPU Cores",
            f"{info['cores_logical']} logical",
            f"{info['cores_physical']} physical" if info["cores_physical"] else None,
            delta_color="off",
        )
        d4.metric("Uptime", info["uptime"])
        st.caption(f"OS version: {info['os_version']}")

# ---------------------------------------------------------------------------
# Tab 2: Network Diagnostics
# ---------------------------------------------------------------------------
with tab_network:
    st.subheader("Network Diagnostics")
    st.write("Check whether a host responds to ping (ICMP echo requests).")

    with st.form("ping_form"):
        host_input = st.text_input("Hostname or IP address", placeholder="e.g. google.com or 8.8.8.8")
        ping_count = st.selectbox("Number of ping attempts", [1, 2, 4, 8], index=2)
        run_ping = st.form_submit_button("Run ping")

    if run_ping:
        with st.spinner("Pinging..."):
            result = monitor.ping_host(host_input, count=ping_count)

        if result["error"]:
            st.error(result["error"])
        elif result["success"]:
            st.success("✅ Response received: the host is reachable.")
        else:
            st.warning("❌ No response received from the host.")

        if result["output"]:
            st.code(result["output"], language="text")

        st.info(
            "**Note:** A failed ping does not always mean the host or service is down. "
            "Many firewalls and servers block ICMP traffic on purpose, so a website "
            "can work in a browser even when ping fails."
        )

# ---------------------------------------------------------------------------
# Tab 3: Support Tickets
# ---------------------------------------------------------------------------
with tab_tickets:
    st.subheader("Support Tickets")

    # Message saved before a rerun (so it survives the page refresh)
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

    st.markdown("#### Create a ticket")
    with st.form("ticket_form", clear_on_submit=True):
        title = st.text_input("Issue title")
        col_a, col_b = st.columns(2)
        category = col_a.selectbox("Category", db.CATEGORIES)
        priority = col_b.selectbox("Priority", db.PRIORITIES, index=1)
        description = st.text_area("Problem description")
        troubleshooting = st.text_area("Troubleshooting already attempted")
        submitted = st.form_submit_button("Submit ticket")

    if submitted:
        try:
            new_id = db.create_ticket(title, category, priority, description, troubleshooting)
            st.success(f"Ticket #{new_id} created.")
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Could not save the ticket: {exc}")

    st.divider()
    st.markdown("#### All tickets")
    status_filter = st.selectbox("Filter by status", ["All"] + db.STATUSES)

    try:
        tickets = db.get_tickets(status_filter)
        all_tickets = db.get_tickets()
    except Exception as exc:
        st.error(f"Could not load tickets: {exc}")
        tickets = all_tickets = None

    if all_tickets is not None:
        m1, m2, m3 = st.columns(3)
        for col, status in zip((m1, m2, m3), db.STATUSES):
            col.metric(status, int((all_tickets["status"] == status).sum()))

        if tickets.empty:
            st.info("No tickets to show. Create one above.")
        else:
            st.dataframe(
                tickets.rename(
                    columns={
                        "id": "ID", "title": "Title", "category": "Category",
                        "priority": "Priority", "description": "Description",
                        "troubleshooting": "Troubleshooting", "status": "Status",
                        "created_at": "Created", "updated_at": "Updated",
                    }
                ),
                hide_index=True,
            )

            st.markdown("#### Update ticket status")
            labels = {
                int(row.id): f"#{row.id} - {row.title} ({row.status})"
                for row in all_tickets.itertuples()
            }
            with st.form("status_form"):
                ticket_id = st.selectbox(
                    "Ticket", list(labels.keys()), format_func=lambda i: labels[i]
                )
                new_status = st.selectbox("New status", db.STATUSES)
                update = st.form_submit_button("Update status")
            if update:
                try:
                    if db.update_ticket_status(ticket_id, new_status):
                        st.session_state["flash"] = f"Ticket #{ticket_id} set to '{new_status}'."
                        st.rerun()  # rerun so the table above shows the new status
                    else:
                        st.error("Ticket not found.")
                except Exception as exc:
                    st.error(f"Could not update the ticket: {exc}")

# ---------------------------------------------------------------------------
# Tab 4: About
# ---------------------------------------------------------------------------
with tab_about:
    st.subheader("About the Project")
    st.markdown(
        """
**Purpose:** A local Python tool that shows how basic IT support work can be automated:
checking machine health, running connectivity checks, and tracking incidents.

**Technologies:** Python, Streamlit, psutil, SQLite, Pandas, Plotly, subprocess.

**How it works**
- `monitor.py` reads live CPU, RAM, disk and OS data with psutil and runs the OS `ping` command safely.
- `database.py` stores tickets in a local SQLite file using parameterized queries.
- `app.py` builds the tabbed Streamlit interface and connects the two modules.

**Limitations**
- Monitors only the machine it runs on, with no history or background alerting.
- No login or user roles; tickets are stored in a single local file.
- Ping only tests ICMP reachability, not whether a specific service or port is working.
- A learning/portfolio project, not a production or enterprise tool.
        """
    )
