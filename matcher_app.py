
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Client Log Matcher", layout="wide")
st.title("📞 Client & Call Log Matcher")

client_file = st.file_uploader("Upload Client List CSV", type="csv", key="client")
calllog_file = st.file_uploader("Upload Call Log CSV", type="csv", key="log")

if client_file and calllog_file:
    client_df = pd.read_csv(client_file)
    calllog_df = pd.read_csv(calllog_file)

    # Normalize phone numbers
    client_df['Phone Number'] = client_df.iloc[:, 1].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    calllog_df['Clean Number'] = calllog_df.iloc[:, 5].astype(str).str.replace(r"\D", "", regex=True).str[-10:]

    # Extract talk time as numeric seconds
    def parse_seconds(value):
        if pd.isnull(value): return 0
        parts = str(value).split(":")
        try:
            if len(parts) == 3:
                return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0])*60 + int(parts[1])
            else:
                return int(parts[0])
        except:
            return 0

    calllog_df['TalkTimeSeconds'] = calllog_df.iloc[:, 10].apply(parse_seconds)

    matched_data = []
    phone_counts = client_df['Phone Number'].value_counts()

    for idx, row in client_df.iterrows():
        name = row[0]
        phone = row['Phone Number']

        if phone == '' or pd.isnull(phone):
            matched_data.append([name, "NEED TO CHECK", "", "", ""])
            continue

        # Find matching rows in call log
        matches = calllog_df[calllog_df['Clean Number'] == phone]
        if matches.empty:
            matched_data.append([name, phone, "", "", ""])
        else:
            longest_row = matches.loc[matches['TalkTimeSeconds'].idxmax()]
            lead_source = longest_row.iloc[19]  # Column T (index 19)
            vendor = longest_row.iloc[27] if lead_source == "MEDICARE CLOSER QUEUE" else ""
            is_duplicate = phone_counts[phone] > 1

            # Mark DUPLICATE only on second or later instances
            already_used = any(p == phone and src != "DUPLICATE" for _, p, src, *_ in matched_data)
            if is_duplicate and already_used:
                matched_data.append([name, phone, "DUPLICATE", "", ""])
            else:
                dnc_flag = "X" if "HEAP DNC UPLINE" in str(longest_row.iloc[27]) else ""
                matched_data.append([name, phone, lead_source, vendor, dnc_flag])

    final_df = pd.DataFrame(matched_data, columns=["Client Name", "Phone Number", "Lead Source", "Vendor", "DNC"])

    # Build stats section starting at G2
    stat_section = final_df["Lead Source"].value_counts().reset_index()
    stat_section.columns = ["Lead Source", "SALES"]
    stat_section["Total Calls"] = ""
    stat_section["Abandoned Calls"] = ""
    stat_section["% SALES"] = "=H2/I2"
    stat_section["% Abandoned"] = "=J2/I2"

    # Combine into final export
    export_df = pd.DataFrame(columns=["Client Name", "Phone Number", "Lead Source", "Vendor", "DNC", "", ""])
    export_df = pd.concat([export_df, final_df], ignore_index=True)
    export_df.loc[0:len(stat_section)-1, ["G", "H", "I", "J", "K", "L"]] = stat_section.values

    # Write to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, header=False, startrow=1, startcol=0)
    st.success("✅ Matching complete!")
    st.download_button("📥 Download Matched File", data=output.getvalue(), file_name="Matched_Client_Stats.xlsx")
