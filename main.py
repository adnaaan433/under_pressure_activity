import streamlit as st
import pandas as pd
from data_loader import load_competitions, load_matches, load_team_events_from_api, load_player_season_stats, load_competition_events_from_api, calculate_player_stats
from visuals import visualize_passes_carries_pitch_only
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

st.set_page_config(page_title="StatsBomb Data Engine", layout="wide")

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Please enter the password to access the app", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Please enter the password to access the app", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()  # Do not continue if check_password is not True.

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pitch Visualization", "Scatter Visualization"])

# Load competitions and seasons
try:
    df_comps = load_competitions()
except Exception as e:
    st.error(f"Error loading competitions: {e}")
    df_comps = pd.DataFrame()

if df_comps is not None and not df_comps.empty:
    # Get unique competition names
    comp_names = df_comps['competition_name'].unique().tolist()
    
    if page == "Pitch Visualization":
        st.title("🎯 Team Events Pitch Visualization")
        
        # Select single comp/season
        col1, col2 = st.columns(2)
        with col1:
            viz3_comp = st.selectbox("Select Competition", comp_names, key='viz3_comp')
            
        viz3_comp_filtered = df_comps[df_comps['competition_name'] == viz3_comp]
        viz3_season_names = viz3_comp_filtered['season_name'].unique().tolist()
        
        with col2:
            viz3_season = st.selectbox("Select Season", viz3_season_names, key='viz3_season')
            
        viz3_row = df_comps[(df_comps['competition_name'] == viz3_comp) & (df_comps['season_name'] == viz3_season)]
        
        if not viz3_row.empty:
            comp_id = viz3_row.iloc[0]['competition_id']
            season_id = viz3_row.iloc[0]['season_id']
            
            with st.spinner("Loading teams for this competition..."):
                matches_df = load_matches(comp_id, season_id)
                
            if matches_df is not None and not matches_df.empty:
                team_names = pd.concat([matches_df['home_team_name'], matches_df['away_team_name']]).dropna().unique()
                team_names = sorted(team_names.tolist())
                
                selected_team = st.selectbox("Select Team", team_names, key='viz3_team')
                
                if st.button("Load Team Events"):
                    with st.spinner(f"Fetching complete match events for {selected_team}..."):
                        status_text = st.empty()
                        progress_bar = st.progress(0)
                        
                        team_events = load_team_events_from_api(comp_id, season_id, selected_team, progress_bar=progress_bar, status_text=status_text)
                        
                        if team_events is not None and not team_events.empty:
                            with st.spinner("Fetching mapping for player known names..."):
                                df_api = load_player_season_stats(comp_id, season_id)
                                if not df_api.empty and 'player_known_name' in df_api.columns:
                                    mapping_cols = ['player_name', 'player_known_name']
                                    if 'player_season_minutes' in df_api.columns:
                                        mapping_cols.append('player_season_minutes')
                                    p_mapping = df_api[mapping_cols].drop_duplicates(subset=['player_name'])
                                    team_events = pd.merge(team_events, p_mapping, on='player_name', how='left')
                                    team_events['player_known_name'] = team_events['player_known_name'].fillna(team_events['player_name'])
                                else:
                                    team_events['player_known_name'] = team_events['player_name']
                        
                        status_text.empty()
                        progress_bar.empty()
                        
                        if team_events is not None and not team_events.empty:
                            st.session_state['viz3_team_events'] = team_events
                            st.success(f"Successfully loaded {len(team_events)} under-pressure events for {selected_team}.")
                        else:
                            st.error(f"No valid under-pressure events found for {selected_team} in this competition.")
            else:
                st.error("No matches found for this competition/season.")
                
        if 'viz3_team_events' in st.session_state:
            viz3_events = st.session_state['viz3_team_events']
            
            if 'player_name' in viz3_events.columns:
                if 'player_known_name' not in viz3_events.columns:
                    viz3_events['player_known_name'] = viz3_events['player_name']
                    
                unique_players_df = viz3_events[['player_name', 'player_known_name']].drop_duplicates().dropna()
                unique_players_df = unique_players_df.sort_values('player_known_name')
                player_mapping = dict(zip(unique_players_df['player_known_name'], unique_players_df['player_name']))
                
                selected_known_name = st.selectbox("Select Player for Visualization", list(player_mapping.keys()), key='viz3_player')
                
                if selected_known_name:
                    selected_player = player_mapping[selected_known_name]
                    st.write(f"{selected_known_name}: Under Pressure Actions")
                    visualize_passes_carries_pitch_only(viz3_events, selected_player, selected_known_name, selected_team, viz3_comp, viz3_season)

    elif page == "Scatter Visualization":
        st.title("📈 Scatter Visualization")
        
        col1, col2 = st.columns(2)
        with col1:
            scatter_comp = st.selectbox("Select Competition", comp_names, key='scatter_comp')
            
        scatter_comp_filtered = df_comps[df_comps['competition_name'] == scatter_comp]
        scatter_season_names = scatter_comp_filtered['season_name'].unique().tolist()
        
        with col2:
            scatter_season = st.selectbox("Select Season", scatter_season_names, key='scatter_season')
            
        scatter_row = df_comps[(df_comps['competition_name'] == scatter_comp) & (df_comps['season_name'] == scatter_season)]
        
        if not scatter_row.empty:
            comp_id = scatter_row.iloc[0]['competition_id']
            season_id = scatter_row.iloc[0]['season_id']
            
            if st.button("Load Data"):
                with st.spinner(f"Fetching complete match events for all teams in {scatter_comp}..."):
                    status_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    comp_events = load_competition_events_from_api(comp_id, season_id, progress_bar=progress_bar, status_text=status_text)
                    
                    if comp_events is not None and not comp_events.empty:
                        with st.spinner("Fetching mapping & calculating aggregate statistics..."):
                            df_api = load_player_season_stats(comp_id, season_id)
                            player_stats_df = df_api if not df_api.empty else None
                            
                            aggregated_stats = calculate_player_stats(comp_events, player_stats_df)
                            
                            if not aggregated_stats.empty:
                                st.session_state['scatter_aggregated_stats'] = aggregated_stats
                                st.success(f"Successfully calculated stats for {len(aggregated_stats)} players.")
                            else:
                                st.error("Failed to calculate player statistics.")
                    else:
                        st.error("No valid under-pressure events found for this competition.")
                    
                    status_text.empty()
                    progress_bar.empty()
                    
        if 'scatter_aggregated_stats' in st.session_state:
            st.write("### Player Statistics Dataframe")
            df_stats = st.session_state['scatter_aggregated_stats'].copy()
            
            # Position filter (multiselect)
            if 'primary_position' in df_stats.columns:
                # st.text(df_stats['primary_position'].unique())
                position_groups = {
                    'FW': ['Centre Forward', 'Right Centre Forward', 'Left Centre Forward'],
                    'Winger/AM': ['Right Wing', 'Left Wing', 'Right Midfielder', 'Left Midfielder', 'Centre Attacking Midfielder', 'Left Attacking Midfielder', 'Right Attacking Midfielder'],
                    'MID': ['Right Centre Midfielder', 'Left Centre Midfielder', 'Centre Defensive Midfielder', 'Right Defensive Midfielder', 'Left Defensive Midfielder'],
                    'FB': ['Right Wing Back', 'Left Wing Back', 'Right Back', 'Left Back'],
                    'CB': ['Centre Back', 'Right Centre Back', 'Left Centre Back'],
                    'GK': ['Goalkeeper']
                }
                
                group_options = list(position_groups.keys())
                selected_groups = st.multiselect("Filter by Primary Position", options=group_options, default=[group_options[0]])
                
                if selected_groups:
                    selected_raw_positions = []
                    for group in selected_groups:
                        selected_raw_positions.extend(position_groups[group])
                    df_stats = df_stats[df_stats['primary_position'].isin(selected_raw_positions)]
                else:
                    df_stats = df_stats.iloc[0:0]
            
            # Minutes filter (slider with step=100)
            if 'player_season_minutes' in df_stats.columns:
                max_mins = int(df_stats['player_season_minutes'].max()) if not df_stats['player_season_minutes'].empty and not pd.isna(df_stats['player_season_minutes'].max()) else 3000
                min_mins = 0
                selected_mins = st.slider("Minimum Player Season Minutes", min_value=min_mins, max_value=max_mins, value=min(1000, max_mins), step=100)
                df_stats = df_stats[df_stats['player_season_minutes'] >= selected_mins]
            
            st.dataframe(df_stats)
            
            st.write("### Player Performance Under Pressure")
            
            # Option to filter labeled players to prevent congestion
            label_all = st.checkbox("Label all players (uncheck to label outer points only)", value=False)
            
            # Option to label only a single team's players
            label_single_team = st.checkbox("Label single team", value=False)
            selected_label_team = None
            if label_single_team and 'team_name' in df_stats.columns:
                team_names_list = sorted(df_stats['team_name'].dropna().unique().tolist())
                selected_label_team = st.selectbox("Select team to label", team_names_list, key='scatter_label_team')
            
            import matplotlib.font_manager as fm
            import matplotlib.patheffects as patheffects
            import os
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            boldonse_path = os.path.join(current_dir, "Boldonse-Regular.ttf")
            notosans_path = os.path.join(current_dir, "NotoSans_Condensed-Regular.ttf")
            boldonse_prop = fm.FontProperties(fname=boldonse_path)
            notosans_prop = fm.FontProperties(fname=notosans_path)
            try:
                fm.fontManager.addfont(notosans_path)
            except Exception:
                pass
            
            orig_font = plt.rcParams.get('font.family')
            plt.rcParams['font.family'] = notosans_prop.get_name()
            
            fig, ax = plt.subplots(figsize=(16, 9))
            # Define custom colormap as requested
            cmap = LinearSegmentedColormap.from_list('custom_cmap', ['red', 'orange', 'green'])
            
            # Filter NaNs for plotting to avoid matplotlib errors
            plot_df = df_stats.dropna(subset=['total_pass_attempts_p90', 'escape_pressure_p90', 'under_pressure_success_rate'])
            
            if not plot_df.empty:
                sc = ax.scatter(plot_df['total_pass_attempts_p90'], 
                                plot_df['escape_pressure_p90'], 
                                c=plot_df['under_pressure_success_rate'], 
                                cmap=cmap, alpha=0.8, edgecolors='w', s=60)
                
                x_median = plot_df['total_pass_attempts_p90'].median()
                y_median = plot_df['escape_pressure_p90'].median()
                ax.axvline(x=x_median, color='gray', linestyle='--', alpha=1, zorder=0)
                ax.axhline(y=y_median, color='gray', linestyle='--', alpha=1, zorder=0)
                
                # Annotate each point with the player's shortened name using adjustText
                from adjustText import adjust_text
                import numpy as np
                texts = []

                # Pre-compute normalised distances from median intersection for font sizing
                x_std = plot_df['total_pass_attempts_p90'].std() or 1
                y_std = plot_df['escape_pressure_p90'].std() or 1
                distances = np.sqrt(
                    ((plot_df['total_pass_attempts_p90'] - x_median) / x_std) ** 2 +
                    ((plot_df['escape_pressure_p90'] - y_median) / y_std) ** 2
                )
                dist_min, dist_max = distances.min(), distances.max()
                # font_min, font_max = 7.5, 12.0
                font_min, font_max = 10, 12

                if not label_all and not label_single_team:
                    # Determine boundaries for outer points (e.g. top/bottom 30%)
                    q_x_high = plot_df['total_pass_attempts_p90'].quantile(0.85)
                    q_x_low = plot_df['total_pass_attempts_p90'].quantile(0.15)
                    q_y_high = plot_df['escape_pressure_p90'].quantile(0.85)
                    q_y_low = plot_df['escape_pressure_p90'].quantile(0.15)

                for idx, row in plot_df.iterrows():
                    # When "Label single team" is active, only annotate players from the selected team
                    if label_single_team and selected_label_team:
                        if row.get('team_name') != selected_label_team:
                            continue
                    elif not label_all:
                        x_val = row['total_pass_attempts_p90']
                        y_val = row['escape_pressure_p90']
                        is_outer = (x_val >= q_x_high or x_val <= q_x_low or 
                                    y_val >= q_y_high or y_val <= q_y_low)
                        if not is_outer:
                            continue

                    name = str(row['player_known_name'])
                    parts = name.split()
                    if len(parts) > 1:
                        short_name = f"{parts[0][0]}. {' '.join(parts[1:])}"
                    else:
                        short_name = name

                    # Scale font size linearly with distance from median intersection
                    d = distances.loc[idx]
                    if dist_max > dist_min:
                        norm_d = (d - dist_min) / (dist_max - dist_min)
                    else:
                        norm_d = 0.0
                    font_size = font_min + norm_d * (font_max - font_min)

                    texts.append(ax.text(row['total_pass_attempts_p90'], row['escape_pressure_p90'], 
                                         short_name, fontsize=font_size, alpha=0.9))
                
                if texts:
                    adjust_text(texts, 
                                force_points=0.8,
                                force_text=1.0, 
                                expand_points=(1.3, 1.3), 
                                expand_text=(1.2, 1.2),
                                max_move=4.0,
                                lim=500,
                                only_move={'points': 'xy', 'text': 'xy'},
                                arrowprops=dict(arrowstyle='-', color='gray', lw=0.5, alpha=0.6))

                cbar = plt.colorbar(sc, ax=ax, label='Under Pressure Success Rate (%)')
                cbar.ax.yaxis.label.set_fontsize(15)
                xlabel = ax.set_xlabel('Pass the ball (per90)', fontsize=15)
                ylabel = ax.set_ylabel('Escapes Pressure (per90)', fontsize=15)
                faux_bold = [patheffects.withStroke(linewidth=0.8, foreground='black')]
                xlabel.set_path_effects(faux_bold)
                ylabel.set_path_effects(faux_bold)
                # cbar.ax.yaxis.label.set_path_effects(faux_bold)
                
                # Make the plot background look good
                ax.grid(True, linestyle='--', alpha=0.33)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_visible(False)
                ax.spines['bottom'].set_visible(False)

                fig.text(0.45, 1, 'What Players do Under Pressure?', ha='center', va='center', fontproperties=fm.FontProperties(fname=boldonse_path, size=20))
                positions_label = '/'.join(selected_groups)
                fig.text(0.45, 0.95, f'{scatter_comp} {positions_label}s with {selected_mins}+ minutes played in {scatter_season} season | Data: Statsbomb | made by: @adnaaan433', ha='center', va='center', fontsize=15)
                fig.text(0.45, 0.92, 'Escape Pressure: Player tries to escape the pressure with Take-On or Carry the ball out', ha='center', va='center', fontsize=15)
                
                st.pyplot(fig)
            else:
                st.info("Not enough data to plot the scatter visualization.")

            st.write("### Player accuracy vs losing")
            
            label_all2 = st.checkbox("Label all players (uncheck to label outer points only)", value=False, key="label_all2")
            
            label_single_team2 = st.checkbox("Label single team", value=False, key="label_single_team2")
            selected_label_team2 = None
            if label_single_team2 and 'team_name' in df_stats.columns:
                team_names_list2 = sorted(df_stats['team_name'].dropna().unique().tolist())
                selected_label_team2 = st.selectbox("Select team to label", team_names_list2, key='scatter_label_team2')
            
            fig2, ax2 = plt.subplots(figsize=(16, 9))
            
            # Filter NaNs for plotting to avoid matplotlib errors
            plot_df2 = df_stats.dropna(subset=['pass_accuracy', 'under_pressure_losing_rate'])
            
            if not plot_df2.empty:
                sc2 = ax2.scatter(plot_df2['pass_accuracy'], 
                                plot_df2['under_pressure_losing_rate'], 
                                color='#1f77b4', alpha=0.8, edgecolors='w', s=60)
                
                x_median2 = plot_df2['pass_accuracy'].median()
                y_median2 = plot_df2['under_pressure_losing_rate'].median()
                ax2.axvline(x=x_median2, color='gray', linestyle='--', alpha=1, zorder=0)
                ax2.axhline(y=y_median2, color='gray', linestyle='--', alpha=1, zorder=0)
                
                # Annotate each point with the player's shortened name using adjustText
                texts2 = []

                # Pre-compute normalised distances from median intersection for font sizing
                x_std2 = plot_df2['pass_accuracy'].std() or 1
                y_std2 = plot_df2['under_pressure_losing_rate'].std() or 1
                distances2 = np.sqrt(
                    ((plot_df2['pass_accuracy'] - x_median2) / x_std2) ** 2 +
                    ((plot_df2['under_pressure_losing_rate'] - y_median2) / y_std2) ** 2
                )
                dist_min2, dist_max2 = distances2.min(), distances2.max()

                if not label_all2 and not label_single_team2:
                    # Determine boundaries for outer points
                    q_x_high2 = plot_df2['pass_accuracy'].quantile(0.85)
                    q_x_low2 = plot_df2['pass_accuracy'].quantile(0.15)
                    q_y_high2 = plot_df2['under_pressure_losing_rate'].quantile(0.85)
                    q_y_low2 = plot_df2['under_pressure_losing_rate'].quantile(0.15)

                for idx, row in plot_df2.iterrows():
                    # When "Label single team" is active, only annotate players from the selected team
                    if label_single_team2 and selected_label_team2:
                        if row.get('team_name') != selected_label_team2:
                            continue
                    elif not label_all2:
                        x_val = row['pass_accuracy']
                        y_val = row['under_pressure_losing_rate']
                        is_outer = (x_val >= q_x_high2 or x_val <= q_x_low2 or 
                                    y_val >= q_y_high2 or y_val <= q_y_low2)
                        if not is_outer:
                            continue

                    name = str(row['player_known_name'])
                    parts = name.split()
                    if len(parts) > 1:
                        short_name = f"{parts[0][0]}. {' '.join(parts[1:])}"
                    else:
                        short_name = name

                    # Scale font size linearly with distance from median intersection
                    d = distances2.loc[idx]
                    if dist_max2 > dist_min2:
                        norm_d = (d - dist_min2) / (dist_max2 - dist_min2)
                    else:
                        norm_d = 0.0
                    font_size = font_min + norm_d * (font_max - font_min)

                    texts2.append(ax2.text(row['pass_accuracy'], row['under_pressure_losing_rate'], 
                                         short_name, fontsize=font_size, alpha=0.9))
                
                if texts2:
                    adjust_text(texts2, 
                                force_points=0.8,
                                force_text=1.0, 
                                expand_points=(1.3, 1.3), 
                                expand_text=(1.2, 1.2),
                                max_move=4.0,
                                lim=500,
                                only_move={'points': 'xy', 'text': 'xy'},
                                arrowprops=dict(arrowstyle='-', color='gray', lw=0.5, alpha=0.6))

                xlabel2 = ax2.set_xlabel('Pass Accuracy Under Pressure (%)', fontsize=15)
                ylabel2 = ax2.set_ylabel('Possession Losing Rate Under Pressure (%)', fontsize=15)
                xlabel2.set_path_effects(faux_bold)
                ylabel2.set_path_effects(faux_bold)
                
                # Make the plot background look good
                ax2.grid(True, linestyle='--', alpha=0.33)
                ax2.spines['top'].set_visible(False)
                ax2.spines['right'].set_visible(False)
                ax2.spines['left'].set_visible(False)
                ax2.spines['bottom'].set_visible(False)

                ax2.invert_yaxis()

                fig2.text(0.45, 1, f'Efficiency Under Pressure', ha='center', va='center', fontproperties=fm.FontProperties(fname=boldonse_path, size=20))
                fig2.text(0.45, 0.95, f'{scatter_comp} {positions_label}s with {selected_mins}+ minutes played in {scatter_season} season | Data: Statsbomb | made by: @adnaaan433', ha='center', va='center', fontsize=15)
                
                st.pyplot(fig2)
            else:
                st.info("Not enough data to plot the second scatter visualization.")
            
            if orig_font: plt.rcParams['font.family'] = orig_font

else:
    st.warning("Could not establish connection with metadata framework. Validate API definitions.")