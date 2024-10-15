import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import numpy as np
import pydeck as pdk

# Function to get the latest CSV file from the archive folder
def get_latest_csv():
    archive_folder = 'archive'
    csv_files = [f for f in os.listdir(archive_folder) if f.startswith('IOCL_') and f.endswith('.csv')]
    if not csv_files:
        return None
    latest_file = max(csv_files, key=lambda x: datetime.strptime(x[5:-4], '%Y_%m_%d_%H%M%S'))
    return os.path.join(archive_folder, latest_file)

# Load the data
@st.cache_data
def load_data():
    csv_file = get_latest_csv()
    if csv_file is None:
        st.error("No CSV file found in the archive folder.")
        return None
    df = pd.read_csv(csv_file, delimiter='|')
    
    # Convert price columns to numeric, replacing 'Not Available' with NaN
    price_columns = ['Petrol Price', 'Diesel Price', 'XTRAPREMIUM Price', 'XTRAMILE Price']
    for col in price_columns:
        df[col] = pd.to_numeric(df[col].replace('Not Available', np.nan), errors='coerce')
    
    # Rename latitude and longitude columns and convert to float
    df = df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    
    return df

# Function to create map
def create_map(df):
    # Remove rows with invalid coordinates
    map_df = df.dropna(subset=['lat', 'lon'])
    
    # Check if there are any valid coordinates
    if map_df.empty:
        st.warning("No valid location data available for the selected filters.")
        return None

    # Calculate the center of the map
    center_lat = map_df['lat'].mean()
    center_lon = map_df['lon'].mean()

    # Create the map layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        map_df,
        get_position=['lon', 'lat'],
        get_color=[200, 30, 0, 160],
        get_radius=100,
        pickable=True
    )

    # Set the view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=10,
        pitch=0
    )

    # Create the map
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{Petrol Pump Name}\nPetrol: ₹{Petrol Price}\nDiesel: ₹{Diesel Price}"}
    )

    return r

# Main app
def main():
    st.title("IOCL Petrol Bunk Dashboard")

    df = load_data()
    if df is None:
        return

    # Sidebar filters
    st.sidebar.header("Filters")
    selected_state = st.sidebar.selectbox("Select State", ["All"] + sorted(df["State"].unique().tolist()))
    
    # Update district options based on selected state
    if selected_state != "All":
        district_options = ["All"] + sorted(df[df["State"] == selected_state]["District"].unique().tolist())
    else:
        district_options = ["All"] + sorted(df["District"].unique().tolist())
    
    selected_district = st.sidebar.selectbox("Select District", district_options)

    # Apply filters
    if selected_state != "All":
        df = df[df["State"] == selected_state]
    if selected_district != "All":
        df = df[df["District"] == selected_district]

    # Display basic stats
    st.header("Basic Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Petrol Bunks", len(df))
    col2.metric("Average Petrol Price", f"₹{df['Petrol Price'].mean():.2f}")
    col3.metric("Average Diesel Price", f"₹{df['Diesel Price'].mean():.2f}")

    # Price comparison chart
    st.header("Fuel Price Comparison")
    price_df = df[["Petrol Price", "Diesel Price", "XTRAPREMIUM Price", "XTRAMILE Price"]].mean().reset_index()
    price_df.columns = ["Fuel Type", "Average Price"]
    fig = px.bar(price_df, x="Fuel Type", y="Average Price", title="Average Fuel Prices")
    st.plotly_chart(fig)

    # Map of petrol bunks
    st.header("Petrol Bunk Locations")
    map_chart = create_map(df)
    if map_chart:
        st.pydeck_chart(map_chart)

    # Data table
    st.header("Petrol Bunk Details")
    st.dataframe(df[["Petrol Pump Name", "Address", "Contact No", "Petrol Price", "Diesel Price", "District", "State"]])

if __name__ == "__main__":
    main()