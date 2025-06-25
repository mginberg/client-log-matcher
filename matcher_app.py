
import streamlit as st
import pandas as pd
import numpy as np
import re

st.title("Client List and Call Log Matcher")

client_file = st.file_uploader("Upload the Client List CSV", type="csv")
call_log_file = st.file_uploader("Upload the Call Log CSV", type="csv")

if client_file and call_log_file:
    client_df = pd.read_csv(client_file)
    call_log_df = pd.read_csv(call_log_file)

    # Normalize phone numbers
    client_df["Phone Number"] = client_df["Phone Number"].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    call_log_df["Number Dialed"] = call_log_df["Number Dialed"].astype(str).str.replace(r"\D", "", regex=True).str[-10:]

    # Find columns
    talk_time_col = [col for col in call_log_df.columns if "talk" in col.lower()][0]
    source_col = call_log_df.columns[19]
    vendor_col = call_log_df.columns[27]

    results = []
    for _, row in client_df.iterrows():
        name, phone = row["Client Name"], row["Phone Number"]
        if not re.match(r"^\d{10}$", phone):
            results.append([name, phone, "NEED TO CHECK", "", ""])
            continue

        matches = call_log_df[call_log_df["Number Dialed"] == phone]
        if matches.empty:
            results.append([name, phone, "NEED TO CHECK", "", ""])
            continue

        # Pick row with longest talk time
        matches[talk_time_col] = pd.to_numeric(matches[talk_time_col], errors="coerce").fillna(0)
        matches = matches.sort_values(by=talk_time_col, ascending=False)
        top_row = matches.iloc[0]
        lead_source = top_row[source_col]
        vendor = top_row[vendor_col] if lead_source == "MEDICARE CLOSER QUEUE" else ""

        results.append([name, phone, lead_source, vendor, ""])
        for _, dup_row in matches.iloc[1:].iterrows():
            results.append([name, phone, "DUPLICATE", "", ""])

    export_df = pd.DataFrame(results, columns=["Client Name", "Phone Number", "Lead Source", "Vendor", "HEAP DNC"])

    # Flag HEAP DNC from call log AB column
    call_log_df["heap_flag"] = call_log_df.iloc[:, 27].astype(str).str.contains("HEAP DNC UPLINE")
    heap_numbers = call_log_df.loc[call_log_df["heap_flag"], "Number Dialed"].unique()
    export_df["HEAP DNC"] = export_df["Phone Number"].isin(heap_numbers).map({True: "X", False: ""})

    # Generate stats
    lead_source_counts = export_df["Lead Source"].value_counts().reset_index()
    lead_source_counts.columns = ["Lead Source", "SALES"]
    stat_section = pd.DataFrame({
        "G": lead_source_counts["Lead Source"],
        "H": "",  # CALLS
        "I": "",  # ABANDON
        "J": lead_source_counts["SALES"],
        "K": "=IF(H2="", "", J2/H2)",
    })

    # Pad to match rows
    export_df = pd.concat([export_df, pd.DataFrame([[""]*len(export_df.columns)]*2, columns=export_df.columns)], ignore_index=True)
    final_df = pd.DataFrame(columns=list("GHIJK"))
    for idx, row in lead_source_counts.iterrows():
        final_df.loc[idx, "G"] = row["Lead Source"]
        final_df.loc[idx, "H"] = ""
        final_df.loc[idx, "I"] = ""
        final_df.loc[idx, "J"] = row["SALES"]
        final_df.loc[idx, "K"] = f"=IF(H{idx+2}="", "", J{idx+2}/H{idx+2})"

    total_row = len(lead_source_counts) + 2
    final_df.loc[total_row-1, "G"] = "TOTAL"
    final_df.loc[total_row-1, "H"] = "=SUM(H2:H{})".format(total_row-1)
    final_df.loc[total_row-1, "I"] = "=SUM(I2:I{})".format(total_row-1)
    final_df.loc[total_row-1, "J"] = "=SUM(J2:J{})".format(total_row-1)
    final_df.loc[total_row-1, "K"] = "=IF(H{}="", "", J{}/H{})".format(total_row, total_row, total_row)

    # Combine
    export_df = pd.concat([export_df, final_df], axis=1)

    st.success("Matching complete. Download below.")
    st.download_button("Download Result CSV", export_df.to_csv(index=False).encode("utf-8"), file_name="Matched_Client_Stats.csv")
