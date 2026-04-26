import streamlit as st
import pandas as pd
from mplsoccer import Sbapi
import concurrent.futures

@st.cache_resource
def get_api():
    try:
        username = st.secrets["statsbomb"]["username"]
        password = st.secrets["statsbomb"]["password"]
        return Sbapi(username=username, password=password, dataframe=True)
    except Exception:
        return Sbapi(dataframe=True)

@st.cache_data
def load_competitions():
    api = get_api()
    df_comps = api.competition()
    return df_comps

@st.cache_data
def load_matches(competition_id, season_id):
    api = get_api()
    matches = api.match(competition_id, season_id)
    return matches

@st.cache_data(show_spinner="Downloading Player Stats from API...")
def load_player_season_stats(competition_id, season_id):
    import requests
    from requests.auth import HTTPBasicAuth
    
    url = f"https://data.statsbombservices.com/api/v4/competitions/{competition_id}/seasons/{season_id}/player-stats"
    try:
        username = st.secrets["statsbomb"]["username"]
        password = st.secrets["statsbomb"]["password"]
        resp = requests.get(url, auth=HTTPBasicAuth(username, password))
        if resp.status_code == 200:
            df = pd.DataFrame(resp.json())
            df['player_known_name'] = df['player_known_name'].fillna(df['player_name'])
            
            # Ensure columns exist before filtering, in case endpoint format shifts
            keep_cols = ['player_name', 'team_name', 'player_known_name', 'player_season_minutes', 'primary_position']
            existing_cols = [c for c in keep_cols if c in df.columns]
            
            return df[existing_cols]
        else:
            st.error(f"Failed to load player stats: HTTP {resp.status_code}")
    except Exception as e:
        st.error(f"API Error fetching player stats: {e}")
        
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def fetch_filtered_team_event(match_id, team_name):
    api = get_api()
    try:
        res = api.event(match_id)
        if res is not None:
            df = res[0]
            if 'team_name' in df.columns:
                df = df[df['team_name'] == team_name]
            if 'under_pressure' in df.columns:
                df = df[df['under_pressure'] == True]
                df = df[df['sub_type_name'] != 'Aerial Lost']
                df = df[df['type_name'].isin(['Carry', 'Pass', 'Dribble', 'Foul Won', 'Dispossessed', 'Miscontrol', 'Shield', 'Error'])]
                if 'type_name' in df.columns:
                    is_carry = df['type_name'] == 'Carry'
                    valid_carry = is_carry & (((df['x'] - df['end_x'])**2 + (df['y'] - df['end_y'])**2) > 25)
                    df = df[~is_carry | valid_carry]
            else:
                return None
            target_cols = ['type_name', 'sub_type_name', 'outcome_name', 'player_name', 'team_name', 'under_pressure', 'x', 'y', 'end_x', 'end_y', 'match_id', 'id', 'index']
            existing_cols = [c for c in target_cols if c in df.columns]
            return df[existing_cols]
    except Exception:
        pass
    return None

