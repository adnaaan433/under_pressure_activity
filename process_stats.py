import pandas as pd
import glob
import os

def generate_player_stats_from_df(full_df):
    if full_df is None or full_df.empty:
        return pd.DataFrame()

    # Drop any rows where player_name is null
    full_df = full_df[full_df['player_name'].notna()].copy()

    # -- Definitions based on provided logic --

    # Passes
    succ_pass = (full_df['type_name'] == 'Pass') & (full_df['outcome_name'].isna())
    unsucc_pass = (full_df['type_name'] == 'Pass') & (full_df['outcome_name'] == 'Incomplete')

    # Carries
    carries = full_df['type_name'] == 'Carry'

    # Ball Retention
    dribbles_won = (full_df['type_name'] == 'Dribble') & (full_df['outcome_name'] == 'Complete')
    fouls_won = full_df['type_name'] == 'Foul Won'
    shields = full_df['type_name'] == 'Shield'
    ball_retention = dribbles_won | fouls_won | shields

    # Possession Lost
    dispossessed = full_df['type_name'] == 'Dispossessed'
    miscontrols = full_df['type_name'] == 'Miscontrol'
    dribbles_lost = (full_df['type_name'] == 'Dribble') & (full_df['outcome_name'] == 'Incomplete')
    errors = full_df['type_name'] == 'Error'
    possession_lost = dispossessed | miscontrols | dribbles_lost | errors

    # Assign calculation boolean masks as integer 1/0 inside the main dataframe
    full_df['successful_passes'] = succ_pass.astype(int)
    full_df['unsuccessful_passes'] = unsucc_pass.astype(int)
    full_df['carries_count'] = carries.astype(int)
    full_df['ball_retention'] = ball_retention.astype(int)
    full_df['possession_lost'] = possession_lost.astype(int)
    full_df['dribbles_won'] = dribbles_won.astype(int)
    full_df['dribbles_lost'] = dribbles_lost.astype(int)

    # Aggregate sums by player_name and team_name
    agg_df = full_df.groupby(['player_name', 'team_name'])[['successful_passes', 'unsuccessful_passes', 'carries_count', 'ball_retention', 'possession_lost', 'dribbles_won', 'dribbles_lost']].sum().reset_index()

    # Rename carries columns perfectly to match the naming
    agg_df.rename(columns={'carries_count': 'carries'}, inplace=True)

    return agg_df
