
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Client Log Matcher", layout="wide")
st.title("📞 Client Log Matcher + Stats Generator")

def normalize_phone(val):
    return "".join(filter(str.isdigit, str(val)))[-10:]

def detect_phone_column(df):
    candidates = ["phone number", "number dialed", "number", "client phone"]
    for col in df.columns:
        if col.strip().lower() in candidates:
            return col
    return None

uploaded_client = st.file_uploader("Upload Client and Phone List", type="csv", key="client_upload")
uploaded_log = st.file_uploader("Upload Call Log CSV", type="csv", key="log_upload")

if uploaded_client and uploaded_log:
    client_df = pd.read_csv(uploaded_client)
    log_df = pd.read_csv(uploaded_log)

    phone_col = detect_phone_column(client_df)
    if not phone_col:
        st.error("❌ Could not detect the phone number column in the client list.")
        st.stop()

    client_df["Phone Number"] = client_df[phone_col].apply(normalize_phone)
    log_df["Normalized Number"] = log_df.iloc[:, 5].apply(normalize_phone)  # column F
    log_df["Talk Time"] = pd.to_numeric(log_df.iloc[:, 10], errors="coerce")  # column K
    log_df["Lead Source"] = log_df.iloc[:, 19]  # column T
    log_df["DNC Flag"] = log_df.iloc[:, 27]  # column AB
    log_df["Vendor"] = log_df.iloc[:, 27]  # AB again used for Vendor when matched

    results = []
    seen = {}

    for _, row in client_df.iterrows():
        number = row["Phone Number"]
        name = row[0]
        match_rows = log_df[log_df["Normalized Number"] == number]

        if number == "" or pd.isna(number):
            results.append([name, "NEED TO CHECK", "", "", ""])
            continue

        if len(match_rows) == 0:
            results.append([name, number, "", "", ""])
        else:
            longest = match_rows.loc[match_rows["Talk Time"].idxmax()]
            if number not in seen:
                lead = longest["Lead Source"]
                vendor = longest["Vendor"] if lead == "MEDICARE CLOSER QUEUE" else ""
                dnc = "X" if "HEAP DNC UPLINE" in str(longest["DNC Flag"]) else ""
                results.append([name, number, lead, vendor, dnc])
                seen[number] = True
            else:
                results.append([name, number, "DUPLICATE", "", ""])

    final_df = pd.DataFrame(results, columns=["Client Name", "Phone Number", "Lead Source", "Vendor", "DNC"])

    # Queue stats
    source_counts = final_df["Lead Source"].value_counts()
    stats_df = pd.DataFrame({
        "Lead Source": source_counts.index,
        "SALES": source_counts.values
    })

    spacer = pd.DataFrame([[""] * 5], columns=final_df.columns)
    combined = pd.concat([final_df, spacer, spacer], ignore_index=True)

    stats_df.insert(0, "", "")
    stats_df.insert(1, "Total Calls", "")
    stats_df.insert(2, "Abandoned Calls", "")
    stats_df["Abandon %"] = ""
    stats_df["Close %"] = ""

    combined_stats = pd.concat([combined, stats_df], ignore_index=True)

    st.success("✅ Matching Complete")
    st.dataframe(combined_stats)

    csv = combined_stats.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Final Sheet", data=csv, file_name="Matched_Client_Stats.csv", mime="text/csv")