def load_team_events_from_api(competition_id, season_id, team_name, progress_bar=None, status_text=None):
    df_matches = load_matches(competition_id, season_id)
    if df_matches is None or df_matches.empty:
        return pd.DataFrame()
        
    team_matches = df_matches[(df_matches['home_team_name'] == team_name) | (df_matches['away_team_name'] == team_name)]
    if team_matches.empty:
        return pd.DataFrame()
        
    if 'match_status' in team_matches.columns:
        match_ids = team_matches[team_matches['match_status'] == 'available']['match_id'].tolist()
    else:
        match_ids = team_matches['match_id'].tolist()
        
    events_list = []
    total = len(match_ids)
    
    if total == 0:
        return pd.DataFrame()
        
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(fetch_filtered_team_event, mid, team_name) for mid in match_ids]
        for future in concurrent.futures.as_completed(futures):
            df_ep = future.result()
            if df_ep is not None and not df_ep.empty:
                events_list.append(df_ep)
                
            completed += 1
            if progress_bar is not None:
                progress_bar.progress(completed / total)
            if status_text is not None:
                status_text.text(f"Downloading events: {completed}/{total} matches completed...")
                
    if events_list:
        return pd.concat(events_list, ignore_index=True)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def fetch_filtered_comp_event(match_id):
    api = get_api()
    try:
        res = api.event(match_id)
        if res is not None:
            df = res[0]
            if 'under_pressure' in df.columns:
                df = df[df['under_pressure'] == True]
                df = df[df['sub_type_name'] != 'Aerial Lost']
                df = df[df['type_name'].isin(['Carry', 'Pass', 'Dribble', 'Foul Won', 'Dispossessed', 'Miscontrol', 'Shield', 'Error'])]
                if 'type_name' in df.columns:
                    is_carry = df['type_name'] == 'Carry'
                    valid_carry = is_carry & (((df['x'] - df['end_x'])**2 + (df['y'] - df['end_y'])**2) > 25)
                    df = df[~is_carry | valid_carry]
            else:
                return None
            target_cols = ['type_name', 'sub_type_name', 'outcome_name', 'player_name', 'team_name', 'under_pressure', 'x', 'y', 'end_x', 'end_y', 'match_id', 'id', 'index']
            existing_cols = [c for c in target_cols if c in df.columns]
            return df[existing_cols]
    except Exception:
        pass
    return None

