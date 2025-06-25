
import streamlit as st
import pandas as pd

st.title("Client List & Call Log Matcher + Stats Generator")

# Upload files
file_1 = st.file_uploader("Upload Client and Phone List (File 1)", type="csv", key="file1")
file_2 = st.file_uploader("Upload Call Log (File 2)", type="csv", key="file2")

if file_1 and file_2:
    # Read files
    client_df = pd.read_csv(file_1)
    call_log_df = pd.read_csv(file_2)

    # Format phone numbers
    client_df['Phone Number'] = client_df['Phone Number'].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    call_log_df['Number Dialed'] = call_log_df['Number Dialed'].astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    call_log_df['Talk Time'] = pd.to_numeric(call_log_df['Talk Time'], errors='coerce')

    # Sort call log by talk time and drop duplicate phone numbers
    call_log_sorted = call_log_df.sort_values(by='Talk Time', ascending=False)
    longest_calls = call_log_sorted.drop_duplicates(subset='Number Dialed', keep='first')

    # Merge and match
    final_df = client_df.merge(
        longest_calls[['Number Dialed', 'Queue Name', 'Source Name']],
        left_on='Phone Number',
        right_on='Number Dialed',
        how='left'
    )

    # Handle duplicates: mark all but the first occurrence of a phone number as DUPLICATE
    final_df['Duplicate Flag'] = final_df.duplicated(subset='Phone Number', keep='first')
    final_df['Lead Source'] = final_df.apply(
        lambda row: "DUPLICATE" if row['Duplicate Flag'] else row['Queue Name'], axis=1
    )

    # Insert 'Vendor' column after 'Lead Source'
    final_df['Vendor'] = final_df.apply(
        lambda row: row['Source Name'] if row['Lead Source'] == "MEDICARE CLOSER QUEUE" else '', axis=1
    )

    # Create final columns
    final_df['HEAP DNC UPLINE'] = final_df['Source Name'].apply(
        lambda x: "X" if isinstance(x, str) and "HEAP DNC UPLINE" in x else ""
    )

    # Replace blank phone numbers with "NEED TO CHECK"
    final_df['Phone Number'] = final_df['Phone Number'].apply(lambda x: x if pd.notna(x) and x != '' else 'NEED TO CHECK')

    # Cleanup
    final_df.drop(columns=['Number Dialed', 'Source Name', 'Queue Name', 'Duplicate Flag'], inplace=True)

    # Rearrange columns to insert Vendor between Lead Source and HEAP DNC UPLINE
    cols = final_df.columns.tolist()
    vendor_index = cols.index('Lead Source') + 1
    cols = cols[:vendor_index] + ['Vendor'] + cols[vendor_index:-1] + ['HEAP DNC UPLINE']
    final_df = final_df[cols]

    # Generate stats section (count only non-duplicate sources)
    lead_source_counts = final_df[final_df['Lead Source'] != 'DUPLICATE']['Lead Source'].value_counts().reset_index()
    lead_source_counts.columns = ['QUEUE STATS', 'SALES']
    lead_source_counts['CALLS'] = ''
    lead_source_counts['ABANDON'] = ''
    lead_source_counts['CLOSING %'] = lead_source_counts.apply(
        lambda row: "=IF(B2=0, 0, D2/(B2-C2))", axis=1
    )
    lead_source_counts = lead_source_counts[['QUEUE STATS', 'CALLS', 'ABANDON', 'SALES', 'CLOSING %']]

    # Show preview
    st.success("File matched and stats generated successfully!")
    st.subheader("Matched Client List")
    st.dataframe(final_df.head(10))

    st.subheader("Queue Stats Preview")
    st.dataframe(lead_source_counts)

    # Save final result with both outputs
    combined_output = final_df.copy()
    for _ in range(3):
        combined_output = combined_output.append(pd.Series(), ignore_index=True)
    for i in range(len(lead_source_counts)):
        combined_output.loc[len(combined_output)] = [None]*len(combined_output.columns)

    # Concatenate stats with final file
    result_with_stats = pd.concat([combined_output, lead_source_counts], axis=1)

    # Download
    csv = result_with_stats.to_csv(index=False).encode('utf-8')
    st.download_button("Download Full Output with Stats", csv, "Matched_Client_List_with_Stats.csv", "text/csv")
