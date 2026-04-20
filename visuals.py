import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import highlight_text
from matplotlib.patches import FancyArrowPatch
from highlight_text import ax_text
import numpy as np

def get_rounded_percentages(sizes):
    if sum(sizes) == 0:
        return [0]*len(sizes)
    exact_pcts = [s / sum(sizes) * 100 for s in sizes]
    int_pcts = [int(p) for p in exact_pcts]
    remainders = [p - i for p, i in zip(exact_pcts, int_pcts)]
    diff = 100 - sum(int_pcts)
    if diff > 0:
        indices = sorted(range(len(sizes)), key=lambda i: remainders[i], reverse=True)
        for i in range(diff):
            int_pcts[indices[i]] += 1
    return int_pcts

COLOR_PASS = '#198754'
COLOR_CARRY = '#e67e22'
COLOR_SUSTAIN = '#0d6efd'
COLOR_LOSS = '#dc3545'

def visualize_passes_carries_pitch_only(df, player_name, player_known_name, team_name, league_name, season_name):
    """
    Plots the pitch layout for passes and carries along with stats visualizations on the right.
    """
    # st.info(f"⚠️ Plotting passes and carries natively using `mplsoccer` mapping for **{player_known_name}**.")
    
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1], wspace=0)
    ax = fig.add_subplot(gs[0])
    ax_stats = fig.add_subplot(gs[1])
    ax_stats.axis('off')

    # Data Preparation
    player_df = df[df['player_name'] == player_name].copy()

    # Passes
    successful_passes = player_df[(player_df['type_name'] == 'Pass') & (player_df['outcome_name'].isna())]
    unsuccessful_passes =  player_df[(player_df['type_name'] == 'Pass') & (player_df['outcome_name'] == 'Incomplete')]
    
    # Carries
    carries = player_df[player_df['type_name'] == 'Carry']

    # Sustain the pressure
    dribbles_won = player_df[(player_df['type_name'] == 'Dribble') & (player_df['outcome_name'] == 'Complete')]
    fouls_won = player_df[(player_df['type_name'] == 'Foul Won')]
    shields = player_df[(player_df['type_name'] == 'Shield')]
    
    # Possession Lost
    dispossessed = player_df[(player_df['type_name'] == 'Dispossessed')]
    miscontrols = player_df[(player_df['type_name'] == 'Miscontrol')]
    dribbles_lost = player_df[(player_df['type_name'] == 'Dribble') & (player_df['outcome_name'] == 'Incomplete')]
    errors = player_df[(player_df['type_name'] == 'Error')]

    # Calculate volumes
    vol_passes = len(successful_passes)
    vol_carries = len(carries)
    vol_sustains = len(dribbles_won) + len(fouls_won) + len(shields)
    vol_loss = len(dispossessed) + len(miscontrols) + len(dribbles_lost) + len(errors) + len(unsuccessful_passes)
    
    total_actions = vol_passes + vol_carries + vol_sustains + vol_loss
    
    # Calculate per90 conversions
    player_mins = 90
    if 'player_season_minutes' in player_df.columns:
        if not pd.isna(player_df['player_season_minutes'].iloc[0]) and player_df['player_season_minutes'].iloc[0] > 0:
            player_mins = player_df['player_season_minutes'].iloc[0]
            
    passes_p90 = (vol_passes / player_mins) * 90
    carries_p90 = (vol_carries / player_mins) * 90
    sustains_p90 = (vol_sustains / player_mins) * 90
    loss_p90 = (vol_loss / player_mins) * 90
    
    # Process Percentages
    pct_passes = vol_passes / total_actions if total_actions > 0 else 0
    pct_carries = vol_carries / total_actions if total_actions > 0 else 0
    pct_sustains = vol_sustains / total_actions if total_actions > 0 else 0
    pct_loss = vol_loss / total_actions if total_actions > 0 else 0

    # Forward/Side/Back Successful Passes Calculation
    # Using visualization axes where Screen X is Statsbomb Y, Screen Y is Statsbomb X
    successful_passes = successful_passes.copy()
    v_x = successful_passes['end_y'] - successful_passes['y']
    v_y = successful_passes['end_x'] - successful_passes['x']
    successful_passes['angle'] = np.degrees(np.arctan2(v_y, v_x))
    
    forward_passes = successful_passes[(successful_passes['angle'] >= 5) & (successful_passes['angle'] <= 175)]
    back_passes = successful_passes[(successful_passes['angle'] <= -5) & (successful_passes['angle'] >= -175)]
    side_passes = successful_passes[
        ((successful_passes['angle'] > -5) & (successful_passes['angle'] < 5)) | 
        (successful_passes['angle'] > 175) | 
        (successful_passes['angle'] < -175)
    ]

    # Forward/Side/Back Unsuccessful Passes Calculation
    unsuccessful_passes = unsuccessful_passes.copy()
    v_x = unsuccessful_passes['end_y'] - unsuccessful_passes['y']
    v_y = unsuccessful_passes['end_x'] - unsuccessful_passes['x']
    unsuccessful_passes['angle'] = np.degrees(np.arctan2(v_y, v_x))
    
    forward_unsuccessful_passes = unsuccessful_passes[(unsuccessful_passes['angle'] >= 5) & (unsuccessful_passes['angle'] <= 175)]
    back_unsuccessful_passes = unsuccessful_passes[(unsuccessful_passes['angle'] <= -5) & (unsuccessful_passes['angle'] >= -175)]
    side_unsuccessful_passes = unsuccessful_passes[
        ((unsuccessful_passes['angle'] > -5) & (unsuccessful_passes['angle'] < 5)) | 
        (unsuccessful_passes['angle'] > 175) | 
        (unsuccessful_passes['angle'] < -175)
    ]

    # Forward/Side/Back Carries Calculation
    carries = carries.copy()
    v_x = carries['end_y'] - carries['y']
    v_y = carries['end_x'] - carries['x']
    carries['angle'] = np.degrees(np.arctan2(v_y, v_x))
    
    forward_carries = carries[(carries['angle'] >= 5) & (carries['angle'] <= 175)]
    back_carries = carries[(carries['angle'] <= -5) & (carries['angle'] >= -175)]
    side_carries = carries[
        ((carries['angle'] > -5) & (carries['angle'] < 5)) | 
        (carries['angle'] > 175) | 
        (carries['angle'] < -175)
    ]

    pitch = VerticalPitch(pitch_type='statsbomb')
    pitch.draw(ax=ax)

    pitch.lines(successful_passes.x, successful_passes.y, successful_passes.end_x, successful_passes.end_y,
            comet=True, transparent=True, color=COLOR_PASS, lw=1, ax=ax, zorder=4)
    pitch.scatter(successful_passes.end_x, successful_passes.end_y, s=10, color='white', edgecolor=COLOR_PASS, ax=ax, zorder=5)
    
    pitch.lines(unsuccessful_passes.x, unsuccessful_passes.y, unsuccessful_passes.end_x, unsuccessful_passes.end_y,
            comet=True, transparent=True, color=COLOR_LOSS, lw=1, ax=ax, zorder=2)
    pitch.scatter(unsuccessful_passes.end_x, unsuccessful_passes.end_y, s=10, color='white', edgecolor=COLOR_LOSS, ax=ax, zorder=3)

    # Carries using FancyArrowPatch for proper dashed lines with arrowheads
    import matplotlib.patches as patches
    for row in carries.itertuples():
        # VerticalPitch (statsbomb) maps x -> y plotting, and y -> 80 - y plotting
        arrow = patches.FancyArrowPatch(
            (row.y, row.x),
            (row.end_y, row.end_x),
            arrowstyle="->",
            color=COLOR_CARRY,
            linestyle='dashed',
            lw=1.5,
            mutation_scale=10,
            zorder=1,
            alpha=0.5,
        )
        ax.add_patch(arrow)
    
    # Title
    total_passes = len(successful_passes) + len(unsuccessful_passes)
    pass_acc = (len(successful_passes) / total_passes * 100) if total_passes > 0 else 0
    # ax.text(40, 123.5, f"Under Pressure Passes: {len(successful_passes)}/{total_passes} ({pass_acc:.1f}% accuracy)", ha='center', va='center')
    # ax.text(40, 127, f"Carries the ball out of pressure: {len(carries)}", color='#e67e22', ha='center', va='center')
    ax_text(40, 125, f"<Successful Pass: {len(successful_passes)}> | <Unsuccessful Pass: {len(unsuccessful_passes)}> | <Carries: {len(carries)}>", 
            highlight_textprops=[{'color': COLOR_PASS}, {'color': COLOR_LOSS}, {'color': COLOR_CARRY}], ha='center', ax=ax)
    
    # Render stats
    
    # Draw Stacked Horizontal Bar Chart directly onto ax_stats
    ax_stats.set_xlim(0, 1)
    ax_stats.set_ylim(0, 1)
    
    names = ["Pass", "Sustain\nPressure", "Carry", "Poss.\nLost"]
    raw_sizes = [vol_passes, vol_sustains, vol_carries, vol_loss]
    raw_colors = [COLOR_PASS, COLOR_SUSTAIN, COLOR_CARRY, COLOR_LOSS]
    
    total_actions = sum(raw_sizes)
    
    ax_stats.text(0, 1, "Under Pressure Activity", ha='left', va='center', fontsize=15, fontweight='bold', transform=ax_stats.transAxes)
    
    if total_actions > 0:
        left = 0.0
        rounded_pcts = get_rounded_percentages(raw_sizes)
        for size, name, color, pct in zip(raw_sizes, names, raw_colors, rounded_pcts):
            if size > 0:
                # Scale the width proportionally across 90% of the axis width
                width_scaled = (size / total_actions) * 0.9
                
                ax_stats.barh(0.95, width_scaled, left=left, color=color, edgecolor='white', height=0.035)
                
                # Plot the stat label slightly below the bar using ax_stats coordinates
                ax_stats.text(left + width_scaled / 2, 0.915, f"{name}\n{pct}%", ha='center', va='top', color=color, fontweight='bold', fontsize=10)
                left += width_scaled
    else:
        ax_stats.text(0.45, 0.7, "No Data", ha='center', va='center', fontweight='bold')

    ax_stats.text(0, 0.775, "Volume of Actions Under Pressure", fontsize=15, fontweight='bold', color='black', transform=ax_stats.transAxes)
    
    def draw_card(ax_obj, text_title, number_val, p90_val, x_pos, y_pos, bg_color):
        # Draw drop shadow
        shadow = patches.Rectangle((x_pos + 0.01, y_pos - 0.01), width=0.42, height=0.15, facecolor='black', edgecolor='none', transform=ax_obj.transAxes, alpha=0.15, zorder=0)
        ax_obj.add_patch(shadow)
        
        # Draw main card cleanly mapped to requested background
        rect = patches.Rectangle((x_pos, y_pos), width=0.42, height=0.15, facecolor=bg_color, edgecolor=bg_color, transform=ax_obj.transAxes, linewidth=1, zorder=1)
        ax_obj.add_patch(rect)
        
        num_str = f"{number_val} ({p90_val:.2f})"
        ax_obj.text(x_pos + 0.025, y_pos + 0.08, num_str, fontsize=20, fontweight='bold', color='white', transform=ax_obj.transAxes, zorder=2)
        ax_obj.text(x_pos + 0.025, y_pos + 0.03, f"{text_title} (per90)", fontsize=10, fontweight='bold', color='white', transform=ax_obj.transAxes, zorder=2)
        
    draw_card(ax_stats, "Passes", vol_passes, passes_p90, 0, 0.6, COLOR_PASS)
    draw_card(ax_stats, "Carries", vol_carries, carries_p90, 0.50, 0.6, COLOR_CARRY)
    draw_card(ax_stats, "Sustains Press", vol_sustains, sustains_p90, 0, 0.425, COLOR_SUSTAIN)
    draw_card(ax_stats, "Possession Lost", vol_loss, loss_p90, 0.50, 0.425, COLOR_LOSS)

    # Pass Breakdown Stacked Bar Chart
    ax_stats.text(0, 0.35, "Passes Breakdown", fontsize=15, fontweight='bold', color='black', transform=ax_stats.transAxes)
    
    vol_fw_pass = len(forward_passes) + len(forward_unsuccessful_passes)
    vol_side_pass = len(side_passes) + len(side_unsuccessful_passes)
    vol_back_pass = len(back_passes) + len(back_unsuccessful_passes)
    
    pass_sizes = [vol_fw_pass, vol_side_pass, vol_back_pass]
    pass_successes = [len(forward_passes), len(side_passes), len(back_passes)]
    pass_names = ["Fwd", "Side", "Back"]
    pass_colors = [COLOR_PASS, COLOR_SUSTAIN, COLOR_LOSS] # Green, Blue, Red
    
    total_passes_brk = sum(pass_sizes)
    if total_passes_brk > 0:
        left_pass = 0.0
        rounded_pass_pcts = get_rounded_percentages(pass_sizes)
        for p_size, p_succ, p_name, p_color, pct_pass in zip(pass_sizes, pass_successes, pass_names, pass_colors, rounded_pass_pcts):
            if p_size > 0:
                p_width_scaled = (p_size / total_passes_brk) * 0.90
                
                ax_stats.barh(0.3, p_width_scaled, left=left_pass, color=p_color, edgecolor='white', height=0.035)
                
                acc_pass = (p_succ / p_size) * 100
                ax_stats.text(left_pass + p_width_scaled / 2, 0.265, f"{p_name}: {pct_pass}%\nAcc: {int(round(acc_pass, 0))}%", ha='center', va='top', color=p_color, fontweight='bold', fontsize=10)
                
                left_pass += p_width_scaled

    # Carries Breakdown Stacked Bar Chart
    ax_stats.text(0, 0.15, "Carries Breakdown", fontsize=15, fontweight='bold', color='black', transform=ax_stats.transAxes)
    
    vol_fw_carry = len(forward_carries)
    vol_side_carry = len(side_carries)
    vol_back_carry = len(back_carries)
    
    carry_sizes = [vol_fw_carry, vol_side_carry, vol_back_carry]
    carry_names = ["Fwd", "Side", "Back"]
    carry_colors = [COLOR_PASS, COLOR_SUSTAIN, COLOR_LOSS] # Green, Blue, Red
    
    total_carries_brk = sum(carry_sizes)
    if total_carries_brk > 0:
        left_carry = 0.0
        rounded_carry_pcts = get_rounded_percentages(carry_sizes)
        for c_size, c_name, c_color, pct_carry in zip(carry_sizes, carry_names, carry_colors, rounded_carry_pcts):
            if c_size > 0:
                c_width_scaled = (c_size / total_carries_brk) * 0.90
                
                ax_stats.barh(0.1, c_width_scaled, left=left_carry, color=c_color, edgecolor='white', height=0.035)
                
                ax_stats.text(left_carry + c_width_scaled / 2, 0.065, f"{c_name}\n{pct_carry}%", ha='center', va='top', color=c_color, fontweight='bold', fontsize=10)
                
                left_carry += c_width_scaled

    # Force the pitch axis visible as well
    ax.axis('off')
    fig.text(0.225, 1, f"{player_known_name}", fontsize=25, fontweight='bold')
    fig.text(0.225, 0.97, f"Actions under pressure, for {team_name}, in {league_name} {season_name} season", fontsize=12)
    fig.text(0.225, 0.94, f"Data: Statsbomb | Made by: @adnaaan433", fontsize=12)

    # PRI Calculation
    retention = ((total_actions - vol_loss) / total_actions) * 100 if total_actions > 0 else 0
    distribution = (len(successful_passes) / total_passes) * 100 if total_passes > 0 else 0
    
    fwd_actions = len(forward_passes) + len(forward_carries)
    total_successful_actions = len(successful_passes) + len(carries) + vol_sustains
    progression = min((fwd_actions / total_successful_actions) * 200, 100) if total_successful_actions > 0 else 0
    
    pri = (0.40 * retention) + (0.30 * distribution) + (0.30 * progression)

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("pri_cmap", ['#dc3545', '#e67e22', '#198754'])
    bg_color = cmap(pri / 100.0)

    bbox_props = dict(boxstyle="round,pad=0.3", facecolor=bg_color, edgecolor="none")

    # fig.text(0.85, 1.02, "PRI Score", fontsize=14, fontweight='bold', color='gray', ha='right', va='center')
    # fig.text(0.85, 0.99, f"{pri:.0f}", fontsize=35, fontweight='bold', color='white', ha='right', va='center', bbox=bbox_props)

    try:
        from urllib.request import urlopen
        from PIL import Image
        from mplsoccer import add_image
        
        csv_path = "teams_name_and_id_Statsbomb_Names.csv"
        if os.path.exists(csv_path):
            df_teams = pd.read_csv(csv_path)
            team_match = df_teams[df_teams['teamName'] == team_name]
            if not team_match.empty:
                ftmb_tid = team_match.iloc[0]['teamId']
                himage_url = f"https://images.fotmob.com/image_resources/logo/teamlogo/{ftmb_tid}.png"
                himage = Image.open(urlopen(himage_url))
                add_image(himage, fig, left=0.125, bottom=0.93, width=0.10, height=0.10)
    except Exception as e:
        pass

    # Render flawlessly in Streamlit 
    st.pyplot(fig)
    
    st.markdown("---")
    st.write("### Detailed Action Breakdowns")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Dribbles Won:** {len(dribbles_won)}")
        st.write(f"**Fouls Won:** {len(fouls_won)}")
        st.write(f"**Shields:** {len(shields)}")
    with col2:
        st.write(f"**Dispossessed:** {len(dispossessed)}")
        st.write(f"**Miscontrols:** {len(miscontrols)}")
        st.write(f"**Dribbles Lost:** {len(dribbles_lost)}")
        st.write(f"**Errors:** {len(errors)}")
