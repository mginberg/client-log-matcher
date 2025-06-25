
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Client Log Matcher + Stats", layout="wide")
st.title("📞 Client Log Matcher + Stats Generator")

def normalize_phone(val):
    return "".join(filter(str.isdigit, str(val)))[-10:]

def detect_phone_column(df):
    for col in df.columns:
        col_clean = col.strip().lower().replace(":", "")
        if "phone" in col_clean or "number" in col_clean:
            return col
    return df.columns[5]

uploaded_client = st.file_uploader("Upload Client and Phone List", type="csv")
uploaded_log = st.file_uploader("Upload Call Log", type="csv")

if uploaded_client and uploaded_log:
    client_df = pd.read_csv(uploaded_client)
    log_df = pd.read_csv(uploaded_log)

    phone_col = detect_phone_column(client_df)
    client_df["Phone Number"] = client_df[phone_col].apply(normalize_phone)
    log_df["Normalized Number"] = log_df.iloc[:, 5].apply(normalize_phone)
    log_df["Talk Time"] = pd.to_numeric(log_df.iloc[:, 10], errors="coerce")
    log_df["Lead Source"] = log_df.iloc[:, 19]
    log_df["DNC Flag"] = log_df.iloc[:, 27]
    log_df["Vendor Source"] = log_df.iloc[:, 27]

    results = []
    seen = {}

    for _, row in client_df.iterrows():
        name = row[0]
        number = row["Phone Number"]

        if not number or number.strip() == "":
            results.append([name, "NEED TO CHECK", "", "", ""])
            continue

        matches = log_df[log_df["Normalized Number"] == number]

        if len(matches) == 0:
            results.append([name, number, "", "", ""])
        else:
            longest = matches.loc[matches["Talk Time"].idxmax()]
            if number not in seen:
                lead = longest["Lead Source"]
                vendor = longest["Vendor Source"] if lead == "MEDICARE CLOSER QUEUE" else ""
                dnc = "X" if "HEAP DNC UPLINE" in str(longest["DNC Flag"]) else ""
                results.append([name, number, lead, vendor, dnc])
                seen[number] = True
            else:
                results.append([name, number, "DUPLICATE", "", ""])

    result_df = pd.DataFrame(results, columns=["Client Name", "Phone Number", "Lead Source", "Vendor", "DNC"])

    # Add 2 blank rows
    spacer = pd.DataFrame([[""] * 5] * 2, columns=result_df.columns)
    combined = pd.concat([result_df, spacer], ignore_index=True)

    # Generate stats
    source_counts = result_df["Lead Source"].value_counts()
    stats_df = pd.DataFrame({
        "Lead Source": source_counts.index,
        "SALES": source_counts.values
    })

    stats_df.insert(0, "", "")
    stats_df.insert(1, "Total Calls", "")
    stats_df.insert(2, "Abandoned Calls", "")
    stats_df["Abandon %"] = ""
    stats_df["Close %"] = ""

    stats_df.columns = ["", "Total Calls", "Abandoned Calls", "Lead Source", "SALES", "Abandon %", "Close %"]
    final_output = pd.concat([combined, stats_df], ignore_index=True)

    st.success("✅ Matching Complete")
    st.dataframe(final_output)

    csv = final_output.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Final Sheet", data=csv, file_name="Matched_Client_Stats.csv", mime="text/csv")
