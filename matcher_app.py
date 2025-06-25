
import pandas as pd
import streamlit as st

st.title("Client Log Matcher")

client_file = st.file_uploader("Upload Client List CSV", type="csv")
log_file = st.file_uploader("Upload Call Log CSV", type="csv")

if client_file and log_file:
    client_df = pd.read_csv(client_file)
    call_df = pd.read_csv(log_file)

    # Clean client numbers to 10-digit format
    client_df['Phone Number'] = client_df.iloc[:, 1].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    call_df['Call Number'] = call_df.iloc[:, 5].astype(str).str.replace(r"\D", "", regex=True).str[-10:]

    client_df['Lead Source'] = ""
    client_df['Vendor'] = ""
    client_df['DNC'] = ""

    # Create a working copy of call_df to track longest duration
    call_df['Talk Time'] = pd.to_numeric(call_df.iloc[:, 10], errors='coerce').fillna(0)

    matched_rows = []
    seen_numbers = {}

    for i, row in client_df.iterrows():
        number = row['Phone Number']
        if number == "" or number.lower() == "nan":
            client_df.at[i, 'Phone Number'] = "NEED TO CHECK"
            continue

        matches = call_df[call_df['Call Number'] == number]

        if not matches.empty:
            # Pick row with longest talk time
            best_match = matches.sort_values(by='Talk Time', ascending=False).iloc[0]
            source = best_match.iloc[19]
            dnc_flag = best_match.iloc[27]
            vendor = best_match.iloc[27] if source == "MEDICARE CLOSER QUEUE" else ""

            if number in seen_numbers:
                client_df.at[i, 'Lead Source'] = "DUPLICATE"
            else:
                client_df.at[i, 'Lead Source'] = source
                client_df.at[i, 'Vendor'] = vendor
                if "HEAP DNC UPLINE" in str(dnc_flag).upper():
                    client_df.at[i, 'DNC'] = "X"
                seen_numbers[number] = i

    # Create stats section starting at column G, row 2
    stats = client_df['Lead Source'].value_counts().reset_index()
    stats.columns = ['Lead Source', 'SALES']
    stats = stats[stats['Lead Source'] != "NEED TO CHECK"]

    final_export = client_df.copy()
    for idx, row in stats.iterrows():
        final_export.loc[idx, 'G'] = row['Lead Source']
        final_export.loc[idx, 'H'] = row['SALES']

    st.success("✅ Matching complete!")
    st.download_button("Download Final Sheet", data=final_export.to_csv(index=False), file_name="Matched_Client_Stats.csv")