def load_competition_events_from_api(competition_id, season_id, progress_bar=None, status_text=None):
    df_matches = load_matches(competition_id, season_id)
    if df_matches is None or df_matches.empty:
        return pd.DataFrame()
        
    if 'match_status' in df_matches.columns:
        match_ids = df_matches[df_matches['match_status'] == 'available']['match_id'].tolist()
    else:
        match_ids = df_matches['match_id'].tolist()
        
    events_list = []
    total = len(match_ids)
    
    if total == 0:
        return pd.DataFrame()
        
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(fetch_filtered_comp_event, mid) for mid in match_ids]
        for future in concurrent.futures.as_completed(futures):
            df_ep = future.result()
            if df_ep is not None and not df_ep.empty:
                events_list.append(df_ep)
                
            completed += 1
            if progress_bar is not None:
                progress_bar.progress(completed / total)
            if status_text is not None:
                status_text.text(f"Downloading events: {completed}/{total} matches completed...")
                
    if events_list:
        return pd.concat(events_list, ignore_index=True)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def calculate_player_stats(events_df, player_stats_df=None):
    import numpy as np
    
    if events_df is None or events_df.empty:
        return pd.DataFrame()

    events = events_df.copy()
    
    events['is_pass'] = events['type_name'] == 'Pass'
    events['is_successful_pass'] = events['is_pass'] & events['outcome_name'].isna()
    events['is_unsuccessful_pass'] = events['is_pass'] & (events['outcome_name'] == 'Incomplete')
    
    events['is_carry'] = events['type_name'] == 'Carry'
    events['is_dribble_won'] = (events['type_name'] == 'Dribble') & (events['outcome_name'] == 'Complete')
    events['is_dribble_lost'] = (events['type_name'] == 'Dribble') & (events['outcome_name'] == 'Incomplete')
    events['is_foul_won'] = events['type_name'] == 'Foul Won'
    events['is_shield'] = events['type_name'] == 'Shield'
    events['is_dispossessed'] = events['type_name'] == 'Dispossessed'
    events['is_miscontrol'] = events['type_name'] == 'Miscontrol'
    events['is_error'] = events['type_name'] == 'Error'

    stats = events.groupby('player_name').agg(
        successful_passes=('is_successful_pass', 'sum'),
        unsuccessful_passes=('is_unsuccessful_pass', 'sum'),
        carries=('is_carry', 'sum'),
        dribble_won=('is_dribble_won', 'sum'),
        dribble_lost=('is_dribble_lost', 'sum'),
        foul_won=('is_foul_won', 'sum'),
        shield=('is_shield', 'sum'),
        dispossessed=('is_dispossessed', 'sum'),
        miscontrol=('is_miscontrol', 'sum'),
        error=('is_error', 'sum'),
        team_name=('team_name', 'first')
    ).reset_index()

    

    if player_stats_df is not None and not player_stats_df.empty:
        stats = pd.merge(stats, player_stats_df, on='player_name', how='left')
        if 'team_name_y' in stats.columns:
            stats['team_name'] = stats['team_name_x']
            stats = stats.drop(columns=['team_name_x', 'team_name_y'])
            
        if 'player_known_name' in stats.columns:
            stats['player_known_name'] = stats['player_known_name'].fillna(stats['player_name'])
        else:
            stats['player_known_name'] = stats['player_name']
            
        if 'player_season_minutes' in stats.columns:
            mins = stats['player_season_minutes'].replace(0, np.nan)
            # stats['passes_p90'] = (stats['total_passes'] / mins) * 90
            # stats['carries_p90'] = (stats['carries'] / mins) * 90
            # stats['sustains_p90'] = (stats['sustains'] / mins) * 90
            # stats['loss_p90'] = (stats['poss_lost'] / mins) * 90
            # stats['total_actions_p90'] = (stats['total_actions'] / mins) * 90
            stats['successful_passes_p90'] = (stats['successful_passes'] / mins) * 90
            stats['unsuccessful_passes_p90'] = (stats['unsuccessful_passes'] / mins) * 90
            stats['pass_accuracy'] = (stats['successful_passes'] / (stats['successful_passes'] + stats['unsuccessful_passes'])) * 100
            stats['pass_accuracy'] = stats['pass_accuracy'].round(2)
            stats['carries_p90'] = (stats['carries'] / mins) * 90
            stats['dribble_won_p90'] = (stats['dribble_won'] / mins) * 90
            stats['dribble_lost_p90'] = (stats['dribble_lost'] / mins) * 90
            stats['foul_won_p90'] = (stats['foul_won'] / mins) * 90
            stats['shield_p90'] = (stats['shield'] / mins) * 90
            stats['dispossessed_p90'] = (stats['dispossessed'] / mins) * 90
            stats['miscontrol_p90'] = (stats['miscontrol'] / mins) * 90
            stats['error_p90'] = (stats['error'] / mins) * 90

            stats['total_pass_attempts_p90'] = stats['successful_passes_p90'] + stats['unsuccessful_passes_p90']
            stats['escape_pressure_p90'] = stats['carries_p90'] + stats['dribble_won_p90'] + stats['foul_won_p90']
            stats['under_pressure_success_rate'] = (stats['successful_passes_p90'] + stats['carries_p90'] + stats['dribble_won_p90'] + stats['shield_p90'] + stats['foul_won_p90'])/(stats['total_pass_attempts_p90'] +stats['carries_p90'] + stats['dribble_won_p90'] + stats['dribble_lost_p90'] + stats['dispossessed_p90'] + stats['miscontrol_p90'] + stats['error_p90'])*100
            stats['under_pressure_success_rate'] = stats['under_pressure_success_rate'].round(2)
            stats['under_pressure_losing_rate'] = (stats['dribble_lost_p90'] + stats['dispossessed_p90'] + stats['miscontrol_p90'] + stats['error_p90'])/(stats['total_pass_attempts_p90'] +stats['carries_p90'] + stats['dribble_won_p90'] + stats['dribble_lost_p90'] + stats['dispossessed_p90'] + stats['miscontrol_p90'] + stats['error_p90'])*100
            stats['under_pressure_losing_rate'] = stats['under_pressure_losing_rate'].round(2)
    else:
        stats['player_known_name'] = stats['player_name']
        
    return stats
