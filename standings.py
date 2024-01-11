import pandas as pd
from espn_api.basketball import League
from datetime import datetime, timedelta
import pytz
import streamlit as st

def highlight_top_four(s):
    return ['background-color: green' if i < 4 else '' for i in range(len(s))]

def main():
    # api connection
    league_id = 1800187247
    year = 2024

    espn_s2 = 'AEC5UWfHuxcu831I73sNZEH4je3W%2FNNxVN4clK3USlazw8tVGSw2qLuTZdyLIKU6HlMpgsz0mZ0OMY%2F2SUwmALZ0YwRQBj41kvt3xawnde4YVncFCxfFz48ZUAORsacFlEvwQlPlbzTp3i%2BmUMALHNhQn5Yn%2Fhah9T5VSERo40psL0U30cbbZfxSoNirW4pueHAcykhIYumCo03uVMlEhObQIaDBBy9Kx2MLOBsGFuHymKx7ndXDPHhB4E1uWur9IGAWmF8GW8zq7NaEgr6DG4Bw'  # Replace with your ESPN_S2 cookie
    swid = '{6E7237F4-5305-42FE-B237-F45305D2FE66}'
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    # manual data import cause rish screwed it all up
    data = {
        "Team": ["Thunderstruck", "White Lightning", "Chef Curry", "Mark Will made it", "TJ's Tall Boys", "Bucksketball", "LameloBawl", "Bum Squad", "Tel Aviv Basketball Club", "Team Srivastava"],
        "Record": ["8-3", "8-3", "8-3", "6-5", "6-5", "5-6", "5-6", "4-7", "3-8", "2-9"]
    }

    df_new = pd.DataFrame(data)

    # start date
    season_start_date = datetime(2023, 10, 24, tzinfo=pytz.timezone('US/Eastern'))

    # current date and time in eastern time (for if I ever automate this script)
    current_date = datetime.now(pytz.timezone('US/Eastern'))

    # number of weeks since the start of the season
    num_weeks = ((current_date - season_start_date).days // 7) + 1

    # dictionary to hold the cumulative points for each team
    cumulative_points = {team.team_name: 0 for team in league.teams}

    # iterate over each week
    for week in range(1, num_weeks + 1):
        # get the boxscores for this week
        boxscores = league.box_scores(week)

        # iterate over each boxscore and update cumulative points
        for boxscore in boxscores:
            cumulative_points[boxscore.home_team.team_name] += boxscore.home_score
            cumulative_points[boxscore.away_team.team_name] += boxscore.away_score


    # initialize a dictionary to hold the cumulative points scored against each team
    cumulative_points_against = {team.team_name: 0 for team in league.teams}

    # iterate over each week
    for week in range(1, num_weeks + 1):
        # fetch the boxscores for this week
        boxscores = league.box_scores(week)

        # iterate over each boxscore and update cumulative points against
        for boxscore in boxscores:
            cumulative_points_against[boxscore.home_team.team_name] += boxscore.away_score
            cumulative_points_against[boxscore.away_team.team_name] += boxscore.home_score

    df_new['PF'] = df_new['Team'].map(cumulative_points)
    df_new['PA'] = df_new['Team'].map(cumulative_points_against)

    # calculate the total weeks from the 'Record' column
    df_new['Total Weeks'] = df_new['Record'].apply(lambda x: sum(map(int, x.split('-'))))

    # calculate average points scored and points against
    df_new['PF/Wk'] = df_new['Team'].map(cumulative_points).div(df_new['Total Weeks'])
    df_new['PA/Wk'] = df_new['Team'].map(cumulative_points_against).div(df_new['Total Weeks'])

    # split 'Record' into 'Wins' and 'Losses' for sorting
    df_new[['Wins', 'Losses']] = df_new['Record'].str.split('-', expand=True).astype(int)

    # sort dataFrame by 'Wins' and then by 'PF'
    df_new.sort_values(by=['Wins', 'PF'], ascending=[False, False], inplace=True)

    # combine 'Wins' and 'Losses' back into 'Record'
    df_new['Record'] = df_new['Wins'].astype(str) + '-' + df_new['Losses'].astype(str)

    # drop the 'Wins' and 'Losses' columns
    df_new.drop(['Wins', 'Losses'], axis=1, inplace=True)
    df_new.index = df_new.index + 1
    df_rounded = df_new.round()


    # streamlit stuff
    styled_df = df_rounded.style.apply(highlight_top_four)
    st.title("White Man Can't Jump Standings")
    st.write("PF and PA include the current week's points")
    st.write("Rish is a bot and fat")
    st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)

if __name__ == "__main__":
    main()