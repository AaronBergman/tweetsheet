import streamlit as st
import json
import zipfile
from collections.abc import MutableMapping
import os
import pandas as pd  # Added for CSV processing

# Flatten nested dictionaries
def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

# Filtered flatten - keeps only specified keys
def filtered_flatten(d, keys_to_keep, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if new_key in keys_to_keep:
            if isinstance(v, MutableMapping):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
    return dict(items)

def process_file(uploaded_file_content):
    try:
        contents = uploaded_file_content.decode('utf-8')

        # Adjusted to handle the specific format of tweets.js
        json_start_index = contents.find('[')
        json_end_index = contents.rfind(']') + 1
        if json_start_index == -1 or json_end_index == -1:
            raise ValueError("Invalid JSON format in tweets.js")

        trimmed_contents = contents[json_start_index:json_end_index]

        data = json.loads(trimmed_contents)

        keys_to_keep = [
            'entities_user_mentions',
            'favorite_count',
            'in_reply_to_status_id_str',
            'id_str',
            'retweet_count',
            'created_at',
            'full_text',
            'in_reply_to_screen_name'
        ]

        # Process each tweet in the data
        processed_tweets = []
        for tweet_wrapper in data:
            tweet = tweet_wrapper.get("tweet", {})
            flattened_tweet = filtered_flatten(tweet, keys_to_keep)
            if flattened_tweet:
                processed_tweets.append(flattened_tweet)

        return processed_tweets
    except json.JSONDecodeError as e:
        st.error("JSON decoding failed. Please check the file format.")
        st.error(f"Error details: {e}")
        return None
    except Exception as e:
        st.error("An error occurred while processing the file.")
        st.error(f"Error details: {e}")
        return None

st.title("Twitter Data Extractor")

uploaded_file = st.file_uploader("Upload your tweets.zip file", type="zip")

if uploaded_file is not None:
    zip_file_name = uploaded_file.name
    base_folder_name = os.path.splitext(zip_file_name)[0]

    with zipfile.ZipFile(uploaded_file, 'r') as zipped_file:
        path_in_zip = os.path.join(base_folder_name, 'data', 'tweets.js')
        if path_in_zip in zipped_file.namelist():
            with zipped_file.open(path_in_zip) as tweets_js_file:
                tweets_js_content = tweets_js_file.read()

        else:
            st.error(f"The zip file does not contain '{path_in_zip}'. Please check the file and try again.")
            st.stop()

    processed_data = process_file(tweets_js_content)
# ... [rest of your code remains unchanged] ...

    if processed_data:
        # Create DataFrame from processed data
        df = pd.DataFrame(processed_data)

        # Convert 'created_at' to datetime
        df['created_at'] = pd.to_datetime(df['created_at'], format='%a %b %d %H:%M:%S %z %Y')

        # Rename and modify 'id' column
        df['link'] = 'https://x.com/u/status/' + df['id_str'].astype(str)
        df.drop(columns='id_str', inplace=True)  # Remove the original 'id_str' column

        # Rename other columns
        rename_dict = {
            'in_reply_to_screen_name': 'user_replying_to',
            'in_reply_to_status_id_str': 'tweet_replying_to'
        }
        df.rename(columns=rename_dict, inplace=True)

        # Rearrange columns
        ordered_columns = [
            'created_at',
            'full_text',
            'favorite_count',
            'retweet_count',
            'user_replying_to',
            'link',
            'tweet_replying_to'
        ]
        df = df[ordered_columns]  # Reorder columns

        # Display the transformed DataFrame
        st.write("### Processed Data")
        st.dataframe(df)

        # CSV Download
        csv = df.to_csv(index=False)
        st.download_button(label="Download Processed Data as CSV", data=csv, file_name="processed_data.csv", mime='text/csv')
    else:
        st.warning("Unable to process the provided tweets.js file. Please ensure it's the correct format.")
